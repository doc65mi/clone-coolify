"""GitHub source adapters. Secret snapshots stay inside the encrypted plan."""
from .coolify import CloneError, resource_id

GIT_FIELDS = set('''git_repository git_branch git_commit_sha build_pack base_directory publish_directory
dockerfile dockerfile_location dockerfile_target_build install_command build_command start_command
watch_paths static_image'''.split())
SETTINGS = set('''is_static is_spa is_force_https_enabled is_gzip_enabled is_stripprefix_enabled
is_permanent_redirect_enabled is_git_submodules_enabled is_git_lfs_enabled is_git_shallow_clone_enabled
use_build_secrets disable_build_cache inject_build_args_to_dockerfile include_source_commit_in_build
include_network_hosts_in_build is_env_sorting_enabled redact_all_env_values_in_logs
include_coolify_default_variables is_container_label_escape_enabled is_preserve_repository_enabled
docker_images_to_keep stop_grace_period rolling_update_drain_seconds is_image_scan_enabled'''.split())
GH_FIELDS = set('''name html_url api_url app_id installation_id client_id client_secret
organization custom_user custom_port webhook_secret'''.split())


def github_snapshot(api, detail):
    matches = [g for g in api.listing('github-apps') if g.get('id') == detail.get('source_id')]
    if len(matches) != 1:
        raise CloneError('Integrazione GitHub sorgente non leggibile')
    integration = matches[0]
    keys = [k for k in api.listing('security/keys') if k.get('id') == integration.get('private_key_id')]
    if len(keys) != 1 or not str(keys[0].get('private_key', '')).startswith('-----BEGIN'):
        raise CloneError('Chiave GitHub non leggibile: necessario read:sensitive')
    if any(not integration.get(k) for k in ('app_id', 'installation_id', 'client_id', 'client_secret', 'html_url')):
        raise CloneError('Credenziali GitHub incomplete o mascherate')
    return {'integration': {k: integration[k] for k in GH_FIELDS | {'uuid'} if k in integration},
            'key': {k: keys[0][k] for k in ('uuid', 'name', 'private_key', 'public_key') if k in keys[0]}}


def import_github(target, snapshot, cache, journal, save):
    gh, key = snapshot['integration'], snapshot['key']
    if gh['uuid'] in cache:
        return cache[gh['uuid']]
    # Reuse only credentials with exactly matching identity and secrets; never overwrite.
    keys = target.listing('security/keys')
    matching = next((k for k in keys if k.get('private_key') == key['private_key']), None)
    if matching:
        key_uuid = resource_id(matching['uuid'])
    else:
        key_uuid = resource_id(target.call('POST', 'security/keys', {
            'name': 'Clone GitHub - ' + str(key.get('name') or 'repository'),
            'private_key': key['private_key']})['uuid'])
        journal.setdefault('created_git_keys', []).append(key_uuid)
        save()
    integrations = target.listing('github-apps')
    matching = next((g for g in integrations if
        all(g.get(f) == gh.get(f) for f in ('app_id', 'installation_id', 'client_id', 'client_secret')) and
        any(k.get('id') == g.get('private_key_id') and k.get('uuid') == key_uuid for k in keys)), None)
    if matching:
        uid = resource_id(matching['uuid'])
    else:
        payload = {k: v for k, v in gh.items() if k in GH_FIELDS and v is not None}
        payload['private_key_uuid'] = key_uuid
        uid = resource_id(target.call('POST', 'github-apps', payload)['uuid'])
        journal.setdefault('created_github_apps', []).append(uid)
        save()
    cache[gh['uuid']] = uid
    return uid


def application_payload(row, github_uuid=None):
    detail = row['detail']
    settings = detail.get('settings') or {}
    payload = {k: v for k, v in settings.items() if k in SETTINGS and v is not None}
    payload.update(is_auto_deploy_enabled=False, is_preview_deployments_enabled=False,
                   is_container_label_readonly_enabled=True)
    if row['kind'] == 'github':
        payload.update({k: v for k, v in detail.items() if k in GIT_FIELDS and v is not None})
        payload['github_app_uuid'] = github_uuid
        return 'applications/private-github-app', payload
    payload.update(docker_registry_image_name=detail['docker_registry_image_name'],
                   docker_registry_image_tag=detail.get('docker_registry_image_tag') or 'latest')
    return 'applications/dockerimage', payload
