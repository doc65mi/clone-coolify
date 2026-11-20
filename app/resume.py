"""Explicit recovery of the legacy PostgreSQL image-check failure, before any restore.

Only a single PostgreSQL database and stateless applications are eligible.
No generic retry, deletion, source downtime or overwriting a populated database.
"""
import copy
from pathlib import Path

from . import backup
from .coolify import CloneError, Coolify, resource_id
from .engine import (IMAGE_MISMATCH, PG_EMPTY, PG_RESTORE, check_database,
                     check_database_image, exec_container, postgres_version, remap, wait_container)
from .planner import APP_FIELDS, DB_FIELDS, container_matches, fingerprint, infrastructure, server_for
from .git_source import GIT_FIELDS
from .ssh import SSH


def eligible(job, plan):
    if not plan or job['status'] != 'failed':
        return False
    data = job['data']
    rows = plan['resources']
    databases = [r for r in rows if r['group'] == 'databases']
    return (data.get('error') == IMAGE_MISMATCH and data.get('phase') == 'ripristino' and
            data.get('source_recovered') and not data.get('restore_attempted') and
            len(databases) == 1 and databases[0]['kind'] == 'postgresql' and
            all(r['group'] in ('applications', 'databases') and
                (r['group'] == 'databases' or not r['container'].get('Mounts')) for r in rows) and
            set(data.get('mapping', {})) == {r['uuid'] for r in rows} and
            len(data.get('backups', [])) == 1 and data['backups'][0].get('kind') == 'database' and
            data['backups'][0].get('resource') == databases[0]['uuid'])


def validate_target(api, ssh, plan, data):
    """Read-only: exact resource set, stopped containers, original credentials and envs."""
    inventory = api.inventory()
    expected = {(r['group'], data['mapping'][r['uuid']]) for r in plan['resources']}
    actual = {(g, r['uuid']) for g in ('applications', 'databases', 'services') for r in inventory[g]}
    if actual != expected:
        raise CloneError('Risorse destinazione cambiate: recupero bloccato')
    if server_for({'server_uuid': plan['target_server']}, inventory)['uuid'] != plan['target_server']:
        raise CloneError('Identità destinazione cambiata: recupero bloccato')
    allowed = {uid for _, uid in expected}
    allowed_environments = {env['id'] for project in inventory.get('project_details', [])
                            if project['uuid'] in data.get('created_projects', [])
                            for env in project.get('environments', [])}
    for container in ssh.containers():
        if infrastructure(container):
            continue
        if not any(container_matches(container, uid) for uid in allowed) or container.get('State', {}).get('Running'):
            raise CloneError('La destinazione deve contenere solo le copie ferme di questo job')
    for row in plan['resources']:
        uid = resource_id(data['mapping'][row['uuid']])
        current = api.call('GET', f"{row['group']}/{uid}")
        if current.get('environment_id') not in allowed_environments:
            raise CloneError('Progetto destinazione cambiato: recupero bloccato')
        if row['group'] == 'databases':
            if current.get('database_type', 'standalone-postgresql') != 'standalone-postgresql' or current.get('is_public'):
                raise CloneError('Configurazione database destinazione cambiata')
            for field in DB_FIELDS['postgresql'] | {'name', 'image'}:
                if (current.get(field) or None) != (row['detail'].get(field) or None):
                    raise CloneError('Configurazione database destinazione cambiata')
        else:
            if any(container_matches(c, uid) for c in ssh.containers()):
                raise CloneError('Applicazione destinazione già avviata: recupero bloccato')
            # Check the source and environment values copied by this job, never log values.
            for field in APP_FIELDS | GIT_FIELDS | {'docker_registry_image_name'}:
                if row['detail'].get(field) is not None and current.get(field) != row['detail'][field]:
                    raise CloneError('Configurazione applicazione destinazione cambiata')
            expected_env = {(v['key'], bool(v.get('is_preview'))): remap(v['value'], data['mapping'])
                            for v in row['env'] if not v['key'].startswith('COOLIFY_')}
            actual_env = {(v['key'], bool(v.get('is_preview'))): v.get('value')
                          for v in api.listing(f'applications/{uid}/envs') if not v['key'].startswith('COOLIFY_')}
            if expected_env != actual_env:
                raise CloneError('Variabili destinazione cambiate: recupero bloccato')


