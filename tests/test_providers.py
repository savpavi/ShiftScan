import asyncio
import base64
import importlib
import json
import sys
import types

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient


_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _connection(provider="openai", **overrides):
    value = {"provider": provider, "model": "test-model", "api_key": "top-secret-key"}
    value.update(overrides)
    return value


def _run_with_transport(monkeypatch, handler, connection, prompt="Return JSON", image=None):
    from services import providers

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    return asyncio.run(providers.generate_json(connection, prompt, image))


@pytest.mark.parametrize(
    ("provider", "host", "path", "auth_header"),
    [
        ("gemini", "generativelanguage.googleapis.com", "/v1beta/models/test-model:generateContent", None),
        ("openai", "api.openai.com", "/v1/chat/completions", "Bearer top-secret-key"),
        ("anthropic", "api.anthropic.com", "/v1/messages", None),
        ("openrouter", "openrouter.ai", "/api/v1/chat/completions", "Bearer top-secret-key"),
    ],
)
def test_generate_json_uses_fixed_provider_endpoint_and_parses_objects(
    monkeypatch, provider, host, path, auth_header
):
    def handler(request):
        assert request.url.host == host
        assert request.url.path == path
        assert request.headers.get("authorization") == auth_header
        body = json.loads(request.content)
        if provider == "gemini":
            assert not request.url.params
            assert request.headers["x-goog-api-key"] == "top-secret-key"
            assert body["generationConfig"]["responseMimeType"] == "application/json"
            response = {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]}
        elif provider == "anthropic":
            assert request.headers["x-api-key"] == "top-secret-key"
            assert body["max_tokens"] == 6000
            response = {"content": [{"type": "text", "text": "```json\n{\"ok\":true}\n```"}]}
        else:
            token_field = "max_completion_tokens" if provider == "openai" else "max_tokens"
            assert body[token_field] == 6000
            response = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        return httpx.Response(200, json=response)

    assert _run_with_transport(monkeypatch, handler, _connection(provider)) == {"ok": True}


@pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic", "openrouter"])
def test_generate_json_sends_provider_native_base64_image(monkeypatch, provider):
    image = {"mime_type": "image/png", "data": base64.b64encode(b"png").decode()}

    def handler(request):
        body = json.loads(request.content)
        if provider == "gemini":
            part = body["contents"][0]["parts"][0]["inlineData"]
            assert part == {"mimeType": "image/png", "data": image["data"]}
            response = {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}
        elif provider == "anthropic":
            source = body["messages"][0]["content"][0]["source"]
            assert source == {"type": "base64", "media_type": "image/png", "data": image["data"]}
            response = {"content": [{"type": "text", "text": "[]"}]}
        else:
            url = body["messages"][0]["content"][1]["image_url"]["url"]
            assert url == f"data:image/png;base64,{image['data']}"
            response = {"choices": [{"message": {"content": "[]"}}]}
        return httpx.Response(200, json=response)

    assert _run_with_transport(monkeypatch, handler, _connection(provider), image=image) == []


@pytest.mark.parametrize(
    ("response_status", "exception", "expected_code", "expected_status"),
    [
        (401, None, "authentication", 401),
        (429, None, "rate_limit", 429),
        (503, None, "unavailable", 503),
        (400, None, "invalid_request", 400),
        (None, httpx.ReadTimeout("late"), "timeout", 504),
    ],
)
def test_generate_json_sanitizes_provider_failures(
    monkeypatch, response_status, exception, expected_code, expected_status
):
    from services.providers import ProviderError

    def handler(request):
        if exception:
            raise exception
        return httpx.Response(response_status, text="upstream top-secret-key private diagnostic")

    with pytest.raises(ProviderError) as raised:
        _run_with_transport(monkeypatch, handler, _connection("openai"))
    assert raised.value.code == expected_code
    assert raised.value.status_code == expected_status
    assert "top-secret-key" not in raised.value.message
    assert "private diagnostic" not in raised.value.message


