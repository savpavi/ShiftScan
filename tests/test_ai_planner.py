"""Gemini'den gelen plan JSON'unun dogrulanmasi."""

from datetime import date

import pytest

from services.ai_planner import (
    ActivityPlanItem,
    apply_activity_plan,
    parse_activity_plan,
)
from services.models import ActivityGoal
from services.timeline_builder import build_timeline, find_free_slots

WEEK_START = date(2026, 8, 24)

GOALS = [ActivityGoal(id="a1", name="Spor", amount=2, unit="hours", preferred="any")]
KNOWN_IDS = {"a1"}


@pytest.fixture
def free_slots():
    timeline = build_timeline(
        [{"start": "2026-08-24T06:00:00Z", "end": "2026-08-24T15:00:00Z"}],
        "Europe/Istanbul"
    )
    return find_free_slots(timeline, WEEK_START, "Europe/Istanbul")


def test_item_without_activity_id_is_skipped():
    """Model 'activity_id' alanini atlarsa istek cokmemeli."""
    assert parse_activity_plan([{"day_index": 0, "hours": 1}], KNOWN_IDS) == []


def test_string_hours_is_coerced():
    """Model sayiyi string olarak dondurse de kabul edilmeli."""
    items = parse_activity_plan(
        [{"day_index": 0, "activity_id": "a1", "hours": "2"}], KNOWN_IDS
    )

    assert len(items) == 1
    assert items[0].hours == 2.0


def test_non_list_payload_yields_empty_plan():
    """Model liste yerine dict/metin dondurse de cokmemeli."""
    assert parse_activity_plan({"Pazartesi": [{"activity_id": "a1"}]}, KNOWN_IDS) == []
    assert parse_activity_plan("Spor yapmalisin", KNOWN_IDS) == []
    assert parse_activity_plan(None, KNOWN_IDS) == []


def test_non_positive_hours_is_skipped():
    plan = [
        {"day_index": 0, "activity_id": "a1", "hours": 0},
        {"day_index": 0, "activity_id": "a1", "hours": -3},
        {"day_index": 0, "activity_id": "a1", "hours": 99},
    ]

    assert parse_activity_plan(plan, KNOWN_IDS) == []


def test_valid_items_survive_alongside_invalid_ones():
    plan = [
        {"day_index": 0, "hours": 1},
        {"day_index": 0, "activity_id": "a1", "hours": 2},
    ]

    items = parse_activity_plan(plan, KNOWN_IDS)

    assert [i.activity_id for i in items] == ["a1"]


def test_apply_activity_plan_places_validated_item(free_slots):
    items = [ActivityPlanItem(day_index=0, activity_id="a1", hours=2)]

    events = apply_activity_plan(free_slots, items, GOALS)

    assert events, "en az bir aktivite yerlesmeliydi"
    assert all(name == "Spor" for _, _, name in events)
    total = sum((e - s).total_seconds() / 3600 for s, e, _ in events)
    assert total == pytest.approx(2.0)


# --- google-genai client wiring -------------------------------------------

import asyncio
import types as _types

import services.ai_planner as ai_planner


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def _fake_client(handler):
    """Builds an object shaped like google.genai.Client for the call we make."""

    async def generate_content(*, model, contents):
        return await handler(model, contents)

    models = _types.SimpleNamespace(generate_content=generate_content)
    return _types.SimpleNamespace(aio=_types.SimpleNamespace(models=models))


@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(ai_planner, "GEMINI_AVAILABLE", True)
    monkeypatch.setattr(ai_planner, "_client", None)
    yield monkeypatch


def test_plan_uses_async_client_and_parses_json(gemini_env, free_slots):
    seen = {}

    async def handler(model, contents):
        seen["model"] = model
        seen["contents"] = contents
        return _FakeResponse('```json\n[{"day_index": 0, "activity_id": "spor", "hours": 1}]\n```')

    gemini_env.setattr(ai_planner, "_client", _fake_client(handler))
    goals = [ActivityGoal(id="spor", name="Spor", amount=3, unit="hours", preferred="any")]

    items = asyncio.run(
        ai_planner.get_gemini_activity_plan(free_slots, goals, {"spor"}, timeout=5)
    )

    assert seen["model"] == ai_planner.gemini_model_name()
    assert "spor" in seen["contents"]
    assert [(i.day_index, i.activity_id, i.hours) for i in items] == [(0, "spor", 1)]


def test_plan_returns_empty_on_timeout(gemini_env, free_slots):
    async def handler(model, contents):
        await asyncio.sleep(1)
        return _FakeResponse("[]")

    gemini_env.setattr(ai_planner, "_client", _fake_client(handler))

    items = asyncio.run(
        ai_planner.get_gemini_activity_plan(free_slots, [], set(), timeout=0.01)
    )
    assert items == []


def test_plan_returns_empty_when_client_raises(gemini_env, free_slots):
    async def handler(model, contents):
        raise RuntimeError("network down")

    gemini_env.setattr(ai_planner, "_client", _fake_client(handler))

    items = asyncio.run(
        ai_planner.get_gemini_activity_plan(free_slots, [], set(), timeout=5)
    )
    assert items == []


def test_plan_skips_client_without_api_key(monkeypatch, free_slots):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    called = []

    async def handler(model, contents):
        called.append(model)
        return _FakeResponse("[]")

    monkeypatch.setattr(ai_planner, "_client", _fake_client(handler))

    items = asyncio.run(
        ai_planner.get_gemini_activity_plan(free_slots, [], set(), timeout=5)
    )
    assert items == []
    assert called == []


def test_configure_gemini_builds_client_from_env(gemini_env):
    built = {}

    class FakeGenai:
        @staticmethod
        def Client(api_key):
            built["api_key"] = api_key
            return "client-object"

    gemini_env.setattr(ai_planner, "genai", FakeGenai)

    assert ai_planner.configure_gemini() is True
    assert built == {"api_key": "test-key"}
    assert ai_planner._client == "client-object"


def test_model_name_comes_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    assert ai_planner.gemini_model_name() == "gemini-test-model"


def test_model_name_defaults_to_current_flash(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert ai_planner.gemini_model_name() == ai_planner.DEFAULT_GEMINI_MODEL
