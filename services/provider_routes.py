"""Kullanıcıya ait BYOK bağlantılarının HTTP rotaları."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from services.accounts import current_user, get_store, require_csrf
from services.providers import SUPPORTED_PROVIDERS, ProviderError, list_models


router = APIRouter()


class ConnectionCreate(BaseModel):
    model_config = {"extra": "forbid"}

    provider: Literal["gemini", "openai", "anthropic", "openrouter"]
    label: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(min_length=1, max_length=4096)

    @field_validator("label", "model", "api_key")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


def _public(record: dict) -> dict:
    fields = ("id", "provider", "label", "model", "auth_type", "created_at")
    return {key: record[key] for key in fields if key in record}


class ModelListRequest(BaseModel):
    """Yeni anahtar (provider + api_key) ya da kayıtlı bağlantı (connection_id) için model listesi."""
    model_config = {"extra": "forbid"}

    provider: Literal["gemini", "openai", "anthropic", "openrouter"] | None = None
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    connection_id: str | None = Field(default=None, min_length=1, max_length=64)


class ModelUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    model: str = Field(min_length=1, max_length=120)


@router.post("/api/providers/models")
async def provider_models(request: Request, body: ModelListRequest):
    user = current_user(request)
    require_csrf(request)
    store = get_store()
    store.throttle(user["id"], action="models", limit=30)
    if body.connection_id:
        connection = store.get_connection(user["id"], body.connection_id)
        provider, api_key = connection["provider"], connection["api_key"]
    elif body.provider and body.api_key and body.api_key.strip():
        provider, api_key = body.provider, body.api_key.strip()
    else:
        raise HTTPException(status_code=422, detail="Sağlayıcı ve API anahtarı gerekli.")
    try:
        models = await list_models(provider, api_key)
    except ProviderError as exc:
        raise HTTPException(exc.status_code, {"code": exc.code, "message": exc.message}) from None
    return {"provider": provider, "models": models}


@router.get("/api/providers")
def providers_metadata():
    reasons = {
        "gemini": "Google abonelik bağlantısı henüz doğrulanmadı.",
        "openai": "ChatGPT abonelik bağlantısı desteklenmiyor; API anahtarı kullanın.",
        "anthropic": "Claude abonelik bağlantısı henüz doğrulanmadı.",
        "openrouter": "OpenRouter abonelik bağlantısı sunmuyor; API anahtarı kullanın.",
    }
    return {
        "providers": [dict(item) for item in SUPPORTED_PROVIDERS],
        "subscriptions": [
            {"id": item["id"], "label": item["label"], "available": False, "reason": reasons[item["id"]]}
            for item in SUPPORTED_PROVIDERS
        ],
    }


@router.get("/api/connections")
def list_connections(request: Request):
    user = current_user(request)
    records = get_store().list_connections(user["id"])
    return {"connections": [_public(record) for record in records]}


@router.post("/api/connections", status_code=status.HTTP_201_CREATED)
def create_connection(request: Request, body: ConnectionCreate):
    user = current_user(request)
    require_csrf(request)
    record = get_store().add_connection(
        user["id"], body.provider, body.label.strip(), body.model.strip(), body.api_key
    )
    return _public(record)


@router.patch("/api/connections/{connection_id}")
def update_connection_model(request: Request, connection_id: str, body: ModelUpdate):
    user = current_user(request)
    require_csrf(request)
    return _public(get_store().update_model(user["id"], connection_id, body.model.strip()))


@router.delete("/api/connections/{connection_id}")
def delete_connection(request: Request, connection_id: str):
    user = current_user(request)
    require_csrf(request)
    deleted = get_store().delete_connection(user["id"], connection_id)
    if deleted is False:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted"}
