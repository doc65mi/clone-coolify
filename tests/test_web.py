import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app import main

PASSWORD = "test-password-at-least-16-chars"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CLONE_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("CLONE_MASTER_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("CLONE_DATA_DIR", str(tmp_path))
    main.sessions.clear()
    main.attempts.clear()
    with TestClient(main.app) as client:
        yield client


def test_login_session_and_csrf(client):
    assert client.get("/api/config").status_code == 401
    response = client.post("/api/login", json={"password": PASSWORD})
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    token = response.json()["csrf"]
    assert client.get("/api/config").status_code == 200
    assert client.post("/api/logout").status_code == 403
    assert client.post("/api/logout", headers={"x-csrf-token": token}).status_code == 200
    assert client.get("/api/config").status_code == 401


def test_validation_never_echoes_secrets(client):
    response = client.post("/api/login", json={"password": {"secret": "NEVER-ECHO-THIS"}})
    assert response.status_code == 422
    assert "NEVER-ECHO-THIS" not in response.text


def test_cross_origin_login_rejected(client):
    assert client.post("/api/login", json={"password": PASSWORD}, headers={"Origin": "https://evil.example"}).status_code == 403


def test_login_rate_limit(client):
    for _ in range(10):
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 429


def test_index_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="it"' in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/health").json()["version"] == "0.8.0"


def test_english_guide_is_authenticated_and_does_not_change_connections(client):
    assert client.get('/api/setup?language=en').status_code == 401
    client.post('/api/login', json={'password': PASSWORD})
    english = client.get('/api/setup?language=en').json()
    italian = client.get('/api/setup?language=it').json()
    assert english['sections'][0]['title'] == 'Choose where to run the app'
    assert italian['sections'][0]['title'] == "Scegli dove eseguire l'app"
    assert english['connections'] == italian['connections']
    assert english['sections'][2]['commands'] == italian['sections'][2]['commands']
    assert client.get('/api/setup?language=unknown').json()['sections'] == italian['sections']


def test_resume_restore_requires_login_csrf_and_exact_confirmation(client):
    url = '/api/jobs/unknown/resume-restore'
    assert client.post(url, json={'confirmation':'RIPRENDI RIPRISTINO'}).status_code == 401
    csrf = client.post('/api/login', json={'password':PASSWORD}).json()['csrf']
    assert client.post(url, json={'confirmation':'RIPRENDI RIPRISTINO'}).status_code == 403
    response = client.post(url, headers={'x-csrf-token':csrf}, json={'confirmation':'RIPRENDI RIPRISTINO', 'snapshot_accepted':False})
    assert response.status_code == 400
    assert not client.get('/api/jobs').json()['busy']


def test_plan_requires_explicit_selection_before_any_server_connection(client):
    token = client.post("/api/login", json={"password": PASSWORD}).json()["csrf"]
    response = client.post("/api/plan", headers={"x-csrf-token": token}, json={"resource_uuids": []})
    assert response.status_code == 400
    assert "Selezionare" in response.json()["detail"]


def test_catalog_requires_login_and_csrf(client):
    assert client.post("/api/resources").status_code == 401
    client.post("/api/login", json={"password": PASSWORD})
    assert client.post("/api/resources").status_code == 403


def test_setup_requires_authentication(client):
    assert client.get("/api/setup").status_code == 401


def test_setup_available_without_connections_and_does_not_read_keys(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ssh_dir", str(tmp_path))
    (tmp_path / "source_ed25519").write_text("SECRET-PRIVATE-KEY")
    (tmp_path / "known_hosts").write_text("SECRET-HOST-KEY-CONTENT")
    client.post("/api/login", json={"password": PASSWORD})
    response = client.get("/api/setup")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sections"]) == 6
    assert data["known_hosts_present"] is True
    assert data["connections"][0]["key_present"] is True
    assert data["connections"][1]["key_present"] is False
    assert all(not c["configured"] for c in data["connections"])
    assert "SECRET-" not in response.text


def test_setup_uses_configured_key_names_without_exposing_tokens(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ssh_dir", str(tmp_path))
    (tmp_path / "custom_key").write_text("PRIVATE-KEY")
    main.store.put("connections", {"source": {"ssh_key":"custom_key", "token":"PRIVATE-TOKEN"}})
    client.post("/api/login", json={"password": PASSWORD})
    response = client.get("/api/setup")
    source = response.json()["connections"][0]
    assert source["configured"] and source["key_present"]
    assert source["key_name"] == "custom_key"
    assert "PRIVATE-" not in response.text


def test_no_execution_without_reviewed_plan(client):
    token = client.post("/api/login", json={"password": PASSWORD}).json()["csrf"]
    response = client.post("/api/execute", headers={"x-csrf-token":token}, json={
        "plan_id":"fake", "confirmation":"CLONA DESTINAZIONE VUOTA",
        "downtime_accepted":True, "external_writers_stopped":True})
    assert response.status_code == 400
    assert not main.store.lock.locked()


def test_saved_servers_api_roles_and_encrypted_credentials(client):
    token=client.post('/api/login',json={'password':PASSWORD}).json()['csrf']
    headers={'x-csrf-token':token}
    def body(name):
        return {'name':name,'connection':{'url':f'https://{name}.example','token':name+'-private-token',
                'ssh_host':f'{name}.example','ssh_key':name+'_ed25519'}}
    assert client.post('/api/servers',json=body('first')).status_code==403
    first=client.post('/api/servers',json=body('first'),headers=headers).json()['id']
    second=client.post('/api/servers',json=body('second'),headers=headers).json()['id']
    assert not client.get('/api/config').json()['configured']
    roles={'source_id':first,'target_id':second}
    assert client.post('/api/server-roles',json=roles,headers=headers).status_code==200
    assert client.get('/api/config').json()['connections']['source']['url']=='https://first.example'
    public=client.get('/api/servers').json()
    assert 'private-token' not in str(public)
    assert all('token' not in p['connection'] for p in public['profiles'])
    main.store.put('current-plan',{'id':'old'})
    assert client.post('/api/server-roles',json={'source_id':second,'target_id':first},headers=headers).status_code==200
    assert main.store.get('current-plan') is None
    assert client.get('/api/config').json()['connections']['target']['url']=='https://first.example'
    before=main.store.get('server-profiles')
    assert main.store.lock.acquire(False)
    try:
        assert client.post('/api/servers',json=body('third'),headers=headers).status_code==409
        assert client.post('/api/server-roles',json=roles,headers=headers).status_code==409
    finally:
        main.store.lock.release()
    assert main.store.get('server-profiles')==before


def test_saved_server_validation_does_not_expose_token(client):
    token=client.post('/api/login',json={'password':PASSWORD}).json()['csrf']
    r=client.post('/api/servers',headers={'x-csrf-token':token},json={'name':'Secret server','connection':{
        'url':'https://user:NEVER-ECHO-PASSWORD@example.com','token':'NEVER-ECHO-TOKEN','ssh_host':'example.com'}})
    assert r.status_code==422
    assert 'NEVER-ECHO' not in r.text
