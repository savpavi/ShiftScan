"""Kullanici tanimli aktivitelerin prompt, dogrulama ve yerlestirmedeki davranisi."""

from datetime import datetime, timedelta

import pytz

from services.ai_planner import (
    ActivityPlanItem,
    apply_activity_plan,
    create_gemini_activity_prompt,
    generate_basic_plan,
    parse_activity_plan,
)
from services.models import ActivityGoal

IST = pytz.timezone("Europe/Istanbul")


def slot(day_index: int, start_hour: int, end_hour: int):
    day = 24 + day_index
    return (
        day_index,
        IST.localize(datetime(2026, 8, day, start_hour)),
        IST.localize(datetime(2026, 8, day, end_hour)),
    )


GOALS = [
    ActivityGoal(id="a1", name="Guitar practice", amount=2, unit="hours", preferred="evening"),
    ActivityGoal(id="a2", name="Sport", amount=2, unit="days", preferred="morning"),
]


def test_prompt_lists_user_activity_names_and_ids():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "a1" in prompt
    assert "Guitar practice" in prompt
    assert "a2" in prompt
    assert "Sport" in prompt


def test_prompt_states_the_preferred_window():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "evening" in prompt
    assert "morning" in prompt


def test_prompt_carries_no_hard_coded_activity_rules():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "Kitap Okuma" not in prompt
    assert "İçerik Üretimi" not in prompt


def test_prompt_asks_for_ids_not_names():
    prompt = create_gemini_activity_prompt([slot(0, 7, 23)], GOALS)

    assert "activity_id" in prompt
    assert "day_index" in prompt


def test_unknown_activity_id_is_dropped():
    raw = [
        {"day_index": 0, "activity_id": "a1", "hours": 1},
        {"day_index": 0, "activity_id": "ghost", "hours": 1},
    ]

    parsed = parse_activity_plan(raw, {"a1", "a2"})

    assert [item.activity_id for item in parsed] == ["a1"]


def test_day_index_out_of_range_is_dropped():
    raw = [{"day_index": 9, "activity_id": "a1", "hours": 1}]

    assert parse_activity_plan(raw, {"a1"}) == []


def test_applied_events_use_the_user_supplied_name():
    plan = [ActivityPlanItem(day_index=0, activity_id="a1", hours=1)]

    events = apply_activity_plan([slot(0, 18, 22)], plan, GOALS)

    assert [name for _, _, name in events] == ["Guitar practice"]


def test_basic_plan_prefers_the_requested_window():
    goals = [ActivityGoal(id="a1", name="Reading", amount=1, unit="hours", preferred="evening")]
    slots = [slot(0, 7, 10), slot(0, 19, 22)]

    events = generate_basic_plan(slots, goals)

    assert events
    start, _, _ = events[0]
    assert start.hour >= 18


def test_basic_plan_falls_back_when_the_window_has_no_room():
    goals = [ActivityGoal(id="a1", name="Reading", amount=1, unit="hours", preferred="evening")]
    slots = [slot(0, 7, 10)]  # sabah disinda bos zaman yok

    events = generate_basic_plan(slots, goals)

    assert len(events) == 1
    start, _, _ = events[0]
    assert start.hour == 7


def test_days_unit_uses_the_default_session_length():
    from services.models import DEFAULT_SESSION_HOURS

    goals = [ActivityGoal(id="a1", name="Sport", amount=2, unit="days", preferred="any")]
    slots = [slot(0, 7, 23), slot(1, 7, 23)]

    events = generate_basic_plan(slots, goals)

    total = sum((end - start).total_seconds() / 3600 for start, end, _ in events)
    assert total == 2 * DEFAULT_SESSION_HOURS


def test_days_unit_places_distinct_sessions_on_distinct_days():
    """'2 days per week' must be two separate day sessions, not one block."""
    from services.models import DEFAULT_SESSION_HOURS

    goals = [ActivityGoal(id="a1", name="Sport", amount=2, unit="days", preferred="any")]
    slots = [slot(0, 7, 23), slot(1, 7, 23)]

    events = generate_basic_plan(slots, goals)

    assert len(events) == 2
    days = {start.date() for start, _, _ in events}
    assert len(days) == 2
    for start, end, _ in events:
        assert (end - start).total_seconds() / 3600 == DEFAULT_SESSION_HOURS


