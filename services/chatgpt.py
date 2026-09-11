"""Opt-in, single-worker ChatGPT subscription bridge with isolated ephemeral homes."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from services.accounts import current_user, require_csrf, get_store

router = APIRouter()
_pending = {}
_active = set()
LOGIN_SECONDS = 600


def enabled():
    return os.environ.get('SHIFTSCAN_CHATGPT_ENABLED', '').lower() == 'true' and bool(shutil.which(os.environ.get('SHIFTSCAN_CODEX_BIN', 'codex')))


def require_enabled():
    if not enabled():
        raise HTTPException(503, 'ChatGPT bağlantısı bu sunucuda etkin değil.')


def _session(home):
    from services.codex_transport import CodexSession
    return CodexSession(home)


def _auth(home):
    path = Path(home) / 'auth.json'
    if not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('Missing credentials')
    value = path.read_text()
    data = json.loads(value)
    if not isinstance(data.get('tokens'), dict) or not data['tokens'].get('access_token'):
        raise ValueError('Not a subscription credential')
    return value


async def _dispose(p):
    try:
        await p['session'].close()
    finally:
        shutil.rmtree(p['home'], ignore_errors=True)


async def _watch(p):
    try:
        success = await p['session'].await_login(p['login_id'], timeout=LOGIN_SECONDS)
        if not success:
            raise ValueError('Login failed')
        account = await p['session'].request('account/read', {'refreshToken': False})
        if (account.get('account') or {}).get('type') != 'chatgpt':
            raise ValueError('Wrong auth type')
        result = await p['session'].request('model/list', {})
        models = result.get('data', [])
        p['models'] = [{'id': m['model'], 'label': m.get('displayName') or m['model'], 'default': bool(m.get('isDefault'))}
                       for m in models if isinstance(m.get('model'), str) and not m.get('hidden', False)]
        if not p['models']:
            raise ValueError('No models')
        _auth(p['home'])
        p['status'] = 'ready'
        await asyncio.sleep(max(0, p['expires'] - time.monotonic()))
    except asyncio.CancelledError:
        raise
    except Exception:
        p['status'] = 'failed'
    finally:
        if p['status'] == 'ready':
            p['status'] = 'expired'
        _pending.pop(p['id'], None)
        await _dispose(p)


class LoginStart(BaseModel):
    model_config = {'extra': 'forbid'}
    label: str = Field(default='ChatGPT hesabım', min_length=1, max_length=80)


class LoginFinish(BaseModel):
    model_config = {'extra': 'forbid'}
    model: str = Field(min_length=1, max_length=120)


def _owned(request, login_id):
    user = current_user(request)
    require_csrf(request)
    p = _pending.get(login_id)
    if not p or p['owner'] != user['id'] or p['csrf'] != request.headers.get('x-csrf-token'):
        raise HTTPException(404, 'Giriş bulunamadı veya süresi doldu. Tekrar başlatın.')
    return p


@router.post('/api/chatgpt/login')
async def start_login(request: Request, body: LoginStart):
    user = current_user(request)
    require_csrf(request)
    require_enabled()
    store = get_store()
    store.throttle(user['id'], action='chatgpt-login', limit=5)
    if not body.label.strip():
        raise HTTPException(422, 'Bağlantı adı boş olamaz.')
    if len(_pending) >= 8 or any(p['owner'] == user['id'] for p in _pending.values()):
        raise HTTPException(409, 'Devam eden giriş var. İptal edin veya tamamlanmasını bekleyin.')
    login_id = secrets.token_urlsafe(24)
    home = tempfile.mkdtemp(prefix='shiftscan-chatgpt-')
    p = {'id': login_id, 'owner': user['id'], 'csrf': request.headers.get('x-csrf-token'),
         'home': home, 'session': _session(home), 'label': body.label.strip(),
         'status': 'pending', 'expires': time.monotonic() + LOGIN_SECONDS}
    _pending[login_id] = p
    try:
        await p['session'].start()
        result = await p['session'].request('account/login/start', {'type': 'chatgptDeviceCode'})
        url = result['verificationUrl']
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'auth.openai.com' or parsed.username or parsed.password or parsed.port not in (None,443):
            raise ValueError('Unexpected verification URL')
        p['login_id'] = result['loginId']
        p['task'] = asyncio.create_task(_watch(p))
        return {'id': login_id, 'verification_url': url, 'user_code': result['userCode'], 'expires_in': LOGIN_SECONDS}
    except BaseException as exc:
        _pending.pop(login_id, None)
        await _dispose(p)
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise HTTPException(502, 'OpenAI girişi başlatılamadı. Sunucu erişimini kontrol edin.') from None


@router.post('/api/chatgpt/login/{login_id}/status')
async def login_status(request: Request, login_id: str):
    p = _owned(request, login_id)
    return {'status': p['status'], 'models': p.get('models', [])}


@router.post('/api/chatgpt/login/{login_id}/finish')
async def finish_login(request: Request, login_id: str, body: LoginFinish):
    p = _owned(request, login_id)
    if p['status'] != 'ready' or body.model not in [m['id'] for m in p['models']]:
        raise HTTPException(409, 'Girişi tamamlayın ve listeden model seçin.')
    # No awaits between checking readiness and encrypting: the expiry task cannot race here.
    record = get_store().add_chatgpt(p['owner'], p['label'], body.model, _auth(p['home']))
    p['status'] = 'consumed'
    _pending.pop(login_id, None)
    p['task'].cancel()
    await asyncio.gather(p['task'], return_exceptions=True)
    return record


@router.delete('/api/chatgpt/login/{login_id}')
async def cancel_login(request: Request, login_id: str):
    p = _owned(request, login_id)
    p['task'].cancel()
    await asyncio.gather(p['task'], return_exceptions=True)
    return {'status': 'cancelled'}


async def generate(connection, prompt):
    from services.providers import ProviderError
    if not enabled():
        raise ProviderError('unavailable', 'ChatGPT bağlantısı bu sunucuda etkin değil.', 503)
    # A connection's refresh token must never be rotated by two concurrent workers.
    key = (connection['owner_id'], connection['id'])
    if key in _active:
        raise ProviderError('rate_limit', 'Bu ChatGPT bağlantısı şu anda kullanılıyor.', 429)
    _active.add(key)
    home = tempfile.mkdtemp(prefix='shiftscan-chatgpt-')
    session = _session(home)
    try:
        path = Path(home) / 'auth.json'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(connection['api_key'])
        await session.start()
        return await session.generate(prompt, connection['model'])
    except asyncio.CancelledError:
        raise
    except Exception:
        raise ProviderError('unavailable', 'ChatGPT isteği tamamlanamadı; bağlantıyı veya kotanı kontrol et.', 503) from None
    finally:
        try:
            await session.close()
            if path.exists():
                get_store().update_chatgpt_secret(*key, _auth(home))
        except Exception:
            raise ProviderError('authentication', 'ChatGPT oturumu kaydedilemedi; hesabı yeniden bağlayın.', 503) from None
        finally:
            shutil.rmtree(home, ignore_errors=True)
            _active.discard(key)


async def shutdown():
    tasks = [p.get('task') for p in list(_pending.values()) if p.get('task')]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
