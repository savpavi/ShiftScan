"""API entegrasyonunda hesap izolasyonu ve görsel veri sınırları."""
import base64
import io
import pytest
from cryptography.fernet import Fernet
from PIL import Image
from fastapi.testclient import TestClient
import main

@pytest.fixture
def configured(monkeypatch,tmp_path):
    monkeypatch.setenv('SHIFTSCAN_DB_PATH',str(tmp_path/'accounts.db'))
    monkeypatch.setenv('SHIFTSCAN_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setenv('SHIFTSCAN_SECURE_COOKIES','false')
    return TestClient(main.app)

def register(client,name):
    response=client.post('/api/auth/register',json={'username':name,'password':'test-password-1234'},headers={'Origin':'http://testserver'})
    assert response.status_code==200, response.text
    return {'Origin':'http://testserver','X-CSRF-Token':response.json()['csrf_token']}

def image():
    output=io.BytesIO();Image.new('RGB',(4,4)).save(output,format='PNG')
    return base64.b64encode(output.getvalue()).decode()

def add(client,headers):
    response=client.post('/api/connections',headers=headers,json={'provider':'gemini','label':'Personal','model':'test-model','api_key':'private-test-key'})
    assert response.status_code in (200,201),response.text
    return response.json().get('connection',response.json())['id']

def test_secret_not_echoed_in_validation(configured):
    response=configured.post('/api/auth/register',headers={'Origin':'http://testserver'},json={'username':'a','password':'private'})
    assert response.status_code==422
    assert 'private' not in response.text

def test_extract_requires_login(configured):
    response=configured.post('/api/ocr/extract',json={'connection_id':'x','start_date':'2026-09-07','image_base64':image()})
    assert response.status_code==401

def test_extract_uses_only_owner_connection(configured,monkeypatch):
    headers=register(configured,'alice');connection_id=add(configured,headers)
    other=TestClient(main.app);other_headers=register(other,'bob')
    async def forbidden(*args,**kwargs):
        raise AssertionError('Provider must not be called for another user')
    monkeypatch.setattr(main,'generate_json',forbidden)
    response=other.post('/api/ocr/extract',headers=other_headers,json={'connection_id':connection_id,'start_date':'2026-09-07','image_base64':image()})
    assert response.status_code==404

def test_extract_normalizes_and_does_not_cache(configured,monkeypatch):
    headers=register(configured,'alice');connection_id=add(configured,headers)
    async def fake(connection,prompt,image=None):
        assert connection['api_key']=='private-test-key'
        assert image['mime_type']=='image/png'
        return {'people':[{'name':'A','days':[{'day_index':0,'status':'off'}]}]}
    monkeypatch.setattr(main,'generate_json',fake)
    response=configured.post('/api/ocr/extract',headers=headers,json={'connection_id':connection_id,'start_date':'2026-09-07','image_base64':image()})
    assert response.status_code==200,response.text
    assert response.json()['people'][0]['days'][1]['status']=='unknown'
    assert response.headers['cache-control']=='no-store'
    assert 'private-test-key' not in response.text

def test_plan_with_connection_checks_csrf(configured):
    headers=register(configured,'alice');connection_id=add(configured,headers)
    response=configured.post('/generate-plan',json={'start_date':'2026-09-07','shift_events':[], 'activities':[{'id':'x','name':'Read','unit':'hours','amount':1}],'connection_id':connection_id})
    assert response.status_code==403

def test_configured_server_key_is_not_used_by_default(configured,monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY','test-secret')
    async def forbidden(*args,**kwargs): raise AssertionError('Global key must not be used')
    monkeypatch.setattr(main,'get_gemini_activity_plan',forbidden)
    response=configured.post('/generate-plan',json={'start_date':'2026-09-07','shift_events':[],'activities':[{'id':'x','name':'Read','unit':'hours','amount':1}]})
    assert response.status_code==200
    assert response.json()['plan_source']=='fallback'

def test_oversize_auth_body_rejected_without_echo(configured):
    response=configured.post('/api/auth/login',content='x'*40_000,headers={'Content-Type':'application/json','Origin':'http://testserver'})
    assert response.status_code==413
    assert len(response.content)<500

def test_legacy_ocr_disabled_by_default(configured,monkeypatch):
    monkeypatch.delenv('SHIFTSCAN_LEGACY_OCR',raising=False)
    async def forbidden(*args,**kwargs): raise AssertionError('Legacy provider must not be called')
    monkeypatch.setattr(main,'process_ocr_image',forbidden)
    response=configured.post('/ocr',json={'image_base64':image()})
    assert response.status_code==503
