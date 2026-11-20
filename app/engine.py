import base64
import json
import re
import time
from pathlib import Path

from . import backup
from .coolify import CloneError, Coolify, resource_id, volume_name
from .planner import APP_FIELDS, DB_COMMON, DB_FIELDS, assert_empty, container_matches, fingerprint, configuration_fingerprint
from .ssh import SSH
from .git_source import application_payload, github_snapshot, import_github


# Paths are obtained from Docker itself, never from a request. Only local volumes are handled.
VOLUME_ARCHIVE = """
import json, os, subprocess, sys
name = sys.argv[1]
info = json.loads(subprocess.check_output(['docker','volume','inspect',name]))[0]
assert info['Driver'] == 'local' and not info.get('Options'), 'Non-local volume'
path = os.path.realpath(info['Mountpoint'])
assert os.path.isdir(path) and path not in ('/', '/data', '/var'), 'Invalid volume path'
os.execvp('tar', ['tar','--numeric-owner','--acls','--xattrs','-czpf','-','-C',path,'.'])
"""
VOLUME_RESTORE = """
import json, os, subprocess, sys
name, job = sys.argv[1:3]
info = json.loads(subprocess.check_output(['docker','volume','inspect',name]))[0]
assert info['Driver'] == 'local' and not info.get('Options'), 'Non-local volume'
assert (info.get('Labels') or {}).get('clone-coolify.job') == job, 'Volume not owned by this job'
path = os.path.realpath(info['Mountpoint'])
assert os.path.isdir(path) and not os.listdir(path), 'Refusing nonempty volume'
# Archive comes exclusively from a verified backup of the operator-owned source volume.
os.execvp('tar',['tar','--numeric-owner','--acls','--xattrs','-xzpf','-','-C',path])
"""

PG_DUMP = 'exec pg_dump -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -Fc'
PG_RESTORE = 'exec pg_restore --clean --if-exists --exit-on-error --no-owner -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}"'
PG_CHECK = '''psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -c "SELECT json_build_object('databases',(SELECT json_agg(datname) FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres'),'roles',(SELECT json_agg(rolname) FROM pg_roles WHERE rolname NOT LIKE 'pg_%'))"'''
PG_DEFAULT_CHECK = '''psql -X -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%') + (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema')) + (SELECT count(*) FROM pg_extension WHERE extname <> 'plpgsql')"'''
MYSQL_DUMP = '''export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-$MARIADB_ROOT_PASSWORD}"; tool=$(command -v mariadb-dump || command -v mysqldump); exec "$tool" -uroot --single-transaction --routines --triggers --events --hex-blob --databases "${MYSQL_DATABASE:-$MARIADB_DATABASE}"'''
MYSQL_RESTORE = '''export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-$MARIADB_ROOT_PASSWORD}"; tool=$(command -v mariadb || command -v mysql); exec "$tool" -uroot'''
MYSQL_CHECK = '''export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-$MARIADB_ROOT_PASSWORD}"; tool=$(command -v mariadb || command -v mysql); "$tool" -uroot -N -B -e "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ('information_schema','performance_schema','mysql','sys'); SELECT CONCAT('USER:',User) FROM mysql.user WHERE User NOT IN ('root','mysql.sys','mysql.session','mysql.infoschema','mariadb.sys'); SELECT CONCAT('ENGINE:',ENGINE) FROM information_schema.TABLES WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema','mysql','sys') AND TABLE_TYPE='BASE TABLE' AND ENGINE <> 'InnoDB';"'''


def exec_container(cid, command, stdin=False):
    return ["docker", "exec", *( ["-i"] if stdin else []), resource_id(cid), "sh", "-ec", command]


def check_database(ssh, row):
    cid = row["container"]["Id"]
    detail, kind = row["detail"], row["kind"]
    if kind == "postgresql":
        result = json.loads(ssh.run(exec_container(cid, PG_CHECK)).decode().strip())
        expected_db = detail["postgres_db"]
        if set(result.get("databases") or []) - {expected_db}:
            raise CloneError("Cluster PostgreSQL con più database: copia completa non supportata da questo adattatore")
        if set(result.get("roles") or []) - {detail["postgres_user"]}:
            raise CloneError("Ruoli PostgreSQL aggiuntivi: adattatore dedicato richiesto")
        if expected_db != "postgres" and int(ssh.run(exec_container(cid, PG_DEFAULT_CHECK)).decode().strip()) != 0:
            raise CloneError("Il database postgres contiene dati aggiuntivi: non verranno ignorati")
    else:
        lines = ssh.run(exec_container(cid, MYSQL_CHECK)).decode().splitlines()
        expected_db = detail[kind + "_database"]
        allowed_user = detail.get(kind + "_user")
        for line in lines:
            if line.startswith("ENGINE:"):
                raise CloneError("Tabelle non InnoDB: backup transazionale non sufficiente")
            if line.startswith("USER:"):
                if line[5:] != allowed_user:
                    raise CloneError("Utenti MySQL/MariaDB aggiuntivi: adattatore dedicato richiesto")
            elif line != expected_db:
                raise CloneError("Istanza MySQL/MariaDB con più database: adattatore dedicato richiesto")


