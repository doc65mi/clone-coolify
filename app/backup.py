"""Stream remote output into authenticated, encrypted backups; no plaintext temporary files."""
import hashlib
import os
import struct
import subprocess
import threading

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .coolify import CloneError

MAGIC = b"CCBACKUP2\n"
CHUNK = 1024 * 1024


def derive(master_key, salt):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"clone-coolify-backup-v2").derive(master_key)


def write_encrypted(stream, output, master_key):
    salt = os.urandom(32)
    cipher = AESGCM(derive(master_key, salt))
    output.write(MAGIC + salt)
    digest = hashlib.sha256()
    total, index = 0, 0
    while True:
        block = stream.read(CHUNK)
        encrypted = cipher.encrypt(index.to_bytes(12, "big"), block, MAGIC)
        output.write(struct.pack(">I", len(encrypted)) + encrypted)
        digest.update(block)
        total += len(block)
        index += 1
        if not block:
            break
    return {"bytes": total, "sha256": digest.hexdigest()}


def read_encrypted(stream, master_key):
    if stream.read(len(MAGIC)) != MAGIC:
        raise CloneError("Formato backup non valido")
    salt = stream.read(32)
    if len(salt) != 32:
        raise CloneError("Backup troncato")
    cipher = AESGCM(derive(master_key, salt))
    index = 0
    while True:
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise CloneError("Backup incompleto: marcatore finale assente")
        size = struct.unpack(">I", size_bytes)[0]
        if not 16 <= size <= CHUNK + 16:
            raise CloneError("Blocco backup non valido")
        encrypted = stream.read(size)
        if len(encrypted) != size:
            raise CloneError("Backup troncato")
        try:
            block = cipher.decrypt(index.to_bytes(12, "big"), encrypted, MAGIC)
        except Exception as exc:
            raise CloneError("Integrità o chiave del backup non valida") from exc
        index += 1
        if not block:
            if stream.read(1):
                raise CloneError("Dati inattesi dopo la fine del backup")
            return
        yield block


def verify_file(path, key, expected):
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as stream:
        for block in read_encrypted(stream, key):
            digest.update(block)
            size += len(block)
    if size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        raise CloneError("Checksum del backup non corrispondente")


def _deadline(process, seconds):
    timer = threading.Timer(seconds, process.kill)
    timer.daemon = True
    timer.start()
    return timer


def capture(ssh, args, path, key):
    process = subprocess.Popen(ssh.argv(ssh.command(args)), stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    timer = _deadline(process, 4 * 3600)
    temporary = path.with_suffix(".partial")
    try:
        with open(temporary, "xb") as stream:
            os.chmod(temporary, 0o600)
            metadata = write_encrypted(process.stdout, stream, key)
            stream.flush()
            os.fsync(stream.fileno())
        if process.wait(timeout=30):
            raise CloneError("Backup remoto fallito; il file parziale non verrà ripristinato")
        if not metadata["bytes"]:
            raise CloneError("Backup vuoto")
        temporary.replace(path)
        verify_file(path, key, metadata)
        return metadata
    finally:
        timer.cancel()
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait()


def restore(ssh, args, path, key, metadata):
    # Authenticate the ENTIRE artifact before the first destination write.
    verify_file(path, key, metadata)
    process = subprocess.Popen(ssh.argv(ssh.command(args)), stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timer = _deadline(process, 4 * 3600)
    try:
        with open(path, "rb") as stream:
            for block in read_encrypted(stream, key):
                process.stdin.write(block)
        process.stdin.close()
        if process.wait(timeout=60):
            raise CloneError("Ripristino remoto fallito; destinazione mantenuta ferma")
    except (BrokenPipeError, subprocess.TimeoutExpired) as exc:
        raise CloneError("Ripristino SSH interrotto") from exc
    finally:
        timer.cancel()
        if not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.kill()
        process.wait()
