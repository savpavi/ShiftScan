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
