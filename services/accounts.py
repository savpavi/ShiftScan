"""SQLite-backed accounts and owner-bound encrypted provider credentials."""
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request

COOKIE_NAME = 'shiftscan_session'
SESSION_SECONDS = 60 * 60 * 24 * 7
USERNAME = re.compile(r'[a-z0-9_][a-z0-9_.-]{2,31}', re.ASCII)


def validate_credentials(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        raise HTTPException(422, 'Geçersiz kullanıcı adı veya parola.')
    username = username.strip().lower()
    if not USERNAME.fullmatch(username) or not 12 <= len(password) <= 128:
        raise HTTPException(422, 'Kullanıcı adı 3–32, parola 12–128 karakter olmalı.')
    return username


def _password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1,
                          maxmem=64 * 1024 * 1024, dklen=32)


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class AccountStore:
    def __init__(self, path, encryption_key):
        if not path or path == ':memory:':
            raise ValueError('A persistent database path is required')
        self.path = str(path)
        self.encryption_key = encryption_key
        self._fernet = Fernet(encryption_key)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self._db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL, password_hash BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS connections (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL, label TEXT NOT NULL, model TEXT NOT NULL,
                    encrypted_secret BLOB NOT NULL, created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS connections_owner ON connections(user_id);
                CREATE TABLE IF NOT EXISTS auth_limits (
                    bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires_at INTEGER NOT NULL
                );
            ''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, username, password):
        username = validate_credentials(username, password)
        salt = secrets.token_bytes(16)
        hashed = _password_hash(password, salt)
        user_id = str(uuid.uuid4())
        try:
            with self._db() as db:
                db.execute('INSERT INTO users VALUES (?, ?, ?, ?)',
                           (user_id, username, salt, hashed))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Bu kullanıcı adı kullanılamıyor.') from None
        return {'id': user_id, 'username': username}

    def throttle(self, ip, action='login', limit=10):
        # Socket peer only: caller must never substitute untrusted forwarding headers.
        bucket = _digest(action + ':' + ip)
        now = int(time.time())
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_limits WHERE expires_at <= ?', (now,))
            row = db.execute('SELECT count FROM auth_limits WHERE bucket=?', (bucket,)).fetchone()
            if row and row['count'] >= limit:
                raise HTTPException(429, 'Çok fazla deneme. Lütfen daha sonra tekrar deneyin.', headers={'Retry-After': '900'})
            db.execute('INSERT INTO auth_limits VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1',
                       (bucket, now + 900))

    def authenticate(self, username, password, ip):
        self.throttle(ip)
        username = validate_credentials(username, password)
        with self._db() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        # Same password KDF work for unknown accounts; don't reveal existence in errors.
        salt = row['salt'] if row else bytes(16)
        expected = row['password_hash'] if row else bytes(32)
        actual = _password_hash(password, salt)
        if not hmac.compare_digest(actual, expected) or row is None:
            raise HTTPException(401, 'Kullanıcı adı veya parola hatalı.')
        return {'id': row['id'], 'username': row['username']}

    def create_session(self, user_id):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = int(time.time())
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM sessions WHERE expires_at <= ?', (now,))
            # Bound retained sessions per user, including repeated successful logins.
            db.execute('DELETE FROM sessions WHERE token_hash IN '
                       '(SELECT token_hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT -1 OFFSET 9)', (user_id,))
            db.execute('INSERT INTO sessions VALUES (?, ?, ?, ?)',
                       (_digest(token), user_id, csrf, now + SESSION_SECONDS))
        return token, csrf

    def session(self, token):
        if not token or len(token) > 128:
            return None
        with self._db() as db:
            row = db.execute('SELECT users.id, users.username, sessions.csrf_token '
                             'FROM sessions JOIN users ON users.id=sessions.user_id '
                             'WHERE token_hash=? AND expires_at>?', (_digest(token), int(time.time()))).fetchone()
        return dict(row) if row else None

    def revoke_session(self, token):
        if token:
            with self._db() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (_digest(token),))

    @staticmethod
    def _metadata(row):
        return {key: row[key] for key in ('id', 'provider', 'label', 'model', 'created_at')} | {'auth_type': 'api_key'}

    def list_connections(self, user_id):
        with self._db() as db:
            rows = db.execute('SELECT id,provider,label,model,created_at FROM connections '
                              'WHERE user_id=? ORDER BY created_at,id', (user_id,)).fetchall()
        return [self._metadata(row) for row in rows]

    def add_connection(self, user_id, provider, label, model, api_key):
        if (provider not in {'openai', 'gemini', 'anthropic', 'openrouter'}
                or not isinstance(label, str) or not 1 <= len(label.strip()) <= 80
                or not isinstance(model, str) or not 1 <= len(model.strip()) <= 120
                or not isinstance(api_key, str) or not 1 <= len(api_key.strip()) <= 4096):
            raise HTTPException(422, 'Geçersiz bağlantı bilgileri.')
        connection_id = str(uuid.uuid4())
        secret = self._fernet.encrypt(json.dumps({'owner': user_id, 'id': connection_id, 'api_key': api_key.strip()}).encode())
        now = int(time.time())
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('SELECT COUNT(*) FROM connections WHERE user_id=?', (user_id,)).fetchone()[0]
            if count >= 20:
                raise HTTPException(409, 'En fazla 20 bağlantı ekleyebilirsiniz.')
            db.execute('INSERT INTO connections VALUES (?,?,?,?,?,?,?)',
                       (connection_id, user_id, provider, label.strip(), model.strip(), secret, now))
        return {'id': connection_id, 'provider': provider, 'label': label.strip(),
                'model': model.strip(), 'created_at': now, 'auth_type': 'api_key'}

    def get_connection(self, user_id, connection_id):
        with self._db() as db:
            row = db.execute('SELECT * FROM connections WHERE user_id=? AND id=?', (user_id, connection_id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Bağlantı bulunamadı.')
        try:
            payload = json.loads(self._fernet.decrypt(row['encrypted_secret']))
            if payload['owner'] != user_id or payload['id'] != connection_id:
                raise ValueError('Owner binding mismatch')
            key = payload['api_key']
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise HTTPException(503, 'Bağlantı anahtarı okunamadı; yapılandırmayı kontrol edin.') from None
        return self._metadata(row) | {'api_key': key, 'owner_id': user_id}

    def delete_connection(self, user_id, connection_id):
        with self._db() as db:
            result = db.execute('DELETE FROM connections WHERE user_id=? AND id=?', (user_id, connection_id))
            if not result.rowcount:
                raise HTTPException(404, 'Bağlantı bulunamadı.')


@lru_cache(maxsize=1)
def _configured_store(path, key):
    return AccountStore(path, key)


def get_store():
    path = os.environ.get('SHIFTSCAN_DB_PATH', '')
    key = os.environ.get('SHIFTSCAN_ENCRYPTION_KEY', '')
    if not path or not key:
        raise HTTPException(503, 'Hesap deposu yapılandırılmamış.')
    try:
        return _configured_store(path, key)
    except (ValueError, TypeError, OSError, sqlite3.Error):
        raise HTTPException(503, 'Hesap deposu kullanılamıyor.') from None


def current_user(request: Request):
    session = get_store().session(request.cookies.get(COOKIE_NAME))
    if session is None:
        raise HTTPException(401, 'Lütfen giriş yapın.')
    return {'id': session['id'], 'username': session['username']}


def require_csrf(request: Request):
    session = get_store().session(request.cookies.get(COOKIE_NAME))
    if session is None:
        raise HTTPException(401, 'Lütfen giriş yapın.')
    token = request.headers.get('X-CSRF-Token', '')
    if not token or not hmac.compare_digest(token.encode(), session['csrf_token'].encode()):
        raise HTTPException(403, 'Geçersiz CSRF doğrulaması.')
