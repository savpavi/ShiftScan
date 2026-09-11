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
            if response.status_code in {400, 404, 409, 422}:
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
