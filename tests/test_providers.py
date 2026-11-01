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
        (404, None, "model_not_found", 400),
        (402, None, "billing", 402),
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

    def throttle(self, key, action="login", limit=10):
        self.throttled = (key, action)

    def get_connection(self, user_id, connection_id):
        if connection_id != "conn-1" or not self.records:
            raise HTTPException(status_code=404, detail="Connection not found")
        return dict(self.records[0])

    def update_model(self, user_id, connection_id, model):
        if connection_id != "conn-1" or not self.records:
            raise HTTPException(status_code=404, detail="Connection not found")
        self.records[0]["model"] = model
        return dict(self.records[0])

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
        "providers": [
            {"id": "gemini", "label": "Google Gemini", "auth_types": ["api_key"], "vision": True},
            {"id": "openai", "label": "OpenAI", "auth_types": ["api_key"], "vision": True},
            {"id": "anthropic", "label": "Anthropic", "auth_types": ["api_key"], "vision": True},
            {"id": "openrouter", "label": "OpenRouter", "auth_types": ["api_key"], "vision": True},
        ],
        "subscriptions": [
            {"id": "gemini", "label": "Google Gemini", "available": False, "reason": "Google abonelik bağlantısı henüz doğrulanmadı."},
            {"id": "openai", "label": "OpenAI", "available": False, "reason": "ChatGPT abonelik bağlantısı desteklenmiyor; API anahtarı kullanın."},
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


# --- Model listesi -----------------------------------------------------------

def _list_with_transport(monkeypatch, handler, provider, api_key="top-secret-key"):
    from services import providers

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs: _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    return asyncio.run(providers.list_models(provider, api_key))


def test_gemini_model_list_keeps_generate_content_chat_models(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        return httpx.Response(200, json={"models": [
            {"name": "models/gemini-3.8-flash", "displayName": "Gemini 3.8 Flash",
             "supportedGenerationMethods": ["generateContent", "countTokens"]},
            {"name": "models/gemma-4-27b-it", "displayName": "Gemma 4",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.1-flash-image", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
        ]})

    models = _list_with_transport(monkeypatch, handler, "gemini")
    assert seen["url"].startswith("https://generativelanguage.googleapis.com/v1beta/models")
    assert "key=" not in seen["url"] and seen["key"] == "top-secret-key"
    assert [m["id"] for m in models] == ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemma-4-27b-it"]
    assert models[0]["label"] == "Gemini 3.8 Flash"


def test_openai_and_openrouter_model_lists_filter_non_chat(monkeypatch):
    def openai(request):
        assert request.headers["Authorization"] == "Bearer top-secret-key"
        return httpx.Response(200, json={"data": [
            {"id": "gpt-x"}, {"id": "o9-mini"}, {"id": "gpt-x-realtime"},
            {"id": "text-embedding-3-small"}, {"id": "gpt-x-transcribe"}, {"id": "dall-e-3"},
        ]})

    assert [m["id"] for m in _list_with_transport(monkeypatch, openai, "openai")] == ["o9-mini", "gpt-x"]

    def openrouter(request):
        if request.url.path == "/api/v1/key":
            assert request.headers["Authorization"] == "Bearer top-secret-key"
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(200, json={"data": [
            {"id": "a/vision", "name": "Vision", "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]}},
            {"id": "b/text", "name": "Text", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
            {"id": "c/painter", "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
        ]})

    models = _list_with_transport(monkeypatch, openrouter, "openrouter")
    assert [(m["id"], m["vision"]) for m in models] == [("a/vision", True), ("b/text", False)]


@pytest.mark.parametrize(("status", "code"), [(400, "authentication"), (401, "authentication"),
                                              (403, "authentication"), (402, "billing"), (429, "rate_limit"), (500, "unavailable")])
def test_model_list_failures_are_sanitized(monkeypatch, status, code):
    from services.providers import ProviderError

    def handler(request):
        return httpx.Response(status, text="top-secret-key upstream diagnostic")

    with pytest.raises(ProviderError) as caught:
        _list_with_transport(monkeypatch, handler, "anthropic")
    assert caught.value.code == code
    assert "top-secret-key" not in caught.value.message


def test_openrouter_model_list_rejects_bad_key(monkeypatch):
    from services.providers import ProviderError

    def handler(request):
        if request.url.path == "/api/v1/key":
            return httpx.Response(401, json={"error": "bad"})
        return httpx.Response(200, json={"data": [{"id": "a/b"}]})

    with pytest.raises(ProviderError) as caught:
        _list_with_transport(monkeypatch, handler, "openrouter")
    assert caught.value.code == "authentication"


def test_model_routes_use_new_key_or_saved_connection_and_patch_model(monkeypatch):
    client, store = _route_client(monkeypatch)
    from services import provider_routes

    calls = []

    async def fake_list(provider, api_key):
        calls.append((provider, api_key))
        return [{"id": "m-1", "label": "M1", "vision": True}]

    monkeypatch.setattr(provider_routes, "list_models", fake_list)

    response = client.post("/api/providers/models", json={"provider": "gemini", "api_key": " new-key "})
    assert response.status_code == 200
    assert response.json()["models"][0]["id"] == "m-1"
    assert calls[-1] == ("gemini", "new-key")
    assert store.throttled == ("user-1", "models")

    assert client.post("/api/providers/models", json={"provider": "gemini"}).status_code == 422
    assert client.post("/api/providers/models", json={"connection_id": "conn-1"}).status_code == 404

    client.post("/api/connections", json={"provider": "openai", "label": "K", "model": "Gemini Flash", "api_key": "saved-key"})
    response = client.post("/api/providers/models", json={"connection_id": "conn-1"})
    assert response.status_code == 200 and "saved-key" not in response.text
    assert calls[-1] == ("openai", "saved-key")

    patched = client.patch("/api/connections/conn-1", json={"model": " m-1 "})
    assert patched.status_code == 200
    assert patched.json()["model"] == "m-1" and "api_key" not in patched.json()
    assert client.patch("/api/connections/nope", json={"model": "m"}).status_code == 404
    assert client.patch("/api/connections/conn-1", json={"model": "m", "x": 1}).status_code == 422
