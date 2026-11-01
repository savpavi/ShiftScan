"""Sabit hedefli BYOK sağlayıcı adaptörleri."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import quote

import httpx


MAX_RESPONSE_BYTES = 1_048_576
MAX_OUTPUT_TOKENS = 6000
TIMEOUT_SECONDS = 45.0

SUPPORTED_PROVIDERS = (
    {"id": "gemini", "label": "Google Gemini", "auth_types": ["api_key"], "vision": True},
    {"id": "openai", "label": "OpenAI", "auth_types": ["api_key"], "vision": True},
    {"id": "anthropic", "label": "Anthropic", "auth_types": ["api_key"], "vision": True},
    {"id": "openrouter", "label": "OpenRouter", "auth_types": ["api_key"], "vision": True},
)


class ProviderError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _request(provider: str, model: str, api_key: str, prompt: str, image: dict | None):
    headers = {"Content-Type": "application/json"}
    if provider == "gemini":
        parts = [{"text": prompt}]
        if image:
            parts.insert(0, {"inlineData": {"mimeType": image["mime_type"], "data": image["data"]}})
        headers["x-goog-api-key"] = api_key
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent",
            headers,
            None,
            {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": MAX_OUTPUT_TOKENS},
            },
        )

    if provider in {"openai", "openrouter"}:
        url = "https://api.openai.com/v1/chat/completions"
        if provider == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        content: str | list[dict[str, Any]] = prompt
        if image:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{image['mime_type']};base64,{image['data']}"}},
            ]
        token_limit = {"max_completion_tokens": MAX_OUTPUT_TOKENS}
        if provider == "openrouter":
            token_limit = {"max_tokens": MAX_OUTPUT_TOKENS}
        return (
            url,
            headers,
            None,
            {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "response_format": {"type": "json_object"},
            } | token_limit,
        )

    if provider == "anthropic":
        headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        content = [{"type": "text", "text": prompt}]
        if image:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": image["mime_type"], "data": image["data"]}})
        return (
            "https://api.anthropic.com/v1/messages",
            headers,
            None,
            {"model": model, "max_tokens": MAX_OUTPUT_TOKENS, "messages": [{"role": "user", "content": content}]},
        )
    raise ProviderError("unavailable", "Sağlayıcı desteklenmiyor.", 400)


MAX_MODELS = 400
# Metin/görsel üretimine uygun olmayan aileler model listesinden çıkarılır.
_NON_CHAT = re.compile(
    r"(embed|tts|audio|realtime|transcribe|whisper|dall-e|image|imagen|veo|omni|live|"
    r"moderation|search|robotics|computer-use|aqa|gemma-embed|babbage|davinci)",
    re.IGNORECASE,
)


def _models_request(provider: str, api_key: str):
    if provider == "gemini":
        return ("https://generativelanguage.googleapis.com/v1beta/models",
                {"x-goog-api-key": api_key}, {"pageSize": "1000"})
    if provider == "openai":
        return ("https://api.openai.com/v1/models", {"Authorization": f"Bearer {api_key}"}, None)
    if provider == "anthropic":
        return ("https://api.anthropic.com/v1/models",
                {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, {"limit": "1000"})
    if provider == "openrouter":
        return ("https://openrouter.ai/api/v1/models", {"Authorization": f"Bearer {api_key}"}, None)
    raise ProviderError("unavailable", "Sağlayıcı desteklenmiyor.", 400)


def _parse_models(provider: str, payload: Any) -> list[dict]:
    items: list[dict] = []
    try:
        if provider == "gemini":
            for raw in payload.get("models", []):
                if "generateContent" not in raw.get("supportedGenerationMethods", []):
                    continue
                model_id = str(raw["name"]).removeprefix("models/")
                items.append({"id": model_id, "label": raw.get("displayName") or model_id, "vision": True})
        elif provider == "anthropic":
            for raw in payload.get("data", []):
                items.append({"id": raw["id"], "label": raw.get("display_name") or raw["id"], "vision": True})
        elif provider == "openai":
            for raw in payload.get("data", []):
                model_id = str(raw["id"])
                if re.match(r"^(gpt-|o\d|chatgpt-)", model_id):
                    items.append({"id": model_id, "label": model_id, "vision": None})
        elif provider == "openrouter":
            for raw in payload.get("data", []):
                arch = raw.get("architecture") or {}
                if "text" not in (arch.get("output_modalities") or ["text"]):
                    continue
                vision = "image" in (arch.get("input_modalities") or [])
                items.append({"id": raw["id"], "label": raw.get("name") or raw["id"], "vision": vision})
    except (KeyError, TypeError, AttributeError):
        raise ProviderError("invalid_output", "Sağlayıcının model listesi okunamadı.", 502) from None
    seen, result = set(), []
    for item in items:
        if item["id"] in seen or _NON_CHAT.search(item["id"]) or len(item["id"]) > 120:
            continue
        seen.add(item["id"])
        result.append({"id": item["id"], "label": str(item["label"])[:120], "vision": item["vision"]})
    if provider in {"openai", "gemini"}:
        result.sort(key=lambda m: m["id"], reverse=True)  # yeni sürümler üstte
    if provider == "gemini":
        result.sort(key=lambda m: not m["id"].startswith("gemini-"))  # Gemma vb. sona
    return result[:MAX_MODELS]


async def list_models(provider: str, api_key: str) -> list[dict]:
    url, headers, params = _models_request(provider, api_key)
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            if provider == "openrouter":
                # Model listesi herkese açık; anahtarı ayrıca doğrula.
                check = await client.get("https://openrouter.ai/api/v1/key", headers=headers)
                if check.status_code in {401, 403}:
                    raise ProviderError("authentication", "Sağlayıcı API anahtarını kabul etmedi.", 401)
            response = await client.get(url, headers=headers, params=params)
    except httpx.TimeoutException:
        raise ProviderError("timeout", "Sağlayıcı zamanında yanıt vermedi.", 504) from None
    except httpx.HTTPError:
        raise ProviderError("unavailable", "Sağlayıcıya şu anda ulaşılamıyor.", 503) from None
    if response.status_code in {400, 401, 403}:
        raise ProviderError("authentication", "Sağlayıcı API anahtarını kabul etmedi.", 401)
    if response.status_code == 429:
        raise ProviderError("rate_limit", "Sağlayıcı istek sınırına ulaştı.", 429)
    if response.status_code >= 400 or len(response.content) > 8 * MAX_RESPONSE_BYTES:
        raise ProviderError("unavailable", "Sağlayıcı model listesini veremedi.", 503)
    try:
        payload = response.json()
    except ValueError:
        raise ProviderError("invalid_output", "Sağlayıcının model listesi okunamadı.", 502) from None
    return _parse_models(provider, payload)


def _output_text(provider: str, payload: Any) -> str:
    try:
        if provider == "gemini":
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        if provider == "anthropic":
            return next(item["text"] for item in payload["content"] if item.get("type") == "text")
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, StopIteration):
        raise ProviderError("invalid_output", "Sağlayıcı geçerli JSON döndürmedi.", 502) from None


def _parse_json(text: str) -> dict | list:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ProviderError("invalid_output", "Sağlayıcı yanıtı geçersiz veya çok büyük.", 502)
    match = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1)
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        raise ProviderError("invalid_output", "Sağlayıcı geçerli JSON döndürmedi.", 502) from None
    if not isinstance(result, (dict, list)):
        raise ProviderError("invalid_output", "Sağlayıcı JSON nesnesi veya listesi döndürmedi.", 502)
    return result


async def _fetch_json(provider: str, url: str, headers: dict, params: dict | None, body: dict) -> dict | list:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
        async with client.stream("POST", url, headers=headers, params=params, json=body) as response:
            if response.status_code in {401, 403}:
                raise ProviderError("authentication", "Sağlayıcı kimlik doğrulamasını reddetti.", 401)
            if response.status_code == 429:
                raise ProviderError("rate_limit", "Sağlayıcı istek sınırına ulaştı.", 429)
            if response.status_code == 404:
                raise ProviderError(
                    "model_not_found",
                    "Sağlayıcı bu model kimliğini tanımadı. Hesaplarım bölümünde bağlantının modelini listeden seç.",
                    400,
                )
            if response.status_code in {400, 409, 422}:
                raise ProviderError("invalid_request", "Sağlayıcı model veya istek ayarlarını kabul etmedi.", 400)
            if response.status_code >= 400:
                raise ProviderError("unavailable", "Sağlayıcı isteği tamamlayamadı.", 503)
            chunks = bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks) > MAX_RESPONSE_BYTES:
                    raise ProviderError("invalid_output", "Sağlayıcı yanıtı geçersiz veya çok büyük.", 502)

    try:
        payload = json.loads(chunks)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        raise ProviderError("invalid_output", "Sağlayıcı geçerli JSON döndürmedi.", 502) from None
    return _parse_json(_output_text(provider, payload))


async def generate_json(connection: dict, prompt: str, image: dict | None = None) -> dict | list:
    provider = connection.get("provider", "")
    url, headers, params, body = _request(
        provider, connection.get("model", ""), connection.get("api_key", ""), prompt, image
    )
    try:
        return await asyncio.wait_for(
            _fetch_json(provider, url, headers, params, body), timeout=TIMEOUT_SECONDS
        )
    except ProviderError:
        raise
    except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException):
        raise ProviderError("timeout", "Sağlayıcı zamanında yanıt vermedi.", 504) from None
    except httpx.HTTPError:
        raise ProviderError("unavailable", "Sağlayıcıya şu anda ulaşılamıyor.", 503) from None
