"""Reusable Coolify server profiles, encrypted and independent of transfer roles."""
import copy
import uuid
from pydantic import ValidationError
from .models import Connection
from .coolify import CloneError


def initialize(store):
    if store.get('server-profiles') is not None:
        return
    registry = {'profiles': [], 'source_id': None, 'target_id': None}
    for index, role in enumerate(('source', 'target'), 1):
        config = (store.get('connections') or {}).get(role)
        if config:
            uid = uuid.uuid4().hex
            registry['profiles'].append({'id': uid, 'name': f'Coolify {index}', 'connection': config})
            registry[role + '_id'] = uid
    store.put('server-profiles', registry)


def registry(store):
    return copy.deepcopy(store.get('server-profiles') or {'profiles': [], 'source_id': None, 'target_id': None})


def public_profiles(store):
    data = registry(store)
    return {**{key: data.get(key) for key in ('source_id', 'target_id')}, 'profiles': [
        {'id': p['id'], 'name': p['name'], 'has_token': bool(p['connection'].get('token')),
         'connection': {k: v for k, v in p['connection'].items() if k != 'token'}}
        for p in data['profiles']]}


def validate_pair(configs):
    if configs['source']['url'].casefold() == configs['target']['url'].casefold():
        raise CloneError('Gli URL delle due istanze devono essere diversi')
    a, b = configs['source'], configs['target']
    if (a['ssh_host'].casefold().rstrip('.'), a['ssh_port']) == (b['ssh_host'].casefold().rstrip('.'), b['ssh_port']):
        raise CloneError('Trasmittente e ricevente devono essere server diversi')


def selected_connections(data):
    profiles = {p['id']: p for p in data['profiles']}
    source, target = data.get('source_id'), data.get('target_id')
    if not source or not target:
        return None
    if source == target or source not in profiles or target not in profiles:
        raise CloneError('Selezionare due server salvati diversi')
    configs = {role: copy.deepcopy(profiles[data[role + '_id']]['connection']) for role in ('source', 'target')}
    validate_pair(configs)
    return configs


def persist(store, data):
    configs = selected_connections(data)
    store.put_many({'server-profiles': data, 'connections': configs, 'current-plan': None})


def save_profile(store, body):
    data = registry(store)
    profile = next((p for p in data['profiles'] if p['id'] == body.id), None)
    if body.id and not profile:
        raise CloneError('Server salvato non trovato')
    config = body.connection.model_dump()
    if not config.get('token') and profile:
        config['token'] = profile['connection']['token']
    try:
        config = Connection.model_validate(config).model_dump()
    except ValidationError:
        raise CloneError('Configurazione server non valida: controllare campi e token API') from None
    if profile:
        profile.update(name=body.name.strip(), connection=config)
    else:
        if len(data['profiles']) >= 100:
            raise CloneError('Limite di 100 server salvati raggiunto')
        profile = {'id': uuid.uuid4().hex, 'name': body.name.strip(), 'connection': config}
        data['profiles'].append(profile)
    persist(store, data)
    return profile['id']


def assign_roles(store, source_id, target_id):
    data = registry(store)
    data.update(source_id=source_id, target_id=target_id)
    if not selected_connections(data):
        raise CloneError('Selezionare trasmittente e ricevente')
    persist(store, data)


def save_connections(store, configs):
    validate_pair(configs)
    data = registry(store)
    for index, role in enumerate(('source', 'target'), 1):
        profile = next((p for p in data['profiles'] if p['id'] == data.get(role + '_id')), None)
        if profile:
            profile['connection'] = copy.deepcopy(configs[role])
        else:
            profile = {'id': uuid.uuid4().hex, 'name': f'Coolify {index}', 'connection': copy.deepcopy(configs[role])}
            data['profiles'].append(profile)
            data[role + '_id'] = profile['id']
    persist(store, data)
