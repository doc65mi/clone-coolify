"""Create dedicated local SSH identities without replacing existing private keys."""
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    folder = Path(__file__).resolve().parent.parent / "ssh"
    folder.mkdir(exist_ok=True)
    for role in ("source", "target"):
        path = folder / (role + "_ed25519")
        if path.exists():
            print(role + ": chiave esistente conservata")
            continue
        key = Ed25519PrivateKey.generate()
        with path.open("xb") as stream:
            stream.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
                                          serialization.NoEncryption()))
        os.chmod(path, 0o600)
        path.with_suffix(".pub").write_bytes(
            key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
            + b" clone-coolify-" + role.encode() + b"-20261120\n")
        print(role + ": chiave dedicata creata")


if __name__ == "__main__":
    main()
