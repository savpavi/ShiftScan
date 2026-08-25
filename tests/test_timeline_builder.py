"""find_free_slots davranış testleri."""

from datetime import date, datetime

import pytz

from services.timeline_builder import build_timeline, find_free_slots

IST = pytz.timezone("Europe/Istanbul")
WEEK_START = date(2026, 8, 24)  # Pazartesi


def day_shift(day: int, start_utc: str = "06:00", end_utc: str = "15:00") -> dict:
    """2026-08-{day} icin UTC ISO formatinda vardiya (09:00-18:00 TRT)."""
    return {
        "start": f"2026-08-{day:02d}T{start_utc}:00Z",
        "end": f"2026-08-{day:02d}T{end_utc}:00Z",
    }


def days_with_slots(free_slots) -> set:
    return {day_name for day_name, _, _ in free_slots}


def test_day_without_shift_still_yields_a_free_slot():
    """Izin gunu planlamadan dusmemeli - uygulamanin ana kullanim senaryosu."""
    timeline = build_timeline([day_shift(d) for d in range(24, 29)])  # Pzt-Cum

    free_slots = find_free_slots(timeline, WEEK_START)

    assert "Cumartesi" in days_with_slots(free_slots)
    assert "Pazar" in days_with_slots(free_slots)


def test_free_day_slot_starts_at_seven_not_midnight():
    """Bos gunde de gece saatleri (00:00-07:00) aktiviteye acilmamali."""
    timeline = build_timeline([day_shift(24)])  # sadece Pazartesi

    saturday = [s for s in find_free_slots(timeline, WEEK_START) if s[0] == "Cumartesi"]

    assert len(saturday) == 1
    _, start, end = saturday[0]
    assert start.hour == 7 and start.minute == 0
    assert end == IST.localize(datetime(2026, 8, 30, 0, 0))  # Pazar 00:00 (exclusive)


def test_week_follows_start_date_not_first_shift():
    """Hafta start_date'ten kurulmali; ilk vardiya Persembe olsa da Pzt-Paz uretilmeli."""
    timeline = build_timeline([day_shift(27)])  # Persembe

    slots = find_free_slots(timeline, WEEK_START)

    assert days_with_slots(slots) == {
        "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar",
    }


def test_night_hours_excluded_on_normal_shift_day():
    """Gece vardiyasi olmayan gunde 00:00-07:00 arasi slot uretilmemeli (regresyon)."""
    timeline = build_timeline([day_shift(24)])

    monday = [s for s in find_free_slots(timeline, WEEK_START) if s[0] == "Pazartesi"]

    assert monday, "Pazartesi icin slot bekleniyordu"
    assert all(start.hour >= 7 for _, start, _ in monday)
