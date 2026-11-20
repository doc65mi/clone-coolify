"""Strict REST adapter: redirects and automatic mutation retries are forbidden."""
import re

import httpx


class CloneError(Exception):
    pass


def resource_id(value):
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise CloneError("Identificatore remoto non valido")
    return value


def volume_name(value):
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", value):
        raise CloneError("Nome volume Docker non valido")
    return value


class Coolify:
    def __init__(self, config, transport=None):
        if config["url"].startswith("http://") and not config.get("allow_http"):
            raise CloneError("API HTTP non cifrata: usare HTTPS o abilitare esplicitamente HTTP sulla rete fidata")
        self.http = httpx.Client(
            base_url=config["url"].rstrip("/") + "/api/v1/",
            headers={"Authorization": "Bearer " + config["token"], "Accept": "application/json"},
            timeout=httpx.Timeout(60, connect=10), verify=True, follow_redirects=False,
            trust_env=False, transport=transport,
        )

    def close(self):
        self.http.close()

    def call(self, method, path, data=None):
        try:
            response = self.http.request(method, path.lstrip("/"), json=data)
        except httpx.HTTPError as exc:
            raise CloneError("Connessione API fallita (rete, TLS o timeout)") from exc
        if not response.is_success:
            # Raw API errors may echo passwords or environment values.
            raise CloneError(f"Coolify: HTTP {response.status_code} su {method} {path.split('?')[0]}")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            if path == "version":
                return response.text.strip().strip('"')
            raise CloneError("Risposta Coolify non JSON") from None

    def listing(self, path):
        data = self.call("GET", path)
        if not isinstance(data, list):
            raise CloneError(f"Formato elenco inatteso: {path}")
        return data

    def inventory(self):
        version = self.call("GET", "version")
        if isinstance(version, dict):
            version = version.get("version", "unknown")
        result = {"version": str(version)}
        for group in ("servers", "projects", "applications", "databases", "services"):
            result[group] = self.listing(group)
        # Individual project responses establish the complete environment -> resource map.
        result["project_details"] = [self.call("GET", f"projects/{resource_id(p['uuid'])}")
                                     for p in result["projects"]]
        return result
