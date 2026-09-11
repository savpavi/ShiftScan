"""Kullanıcıya ait BYOK bağlantılarının HTTP rotaları."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from services.accounts import current_user, get_store, require_csrf
from services.providers import SUPPORTED_PROVIDERS


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


@router.get("/api/providers")
def providers_metadata():
    reasons = {
        "gemini": "Google abonelik bağlantısı henüz doğrulanmadı.",
        "openai": "ChatGPT abonelik bağlantısı henüz doğrulanmadı.",
        "anthropic": "Claude abonelik bağlantısı henüz doğrulanmadı.",
        "openrouter": "OpenRouter abonelik bağlantısı sunmuyor; API anahtarı kullanın.",
    }
    from services.chatgpt import enabled
    return {
        "chatgpt_enabled": enabled(),
        "providers": [dict(item) for item in SUPPORTED_PROVIDERS],
        "subscriptions": [
            {"id": item["id"], "label": item["label"], "available": enabled() if item["id"] == "openai" else False, "reason": "ChatGPT cihaz koduyla giriş; yalnız planlama." if item["id"] == "openai" and enabled() else reasons[item["id"]]}
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


@router.delete("/api/connections/{connection_id}")
def delete_connection(request: Request, connection_id: str):
    user = current_user(request)
    require_csrf(request)
    deleted = get_store().delete_connection(user["id"], connection_id)
    if deleted is False:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted"}
