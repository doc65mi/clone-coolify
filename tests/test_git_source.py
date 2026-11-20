from app.git_source import application_payload, github_snapshot, import_github
from app.coolify import CloneError
from app.planner import build_plan, public_plan
from test_selection import inputs, SelectedAPI
import pytest


GH = {'id': 2, 'uuid': 'github-source', 'name': 'GitHub', 'app_id': 123, 'installation_id': 456,
      'client_id': 'client', 'client_secret': 'private-secret', 'html_url': 'https://github.com', 'private_key_id': 1}
KEY = {'id': 1, 'uuid': 'git-key', 'name': 'Git', 'private_key': '-----BEGIN PRIVATE KEY-----\nfixture', 'public_key': 'public'}


class GitAPI(SelectedAPI):
    def call(self, method, path):
        result = super().call(method, path)
        if path == 'applications/app-one':
            result.update(git_repository='owner/repo', git_branch='main', build_pack='dockerfile',
                          source_type='App\\Models\\GithubApp', source_id=2,
                          docker_registry_image_name=None, custom_labels='generated-labels',
                          settings={'is_container_label_readonly_enabled': True, 'is_git_lfs_enabled': True})
        return result
    def listing(self, path):
        if path == 'github-apps':
            return [GH.copy()]
        if path == 'security/keys':
            return [KEY.copy()]
        return super().listing(path)


def test_git_plan_accepts_missing_registry_and_generated_labels_without_exposing_secrets():
    plan = build_plan(*inputs(), GitAPI(), resource_uuids=['app-one'])
    assert plan['blocks'] == []
    assert plan['resources'][0]['kind'] == 'github'
    assert 'private-secret' not in str(public_plan(plan))
    assert 'PRIVATE KEY' not in str(public_plan(plan))
    endpoint, payload = application_payload(plan['resources'][0], 'target-github')
    assert endpoint == 'applications/private-github-app'
    assert payload['github_app_uuid'] == 'target-github'
    assert payload['build_pack'] == 'dockerfile'
    assert payload['is_git_lfs_enabled'] is True
    assert payload['is_auto_deploy_enabled'] is False
    assert payload['is_preview_deployments_enabled'] is False
    assert 'custom_labels' not in payload


def test_manual_labels_remain_blocked():
    class Manual(GitAPI):
        def call(self, method, path):
            result = super().call(method, path)
            if path == 'applications/app-one':
                result['settings']['is_container_label_readonly_enabled'] = False
            return result
    plan = build_plan(*inputs(), Manual(), resource_uuids=['app-one'])
    assert any('Etichette proxy manuali' in b for b in plan['blocks'])


def test_unreadable_git_key_blocks_before_copy():
    class Locked(GitAPI):
        def listing(self, path):
            return [{**KEY, 'private_key': '********'}] if path == 'security/keys' else super().listing(path)
    plan = build_plan(*inputs(), Locked(), resource_uuids=['app-one'])
    assert any('Chiave GitHub non leggibile' in b for b in plan['blocks'])


def test_import_journals_each_credential_and_deduplicates_same_integration():
    snapshot = github_snapshot(GitAPI(), {'source_id': 2})
    class Target:
        calls = []
        def listing(self, path):
            return []
        def call(self, method, path, payload):
            self.calls.append((path, payload))
            return {'uuid': 'new-key' if path == 'security/keys' else 'new-github'}
    target, cache, journal, saves = Target(), {}, {}, []
    save = lambda: saves.append(str(journal))
    assert import_github(target, snapshot, cache, journal, save) == 'new-github'
    assert import_github(target, snapshot, cache, journal, save) == 'new-github'
    assert len(target.calls) == 2 and len(saves) == 2
    assert target.calls[1][1]['private_key_uuid'] == 'new-key'
    assert journal == {'created_git_keys': ['new-key'], 'created_github_apps': ['new-github']}


@pytest.mark.parametrize('metadata', [{'database_type': 'standalone-postgresql'}, {'type': 'postgresql'}, {}])
def test_postgres_engine_recognized_from_api_model_or_postgres_fields(metadata):
    args = list(inputs())
    args[2]['containers'].append({'Id': 'db-container', 'Name': '/database-resource',
        'State': {'Running': True}, 'Mounts': [{'Type': 'volume', 'Name': 'db', 'Destination': '/var/lib/postgresql'}]})
    class DatabaseAPI:
        def call(self, method, path):
            return {**metadata, 'environment_id': 1, 'postgres_user': 'postgres',
                    'postgres_password': 'secret', 'postgres_db': 'app'}
        def listing(self, path):
            return []
    plan = build_plan(*args, DatabaseAPI(), resource_uuids=['database-resource'])
    assert plan['blocks'] == []
    assert plan['resources'][0]['kind'] == 'postgresql'
