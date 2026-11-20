import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .coolify import CloneError, Coolify
from .catalog import expand_database_selection, linked_source_catalog
from .engine import check_database, recover_source, run_clone
from .models import Connections, Execute, Login, PlanOptions
from .planner import build_plan, fingerprint, public_plan
from .ssh import SSH
from .setup_guide import setup_status
from .store import Store

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()
sessions = {}
attempts = {}
auth_lock = threading.Lock()
store = None
ssh_dir = None
master_key = None
admin_hash = None


@asynccontextmanager
async def lifespan(app):
    global store, ssh_dir, master_key, admin_hash
    password = os.environ.get("CLONE_ADMIN_PASSWORD", "")
    key = os.environ.get("CLONE_MASTER_KEY", "")
    if len(password) < 16 or not key:
        raise RuntimeError("Eseguire python tools/setup.py: password >=16 caratteri e chiave master obbligatorie")
    master_key = base64.urlsafe_b64decode(key)
    if len(master_key) != 32:
        raise RuntimeError("Chiave master Fernet non valida")
    admin_hash = hashlib.sha256(password.encode()).digest()
    store = Store(os.environ.get("CLONE_DATA_DIR", ROOT / "data"), key)
    # Fail if another app instance holds the same state. No concurrent migration workers.
    lock_file = open(store.root / "worker.lock", "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0)
            lock_file.write(b"0")
            lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        raise RuntimeError("Un'altra istanza usa già questa directory dati") from None
    store.interrupt_jobs()
    previous_plan = store.get('current-plan')
    if previous_plan and previous_plan.get('version') != VERSION:
        store.put('current-plan', None)
    ssh_dir = os.environ.get("CLONE_SSH_DIR", str(ROOT / "ssh"))
    try:
        yield
    finally:
        lock_file.close()


app = FastAPI(title="Clone Coolify", version=VERSION, lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def headers(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Origine della richiesta non autorizzata"}, status_code=403)
        if int(request.headers.get("content-length", "0") or "0") > 65536:
            return JSONResponse({"detail": "Richiesta troppo grande"}, status_code=413)
    response = await call_next(request)
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    return response


@app.exception_handler(CloneError)
async def clone_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # FastAPI's default echoes input, including API tokens and login passwords.
    return JSONResponse({"detail": "Dati non validi", "fields": [".".join(map(str, e["loc"])) for e in exc.errors()]}, status_code=422)


def authorize(request: Request):
    sid = request.cookies.get("clone_session", "")
    with auth_lock:
        session = sessions.get(hashlib.sha256(sid.encode()).hexdigest())
        now = time.time()
        if not session or now - session["last"] > 1800 or now - session["created"] > 28800:
            raise HTTPException(401, "Accesso richiesto")
        if request.method != "GET" and not hmac.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf"]):
            raise HTTPException(403, "Token CSRF non valido")
        session["last"] = now
        return session


def idle():
    if store.lock.locked():
        raise HTTPException(409, "Un'operazione è già in corso")


@app.get("/health")
def health():
    return {"status": "ok", "product": "clone-coolify", "version": VERSION}


@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    address = request.client.host if request.client else "local"
    with auth_lock:
        now = time.time()
        recent = [t for t in attempts.get(address, []) if now - t < 300]
        if len(recent) >= 10:
            raise HTTPException(429, "Troppi tentativi: riprovare fra cinque minuti")
        if not hmac.compare_digest(hashlib.sha256(body.password.encode()).digest(), admin_hash):
            attempts[address] = recent + [now]
            raise HTTPException(401, "Password non valida")
        attempts.pop(address, None)
        for key, value in list(sessions.items()):
            if now - value["last"] > 1800 or now - value["created"] > 28800:
                sessions.pop(key)
        sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        sessions[hashlib.sha256(sid.encode()).hexdigest()] = {"csrf": csrf, "last": now, "created": now}
    response.set_cookie("clone_session", sid, httponly=True, secure=request.url.scheme == "https",
                        samesite="strict", max_age=28800, path="/")
    return {"csrf": csrf}


@app.get("/api/session")
def session(session=Depends(authorize)):
    return {"csrf": session["csrf"], "version": VERSION}


@app.post("/api/logout")
def logout(request: Request, response: Response, session=Depends(authorize)):
    sid = request.cookies.get("clone_session", "")
    with auth_lock:
        sessions.pop(hashlib.sha256(sid.encode()).hexdigest(), None)
    response.delete_cookie("clone_session")
    return {"ok": True}


@app.get("/api/config")
def read_config(session=Depends(authorize)):
    configs = store.get("connections")
    return {"configured": bool(configs), "connections": {
        role: {k: v for k, v in config.items() if k != "token"} for role, config in (configs or {}).items()},
        "ssh_directory": str(ssh_dir)}


@app.get("/api/setup")
def read_setup(language: str = 'it', session=Depends(authorize)):
    return setup_status(store.get("connections"), ssh_dir, VERSION, language)


@app.post("/api/config")
def save_config(body: Connections, session=Depends(authorize)):
    if not store.lock.acquire(blocking=False):
        raise HTTPException(409, "Un'operazione è già in corso")
    try:
        configs = body.model_dump()
        if configs["source"]["url"] == configs["target"]["url"]:
            raise CloneError("Gli URL delle due istanze devono essere diversi")
        store.put("connections", configs)
        store.put("current-plan", None)
        return {"ok": True}
    finally:
        store.lock.release()


@app.post("/api/resources")
def read_source_resources(session=Depends(authorize)):
    if not store.lock.acquire(blocking=False):
        raise HTTPException(409, "Un'operazione è già in corso")
    api = None
    try:
        configs = store.get("connections")
        if not configs:
            raise CloneError("Configurare prima le connessioni")
        api = Coolify(configs["source"])
        return {"resources": linked_source_catalog(api.inventory(), api)}
    finally:
        if api:
            api.close()
        store.lock.release()


@app.post("/api/plan")
def plan(body: PlanOptions, session=Depends(authorize)):
    if not body.resource_uuids:
        raise CloneError("Selezionare almeno una risorsa da clonare prima dell'analisi")
    if not store.lock.acquire(blocking=False):
        raise HTTPException(409, "Un'operazione è già in corso")
    clients = []
    try:
        configs = store.get("connections")
        if not configs:
            raise CloneError("Configurare prima le due connessioni")
        inventories, probes = {}, {}
        for role in ("source", "target"):
            api = Coolify(configs[role])
            clients.append(api)
            inventories[role] = api.inventory()
            probes[role] = SSH(configs[role], ssh_dir).probe()
        catalog = linked_source_catalog(inventories["source"], clients[0], set(body.resource_uuids))
        selection = expand_database_selection(set(body.resource_uuids), catalog)
        result = build_plan(inventories["source"], inventories["target"], probes["source"], probes["target"],
                            configs, clients[0], body.preserve_domains, selection)
        # Database shape is checked read-only before the plan can be executable.
        for row in result["resources"]:
            if row["group"] == "databases" and not row["blocks"]:
                try:
                    check_database(SSH(configs["source"], ssh_dir), row)
                except CloneError as exc:
                    row["blocks"].append(str(exc))
                    result["blocks"].append(f"{row['name']}: {exc}")
        store.put("current-plan", result)
        return public_plan(result)
    finally:
        for api in clients:
            api.close()
        store.lock.release()


@app.get("/api/plan")
def get_plan(session=Depends(authorize)):
    result = store.get("current-plan")
    return public_plan(result) if result else None


@app.post("/api/execute", status_code=202)
def execute(body: Execute, session=Depends(authorize)):
    if not store.lock.acquire(blocking=False):
        raise HTTPException(409, "Un'operazione è già in corso")
    launched = False
    try:
        plan = store.get("current-plan")
        if not plan or plan["id"] != body.plan_id or plan["blocks"] or time.time() - plan["created"] > 900:
            raise CloneError("Piano assente, bloccato o scaduto; analizzare di nuovo")
        if body.confirmation != "CLONA DESTINAZIONE VUOTA" or not body.downtime_accepted or not body.external_writers_stopped:
            raise CloneError("Confermare fermo sorgente, assenza di scrittori esterni e destinazione vuota")
        configs = store.get("connections")
        if fingerprint(configs) != plan["config_hash"]:
            raise CloneError("Connessioni modificate: rigenerare il piano")
        job_id = uuid.uuid4().hex
        store.put(f"job-config:{job_id}", configs)
        store.put(f"job-plan:{job_id}", plan)
        store.job(job_id, "queued", {"phase": "queued", "progress": 0})
        # Consume the plan before launch: double clicks/replays cannot duplicate work.
        store.put("current-plan", None)
        thread = threading.Thread(target=run_clone,
            args=(store, configs, plan, job_id, ssh_dir, master_key), daemon=True, name="clone-worker")
        thread.start()
        launched = True
        return {"job_id": job_id}
    finally:
        if not launched:
            store.lock.release()


@app.get("/api/jobs")
def jobs(session=Depends(authorize)):
    return {"busy": store.lock.locked(), "jobs": store.jobs()}


@app.get("/api/jobs/{job_id}/events")
def events(job_id: str, session=Depends(authorize)):
    return store.events(job_id)


@app.post("/api/jobs/{job_id}/recover")
def recover(job_id: str, session=Depends(authorize)):
    if not store.lock.acquire(blocking=False):
        raise HTTPException(409, "Attendere la conclusione dell'operazione corrente")
    try:
        recover_source(store, job_id, ssh_dir)
        return {"ok": True}
    finally:
        store.lock.release()


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
