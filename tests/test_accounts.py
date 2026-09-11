"""Real-database account, session and secret-isolation boundaries."""
import importlib.util
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def test_account_module_exists():
    assert importlib.util.find_spec('services.accounts') is not None


@pytest.fixture
def store(tmp_path, monkeypatch):
    from services.accounts import get_store
    monkeypatch.setenv('SHIFTSCAN_DB_PATH', str(tmp_path / 'accounts.sqlite3'))
    monkeypatch.setenv('SHIFTSCAN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setenv('SHIFTSCAN_SECURE_COOKIES', 'false')
    return get_store()


@pytest.fixture
def client(store):
    from services.account_routes import router
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, headers={'Origin': 'http://testserver'}) as client:
        yield client


def register(client, username='alice'):
    return client.post('/api/auth/register', json={'username': username, 'password': 'long-password-123!'})


def test_disk_secrets_encrypted_and_owner_enforced(store):
    alice = store.register('alice', 'long-password-123!')
    bob = store.register('bob', 'different-password!')
    secret = 'sk-TOP-SECRET-DO-NOT-PERSIST'
    conn = store.add_connection(alice['id'], 'openai', 'Work', 'gpt-test', secret)
    assert 'api_key' not in conn
    assert 'api_key' not in store.list_connections(alice['id'])[0]
    assert store.get_connection(alice['id'], conn['id'])['api_key'] == secret
    assert store.list_connections(bob['id']) == []
    for method in (store.get_connection, store.delete_connection):
        with pytest.raises(HTTPException) as error:
            method(bob['id'], conn['id'])
        assert error.value.status_code == 404
    with sqlite3.connect(store.path) as db:
        dump = '\n'.join(db.iterdump())
    assert secret not in dump
    assert 'long-password-123!' not in dump
    store.delete_connection(alice['id'], conn['id'])
    assert store.list_connections(alice['id']) == []


def test_register_login_logout_csrf_and_cookie(client, store):
    response = register(client)
    assert response.status_code == 200
    assert response.json()['user']['username'] == 'alice'
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie
    csrf = response.json()['csrf_token']
    raw = client.cookies.get('shiftscan_session')
    with sqlite3.connect(store.path) as db:
        assert raw not in '\n'.join(db.iterdump())
    assert client.get('/api/session').json()['user']['username'] == 'alice'
    assert client.post('/api/auth/logout').status_code == 403
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 200
    assert store.session(raw) is None
    assert client.get('/api/session').json()['user'] is None
    result = client.post('/api/auth/login', json={'username': 'ALICE', 'password': 'long-password-123!'})
    assert result.status_code == 200
    assert result.json()['csrf_token'] != csrf


def test_auth_rejects_cross_origin_and_absent_origin(client):
    assert register(client).status_code == 200
    assert client.post('/api/auth/login', headers={'Origin': 'https://evil.example'}, json={'username': 'alice', 'password': 'long-password-123!'}).status_code == 403
    client.headers.pop('Origin')
    assert client.post('/api/auth/register', json={'username': 'bob', 'password': 'long-password-123!'}).status_code == 403


@pytest.mark.parametrize('username,password', [("x'; DROP TABLE users;--", 'long-password-123!'), ('a', 'long-password-123!'), ('alice', 'short'), ('alice', 'x'*129)])
def test_invalid_auth_rejected(client, username, password):
    assert client.post('/api/auth/register', json={'username': username, 'password': password}).status_code == 422


def test_session_expiry(store):
    user = store.register('alice', 'long-password-123!')
    token, _ = store.create_session(user['id'])
    assert store.session(token)['id'] == user['id']
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE sessions SET expires_at=0')
    assert store.session(token) is None


def test_throttle_persists_across_store_instances(store):
    from services.accounts import AccountStore
    store.register('alice', 'long-password-123!')
    for _ in range(10):
        with pytest.raises(HTTPException) as error:
            store.authenticate('alice', 'wrong-password-long', '127.0.0.1')
        assert error.value.status_code == 401
    other = AccountStore(store.path, store.encryption_key)
    with pytest.raises(HTTPException) as error:
        other.authenticate('alice', 'long-password-123!', '127.0.0.1')
    assert error.value.status_code == 429


def test_connections_cap_is_transactional(store):
    user = store.register('alice', 'long-password-123!')
    def add(i):
        try:
            store.add_connection(user['id'], 'openai', str(i), 'gpt-test', 'secret')
            return 200
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(add, range(25)))
    assert results.count(200) == 20
    assert results.count(409) == 5


def test_missing_config_is_safe(monkeypatch):
    from services.account_routes import router
    monkeypatch.delenv('SHIFTSCAN_DB_PATH', raising=False)
    monkeypatch.delenv('SHIFTSCAN_ENCRYPTION_KEY', raising=False)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, headers={'Origin': 'http://testserver'}) as client:
        assert client.get('/api/session').json() == {'user': None, 'csrf_token': None, 'configured': False}
        assert register(client).status_code == 503


def test_encrypted_secret_cannot_be_transplanted_between_owners(store):
    alice = store.register('alice', 'long-password-123!')
    bob = store.register('bob', 'long-password-123!')
    first = store.add_connection(alice['id'], 'openai', 'A', 'model', 'alice-secret')
    second = store.add_connection(bob['id'], 'openai', 'B', 'model', 'bob-secret')
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE connections SET encrypted_secret=(SELECT encrypted_secret FROM connections WHERE id=?) WHERE id=?', (first['id'], second['id']))
    with pytest.raises(HTTPException) as error:
        store.get_connection(bob['id'], second['id'])
    assert error.value.status_code == 503
    assert 'alice-secret' not in str(error.value)


def test_secure_cookie_default_and_foreign_session_csrf(client, store, monkeypatch):
    monkeypatch.delenv('SHIFTSCAN_SECURE_COOKIES', raising=False)
    response = register(client)
    assert '; Secure' in response.headers['set-cookie']
    first_csrf = response.json()['csrf_token']
    bob = store.register('bob', 'long-password-123!')
    token, _ = store.create_session(bob['id'])
    client.cookies.clear()
    client.cookies.set('shiftscan_session', token)
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': first_csrf}).status_code == 403
    assert store.session(token)['id'] == bob['id']


def test_sql_injection_connection_id_returns_not_found(store):
    user = store.register('alice', 'long-password-123!')
    connection = store.add_connection(user['id'], 'openai', 'label', 'model', 'secret')
    with pytest.raises(HTTPException) as error:
        store.get_connection(user['id'], "' OR 1=1 --")
    assert error.value.status_code == 404
    assert store.get_connection(user['id'], connection['id'])['api_key'] == 'secret'


def test_invalid_fernet_configuration_is_unavailable(tmp_path, monkeypatch):
    from services.accounts import get_store
    monkeypatch.setenv('SHIFTSCAN_DB_PATH', str(tmp_path/'never-created.sqlite3'))
    monkeypatch.setenv('SHIFTSCAN_ENCRYPTION_KEY', 'invalid')
    with pytest.raises(HTTPException) as error:
        get_store()
    assert error.value.status_code == 503
    assert not (tmp_path/'never-created.sqlite3').exists()
