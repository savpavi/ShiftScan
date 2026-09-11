"""Bağımsız incelemede bulunan giriş yarışı ve token yaşam döngüsü regresyonları."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import services.chatgpt as bridge
from services.providers import ProviderError


def test_parallel_finish_consumes_login_once(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, '_pending', {})
    monkeypatch.setattr(bridge, 'current_user', lambda request: {'id': 'owner'})
    monkeypatch.setattr(bridge, 'require_csrf', lambda request: None)
    request = SimpleNamespace(headers={'x-csrf-token': 'csrf'})
    saved = []

    def save(*args):
        saved.append(args)
        return {'id': str(len(saved))}

    monkeypatch.setattr(bridge, 'get_store', lambda: SimpleNamespace(add_chatgpt=save))
    (tmp_path / 'auth.json').write_text(json.dumps({'tokens': {'access_token': 'test-token'}}))

    async def run():
        async def waiting():
            await asyncio.sleep(600)

        watcher = asyncio.create_task(waiting())
        await asyncio.sleep(0)
        p = {'owner': 'owner', 'csrf': 'csrf', 'home': str(tmp_path),
             'status': 'ready', 'models': [{'id': 'model-slug'}],
             'label': 'Personal', 'task': watcher}
        bridge._pending['login'] = p
        results = await asyncio.gather(
            bridge.finish_login(request, 'login', bridge.LoginFinish(model='model-slug')),
            bridge.finish_login(request, 'login', bridge.LoginFinish(model='model-slug')),
            return_exceptions=True,
        )
        assert len(saved) == 1
        assert sum(isinstance(result, dict) for result in results) == 1
        rejected = next(result for result in results if isinstance(result, HTTPException))
        assert rejected.status_code in (404, 409)
        assert 'login' not in bridge._pending

    asyncio.run(run())


def test_cancel_during_watcher_cleanup_does_not_strand_login(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, '_pending', {})
    home = tmp_path / 'home'
    home.mkdir()

    async def run():
        closing = asyncio.Event()

        class Session:
            async def await_login(self, *args, **kwargs):
                return False

            async def close(self):
                closing.set()
                await asyncio.sleep(600)

        pending = {'id': 'login', 'login_id': 'device', 'home': str(home),
                   'session': Session(), 'status': 'pending'}
        bridge._pending['login'] = pending
        task = asyncio.create_task(bridge._watch(pending))
        await asyncio.wait_for(closing.wait(), 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert 'login' not in bridge._pending
        assert not home.exists()

    asyncio.run(run())


def test_model_menu_uses_generation_slug_not_display_id(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, '_pending', {})
    home = tmp_path / 'home'
    home.mkdir()
    (home / 'auth.json').write_text(json.dumps({'tokens': {'access_token': 'test-token'}}))

    async def run():
        class Session:
            async def await_login(self, *args, **kwargs):
                return True

            async def request(self, method, params):
                if method == 'account/read':
                    return {'account': {'type': 'chatgpt'}}
                return {'data': [{'id': 'menu-preset-id', 'model': 'generation-model',
                                  'displayName': 'Model label', 'isDefault': True}]}

            async def close(self):
                pass

        pending = {'id': 'login', 'login_id': 'device', 'home': str(home),
                   'session': Session(), 'status': 'pending',
                   'expires': time.monotonic() + 600}
        bridge._pending['login'] = pending
        task = asyncio.create_task(bridge._watch(pending))
        await asyncio.sleep(0)
        try:
            assert pending['status'] == 'ready'
            assert pending['models'] == [{'id': 'generation-model', 'label': 'Model label', 'default': True}]
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(run())


@pytest.mark.parametrize('failure', ['database', 'auth_file', 'close'])
def test_refresh_cleanup_errors_are_safe_and_release_resources(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(bridge, 'enabled', lambda: True)
    monkeypatch.setattr(bridge, '_active', set())
    home = tmp_path / 'private-home'
    home.mkdir()
    monkeypatch.setattr(bridge.tempfile, 'mkdtemp', lambda **kwargs: str(home))
    secret = 'test-sensitive-token'
    connection = {'owner_id': 'owner', 'id': 'connection', 'model': 'model',
                  'api_key': json.dumps({'tokens': {'access_token': secret}})}

    class Session:
        async def start(self):
            pass

        async def generate(self, prompt, model):
            if failure == 'auth_file':
                (home / 'auth.json').write_text('invalid-json-' + secret)
            return {'plan': []}

        async def close(self):
            if failure == 'close':
                raise OSError(secret)

    def persist(*args):
        if failure == 'database':
            raise OSError(secret)
        return True

    monkeypatch.setattr(bridge, '_session', lambda path: Session())
    monkeypatch.setattr(bridge, 'get_store', lambda: SimpleNamespace(update_chatgpt_secret=persist))
    with pytest.raises(ProviderError) as caught:
        asyncio.run(bridge.generate(connection, 'plan'))
    assert caught.value.code == 'authentication'
    assert secret not in str(caught.value)
    assert not home.exists()
    assert not bridge._active
