"""Generate installation secrets once; never replace an existing encryption key."""
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

root = Path(__file__).resolve().parent.parent
path = root / ".env"
if path.exists():
    print("Il file .env esiste già: nessuna chiave modificata.")
else:
    with path.open("x", encoding="utf-8") as stream:
        stream.write("CLONE_ADMIN_PASSWORD=" + secrets.token_urlsafe(30) + "\n")
        stream.write("CLONE_MASTER_KEY=" + Fernet.generate_key().decode() + "\n")
        stream.write("CLONE_PORT=8787\n")
    if os.name != "nt":
        os.chmod(path, 0o600)
    print("Creato .env. Leggi CLONE_ADMIN_PASSWORD per accedere e conserva CLONE_MASTER_KEY in un luogo sicuro.")
(root / "ssh").mkdir(exist_ok=True)
print("Avvio Docker: docker compose up -d --build")
print("Dashboard: http://127.0.0.1:8787")