def resume_restore(store, job, configs, plan, ssh_dir, master_key):
    job_id, data = job['id'], copy.deepcopy(job['data'])
    api = None
    target_ssh = None
    started = False
    outcome = 'failed'
    data.update(phase='verifica_recupero', progress=65)
    data.pop('error', None)
    def save():
        store.job(job_id, 'running', data)
    try:
        if not eligible(job, plan) or fingerprint(configs) != plan['config_hash']:
            raise CloneError('Job non idoneo al recupero automatico')
        save()
        store.event(job_id, 'Verifica del recupero dal backup esistente; sorgente non fermata')
        source_ssh, target_ssh = SSH(configs['source'], ssh_dir), SSH(configs['target'], ssh_dir)
        if (source_ssh.probe()['machine_id'] != plan['source_machine'] or
                target_ssh.probe()['machine_id'] != plan['target_machine']):
            raise CloneError('Identità server cambiata: recupero bloccato')
        row = copy.deepcopy(next(r for r in plan['resources'] if r['group'] == 'databases'))
        matches = [c for c in source_ssh.containers() if c['Id'] == row['container']['Id']]
        if len(matches) != 1 or matches[0].get('Image') != row['container']['Image'] or not matches[0]['State']['Running']:
            raise CloneError('Database sorgente cambiato: recupero bloccato')
        row['postgres_version'] = postgres_version(source_ssh, matches[0])
        artifact = data['backups'][0]
        filename = artifact['file']
        if Path(filename).name != filename or filename != row['uuid'] + '.db.ccb':
            raise CloneError('Percorso backup non valido')
        path = store.root / 'backups' / resource_id(job_id) / filename
        backup.verify_file(path, master_key, artifact)
        api = Coolify(configs['target'])
        validate_target(api, target_ssh, plan, data)
        uid = resource_id(data['mapping'][row['uuid']])
        # Journal intent before start; failures always stop this job's database.
        started = True
        data.update(phase='ripristino', progress=70)
        save()
        api.call('POST', f'databases/{uid}/start')
        container = wait_container(target_ssh, uid)
        check_database_image(row, container, target_ssh)
        check_database(target_ssh, {**row, 'container': container})
        if int(target_ssh.run(exec_container(container['Id'], PG_EMPTY)).decode().strip()) != 0:
            raise CloneError('Il database destinazione contiene dati: nessuna sovrascrittura consentita')
        data['restore_attempted'] = True
        save()
        store.event(job_id, 'Versione PostgreSQL compatibile e destinazione vuota verificate; ripristino del backup conservato')
        backup.restore(target_ssh, exec_container(container['Id'], PG_RESTORE, stdin=True), path, master_key, artifact)
        check_database(target_ssh, {**row, 'container': container})
        data.update(phase='copia_completata', progress=100, resumed_from_backup=True)
        outcome = 'copied'
        store.event(job_id, 'Ripristino completato dal backup originale; destinazione ferma per la verifica finale')
    except Exception as exc:
        data['error'] = str(exc) if isinstance(exc, CloneError) else 'Recupero non riuscito; controllare configurazione e backup'
        store.event(job_id, data['error'])
    finally:
        if started and target_ssh:
            try:
                uid = data['mapping'][next(r['uuid'] for r in plan['resources'] if r['group'] == 'databases')]
                target_ssh.stop([c['Id'] for c in target_ssh.containers() if container_matches(c, uid)])
            except Exception:
                outcome = 'failed'
                data['error'] = 'Arresto destinazione da verificare manualmente'
                store.event(job_id, data['error'])
        if api:
            api.close()
        store.job(job_id, outcome, data)
        store.lock.release()
