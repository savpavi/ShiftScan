"""ActivityGoal ve CalendarLabels dogrulama sinirlari."""

import pytest
from pydantic import ValidationError

from services.models import (
    DEFAULT_SESSION_HOURS,
    MAX_ACTIVITIES,
    PREFERRED_WINDOWS,
    ActivityGoal,
    CalendarLabels,
)


def goal(**overrides):
    base = {"id": "a1", "name": "Sport", "amount": 3, "unit": "days"}
    base.update(overrides)
    return base


def test_preferred_defaults_to_any():
    assert ActivityGoal(**goal()).preferred == "any"


def test_unit_must_be_hours_or_days():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(unit="weeks"))


def test_amount_must_be_positive():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(amount=0))


def test_amount_cannot_exceed_a_full_week():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(amount=169))


def test_name_cannot_be_empty():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(name=""))


def test_name_length_is_bounded():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(name="x" * 81))


def test_preferred_must_be_a_known_window():
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(preferred="midnight"))


def test_activity_goal_rejects_unknown_field():
    """Bir yazim hatasi (orn. 'prefered') sessizce yutulmamali."""
    with pytest.raises(ValidationError):
        ActivityGoal(**goal(prefered="evening"))


def test_labels_have_neutral_defaults():
    labels = CalendarLabels()

    assert labels.shift == "Shift"
    assert labels.sleep == "Sleep"


def test_label_cannot_be_empty():
    with pytest.raises(ValidationError):
        CalendarLabels(shift="", sleep="Sleep")


def test_calendar_labels_rejects_unknown_field():
    with pytest.raises(ValidationError):
        CalendarLabels(shift="Shift", sleep="Sleep", extra_field="oops")


def test_every_preferred_value_except_any_has_a_window():
    for value in ("morning", "afternoon", "evening"):
        start, end = PREFERRED_WINDOWS[value]
        assert 0 <= start < end <= 24

    assert "any" not in PREFERRED_WINDOWS


def test_module_constants_match_the_spec():
    assert MAX_ACTIVITIES == 20
    assert DEFAULT_SESSION_HOURS == 1.0