def test_basic_plan_matches_preferred_window_in_a_slot_ending_at_midnight():
    """
    Regression: find_free_slots closes a day's final free slot at the NEXT
    day's 00:00 (see services/timeline_builder.py). slot_matches must not
    read '.hour' off that endpoint - end.hour == 0 there, which would make
    every day's after-shift/evening block invisible to window matching.
    """
    goals = [ActivityGoal(id="a1", name="Reading", amount=1, unit="hours", preferred="evening")]
    slots = [
        (0, IST.localize(datetime(2026, 8, 24, 7)), IST.localize(datetime(2026, 8, 24, 9))),
        (0, IST.localize(datetime(2026, 8, 24, 18)), IST.localize(datetime(2026, 8, 25, 0))),
    ]

    events = generate_basic_plan(slots, goals)

    assert events
    start, _, _ = events[0]
    assert start.hour == 18


def whole_day_slot(day_index: int):
    """Izin gunu tek parca gelir: 07:00'den ertesi gunun 00:00'ina kadar."""
    day = 24 + day_index
    return (
        day_index,
        IST.localize(datetime(2026, 8, day, 7)),
        IST.localize(datetime(2026, 8, day + 1, 0)),
    )


def test_basic_plan_places_inside_the_window_in_a_single_piece_day_slot():
    """
    Gercek veride bir izin gunu tek bir 07:00-24:00 slotudur ve ucun uc
    penceresiyle de kesisir. Slotu secmek yeterli degil: yerlestirme de
    pencerenin icinde olmali, yoksa tercih fiilen etkisizdir.
    """
    goals = [
        ActivityGoal(id="a1", name="Evening yoga", amount=1, unit="hours", preferred="evening")
    ]

    events = generate_basic_plan([whole_day_slot(0)], goals)

    assert len(events) == 1
    start, end, _ = events[0]
    assert start >= IST.localize(datetime(2026, 8, 24, 18))
    assert end <= IST.localize(datetime(2026, 8, 24, 23))


def test_basic_plan_days_unit_also_lands_inside_the_window():
    goals = [ActivityGoal(id="a1", name="Sport", amount=1, unit="days", preferred="morning")]

    events = generate_basic_plan([whole_day_slot(0)], goals)

    assert len(events) == 1
    start, end, _ = events[0]
    assert start >= IST.localize(datetime(2026, 8, 24, 7))
    assert end <= IST.localize(datetime(2026, 8, 24, 12))


def test_ai_plan_placement_lands_inside_the_preferred_window():
    """AI yolu da tercihi ayni sekilde uygulamali (bkz. generate_basic_plan)."""
    goals = [
        ActivityGoal(id="a1", name="Evening yoga", amount=1, unit="hours", preferred="evening")
    ]
    plan = [ActivityPlanItem(day_index=0, activity_id="a1", hours=1)]

    events = apply_activity_plan([whole_day_slot(0)], plan, goals)

    assert len(events) == 1
    start, end, _ = events[0]
    assert start >= IST.localize(datetime(2026, 8, 24, 18))
    assert end <= IST.localize(datetime(2026, 8, 24, 23))


def test_ai_plan_placement_falls_back_when_the_window_has_no_room():
    """Pencereye sigmayan saat sessizce dusmez, bos zamana konur."""
    goals = [
        ActivityGoal(id="a1", name="Evening yoga", amount=2, unit="hours", preferred="evening")
    ]
    plan = [ActivityPlanItem(day_index=0, activity_id="a1", hours=2)]
    slots = [slot(0, 7, 10)]  # aksam penceresiyle hic kesismiyor

    events = apply_activity_plan(slots, plan, goals)

    total = sum((end - start).total_seconds() / 3600 for start, end, _ in events)
    assert total == 2.0
    assert events[0][0].hour == 7
