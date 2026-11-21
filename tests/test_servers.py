import copy
import pytest
from cryptography.fernet import Fernet
from app import servers
from app.coolify import CloneError
from app.models import SavedServer
from app.store import Store


def config(name):
    return dict(url=f'https://{name}.example',token=f'{name}-private-token',ssh_host=f'{name}.example',
                ssh_port=22,ssh_user='root',ssh_key=f'{name}_ed25519',server_uuid='',sudo=False,allow_http=False)


@pytest.fixture
def setup_profiles(tmp_path):
    store=Store(tmp_path,Fernet.generate_key().decode())
    connections={'source':config('first'),'target':config('second')}
    store.put('connections',connections)
    servers.initialize(store)
    return store,connections,servers.registry(store)


def test_migration_preserves_existing_connections_and_profile_ids(setup_profiles):
    store,connections,registry=setup_profiles
    servers.initialize(store)
    assert servers.registry(store)==registry
    assert store.get('connections')==connections
    assert len(registry['profiles'])==2
    assert servers.selected_connections(registry)==connections


def test_saved_profiles_remain_encrypted_and_public_responses_redact_tokens(setup_profiles):
    store,_,_=setup_profiles
    public=servers.public_profiles(store)
    assert all(p['has_token'] and 'token' not in p['connection'] for p in public['profiles'])
    assert 'first-private-token' not in str(public)
    assert b'first-private-token' not in store.path.read_bytes()


def test_add_third_server_does_not_change_active_roles(setup_profiles):
    store,connections,before=setup_profiles
    uid=servers.save_profile(store,SavedServer(name='Third server',connection=config('third')))
    after=servers.registry(store)
    assert len(after['profiles'])==3
    assert after['source_id']==before['source_id'] and after['target_id']==before['target_id']
    assert any(p['id']==uid for p in after['profiles'])
    assert store.get('connections')==connections


def test_roles_can_be_swapped_and_previous_plan_is_invalidated(setup_profiles):
    store,connections,data=setup_profiles
    store.put('current-plan',{'id':'old-plan'})
    store.put('job-config:completed',connections)
    servers.assign_roles(store,data['target_id'],data['source_id'])
    assert store.get('connections')=={'source':connections['target'],'target':connections['source']}
    assert store.get('current-plan') is None
    assert store.get('job-config:completed')==connections


def test_same_profile_rejected_without_changing_roles_or_plan(setup_profiles):
    store,connections,data=setup_profiles
    store.put('current-plan',{'id':'keep'})
    with pytest.raises(CloneError):
        servers.assign_roles(store,data['source_id'],data['source_id'])
    assert store.get('connections')==connections
    assert servers.registry(store)==data
    assert store.get('current-plan')=={'id':'keep'}


def test_two_profiles_for_same_host_cannot_be_opposite_roles(setup_profiles):
    store,_,data=setup_profiles
    duplicate=config('first');duplicate['url']='https://other-api.example'
    uid=servers.save_profile(store,SavedServer(name='Same SSH host',connection=duplicate))
    with pytest.raises(CloneError,match='diversi'):
        servers.assign_roles(store,data['source_id'],uid)


def test_edit_keeps_stored_token_when_blank_and_updates_active_connection(setup_profiles):
    store,connections,data=setup_profiles
    update=config('first');update.update(token='',ssh_port=2222)
    servers.save_profile(store,SavedServer(id=data['source_id'],name='Renamed',connection=update))
    active=store.get('connections')['source']
    assert active['token']==connections['source']['token']
    assert active['ssh_port']==2222
    assert servers.registry(store)['profiles'][0]['name']=='Renamed'


def test_invalid_active_edit_does_not_partially_write_registry(setup_profiles):
    store,connections,data=setup_profiles
    with pytest.raises(CloneError):
        servers.save_profile(store,SavedServer(id=data['source_id'],name='Invalid edit',connection=config('second')))
    assert servers.registry(store)==data
    assert store.get('connections')==connections


def test_new_server_without_token_is_rejected_and_not_saved(setup_profiles):
    store,_,before=setup_profiles
    missing=config('third');missing['token']=''
    with pytest.raises(CloneError,match='token API'):
        servers.save_profile(store,SavedServer(name='Third',connection=missing))
    assert servers.registry(store)==before


def test_atomic_store_update_does_not_write_partial_values(setup_profiles):
    store,_,before=setup_profiles
    with pytest.raises(TypeError):
        store.put_many({'server-profiles':{'profiles':[]},'bad':object()})
    assert servers.registry(store)==before
