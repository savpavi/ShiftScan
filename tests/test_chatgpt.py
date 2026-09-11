import json
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from services.accounts import AccountStore


def test_subscription_secret_isolated_and_refresh_does_not_resurrect(tmp_path):
    store=AccountStore(tmp_path/'db',Fernet.generate_key())
    a=store.register('alice','password-long-123'); b=store.register('bobby','password-long-123')
    c=store.add_chatgpt(a['id'],'Personal','test-model',json.dumps({'tokens':{'access_token':'private-token'}}))
    assert c['auth_type']=='oauth'
    assert 'private-token' not in str(store.list_connections(a['id']))
    assert b'private-token' not in (tmp_path/'db').read_bytes()
    with pytest.raises(HTTPException):store.get_connection(b['id'],c['id'])
    assert store.get_connection(a['id'],c['id'])['owner_id']==a['id']
    store.delete_connection(a['id'],c['id'])
    assert not store.update_chatgpt_secret(a['id'],c['id'],'new-token')


def test_disabled_chatgpt_fails_closed(monkeypatch):
    from services.chatgpt import require_enabled
    monkeypatch.delenv('SHIFTSCAN_CHATGPT_ENABLED',raising=False)
    with pytest.raises(HTTPException) as e:require_enabled()
    assert e.value.status_code==503


def test_device_login_routes_and_model_selection(tmp_path, monkeypatch):
    import asyncio
    from pathlib import Path
    from fastapi.testclient import TestClient
    import main
    import services.chatgpt as bridge
    monkeypatch.setenv('SHIFTSCAN_DB_PATH',str(tmp_path/'users.db'))
    monkeypatch.setenv('SHIFTSCAN_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setenv('SHIFTSCAN_SECURE_COOKIES','false')
    monkeypatch.setattr(bridge,'enabled',lambda:True)
    homes=[]
    class Fake:
        def __init__(self,home):self.home=home;homes.append(home)
        async def start(self):pass
        async def close(self):pass
        async def request(self,method,params):
            if method=='account/login/start':return {'loginId':'fake','verificationUrl':'https://auth.openai.com/codex/device','userCode':'TEST-CODE'}
            if method=='account/read':return {'account':{'type':'chatgpt'}}
            return {'data':[{'id':'display-id','model':'test-model','displayName':'Test model','isDefault':True}]}
        async def await_login(self,*args,**kwargs):
            Path(self.home,'auth.json').write_text(json.dumps({'tokens':{'access_token':'test-token'}}))
            return True
    monkeypatch.setattr(bridge,'_session',Fake)
    with TestClient(main.app) as c:
        def register(name):
            r=c.post('/api/auth/register',headers={'Origin':'http://testserver'},json={'username':name,'password':'long-password-1234'})
            return {'X-CSRF-Token':r.json()['csrf_token']}
        headers=register('alice')
        assert c.post('/api/chatgpt/login',json={}).status_code==403
        result=c.post('/api/chatgpt/login',headers=headers,json={})
        assert result.status_code==200,result.text
        lid=result.json()['id']
        r=c.post(f'/api/chatgpt/login/{lid}/status',headers=headers)
        assert r.json()['status']=='ready'
        assert 'test-token' not in r.text
        assert c.post(f'/api/chatgpt/login/{lid}/finish',headers=headers,json={'model':'invented'}).status_code==409
        r=c.post(f'/api/chatgpt/login/{lid}/finish',headers=headers,json={'model':'test-model'})
        assert r.status_code==200,r.text
        assert r.json()['provider']=='chatgpt' and r.json()['auth_type']=='oauth'
        assert not Path(homes[0]).exists()
        assert c.get('/api/connections').json()['connections'][0]['provider']=='chatgpt'
        pending=c.post('/api/chatgpt/login',headers=headers,json={}).json()['id']
        other=register('bobby')
        assert c.post(f'/api/chatgpt/login/{pending}/status',headers=other).status_code==404
        # owner login can cancel with the original session restored by client cookie.
        for p in list(bridge._pending.values()):
            c.portal.call(p['task'].cancel)


def test_chatgpt_ocr_rejected_before_model_call():
    import asyncio
    from services.providers import generate_json,ProviderError
    with pytest.raises(ProviderError) as e:
        asyncio.run(generate_json({'provider':'chatgpt'},'prompt',image={'data':'x'}))
    assert e.value.code=='invalid_request'