def test_generate_json_applies_overall_deadline_and_disables_redirects(monkeypatch):
    from services import providers
    from services.providers import ProviderError

    seen = {}

    async def handler(request):
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    def client_factory(**kwargs):
        seen.update(kwargs)
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(providers, "TIMEOUT_SECONDS", 0.01)
    with pytest.raises(ProviderError) as raised:
        asyncio.run(providers.generate_json(_connection("openai"), "Return JSON"))
    assert raised.value.code == "timeout"
    assert seen["follow_redirects"] is False


def test_generate_json_rejects_malformed_and_oversized_output(monkeypatch):
    from services.providers import ProviderError

    bodies = iter(["not-json", "x" * (1_048_576 + 1)])

    def handler(request):
        text = next(bodies)
        return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})

    for _ in range(2):
        with pytest.raises(ProviderError) as raised:
            _run_with_transport(monkeypatch, handler, _connection("openai"))
        assert raised.value.code == "invalid_output"


class _Store:
    def __init__(self):
        self.records = []

    def list_connections(self, user_id):
        return list(self.records)

    def add_connection(self, user_id, provider, label, model, api_key):
        record = {"id": "conn-1", "provider": provider, "label": label, "model": model, "api_key": api_key}
        self.records.append(record)
        return record

    def delete_connection(self, user_id, connection_id):
        if connection_id != "conn-1":
            raise HTTPException(status_code=404, detail="Connection not found")
        self.records.clear()


def _route_client(monkeypatch):
    store = _Store()
    fake_accounts = types.ModuleType("services.accounts")
    fake_accounts.get_store = lambda: store
    fake_accounts.current_user = lambda request: {"id": "user-1", "username": "ege"}
    fake_accounts.require_csrf = lambda request: None
    monkeypatch.setitem(sys.modules, "services.accounts", fake_accounts)
    sys.modules.pop("services.provider_routes", None)
    routes = importlib.import_module("services.provider_routes")
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), store


def test_provider_metadata_marks_subscription_adapters_unavailable(monkeypatch):
    client, _ = _route_client(monkeypatch)
    response = client.get("/api/providers")
    assert response.status_code == 200
    assert response.json() == {
        "chatgpt_enabled": False,
        "providers": [
            {"id": "gemini", "label": "Google Gemini", "auth_types": ["api_key"], "vision": True},
            {"id": "openai", "label": "OpenAI", "auth_types": ["api_key"], "vision": True},
            {"id": "anthropic", "label": "Anthropic", "auth_types": ["api_key"], "vision": True},
            {"id": "openrouter", "label": "OpenRouter", "auth_types": ["api_key"], "vision": True},
        ],
        "subscriptions": [
            {"id": "gemini", "label": "Google Gemini", "available": False, "reason": "Google abonelik bağlantısı henüz doğrulanmadı."},
            {"id": "openai", "label": "OpenAI", "available": False, "reason": "ChatGPT abonelik bağlantısı henüz doğrulanmadı."},
            {"id": "anthropic", "label": "Anthropic", "available": False, "reason": "Claude abonelik bağlantısı henüz doğrulanmadı."},
            {"id": "openrouter", "label": "OpenRouter", "available": False, "reason": "OpenRouter abonelik bağlantısı sunmuyor; API anahtarı kullanın."},
        ],
    }


def test_connection_routes_validate_and_never_return_api_key(monkeypatch):
    client, store = _route_client(monkeypatch)
    created = client.post(
        "/api/connections",
        json={"provider": "openai", "label": "Kişisel", "model": "gpt-test", "api_key": "top-secret-key"},
    )
    assert created.status_code == 201
    assert created.json() == {"id": "conn-1", "provider": "openai", "label": "Kişisel", "model": "gpt-test"}
    assert client.get("/api/connections").json() == {"connections": [created.json()]}
    assert store.records[0]["api_key"] == "top-secret-key"

    invalid = client.post(
        "/api/connections",
        json={"provider": "evil", "label": "x", "model": "x", "api_key": "x"},
    )
    assert invalid.status_code == 422
    assert "top-secret-key" not in invalid.text

    assert client.delete("/api/connections/conn-1").json() == {"status": "deleted"}
