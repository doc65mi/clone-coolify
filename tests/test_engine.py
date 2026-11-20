"""Exercise the actual migration worker's journaling and source recovery without touching servers."""
import time

import pytest
from cryptography.fernet import Fernet

from app import engine
from app.coolify import CloneError
from app.planner import fingerprint
from app.store import Store


class FakeSSH:
    instances = []
    fail_dump = False
    def __init__(self, config, directory):
        self.role = config["role"]
        self.stops = []
        self.starts = []
        self.instances.append(self)
    def probe(self):
        return {"machine_id": self.role, "containers": self.containers()}
    def containers(self):
        if self.role == "target":
            return []
        return [{"Id":"source-container", "Name":"/source-app", "Config":{"Labels":{}},
                 "State":{"Running":not self.stops or bool(self.starts)},"Mounts":[]}]
    def run(self, args, **kwargs):
        return b""
    def stop(self, ids):
        self.stops.extend(ids)
    def start(self, ids):
        self.starts.extend(ids)


class FakeAPI:
    calls = []
    detail = {"name":"example", "docker_registry_image_name":"nginx", "environment_id":1}
    fail = False
    def __init__(self, config):
        self.role = config["role"]
    def close(self):
        pass
    def inventory(self):
        return {"applications": [{"uuid":"source-app"}] if self.role == "source" else [],
                "databases":[],"services":[]}
    def listing(self, path):
        return []
    def call(self, method, path, data=None):
        self.calls.append((self.role, method, path, data))
        if self.fail and method == "POST" and path.startswith("applications/"):
            raise CloneError("Creazione fallita")
        if path == "applications/source-app":
            return self.detail.copy()
        if path == "projects" and method == "POST":
            return {"uuid":"new-project"}
        if path == "projects/new-project":
            return {"environments":[{"name":"production","uuid":"new-env"}]}
        if path == "applications/dockerimage":
            return {"uuid":"new-app"}
        return {}


@pytest.fixture
def setup_worker(tmp_path, monkeypatch):
    FakeSSH.instances=[]
    FakeAPI.calls=[]
    FakeAPI.fail=False
    FakeAPI.detail={"name":"example", "docker_registry_image_name":"nginx", "environment_id":1}
    monkeypatch.setattr(engine,"SSH",FakeSSH)
    monkeypatch.setattr(engine,"Coolify",FakeAPI)
    store=Store(tmp_path,Fernet.generate_key().decode())
    configs={"source":{"role":"source"},"target":{"role":"target"}}
    plan={"id":"plan", "created":time.time(),"config_hash":fingerprint(configs),"blocks":[],
          "source_machine":"source","target_machine":"target","target_server":"target-server",
          "preserve_domains":False,"resources":[{"uuid":"source-app","name":"example",
            "group":"applications","kind":"dockerimage","env":[],"storages":[],
            "detail":FakeAPI.detail.copy(),"container":FakeSSH({"role":"source"},None).containers()[0],
            "location":{"project":"old-project","project_name":"Project","environment":"production"}}]}
    FakeSSH.instances=[]
    return store, configs, plan


def run(setup_worker):
    store,configs,plan=setup_worker
    assert store.lock.acquire(False)
    engine.run_clone(store,configs,plan,"job",None,b"x"*32)
    assert not store.lock.locked()
    return store.jobs()[0]


def test_stateless_clone_creates_mapping_but_never_starts_target_app(setup_worker):
    job=run(setup_worker)
    assert job["status"] == "copied"
    assert job["data"]["mapping"] == {"source-app":"new-app"}
    assert job["data"]["source_recovered"] is True
    source=next(s for s in FakeSSH.instances if s.role=="source")
    assert source.stops == ["source-container"]
    assert source.starts == ["source-container"]
    assert not any(path.endswith("/start") for _,_,path,_ in FakeAPI.calls)


def test_failure_during_backup_recovers_source_and_retains_journal(setup_worker, monkeypatch):
    store, configs, plan=setup_worker
    plan["resources"][0]["container"]["Mounts"]=[{"Name":"uploads","Destination":"/uploads"}]
    def broken(*args):
        raise CloneError("Backup interrotto")
    monkeypatch.setattr(engine.backup,"capture",broken)
    job=run(setup_worker)
    assert job["status"]=="failed"
    assert job["data"]["source_recovered"] is True
    assert job["data"]["mapping"]=={"source-app":"new-app"}
    source=next(s for s in FakeSSH.instances if s.role=="source")
    assert source.starts==["source-container"]


