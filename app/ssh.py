"""SSH uses mounted private keys and a mandatory, operator-verified known_hosts file."""
import json
import os
import shlex
import subprocess
from pathlib import Path

from .coolify import CloneError


class SSH:
    def __init__(self, config, directory):
        self.config = config
        directory = Path(directory).resolve()
        self.key = directory / config["ssh_key"]
        self.known_hosts = directory / "known_hosts"
        if self.key.parent != directory or not self.key.is_file() or not self.known_hosts.is_file():
            raise CloneError("Chiave SSH o known_hosts assente nella cartella ssh")

    def argv(self, command):
        host = self.config["ssh_host"]
        if ":" in host:
            host = f"[{host}]"
        return ["ssh", "-F", os.devnull, "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", f"UserKnownHostsFile={self.known_hosts}", "-o", "ConnectTimeout=15",
                "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
                "-o", "IdentitiesOnly=yes", "-i", str(self.key), "-p", str(self.config["ssh_port"]),
                f"{self.config['ssh_user']}@{host}", command]

    def command(self, args):
        prefix = ["sudo", "-n"] if self.config.get("sudo") else []
        return shlex.join(prefix + args)

    def run(self, args, timeout=120, input_data=None):
        try:
            process = subprocess.run(self.argv(self.command(args)), input=input_data,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CloneError("SSH non disponibile o comando scaduto") from exc
        if process.returncode:
            raise CloneError("Comando SSH fallito: verificare host key, accesso e privilegi (output remoto omesso)")
        return process.stdout

    def probe(self):
        # No writes, no accepting unknown host keys, no Docker socket exposed to this application.
        info = json.loads(self.run(["docker", "info", "--format", "{{json .}}"], timeout=30))
        containers = self.containers()
        return {"id": info.get("ID"), "name": info.get("Name"), "architecture": info.get("Architecture"),
                "os": info.get("OSType"), "swarm": info.get("Swarm", {}).get("LocalNodeState"),
                "containers": containers,
                "machine_id": self.run(["cat", "/etc/machine-id"], timeout=30).decode().strip()}

    def containers(self):
        ids = self.run(["docker", "ps", "-aq"]).decode().split()
        if not ids:
            return []
        return json.loads(self.run(["docker", "inspect", *ids]))

    def stop(self, ids):
        if ids:
            self.run(["docker", "stop", "--time", "60", *ids], timeout=max(180, len(ids) * 70))

    def start(self, ids):
        if ids:
            self.run(["docker", "start", *ids], timeout=max(180, len(ids) * 30))