def remap(value, mapping):
    if isinstance(value, str):
        for old, new in sorted(mapping.items(), key=lambda pair: -len(pair[0])):
            value = value.replace(old, new)
    return value


def wait_container(ssh, uid, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = [c for c in ssh.containers() if container_matches(c, uid)]
        if len(matches) == 1:
            c = matches[0]
            state = c.get("State", {})
            health = state.get("Health", {}).get("Status")
            if state.get("Running") and health in (None, "healthy"):
                return c
            if health == "unhealthy" or state.get("Status") == "dead":
                raise CloneError("Container destinazione non sano")
        time.sleep(2)
    raise CloneError("Timeout di avvio della risorsa destinazione")


def restart_source(ssh, data, plan):
    ssh.start(data["stopped_source"])
    for row in plan["resources"]:
        if row["container"]["Id"] in data["stopped_source"]:
            wait_container(ssh, row["uuid"])
    data["source_recovered"] = True


def run_clone(store, configs, plan, job_id, ssh_dir, master_key):
    data = {"plan_id": plan["id"], "phase": "preflight", "mapping": {}, "created_projects": [],
            "stopped_source": [], "target_containers": [], "backups": [], "volumes": [], "progress": 0,
            "source_recovered": False}
    source = target = None
    src_ssh = dst_ssh = None
    outcome = "failed"

    def save():
        store.job(job_id, "running", data)

    def event(message):
        store.event(job_id, message)

    def phase(value, progress):
        data.update(phase=value, progress=progress)
        save()

    try:
        source, target = Coolify(configs["source"]), Coolify(configs["target"])
        src_ssh, dst_ssh = SSH(configs["source"], ssh_dir), SSH(configs["target"], ssh_dir)
        if fingerprint(configs) != plan["config_hash"] or time.time() - plan["created"] > 900 or plan["blocks"]:
            raise CloneError("Piano bloccato, modificato o scaduto: ripetere l'analisi")
        event("Controlli aggiornati di identità, destinazione vuota e risorse sorgente")
        source_probe, target_probe = src_ssh.probe(), dst_ssh.probe()
        if source_probe["machine_id"] != plan["source_machine"] or target_probe["machine_id"] != plan["target_machine"]:
            raise CloneError("Identità SSH cambiata dopo il piano")
        assert_empty(target.inventory(), target_probe)
        # Revalidate all source configuration immediately before the first mutation.
        now_inventory = source.inventory()
        expected = {(r["group"], r["uuid"]) for r in plan["resources"]}
        selected_ids = set(plan.get("selected_uuids", [r["uuid"] for r in plan["resources"]]))
        current = {(g, r["uuid"]) for g in ("applications", "databases", "services") for r in now_inventory[g] if r["uuid"] in selected_ids}
        if current != expected:
            raise CloneError("Inventario cambiato dopo il piano")
        for row in plan["resources"]:
            current_detail = source.call("GET", f"{row['group']}/{row['uuid']}")
            if configuration_fingerprint(current_detail) != configuration_fingerprint(row["detail"]):
                raise CloneError("Configurazione sorgente cambiata dopo il piano")
            if row["group"] == "applications":
                if row.get('git_source') and fingerprint(github_snapshot(source, current_detail)) != fingerprint(row['git_source']):
                    raise CloneError('Credenziali GitHub cambiate dopo il piano')
                current_env = source.listing(f"applications/{row['uuid']}/envs")
                if configuration_fingerprint(current_env) != configuration_fingerprint(row["env"]):
                    raise CloneError("Variabili sorgente cambiate dopo il piano")
            else:
                check_database(src_ssh, row)
            container = next((c for c in source_probe["containers"] if c["Id"] == row["container"]["Id"]), None)
            if not container or not container.get("State", {}).get("Running"):
                raise CloneError("Container sorgente cambiato o fermo dopo il piano")
            if row["group"] == "applications":
                names = {m.get("Name") for m in container.get("Mounts", []) if m.get("Type") == "volume"}
                if any(not any(container_matches(c, uid) for uid in selected_ids) and
                       any(m.get("Type") == "volume" and m.get("Name") in names for m in c.get("Mounts", []))
                       for c in source_probe["containers"]):
                    raise CloneError("Un volume selezionato è ora condiviso con un container escluso: rigenerare il piano")
        # Remote utilities are required before any source downtime.
        for ssh in (src_ssh, dst_ssh):
            ssh.run(["python3", "-c", "import sys; assert sys.version_info >= (3,8)"])
            ssh.run(["tar", "--version"])
        backup_dir = store.root / "backups" / job_id
        backup_dir.mkdir(parents=True, exist_ok=False)
        phase("creazione", 10)
        locations = {}
        github_cache = {}
        for row in plan["resources"]:
            location = row["location"]
            old_project = location["project"]
            if old_project not in locations:
                result = target.call("POST", "projects", {"name": location["project_name"],
                    "description": f"Clone {job_id}"})
                new_project = resource_id(result["uuid"])
                locations[old_project] = {"uuid": new_project, "envs": {}}
                data["created_projects"].append(new_project)
                save()
            project = locations[old_project]
            env_name = location["environment"]
            if env_name not in project["envs"]:
                detail = target.call("GET", f"projects/{project['uuid']}")
                env = next((e for e in detail.get("environments", []) if e.get("name") == env_name), None)
                if env is None:
                    env = target.call("POST", f"projects/{project['uuid']}/environments", {"name": env_name})
                project["envs"][env_name] = resource_id(env["uuid"])
            detail = row["detail"]
            fields = APP_FIELDS if row["group"] == "applications" else DB_COMMON | DB_FIELDS[row["kind"]]
            payload = {k: v for k, v in detail.items() if k in fields and v is not None}
            payload.update(project_uuid=project["uuid"], environment_uuid=project["envs"][env_name],
                           server_uuid=plan["target_server"], instant_deploy=False)
            if row["group"] == "applications":
                gh_uuid = import_github(target, row['git_source'], github_cache, data, save) if row.get('git_source') else None
                endpoint, app_payload = application_payload(row, gh_uuid)
                payload.update(app_payload)
                payload.update(domains=detail.get("fqdn") if plan["preserve_domains"] else None,
                               autogenerate_domain=False)
            else:
                payload["is_public"] = False
                endpoint = f"databases/{row['kind']}"
            result = target.call("POST", endpoint, payload)
            new_uid = resource_id(result["uuid"])
            data["mapping"][row["uuid"]] = new_uid
            # Persist after EVERY mutation; failed jobs are never retried implicitly.
            save()
            event(f"Creata risorsa {row['group']}: {row['uuid']} → {new_uid}")

        # Variables are mapped only after all new UUIDs exist.
        for row in plan["resources"]:
            if row["group"] != "applications":
                continue
            new_uid = data["mapping"][row["uuid"]]
            variables = []
            for v in row["env"]:
                if v["key"].startswith("COOLIFY_"):
                    continue
                variables.append({**{k: v[k] for k in ("key", "is_literal", "is_multiline", "is_preview", "is_runtime", "is_buildtime") if k in v},
                                  "value": remap(v["value"], data["mapping"])})
            if variables:
                target.call("PATCH", f"applications/{new_uid}/envs/bulk", {"data": variables})
            for storage in row["storages"]:
                target.call("POST", f"applications/{new_uid}/storages", {
                    "type": "persistent", "name": remap(storage["name"], data["mapping"]),
                    "mount_path": storage["mount_path"]})

        phase("fermo_sorgente", 25)
        # Journal intent BEFORE stop: recovery is safe even if the process dies during SSH.
        data["stopped_source"] = [r["container"]["Id"] for r in plan["resources"] if r["group"] == "applications"]
        save()
        event("Sospensione delle applicazioni sorgente; database disponibili per il dump")
        src_ssh.stop(data["stopped_source"])
        if any(c.get("State", {}).get("Running") for c in src_ssh.containers() if c["Id"] in data["stopped_source"]):
            raise CloneError("Una applicazione sorgente è ripartita durante il fermo")

        phase("backup", 35)
        for index, row in enumerate(plan["resources"]):
            if row["group"] == "databases":
                command = PG_DUMP if row["kind"] == "postgresql" else MYSQL_DUMP
                path = backup_dir / f"{row['uuid']}.db.ccb"
                metadata = backup.capture(src_ssh, exec_container(row["container"]["Id"], command), path, master_key)
                data["backups"].append({"resource": row["uuid"], "kind": "database", "file": path.name, **metadata})
                save()
            else:
                for mount_index, mount in enumerate(row["container"].get("Mounts", [])):
                    volume = volume_name(mount["Name"])
                    path = backup_dir / f"{row['uuid']}.{mount_index}.volume.ccb"
                    metadata = backup.capture(src_ssh, ["python3", "-c", VOLUME_ARCHIVE, volume], path, master_key)
                    data["backups"].append({"resource": row["uuid"], "kind": "volume", "source_volume": volume,
                                            "mount": mount["Destination"], "file": path.name, **metadata})
                    save()
            event(f"Backup cifrato verificato: {row['uuid']}")
        # Keep downtime limited to backup acquisition; restoration does not require the source stopped.
        restart_source(src_ssh, data, plan)
        save()
        event("Applicazioni sorgente riavviate; il clone rappresenta l'istante del backup")
        phase("ripristino", 65)
        for row in plan["resources"]:
            new_uid = data["mapping"][row["uuid"]]
            if row["group"] == "databases":
                # New, private databases only. No writes to pre-existing target resources.
                target.call("POST", f"databases/{new_uid}/start")
                container = wait_container(dst_ssh, new_uid)
                data["target_containers"].append(container["Id"])
                save()
                source_image = row["container"]["Image"]
                if container["Image"] != source_image:
                    raise CloneError("L'immagine database è cambiata (tag mobile): fissare la stessa immagine prima della copia")
                artifact = next(a for a in data["backups"] if a["resource"] == row["uuid"] and a["kind"] == "database")
                command = PG_RESTORE if row["kind"] == "postgresql" else MYSQL_RESTORE
                backup.restore(dst_ssh, exec_container(container["Id"], command, stdin=True),
                               backup_dir / artifact["file"], master_key, artifact)
                check_database(dst_ssh, {**row, "container": container})
                dst_ssh.stop([container["Id"]])
            else:
                for artifact in [a for a in data["backups"] if a["resource"] == row["uuid"] and a["kind"] == "volume"]:
                    new_volume = volume_name(remap(artifact["source_volume"], data["mapping"]))
                    # Source volume naming is retained with resource UUID substitution.
                    # A later activation MUST verify the actual container mounts before use.
                    existing = dst_ssh.run(["docker", "volume", "ls", "--format", "{{.Name}}"], timeout=30).decode().splitlines()
                    if new_volume in existing:
                        raise CloneError("Volume destinazione già esistente: nessuna sovrascrittura consentita")
                    dst_ssh.run(["docker", "volume", "create", "--label", f"clone-coolify.job={job_id}", new_volume])
                    data["volumes"].append({"name": new_volume, "resource": new_uid, "mount": artifact["mount"]})
                    save()
                    backup.restore(dst_ssh, ["python3", "-c", VOLUME_RESTORE, new_volume, job_id],
                                   backup_dir / artifact["file"], master_key, artifact)
            event(f"Ripristino completato: {new_uid}")
        phase("copia_completata", 100)
        outcome = "copied"
        event("Copia completata; destinazione ferma. Verificare mount, applicazioni e DNS prima del passaggio del traffico.")
    except Exception as exc:
        message = str(exc) if isinstance(exc, CloneError) else "Errore interno; verificare configurazione e compatibilità (dettagli sensibili omessi)"
        data["error"] = message
        event(message)
    finally:
        if src_ssh and data["stopped_source"] and not data["source_recovered"]:
            try:
                restart_source(src_ssh, data, plan)
                event("Ripristinato l'avvio delle applicazioni sorgente")
            except Exception:
                data["recovery_required"] = True
                event("ATTENZIONE: riavvio sorgente non riuscito. Usare Recupera sorgente o intervenire via SSH.")
        if outcome != "copied" and dst_ssh:
            try:
                # Detect even an unjournaled database start whose API response was lost.
                new_uuids = set(data["mapping"].values())
                ids = [c["Id"] for c in dst_ssh.containers() if any(container_matches(c, uid) for uid in new_uuids)
                       and c.get("State", {}).get("Running")]
                dst_ssh.stop(ids)
            except Exception:
                event("Arresto destinazione da verificare manualmente")
        if source:
            source.close()
        if target:
            target.close()
        store.put(f"job-config:{job_id}", configs)
        store.job(job_id, outcome, data)
        store.lock.release()


def recover_source(store, job_id, ssh_dir):
    job = next((j for j in store.jobs() if j["id"] == job_id), None)
    if not job:
        raise CloneError("Operazione non trovata")
    configs = store.get(f"job-config:{job_id}")
    if not configs:
        raise CloneError("Connessioni originali non disponibili")
    data = job["data"]
    ssh = SSH(configs["source"], ssh_dir)
    plan = store.get(f"job-plan:{job_id}")
    if plan and ssh.probe()["machine_id"] != plan["source_machine"]:
        raise CloneError("Identità sorgente cambiata: recupero automatico bloccato")
    if plan:
        restart_source(ssh, data, plan)
    else:
        ssh.start(data.get("stopped_source", []))
    data["source_recovered"] = True
    data["recovery_required"] = False
    store.job(job_id, job["status"], data)
    store.event(job_id, "Recupero sorgente richiesto dall'operatore: comando di avvio completato")
