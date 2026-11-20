import copy
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.coolify import CloneError, Coolify
from app.models import Connection
from app.planner import assert_empty, build_plan, public_plan
from app.store import Store


def config(**extra):
    return {"url": "https://source.example", "token": "secret-token", "ssh_host": "source.example", **extra}


def inventory():
    return {"version": "4.7.5", "servers": [{"uuid": "server"}], "projects": [], "project_details": [],
            "applications": [], "databases": [], "services": []}


def probe(machine="source"):
    return {"id": machine, "machine_id": machine, "architecture": "x86_64", "os": "linux",
            "swarm": "inactive", "containers": []}


class NoAPI:
    def call(self, *args):
        raise AssertionError("No resources should require detail calls")


def test_same_server_cannot_clone():
    plan = build_plan(inventory(), inventory(), probe(), probe(), {"source": config(), "target": config()}, NoAPI())
    assert "Sorgente e destinazione coincidono" in plan["blocks"]


def test_target_with_hidden_container_is_not_empty():
    target = probe("target")
    target["containers"] = [{"Name": "/unmanaged-production-database"}]
    with pytest.raises(CloneError):
        assert_empty(inventory(), target)


def test_target_with_api_resource_is_not_empty():
    inv = inventory()
    inv["applications"] = [{"uuid": "existing"}]
    with pytest.raises(CloneError):
        assert_empty(inv, probe("target"))


def test_coolify_proxy_error_pages_helper_is_infrastructure():
    target = probe("target")
    target["containers"] = [{"Name":"/coolify-proxy-error-pages", "Config":{"Image":"busybox:musl"}}]
    assert_empty(inventory(), target)


def test_proxy_error_pages_name_alone_cannot_hide_arbitrary_workload():
    target = probe("target")
    target["containers"] = [{"Name":"/coolify-proxy-error-pages", "Config":{"Image":"postgres:17"}}]
    with pytest.raises(CloneError):
        assert_empty(inventory(), target)


def test_services_block_entire_plan():
    inv = inventory()
    inv["services"] = [{"uuid": "wordpress-stack"}]
    plan = build_plan(inv, inventory(), probe(), probe("target"),
                      {"source": config(), "target": config()}, NoAPI())
    assert any("Services/Compose" in b for b in plan["blocks"])


def test_version_mismatch_blocks():
    dst = inventory()
    dst["version"] = "4.8.0"
    plan = build_plan(inventory(), dst, probe(), probe("target"),
                      {"source": config(), "target": config()}, NoAPI())
    assert any("versioni" in b for b in plan["blocks"])


def test_api_never_follows_redirects_or_exposes_error_secrets():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://attacker.example"},
                              json={"password": "PRIVATE-SECRET"})
    api = Coolify(config(), httpx.MockTransport(handler))
    with pytest.raises(CloneError) as error:
        api.call("POST", "projects", {"name": "test"})
    assert len(calls) == 1
    assert "PRIVATE-SECRET" not in str(error.value)
    api.close()


def test_http_requires_explicit_opt_in():
    with pytest.raises(CloneError):
        Coolify(config(url="http://source.example"))


@pytest.mark.parametrize("field,value", [("ssh_host", "host;reboot"), ("ssh_user", "root --command"),
                                        ("ssh_key", "../key"), ("url", "https://user:pass@host")])
def test_connection_rejects_injection(field, value):
    with pytest.raises(ValidationError):
        Connection(**config(**{field: value}))


def test_persisted_configuration_is_encrypted(tmp_path):
    key = Fernet.generate_key().decode()
    store = Store(tmp_path, key)
    store.put("connections", {"token": "TOP-SECRET-123"})
    assert store.get("connections")["token"] == "TOP-SECRET-123"
    assert b"TOP-SECRET-123" not in store.path.read_bytes()


def test_interrupted_jobs_are_detected_on_restart(tmp_path):
    store = Store(tmp_path, Fernet.generate_key().decode())
    store.job("abc", "running", {"stopped_source": ["id"]})
    store.interrupt_jobs()
    assert store.jobs()[0]["status"] == "interrupted"
    assert store.jobs()[0]["data"]["stopped_source"] == ["id"]


def test_public_plan_excludes_environment_values():
    plan = build_plan(inventory(), inventory(), probe(), probe("target"),
                      {"source": config(), "target": config()}, NoAPI())
    plan["resources"] = [{"uuid": "uid", "name": "App", "group": "applications", "kind": "dockerimage",
        "blocks": [], "container": {"Mounts": []}, "env": [{"value": "SECRET-VALUE"}],
        "detail": {"password": "SECRET-PASSWORD"}}]
    serialized = json.dumps(public_plan(plan))
    assert "SECRET-" not in serialized
