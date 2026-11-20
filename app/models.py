import ipaddress
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


class Connection(BaseModel):
    url: str
    token: str = Field(min_length=8, max_length=4096)
    server_uuid: str = Field(default="", max_length=100)
    ssh_host: str
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = "root"
    ssh_key: str = "id_ed25519"
    sudo: bool = False
    allow_http: bool = False

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        u = urlsplit(value.strip().rstrip("/"))
        if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError("Indicare un URL HTTP(S) senza credenziali, query o frammenti")
        if u.path not in ("", "/", "/api/v1", "/api/v1/"):
            raise ValueError("Indicare l'URL base di Coolify o /api/v1")
        # Reject malformed ports now, before reaching an HTTP client.
        _ = u.port
        return value.strip().rstrip("/").removesuffix("/api/v1")

    @field_validator("ssh_host")
    @classmethod
    def valid_host(cls, value):
        try:
            ipaddress.ip_address(value)
            return value
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", value):
                raise ValueError("Host SSH non valido")
            return value

    @field_validator("ssh_user", "ssh_key")
    @classmethod
    def simple_name(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}", value) or ".." in value:
            raise ValueError("Nome non valido")
        return value

    @field_validator("server_uuid")
    @classmethod
    def uuid_name(cls, value):
        if value and not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("UUID server non valido")
        return value


class Connections(BaseModel):
    source: Connection
    target: Connection


class Login(BaseModel):
    password: str = Field(max_length=1024)


class Execute(BaseModel):
    plan_id: str
    confirmation: str
    downtime_accepted: bool = False
    external_writers_stopped: bool = False


class PlanOptions(BaseModel):
    # Destination applications remain stopped until explicitly activated.
    preserve_domains: bool = False
    resource_uuids: list[str] = Field(default_factory=list, max_length=1000)

    @field_validator("resource_uuids")
    @classmethod
    def selected_ids(cls, values):
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) for value in values):
            raise ValueError("Identificatore risorsa non valido")
        return sorted(set(values))
