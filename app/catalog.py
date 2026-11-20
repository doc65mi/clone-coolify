"""Discover application/database edges without returning configuration values to the client."""
import re
from collections import Counter
from urllib.parse import urlsplit

from .coolify import CloneError, resource_id
from .planner import source_catalog


def _hostname(value):
    try:
        return (urlsplit(value).hostname or "").lower()
    except ValueError:
        return ""


def _references(value, uid):
    return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(uid) + r"(?![A-Za-z0-9_-])", value))


def _database_aliases(databases):
    aliases = {}
    for db in databases:
        names = {str(db["uuid"]).lower()}
        if db.get("name"):
            names.add(str(db["name"]).lower())
        for key in ("internal_db_url", "internal_db_url_readonly", "external_db_url"):
            host = _hostname(str(db.get(key) or ""))
            if host:
                names.add(host)
        aliases[db["uuid"]] = names
    counts = Counter(name for names in aliases.values() for name in names)
    return {uid: {name for name in names if counts[name] == 1} for uid, names in aliases.items()}


def _variable_hosts(variable, value):
    hosts = set()
    for candidate in re.findall(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'<>]+", value):
        host = _hostname(candidate)
        if host:
            hosts.add(host)
    key = str(variable.get("key") or "").upper()
    if re.search(r"(?:^|_)(?:HOST|HOSTNAME|SERVER)$", key):
        host = _hostname("//" + value.strip())
        if host:
            hosts.add(host)
    return hosts


def linked_source_catalog(inventory, api, selected_application_ids=None):
    rows = source_catalog(inventory)
    databases = inventory["databases"]
    aliases = _database_aliases(databases)
    by_uid = {row["uuid"]: row for row in rows}
    owners = {db["uuid"]: [] for db in databases}
    for row in rows:
        row.update(database_uuids=[], embedded_databases=[], application_uuids=[], dependency_warning="")
        if row["group"] == "databases":
            continue
        if selected_application_ids is not None and row["uuid"] not in selected_application_ids:
            continue
        uid = resource_id(row["uuid"])
        if row["group"] == "services":
            try:
                detail = api.call("GET", f"services/{uid}")
                for index, item in enumerate(detail.get("databases") or []):
                    if item.get("is_removed_from_compose") or item.get("deleted_at"):
                        continue
                    image = str(item.get("image") or "").split("@", 1)[0].rsplit("/", 1)[-1].split(":", 1)[0]
                    row["embedded_databases"].append({
                        "uuid": str(item.get("uuid") or f"internal-{index}"),
                        "name": item.get("human_name") or item.get("name") or "Database interno",
                        "kind": item.get("database_type") or item.get("type") or image or "Database",
                    })
            except CloneError:
                row["dependency_warning"] = "Impossibile verificare i database interni dello stack."
        if not databases:
            continue
        try:
            variables = api.listing(f"{row['group']}/{uid}/envs")
        except CloneError:
            row["dependency_warning"] = "Collegamenti database non verificabili: controllare accesso API e configurazione."
            continue
        linked = set()
        for variable in variables:
            if str(variable.get("key") or "").startswith("COOLIFY_"):
                continue
            value = variable.get("real_value")
            if not isinstance(value, str) or not value:
                value = variable.get("value")
            if (variable.get("is_shown_once") or not isinstance(value, str) or
                    re.fullmatch(r"[•*]{4,}", value) or "{{" in value):
                row["dependency_warning"] = "Alcune variabili non sono leggibili: i collegamenti potrebbero essere incompleti."
                continue
            hosts = _variable_hosts(variable, value)
            for db in databases:
                db_uid = db["uuid"]
                if _references(value, db_uid) or hosts & aliases[db_uid]:
                    linked.add(db_uid)
        row["database_uuids"] = sorted(linked)
        for db_uid in row["database_uuids"]:
            owners[db_uid].append(uid)
    for db_uid, app_uids in owners.items():
        by_uid[db_uid]["application_uuids"] = sorted(app_uids)
    return rows


def expand_database_selection(selected, catalog):
    expanded = set(selected)
    for row in catalog:
        if row["uuid"] in selected and row["group"] != "databases":
            expanded.update(row.get("database_uuids", []))
    return sorted(expanded)
