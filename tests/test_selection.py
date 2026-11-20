import copy

import pytest

from app.coolify import CloneError
from app.planner import build_plan, select_resources, source_catalog


class SelectedAPI:
    def __init__(self, env=None, volume=False):
        self.calls = []
        self.env = env or []
        self.volume = volume

    def call(self, method, path):
        self.calls.append(path)
        if path == "applications/app-one":
            return {"uuid": "app-one", "name": "First app", "environment_id": 1,
                    "build_pack": "dockerimage", "docker_registry_image_name": "nginx"}
        if path == "applications/app-one/storages":
            return {"persistent_storages": [{"name": "uploads", "mount_path": "/uploads"}] if self.volume else [], "file_storages": []}
        raise AssertionError("Excluded resource was inspected: " + path)

    def listing(self, path):
        self.calls.append(path)
        assert path == "applications/app-one/envs"
        return self.env


def inputs():
    source = {"version": "4.7.5", "servers": [{"uuid": "src-server"}], "projects": [],
              "project_details": [{"uuid": "project", "name": "Demo", "environments": [{"id": 1, "name": "production"}]}],
              "applications": [{"uuid": "app-one", "name": "First app", "environment_id": 1},
                               {"uuid": "app-two", "name": "Second app"}],
              "databases": [{"uuid": "database-resource", "name": "Main database"}],
              "services": [{"uuid": "unsupported-stack", "name": "Unselected stack"}]}
    target = {"version": "4.7.5", "servers": [{"uuid": "dst-server"}], "projects": [],
              "project_details": [], "applications": [], "databases": [], "services": []}
    src_probe = {"machine_id": "source", "id": "src", "os": "linux", "architecture": "amd64", "swarm": "inactive",
                 "containers": [{"Id": "container-one", "Name": "/app-one", "Config": {"Labels": {}}, "State": {"Running": True}, "Mounts": []},
                                {"Id": "container-two", "Name": "/app-two", "Config": {"Labels": {}}, "State": {"Running": True}, "Mounts": []}]}
    dst_probe = {**src_probe, "machine_id": "target", "id": "dst", "containers": []}
    configs = {"source": {"url": "https://source", "ssh_host": "source"},
               "target": {"url": "https://target", "ssh_host": "target"}}
    return source, target, src_probe, dst_probe, configs


def test_only_selected_app_is_planned_and_unselected_stack_does_not_block():
    api = SelectedAPI()
    plan = build_plan(*inputs(), api, resource_uuids=["app-one"])
    assert not plan["blocks"]
    assert [r["uuid"] for r in plan["resources"]] == ["app-one"]
    assert plan["selected_uuids"] == ["app-one"]
    assert all("app-two" not in path and "database-resource" not in path for path in api.calls)


def test_selected_app_reports_excluded_database_dependency():
    api = SelectedAPI(env=[{"key": "DATABASE_URL", "value": "postgres://user:password@database-resource:5432/db"}])
    plan = build_plan(*inputs(), api, resource_uuids=["app-one"])
    assert any("Dipendenza esclusa" in b and "Main database" in b for b in plan["blocks"])
    assert "password" not in " ".join(plan["blocks"])


def test_volume_shared_with_excluded_container_blocks_copy():
    args = list(inputs())
    mount = {"Type": "volume", "Name": "uploads", "Destination": "/uploads"}
    for container in args[2]["containers"]:
        container["Mounts"] = [mount.copy()]
    plan = build_plan(*args, SelectedAPI(volume=True), resource_uuids=["app-one"])
    assert any("Volume condiviso" in b for b in plan["blocks"])


@pytest.mark.parametrize("selected", [[], ["deleted-app"]])
def test_empty_or_stale_selection_is_rejected(selected):
    with pytest.raises(CloneError):
        select_resources(inputs()[0], selected)


def test_catalog_contains_no_credentials_or_configuration_payloads():
    source = inputs()[0]
    source["applications"][0].update(token="SECRET", docker_compose_raw="PRIVATE-COMPOSE", password="PASSWORD")
    result = source_catalog(source)
    assert len(result) == 4
    assert all("token" not in r and "password" not in r and "docker_compose_raw" not in r for r in result)


def test_selecting_unsupported_stack_blocks_that_selection():
    plan = build_plan(*inputs(), SelectedAPI(), resource_uuids=["unsupported-stack"])
    assert any("Services/Compose" in b for b in plan["blocks"])
    assert [r["uuid"] for r in plan["resources"]] == ["unsupported-stack"]
