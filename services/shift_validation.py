"""Vardiya istekleri icin paylasilan model ve liste dogrulamasi."""

from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, model_validator


MAX_SHIFTS = 56
MAX_SHIFT_HOURS = 24
UTC = datetime_timezone.utc


def _parse_datetime(value: str) -> datetime:
    """ISO tarih-saatini ``Z`` son eki dahil ayrıştırır."""

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ShiftEvent(BaseModel):
    """Dis API'de ISO tarih-saatleri string olarak korunan vardiya."""

    model_config = {"extra": "forbid"}

    start: str
    end: str

    @model_validator(mode="after")
    def dates_are_ordered_and_bounded(self):
        try:
            start = _parse_datetime(self.start)
            end = _parse_datetime(self.end)
        except (TypeError, ValueError) as exc:
            raise ValueError("start and end must be ISO datetimes") from exc

        if (start.tzinfo is None) != (end.tzinfo is None):
            raise ValueError("start and end must use the same timezone style")
        comparable_start = start.astimezone(UTC) if start.tzinfo is not None else start
        comparable_end = end.astimezone(UTC) if end.tzinfo is not None else end
        if comparable_end <= comparable_start:
            raise ValueError("end must be after start")
        if comparable_end - comparable_start > timedelta(hours=MAX_SHIFT_HOURS):
            raise ValueError("shift must not exceed 24 hours")
        return self


def _in_timezone(value: str, target: ZoneInfo) -> datetime:
    parsed = _parse_datetime(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(target)

    candidates = [parsed.replace(tzinfo=target, fold=fold) for fold in (0, 1)]
    valid = [
        candidate
        for candidate in candidates
        if candidate.astimezone(UTC).astimezone(target).replace(tzinfo=None) == parsed
    ]
    if not valid:
        raise ValueError("naive datetime does not exist in target timezone")
    if len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset():
        raise ValueError("naive datetime is ambiguous in target timezone")
    return valid[0]


def validate_shifts(events: list[dict[str, Any]], week_start: date, timezone: str) -> list[ShiftEvent]:
    """Vardiyaların adet, hafta ve çakışma sınırlarını doğrular."""

    if len(events) > MAX_SHIFTS:
        raise ValueError(f"at most {MAX_SHIFTS} shifts are allowed")
    try:
        target = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("unknown timezone") from exc

    week_begin = datetime.combine(week_start, time.min, target)
    week_end = week_begin + timedelta(days=7)
    result: list[ShiftEvent] = []
    intervals: list[tuple[datetime, datetime]] = []
    for raw_event in events:
        event = ShiftEvent.model_validate(raw_event)
        start = _in_timezone(event.start, target)
        end = _in_timezone(event.end, target)
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        if end_utc <= start_utc:
            raise ValueError("end must be after start")
        if end_utc - start_utc > timedelta(hours=MAX_SHIFT_HOURS):
            raise ValueError("shift must not exceed 24 hours")
        if not week_begin <= start < week_end:
            raise ValueError("shift start must be inside the requested week")
        if end > week_end and start.date() != (week_start + timedelta(days=6)):
            raise ValueError("shift end must be inside the requested week")
        result.append(event)
        intervals.append((start_utc, end_utc))

    intervals.sort(key=lambda item: item[0])
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] < previous[1]:
            raise ValueError("shifts overlap")
    return result
