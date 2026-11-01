"""Browser account routes. Secrets and session bearer tokens never enter JSON."""
import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from services.accounts import COOKIE_NAME, SESSION_SECONDS, get_store, require_csrf

router = APIRouter()


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=12, max_length=128)


def _origin_check(request):
    origin = request.headers.get('origin')
    expected = f'{request.url.scheme}://{request.url.netloc}'
    if not origin or origin != expected or request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'İstek kaynağı doğrulanamadı.')


def _session_response(user=None, csrf=None, configured=True):
    return {'user': user, 'csrf_token': csrf, 'configured': configured}


def _set_session(request, response, user):
    store = get_store()
    store.revoke_session(request.cookies.get(COOKIE_NAME))
    token, csrf = store.create_session(user['id'])
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=os.environ.get('SHIFTSCAN_SECURE_COOKIES', 'true').lower() != 'false',
                        samesite='lax', path='/')
    response.headers['Cache-Control'] = 'no-store'
    return _session_response(user, csrf)


@router.get('/api/session')
def session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    try:
        store = get_store()
    except HTTPException as error:
        if error.status_code != 503:
            raise
        return _session_response(configured=False)
    user_session = store.session(request.cookies.get(COOKIE_NAME))
    if user_session is None:
        return _session_response()
    return _session_response({'id': user_session['id'], 'username': user_session['username']}, user_session['csrf_token'])


@router.post('/api/auth/register')
def register(body: Credentials, request: Request, response: Response):
    _origin_check(request)
    store = get_store()
    store.throttle(request.client.host if request.client else 'unknown', action='register', limit=5)
    return _set_session(request, response, store.register(body.username, body.password))


@router.post('/api/auth/login')
def login(body: Credentials, request: Request, response: Response):
    _origin_check(request)
    user = get_store().authenticate(body.username, body.password, request.client.host if request.client else 'unknown')
    return _set_session(request, response, user)


@router.post('/api/auth/logout')
def logout(request: Request, response: Response):
    require_csrf(request)
    get_store().revoke_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path='/', httponly=True, samesite='lax',
                           secure=os.environ.get('SHIFTSCAN_SECURE_COOKIES', 'true').lower() != 'false')
    response.headers['Cache-Control'] = 'no-store'
    return _session_response()
