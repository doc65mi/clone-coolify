"""A plan is all-or-nothing: unsupported state blocks every remote write."""
import hashlib
import json
import re
import socket
import time
import uuid
from urllib.parse import urlsplit

from .coolify import CloneError, resource_id
from .git_source import github_snapshot

APP_FIELDS = set("""name description ports_exposes ports_mappings
health_check_enabled health_check_path health_check_port health_check_host health_check_method
health_check_return_code health_check_scheme health_check_response_text health_check_interval
health_check_timeout health_check_retries health_check_start_period limits_memory limits_memory_swap
limits_memory_swappiness limits_memory_reservation limits_cpus limits_cpuset limits_cpu_shares
redirect is_force_https_enabled is_gzip_enabled is_stripprefix_enabled is_permanent_redirect_enabled
stop_grace_period rolling_update_drain_seconds docker_images_to_keep max_restart_count""".split())
DB_COMMON = set("name description image limits_memory limits_memory_swap limits_memory_swappiness limits_memory_reservation limits_cpus limits_cpuset limits_cpu_shares".split())
DB_FIELDS = {
    "postgresql": set("postgres_user postgres_password postgres_db postgres_initdb_args postgres_host_auth_method postgres_conf".split()),
    "mysql": set("mysql_root_password mysql_user mysql_password mysql_database mysql_conf".split()),
    "mariadb": set("mariadb_root_password mariadb_user mariadb_password mariadb_database mariadb_conf".split()),
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def configuration_fingerprint(value):
    """Ignore observation timestamps, including nested server heartbeat timestamps.

    Keep every other field, including credentials, image, source and network identity.
    These timestamps change when Coolify polls a resource without editing its config.
    """
    volatile = {'updated_at', 'sentinel_updated_at', 'last_online', 'last_online_at',
                'last_restart_at', 'last_health_check_at'}
    def stable(item):
        if isinstance(item, dict):
            return {key: stable(val) for key, val in item.items() if key not in volatile}
        if isinstance(item, list):
            return [stable(val) for val in item]
        return item
    return fingerprint(stable(value))


def container_matches(container, uid):
    name = container.get("Name", "").lstrip("/")
    labels = container.get("Config", {}).get("Labels") or {}
    return (name == uid or name.startswith(uid + "-") or
            any(str(labels.get(k, "")) == uid for k in
                ("coolify.resource.uuid", "coolify.applicationId", "coolify.databaseId")))


def infrastructure(container):
    # Exact allowlist. Unknown workloads on the target block the plan.
    name = container.get("Name", "").lstrip("/")
    if name == "coolify-proxy-error-pages":
        return container.get("Config", {}).get("Image") in {"busybox:musl", "docker.io/library/busybox:musl"}
    return name in {
        "coolify", "coolify-db", "coolify-redis", "coolify-realtime", "coolify-proxy", "coolify-sentinel"
    }


def server_for(config, inventory):
    servers = inventory["servers"]
    if config.get("server_uuid"):
        matches = [s for s in servers if s.get("uuid") == config["server_uuid"]]
        if len(matches) != 1:
            raise CloneError("UUID server non trovato o non visibile al token")
        return matches[0]
    if len(servers) != 1:
        raise CloneError("L'istanza gestisce più server: specificare l'UUID del server nella connessione")
    return servers[0]


def same_host(first, second):
    if first == second:
        return True
    try:
        a = {r[4][0] for r in socket.getaddrinfo(first, None)}
        b = {r[4][0] for r in socket.getaddrinfo(second, None)}
        return bool(a & b)
    except OSError:
        return False


def environment_map(inventory):
    mapping = {}
    for project in inventory["project_details"]:
        for env in project.get("environments", []):
            mapping[env.get("id")] = {"project": project["uuid"], "project_name": project["name"],
                                      "environment": env.get("name", "production")}
    return mapping


def assert_empty(inventory, probe):
    if any(inventory[g] for g in ("applications", "databases", "services")):
        raise CloneError("La destinazione contiene già risorse Coolify: nessuna scrittura consentita")
    if any(not infrastructure(c) for c in probe["containers"]):
        raise CloneError("La destinazione contiene container estranei a Coolify")


def select_resources(inventory, selected):
    available = {row["uuid"] for group in ("applications", "databases", "services") for row in inventory[group]}
    if selected is None:
        return available
    selected = set(selected)
    if not selected:
        raise CloneError("Selezionare almeno un'applicazione o un database da clonare")
    if selected - available:
        raise CloneError("Una risorsa selezionata non è più disponibile: ricaricare l'elenco")
    return selected


def source_catalog(inventory):
    locations = environment_map(inventory)
    return [{"uuid": row["uuid"], "name": row.get("name") or row["uuid"], "group": group,
             "kind": row.get("database_type") or row.get("type") or row.get("build_pack") or group,
             "project": (locations.get(row.get("environment_id")) or {}).get("project_name", ""),
             "environment": (locations.get(row.get("environment_id")) or {}).get("environment", ""),
             "supported_hint": "Adattatore Compose non disponibile" if group == "services" else "Da verificare nel piano"}
            for group in ("applications", "databases", "services") for row in inventory[group]]


def build_plan(source, target, source_probe, target_probe, configs, source_api, preserve_domains=False, resource_uuids=None):
    blocks, warnings, resources = [], [], []
    selected = select_resources(source, resource_uuids)
    all_ids = {r["uuid"]: r.get("name") or r["uuid"] for g in ("applications", "databases", "services") for r in source[g]}
    if not source_probe.get("machine_id") or not source_probe.get("id") or not target_probe.get("id"):
        blocks.append("Identità dei server non verificabile")
    if (source_probe.get("machine_id") == target_probe.get("machine_id") or
            source_probe.get("id") == target_probe.get("id")):
        blocks.append("Sorgente e destinazione coincidono")
    if source["version"] != target["version"]:
        blocks.append("Le versioni Coolify devono coincidere")
    for probe in (source_probe, target_probe):
        if probe.get("os") != "linux" or probe.get("swarm") not in ("inactive", None):
            blocks.append("Questa release richiede Docker Linux senza Swarm")
    if source_probe.get("architecture") != target_probe.get("architecture"):
        blocks.append("Architetture CPU diverse")
    try:
        assert_empty(target, target_probe)
    except CloneError as exc:
        blocks.append(str(exc))
    src_server = server_for(configs["source"], source)
    dst_server = server_for(configs["target"], target)
    for role, server in (("source", src_server), ("target", dst_server)):
        config = configs[role]
        api_host = urlsplit(config["url"]).hostname
        if not same_host(api_host, config["ssh_host"]):
            blocks.append(f"{role}: API e SSH devono puntare allo stesso host; proxy esterni non supportati in questa release")
        ip = server.get("ip")
        if ip and ip not in ("127.0.0.1", "::1", "localhost", "host.docker.internal") and not same_host(ip, config["ssh_host"]):
            blocks.append(f"{role}: il server gestito da Coolify non coincide con l'host SSH")
    if len(source["servers"]) != 1 or len(target["servers"]) != 1:
        blocks.append("La clonazione completa di istanze con più server gestiti richiede un adattatore dedicato")
    envs = environment_map(source)
    selected_services = [s for s in source["services"] if s["uuid"] in selected]
    if selected_services:
        blocks.append("Stack Services/Compose rilevati: l'adattatore di copia completa non è ancora disponibile")
        resources.extend({"uuid": s["uuid"], "name": s.get("name") or s["uuid"], "group": "services", "kind": "compose",
                          "container": {}, "env": [], "blocks": ["Adattatore Compose non disponibile"]} for s in selected_services)
    covered = set()
    for group in ("databases", "applications"):
        for item in source[group]:
            uid = resource_id(item["uuid"])
            if uid not in selected:
                continue
            detail = source_api.call("GET", f"{group}/{uid}")
            location = envs.get(detail.get("environment_id"))
            row_blocks = []
            if not location:
                row_blocks.append("Progetto/ambiente non ricostruibile dal token")
            containers = [c for c in source_probe["containers"] if container_matches(c, uid)]
            if len(containers) != 1:
                row_blocks.append("Richiesto esattamente un container esistente per risorsa")
            covered.update(c["Id"] for c in containers)
            container = containers[0] if len(containers) == 1 else {}
            if container and not container.get("State", {}).get("Running"):
                row_blocks.append("La risorsa sorgente deve essere avviata per il controllo prima della copia")
            mounts = container.get("Mounts", [])
            env = []
            storages = []
            git_source = None
            if group == "applications":
                kind = "dockerimage"
                if detail.get("build_pack") == "dockercompose" or detail.get("docker_compose_raw"):
                    row_blocks.append("Applicazione Compose: adattatore non disponibile")
                elif detail.get("git_repository"):
                    if str(detail.get("source_type", "")).endswith('GithubApp') and detail.get('build_pack') == 'dockerfile':
                        kind = 'github'
                        try:
                            git_source = github_snapshot(source_api, detail)
                        except CloneError as exc:
                            row_blocks.append(str(exc))
                        warnings.append(f"{detail.get('name') or uid}: saranno importate le credenziali GitHub necessarie; auto deploy e anteprime disattivati sulla copia. Il codice sarà ricostruito da Git al successivo deploy manuale.")
                    else:
                        row_blocks.append("Sorgente Git/build pack: adattatore non disponibile")
                elif detail.get('dockerfile'):
                    row_blocks.append('Dockerfile senza repository: adattatore non disponibile')
                if kind == 'dockerimage' and not detail.get("docker_registry_image_name"):
                    row_blocks.append("Immagine Docker assente o non visibile")
                env = source_api.listing(f"applications/{uid}/envs")
                storage_result = source_api.call("GET", f"applications/{uid}/storages")
                storages = storage_result.get("persistent_storages", [])
                if storage_result.get("file_storages"):
                    row_blocks.append("File mount: copia completa non ancora supportata")
                for variable in env:
                    value = variable.get("value")
                    if isinstance(value, str) and not variable.get("key", "").startswith("COOLIFY_"):
                        for other_id, other_name in all_ids.items():
                            if other_id not in selected and other_id in value:
                                row_blocks.append(f"Dipendenza esclusa dalla selezione: {other_name} ({other_id})")
                    if variable.get("is_shown_once") or variable.get("is_shared") or not isinstance(value, str):
                        row_blocks.append("Variabili bloccate, condivise o non leggibili")
                    elif "{{" in value or "$SERVICE_" in value or re.fullmatch(r"[•*]{4,}", value):
                        row_blocks.append("Variabili con riferimenti non risolti o valori mascherati")
                    elif (not variable.get("key", "").startswith("COOLIFY_") and
                          configs["source"]["ssh_host"] in value):
                        row_blocks.append("Variabile con indirizzo esplicito della sorgente: rimappatura manuale richiesta")
                for m in mounts:
                    if m.get("Type") != "volume":
                        row_blocks.append("Bind mount o tmpfs: impossibile garantire copia completa")
                    elif len([s for s in storages if s.get("mount_path") == m.get("Destination")]) != 1:
                        row_blocks.append("Volume non descritto dagli storage API")
                    else:
                        storage = next(s for s in storages if s.get("mount_path") == m.get("Destination"))
                        if storage.get("name") != m.get("Name"):
                            row_blocks.append("Nome volume effettivo diverso dal nome API: rimappatura non verificabile in questa release")
                if len(storages) != len(mounts):
                    row_blocks.append("Storage API e mount del container non corrispondono")
                for mount in mounts:
                    if mount.get("Type") == "volume" and any(
                        c.get("Id") != container.get("Id") and not any(container_matches(c, sid) for sid in selected) and
                        any(m.get("Type") == "volume" and m.get("Name") == mount.get("Name") for m in c.get("Mounts", []))
                        for c in source_probe["containers"]):
                        row_blocks.append("Volume condiviso con un container non selezionato: includere tutti gli scrittori o separare i dati")
                # Runtime features below cannot be silently dropped by the creation adapter.
                for field in ("custom_docker_run_options", "pre_deployment_command", "post_deployment_command",
                              "custom_internal_name", "custom_container_name_prefix"):
                    if detail.get(field):
                        row_blocks.append(f"Configurazione avanzata da adattare: {field}")
                settings = detail.get("settings") or {}
                if detail.get('custom_labels') and settings.get('is_container_label_readonly_enabled') is not True:
                    row_blocks.append('Etichette proxy manuali: rimappatura dedicata necessaria')
                if settings.get("is_gpu_enabled") or detail.get("is_http_basic_auth_enabled"):
                    row_blocks.append("GPU/autenticazione proxy richiedono un adattatore dedicato")
            else:
                raw_kind = str(detail.get("database_type") or detail.get("type") or item.get("database_type") or item.get("type", "")).lower()
                kind = next((k for k in DB_FIELDS if k in raw_kind), "")
                if not kind:
                    # Some API versions expose the model name instead of `type`.
                    kind = next((k for k in DB_FIELDS if any(f.startswith(('postgres' if k == 'postgresql' else k) + "_") for f in detail)), "")
                if kind not in DB_FIELDS:
                    row_blocks.append("Motore database non ancora supportato (PostgreSQL, MySQL, MariaDB disponibili)")
                else:
                    required = {"postgresql": ["postgres_user", "postgres_password", "postgres_db"],
                                "mysql": ["mysql_root_password", "mysql_database"],
                                "mariadb": ["mariadb_root_password", "mariadb_database"]}[kind]
                    if any(not detail.get(k) for k in required):
                        row_blocks.append("Credenziali o database non leggibili: richiedere token read:sensitive")
                if any(m.get("Type") != "volume" for m in mounts) or len(mounts) != 1:
                    row_blocks.append("Database con mount aggiuntivi: necessaria verifica dedicata")
                if detail.get("is_public"):
                    row_blocks.append("Database pubblico: dipendenze e client esterni da rimappare")
                db_env = source_api.listing(f"databases/{uid}/envs")
                if any(not v.get("key", "").startswith("COOLIFY_") for v in db_env):
                    row_blocks.append("Variabili database aggiuntive: copia completa da adattare")
            row = {"uuid": uid, "name": detail.get("name") or uid, "group": group, "kind": kind,
                   "location": location, "detail": detail, "env": env, "storages": storages,
                   "container": container, "git_source": git_source, "blocks": list(dict.fromkeys(row_blocks))}
            resources.append(row)
            blocks.extend(f"{row['name']}: {b}" for b in row["blocks"])
    unknown = [c for c in source_probe["containers"] if c["Id"] not in covered and not infrastructure(c)]
    if unknown and resource_uuids is None:
        blocks.append("Container esterni o stack non riconosciuti sulla sorgente: impossibile fermare tutti gli scrittori in modo affidabile")
    if not resources:
        blocks.append("Nessuna risorsa clonabile rilevata")
    warnings.extend([
        "Copia con fermo delle applicazioni sorgente; nessun cambio DNS automatico.",
        "La destinazione rimane ferma dopo la copia: l'avvio può duplicare cron, email, webhook e pagamenti.",
        "Creazione database, credenziali, ripristino dati e rimappatura dei collegamenti dell'app sono automatici durante la clonazione.",
        "Utenti Coolify, impostazioni globali, cron, registry, backup pianificati e servizi esterni non sono clonati in questa release.",
        "Serve spazio locale per backup cifrati e sulla destinazione per tutti i volumi.",
    ])
    if resource_uuids is not None:
        warnings.append("Saranno copiate e fermate solo le risorse selezionate. Le altre restano invariate: sospendere eventuali loro scritture verso i database selezionati.")
    if preserve_domains:
        warnings.append("I domini originali saranno registrati sulla destinazione; DNS invariato.")
    return {"id": uuid.uuid4().hex, "created": time.time(), "version": "0.8.0", "selected_uuids": sorted(selected),
            "source_version": source["version"], "target_version": target["version"],
            "source_machine": source_probe["machine_id"], "target_machine": target_probe["machine_id"],
            "source_server": src_server["uuid"], "target_server": dst_server["uuid"],
            "resources": resources, "blocks": list(dict.fromkeys(blocks)), "warnings": warnings,
            "preserve_domains": preserve_domains, "config_hash": fingerprint(configs)}


def public_plan(plan):
    return {k: plan[k] for k in ("id", "created", "version", "source_version", "target_version", "blocks", "warnings")} | {
        "resources": [{k: row[k] for k in ("uuid", "name", "group", "kind", "blocks")} |
                      {"volumes": len(row["container"].get("Mounts", [])), "variables": len(row["env"])}
                      for row in plan["resources"]]}
