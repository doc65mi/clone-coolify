import copy
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app import resume
from app.coolify import CloneError
from app.engine import IMAGE_MISMATCH, PG_EMPTY, PG_VERSION, check_database_image
from app.planner import fingerprint
from app.store import Store


def records():
    db = dict(uuid='old-db', group='databases', kind='postgresql', env=[],
              detail=dict(name='DB', image='postgres:18-alpine', postgres_user='postgres',
                          postgres_password='secret', postgres_db='postgres'),
              container=dict(Id='source-db', Image='source-image', Mounts=[{'Type':'volume'}]))
    app = dict(uuid='old-app', group='applications', kind='dockerimage', env=[],
               detail={'name':'App'}, container={'Mounts':[]})
    config = {'source':{'role':'source'}, 'target':{'role':'target'}}
    plan = dict(resources=[db, app], config_hash=fingerprint(config), source_machine='source',
                target_machine='target', target_server='server')
    job = dict(id='job', status='failed', data=dict(error=IMAGE_MISMATCH, phase='ripristino',
        source_recovered=True, mapping={'old-db':'new-db','old-app':'new-app'},
        created_projects=['project'], backups=[{'resource':'old-db','kind':'database','file':'old-db.db.ccb'}]))
    return job, config, plan


@pytest.mark.parametrize('version,allowed', [('180007',True),('180006',True),('170007',False),('bad',False)])
def test_postgres_logical_restore_checks_major_not_docker_hash(version, allowed):
    class SSH:
        def run(self, args): return version.encode()
    row = records()[2]['resources'][0] | {'postgres_version':180006}
    if allowed:
        check_database_image(row, {'Id':'target', 'Image':'different-image'}, SSH())
    else:
        with pytest.raises(CloneError):
            check_database_image(row, {'Id':'target', 'Image':'different-image'}, SSH())


def test_recovery_is_limited_to_failure_before_any_restore_and_stateless_apps():
    job, _, plan = records()
    assert resume.eligible(job, plan)
    job['data']['restore_attempted'] = True
    assert not resume.eligible(job, plan)
    job['data'].pop('restore_attempted')
    plan['resources'][1]['container']['Mounts'] = [{'Name':'uploads'}]
    assert not resume.eligible(job, plan)


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    job, configs, plan = records()
    calls = []
    class SSH:
        instances = []
        empty = True
        def __init__(self, config, directory):
            self.role = config['role']; self.started = False; self.instances.append(self)
        def probe(self): return {'machine_id':self.role}
        def containers(self):
            if self.role == 'source':
                return [{'Id':'source-db', 'Image':'source-image', 'State':{'Running':True}}]
            return [{'Id':'target-db', 'Name':'/new-db', 'Image':'new-image', 'State':{'Running':self.started}}]
        def run(self, args):
            if args[-1] == PG_VERSION: return b'180006' if self.role == 'source' else b'180007'
            if args[-1] == PG_EMPTY: return b'0' if self.empty else b'1'
            return b'{"databases":null,"roles":["postgres"]}'
        def stop(self, ids): calls.append(('stop',self.role,ids)); self.started=False
    class API:
        changed = False
        def __init__(self, config): pass
        def close(self): pass
        def inventory(self):
            return {'servers':[{'uuid':'server'}], 'project_details':[{'uuid':'project','environments':[{'id':1}]}], 'applications':[{'uuid':'new-app'}],
                    'databases':[{'uuid':'new-db'}], 'services':[]}
        def call(self, method, path, payload=None):
            calls.append((method,path))
            if method == 'POST':
                next(s for s in SSH.instances if s.role=='target').started=True
                return {}
            row = plan['resources'][0 if path.startswith('databases') else 1]
            return {**row['detail'], 'environment_id':1, 'name':'Changed' if self.changed else row['detail']['name']}
        def listing(self, path): return []
    monkeypatch.setattr(resume, 'SSH', SSH)
    monkeypatch.setattr(resume, 'Coolify', API)
    monkeypatch.setattr(resume.backup, 'verify_file', lambda *args: calls.append(('verify',)))
    monkeypatch.setattr(resume.backup, 'restore', lambda *args: calls.append(('restore',)))
    store = Store(tmp_path, Fernet.generate_key().decode())
    return store, job, configs, plan, calls, SSH, API


def run(fixture):
    store, job, configs, plan, calls, _, _ = fixture
    assert store.lock.acquire(False)
    resume.resume_restore(store, job, configs, plan, Path('ssh'), b'x'*32)
    assert not store.lock.locked()
    return store.jobs()[0]


def test_resume_uses_verified_backup_and_stops_only_destination(recovery):
    result = run(recovery)
    calls = recovery[4]
    assert result['status'] == 'copied'
    assert result['data']['restore_attempted']
    assert result['data']['resumed_from_backup']
    assert calls.index(('verify',)) < calls.index(('POST','databases/new-db/start')) < calls.index(('restore',))
    assert ('stop','target',['target-db']) in calls
    assert not any(c[:2] == ('stop','source') for c in calls)
    assert not any(c[0] in ('PATCH','DELETE') for c in calls)


def test_populated_destination_is_not_overwritten(recovery):
    recovery[5].empty = False
    result = run(recovery)
    assert result['status'] == 'failed'
    assert 'contiene dati' in result['data']['error']
    assert ('restore',) not in recovery[4]
    assert ('stop','target',['target-db']) in recovery[4]


def test_changed_destination_blocks_before_start(recovery):
    recovery[6].changed = True
    assert run(recovery)['status'] == 'failed'
    assert not any(c[0]=='POST' for c in recovery[4])


def test_corrupt_backup_blocks_all_remote_writes(recovery, monkeypatch):
    def invalid(*args): raise CloneError('Backup corrotto')
    monkeypatch.setattr(resume.backup, 'verify_file', invalid)
    assert run(recovery)['status'] == 'failed'
    assert recovery[4] == []
