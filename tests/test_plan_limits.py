"""AI plan hedef sinirlari ve vardiya dogrulama sozlesmesi."""

from datetime import date, datetime, timedelta
import subprocess
import sys

import pytest
from pydantic import ValidationError

from services.ai_planner import ActivityPlanItem, place_activity_plan
from services.models import ActivityGoal
from services.shift_validation import ShiftEvent, validate_shifts


def _slot(day_index: int, start_hour: int = 8, end_hour: int = 20):
    day = datetime(2026, 9, 7) + timedelta(days=day_index)
    return day_index, day.replace(hour=start_hour), day.replace(hour=end_hour)


def _hours(events):
    return [(end - start).total_seconds() / 3600 for start, end, _ in events]


def test_ai_hours_goal_caps_total_and_each_block():
    goal = ActivityGoal(id="reading", name="Reading", amount=1, unit="hours")
    plan = [ActivityPlanItem(day_index=0, activity_id="reading", hours=12)]

    events, unplaced = place_activity_plan([_slot(0)], plan, [goal])

    assert _hours(events) == [1]
    assert unplaced == []


def test_ai_hours_goal_splits_long_request_into_two_hour_blocks():
    goal = ActivityGoal(id="reading", name="Reading", amount=5, unit="hours")
    plan = [ActivityPlanItem(day_index=0, activity_id="reading", hours=12)]

    events, unplaced = place_activity_plan([_slot(0)], plan, [goal])

    assert _hours(events) == [2, 2, 1]
    assert unplaced == []


def test_ai_days_goal_places_one_hour_once_per_distinct_day():
    goal = ActivityGoal(id="sport", name="Sport", amount=2, unit="days")
    plan = [
        ActivityPlanItem(day_index=0, activity_id="sport", hours=12),
        ActivityPlanItem(day_index=0, activity_id="sport", hours=1),
        ActivityPlanItem(day_index=1, activity_id="sport", hours=3),
        ActivityPlanItem(day_index=2, activity_id="sport", hours=1),
    ]

    events, unplaced = place_activity_plan([_slot(0), _slot(1), _slot(2)], plan, [goal])

    assert [(start.weekday(), hours) for (start, _, _), hours in zip(events, _hours(events))] == [
        (0, 1),
        (1, 1),
    ]
    assert unplaced == []


def test_ai_tiny_model_duration_terminates_without_zero_length_event():
    code = """
from datetime import datetime
from services.ai_planner import ActivityPlanItem, place_activity_plan
from services.models import ActivityGoal

start = datetime(2026, 9, 7, 8)
events, unplaced = place_activity_plan(
    [(0, start, start.replace(hour=20))],
    [ActivityPlanItem(day_index=0, activity_id='reading', hours=1e-12)],
    [ActivityGoal(id='reading', name='Reading', amount=.1, unit='hours')],
)
print(len(events), unplaced[0]['amount'])
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=2,
        check=True,
    )

    assert result.stdout.strip() == "0 0.1"


def test_shift_event_keeps_string_api_and_forbids_extra_fields():
    event = ShiftEvent(start="2026-09-07T09:00:00", end="2026-09-07T17:00:00")

    assert event.start == "2026-09-07T09:00:00"
    assert event.end == "2026-09-07T17:00:00"
    with pytest.raises(ValidationError):
        ShiftEvent(start=event.start, end=event.end, employee="Ege")


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("not-a-date", "2026-09-07T17:00:00"),
        ("2026-09-07T17:00:00", "2026-09-07T09:00:00"),
        ("2026-09-07T09:00:00", "2026-09-08T09:00:01"),
    ],
)
def test_shift_event_rejects_invalid_order_or_more_than_24_hours(start, end):
    with pytest.raises(ValidationError):
        ShiftEvent(start=start, end=end)


def test_validate_shifts_accepts_empty_list_naive_times_and_sunday_overnight():
    assert validate_shifts([], date(2026, 9, 7), "Europe/Istanbul") == []

    events = validate_shifts(
        [
            {"start": "2026-09-07T09:00:00", "end": "2026-09-07T17:00:00"},
            {"start": "2026-09-13T22:00:00", "end": "2026-09-14T06:00:00"},
        ],
        date(2026, 9, 7),
        "Europe/Istanbul",
    )

    assert [event.start for event in events] == [
        "2026-09-07T09:00:00",
        "2026-09-13T22:00:00",
    ]


def test_validate_shifts_rejects_more_than_56_or_start_outside_week():
    event = {"start": "2026-09-07T09:00:00", "end": "2026-09-07T10:00:00"}
    with pytest.raises(ValueError, match="56"):
        validate_shifts([event] * 57, date(2026, 9, 7), "Europe/Istanbul")

    with pytest.raises(ValueError, match="week"):
        validate_shifts(
            [{"start": "2026-09-14T00:00:00", "end": "2026-09-14T01:00:00"}],
            date(2026, 9, 7),
            "Europe/Istanbul",
        )


def test_validate_shifts_detects_overlap_at_same_instant_across_offsets():
    with pytest.raises(ValueError, match="overlap"):
        validate_shifts(
            [
                {"start": "2026-09-07T09:00:00+03:00", "end": "2026-09-07T17:00:00+03:00"},
                {"start": "2026-09-07T06:30:00Z", "end": "2026-09-07T07:30:00Z"},
            ],
            date(2026, 9, 7),
            "Europe/Istanbul",
        )


def test_validate_shifts_allows_touching_events_but_rejects_ambiguous_naive_time():
    events = validate_shifts(
        [
            {"start": "2026-09-07T09:00:00", "end": "2026-09-07T10:00:00"},
            {"start": "2026-09-07T10:00:00", "end": "2026-09-07T11:00:00"},
        ],
        date(2026, 9, 7),
        "Europe/Istanbul",
    )
    assert len(events) == 2

    with pytest.raises(ValueError, match="ambiguous"):
        validate_shifts(
            [{"start": "2026-11-01T01:30:00", "end": "2026-11-01T03:30:00"}],
            date(2026, 10, 26),
            "America/New_York",
        )
