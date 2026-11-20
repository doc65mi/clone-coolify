"""Encrypted configuration/snapshots, durable job journal, single-worker lock."""
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from cryptography.fernet import Fernet


class Store:
    def __init__(self, root, key):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key.encode())
        self.lock = threading.Lock()
        self.path = self.root / "clone.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS secrets (name TEXT PRIMARY KEY, value BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    created REAL NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job TEXT NOT NULL, time REAL NOT NULL, message TEXT NOT NULL);
            """)
        if os.name != "nt":
            os.chmod(self.path, 0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def put(self, name, data):
        blob = self.cipher.encrypt(json.dumps(data).encode())
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO secrets VALUES (?, ?)", (name, blob))

    def get(self, name, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM secrets WHERE name=?", (name,)).fetchone()
        return json.loads(self.cipher.decrypt(row[0])) if row else default

    def job(self, job_id, status, data):
        # Job metadata must never contain credentials, remote responses or environment values.
        with self.connect() as db:
            db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                       "status=excluded.status,data=excluded.data",
                       (job_id, status, time.time(), json.dumps(data)))

    def jobs(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 50").fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]

    def event(self, job_id, message):
        with self.connect() as db:
            db.execute("INSERT INTO events(job,time,message) VALUES (?, ?, ?)",
                       (job_id, time.time(), message))

    def events(self, job_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM events WHERE job=? ORDER BY seq", (job_id,))]

    def interrupt_jobs(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status='interrupted' WHERE status IN ('running','queued')")