def test_changed_configuration_prevents_every_remote_write(setup_worker):
    FakeAPI.detail["name"]="changed-after-plan"
    job=run(setup_worker)
    assert job["status"]=="failed"
    assert not any(method in {"POST","PATCH","DELETE"} for _,method,_,_ in FakeAPI.calls)


def test_coolify_polling_timestamps_do_not_block_clone(setup_worker):
    row = setup_worker[2]['resources'][0]
    row['detail'].update(updated_at='old', destination={'server': {'uuid': 'server', 'updated_at': 'old', 'sentinel_updated_at': 'old'}})
    FakeAPI.detail.update(updated_at='new', destination={'server': {'uuid': 'server', 'updated_at': 'new', 'sentinel_updated_at': 'new'}})
    assert run(setup_worker)['status'] == 'copied'


def test_nested_server_identity_change_still_blocks_every_write(setup_worker):
    setup_worker[2]['resources'][0]['detail']['destination'] = {'server': {'uuid': 'original'}}
    FakeAPI.detail['destination'] = {'server': {'uuid': 'different'}}
    assert run(setup_worker)['status'] == 'failed'
    assert not any(method in {'POST', 'PATCH', 'DELETE'} for _, method, _, _ in FakeAPI.calls)


def test_creation_failure_never_stops_source(setup_worker):
    FakeAPI.fail=True
    job=run(setup_worker)
    assert job["status"]=="failed"
    source=next(s for s in FakeSSH.instances if s.role=="source")
    assert source.stops==[]


def test_git_worker_uses_github_adapter_without_starting_target(setup_worker, monkeypatch):
    snapshot = {'integration': {'uuid': 'old-github'}, 'key': {}}
    row = setup_worker[2]['resources'][0]
    FakeAPI.detail.update(git_repository='owner/repo', git_branch='main', build_pack='dockerfile')
    row.update(kind='github', detail=FakeAPI.detail.copy(), git_source=snapshot)
    monkeypatch.setattr(engine, 'github_snapshot', lambda *args: snapshot)
    imports = []
    monkeypatch.setattr(engine, 'import_github', lambda *args: imports.append(args[1]) or 'new-github')
    original = FakeAPI.call
    def call(self, method, path, data=None):
        if path == 'applications/private-github-app':
            self.calls.append((self.role, method, path, data))
            return {'uuid': 'new-app'}
        return original(self, method, path, data)
    monkeypatch.setattr(FakeAPI, 'call', call)
    job = run(setup_worker)
    assert job['status'] == 'copied'
    assert len(imports) == 1
    payload = next(data for _, _, path, data in FakeAPI.calls if path == 'applications/private-github-app')
    assert payload['git_repository'] == 'owner/repo'
    assert payload['github_app_uuid'] == 'new-github'
    assert payload['instant_deploy'] is False
    assert payload['is_auto_deploy_enabled'] is False
    assert not any(path.endswith('/start') for _, _, path, _ in FakeAPI.calls)


def test_nonselected_workloads_are_not_created_or_stopped(setup_worker, monkeypatch):
    original_inventory = FakeAPI.inventory
    original_containers = FakeSSH.containers
    def inventory_with_extras(self):
        value = original_inventory(self)
        if self.role == "source":
            value["applications"].append({"uuid":"ignored-app"})
            value["services"].append({"uuid":"ignored-stack"})
        return value
    def containers_with_extras(self):
        values = original_containers(self)
        if self.role == "source":
            values.append({"Id":"ignored-container", "Name":"/ignored-app", "State":{"Running":True}, "Config":{"Labels":{}}, "Mounts":[]})
        return values
    monkeypatch.setattr(FakeAPI, "inventory", inventory_with_extras)
    monkeypatch.setattr(FakeSSH, "containers", containers_with_extras)
    setup_worker[2]["selected_uuids"] = ["source-app"]
    job = run(setup_worker)
    assert job["status"] == "copied"
    source = next(s for s in FakeSSH.instances if s.role == "source")
    assert source.stops == ["source-container"]
    assert job["data"]["mapping"] == {"source-app":"new-app"}
