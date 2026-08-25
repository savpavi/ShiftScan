"""Gemini'den gelen plan JSON'unun dogrulanmasi."""

from datetime import date

import pytest

from services.ai_planner import (
    ActivityPlanItem,
    apply_activity_plan,
    parse_activity_plan,
)
from services.timeline_builder import build_timeline, find_free_slots

WEEK_START = date(2026, 8, 24)


@pytest.fixture
def free_slots():
    timeline = build_timeline(
        [{"start": "2026-08-24T06:00:00Z", "end": "2026-08-24T15:00:00Z"}]
    )
    return find_free_slots(timeline, WEEK_START)


def test_item_without_activity_is_skipped():
    """Model 'activity' alanini atlarsa istek cokmemeli."""
    assert parse_activity_plan([{"day": "Pazartesi", "hours": 1}]) == []


def test_string_hours_is_coerced():
    """Model sayiyi string olarak dondurse de kabul edilmeli."""
    items = parse_activity_plan([{"day": "Pazartesi", "activity": "Spor", "hours": "2"}])

    assert len(items) == 1
    assert items[0].hours == 2.0


def test_non_list_payload_yields_empty_plan():
    """Model liste yerine dict/metin dondurse de cokmemeli."""
    assert parse_activity_plan({"Pazartesi": [{"activity": "Spor"}]}) == []
    assert parse_activity_plan("Spor yapmalisin") == []
    assert parse_activity_plan(None) == []


def test_non_positive_hours_is_skipped():
    plan = [
        {"day": "Pazartesi", "activity": "Spor", "hours": 0},
        {"day": "Pazartesi", "activity": "Spor", "hours": -3},
        {"day": "Pazartesi", "activity": "Spor", "hours": 99},
    ]

    assert parse_activity_plan(plan) == []


def test_valid_items_survive_alongside_invalid_ones():
    plan = [
        {"day": "Pazartesi", "hours": 1},
        {"day": "Pazartesi", "activity": "Spor", "hours": 2},
    ]

    items = parse_activity_plan(plan)

    assert [i.activity for i in items] == ["Spor"]


def test_apply_activity_plan_places_validated_item(free_slots):
    items = [ActivityPlanItem(day="Pazartesi", activity="Spor", hours=2)]

    events = apply_activity_plan(free_slots, items)

    assert events, "en az bir aktivite yerlesmeliydi"
    assert all(name == "Spor" for _, _, name in events)
    total = sum((e - s).total_seconds() / 3600 for s, e, _ in events)
    assert total == pytest.approx(2.0)
