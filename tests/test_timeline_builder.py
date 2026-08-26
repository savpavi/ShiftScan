"""find_free_slots davranış testleri."""

from datetime import date, datetime

import pytest
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
    return {day_index for day_index, _, _ in free_slots}


def test_day_without_shift_still_yields_a_free_slot():
    """Izin gunu planlamadan dusmemeli - uygulamanin ana kullanim senaryosu."""
    timeline = build_timeline([day_shift(d) for d in range(24, 29)], "Europe/Istanbul")  # Pzt-Cum

    free_slots = find_free_slots(timeline, WEEK_START, "Europe/Istanbul")

    assert 5 in days_with_slots(free_slots)
    assert 6 in days_with_slots(free_slots)


def test_free_day_slot_starts_at_seven_not_midnight():
    """Bos gunde de gece saatleri (00:00-07:00) aktiviteye acilmamali."""
    timeline = build_timeline([day_shift(24)], "Europe/Istanbul")  # sadece Pazartesi

    saturday = [s for s in find_free_slots(timeline, WEEK_START, "Europe/Istanbul") if s[0] == 5]

    assert len(saturday) == 1
    _, start, end = saturday[0]
    assert start.hour == 7 and start.minute == 0
    assert end == IST.localize(datetime(2026, 8, 30, 0, 0))  # Pazar 00:00 (exclusive)


def test_week_follows_start_date_not_first_shift():
    """Hafta start_date'ten kurulmali; ilk vardiya Persembe olsa da Pzt-Paz uretilmeli."""
    timeline = build_timeline([day_shift(27)], "Europe/Istanbul")  # Persembe

    slots = find_free_slots(timeline, WEEK_START, "Europe/Istanbul")

    assert days_with_slots(slots) == set(range(7))


def test_night_hours_excluded_on_normal_shift_day():
    """Gece vardiyasi olmayan gunde 00:00-07:00 arasi slot uretilmemeli (regresyon)."""
    timeline = build_timeline([day_shift(24)], "Europe/Istanbul")

    monday = [s for s in find_free_slots(timeline, WEEK_START, "Europe/Istanbul") if s[0] == 0]

    assert monday, "Pazartesi icin slot bekleniyordu"
    assert all(start.hour >= 7 for _, start, _ in monday)


# --- Uyku blogu ve gece filtresi (backlog madde 7 ve 9) ---


def local_shift(start_day: int, start_hour: int, end_day: int, end_hour: int) -> dict:
    """Yerel saatle (TRT) vardiya - gece vardiyasi iki gune yayilabilir."""
    return {
        "start": f"2026-08-{start_day:02d}T{start_hour:02d}:00:00+03:00",
        "end": f"2026-08-{end_day:02d}T{end_hour:02d}:00:00+03:00",
    }


def sleep_blocks(timeline):
    return [(s, e) for s, e, kind in timeline if kind == "sleep"]


def test_sleep_falls_on_the_night_after_the_shift_not_before_it():
    """Pazartesi 09-18 calisan kisi Sali'ye baglayan gece uyur, Pazartesi sabahi degil."""
    timeline = build_timeline([local_shift(24, 9, 24, 18)], "Europe/Istanbul")

    (start, end), = sleep_blocks(timeline)

    assert start == IST.localize(datetime(2026, 8, 25, 0, 30))
    assert end == IST.localize(datetime(2026, 8, 25, 8, 30))


def test_consecutive_shifts_do_not_produce_overlapping_sleep():
    """Sali aksam + Carsamba gunduz vardiyasi ayni geceye iki uyku yazmamali."""
    timeline = build_timeline([local_shift(25, 14, 25, 22), local_shift(26, 9, 26, 18)], "Europe/Istanbul")

    blocks = sorted(sleep_blocks(timeline))

    for (_, first_end), (second_start, _) in zip(blocks, blocks[1:]):
        assert first_end <= second_start, f"{first_end} > {second_start}"


def test_overnight_shift_sleeps_the_morning_it_ends():
    """Gece vardiyasi (Sali 23:00 -> Carsamba 07:00) Carsamba sabahi uyunur."""
    timeline = build_timeline([local_shift(25, 23, 26, 7)], "Europe/Istanbul")

    (start, end), = sleep_blocks(timeline)

    assert start == IST.localize(datetime(2026, 8, 26, 8, 0))
    assert end == IST.localize(datetime(2026, 8, 26, 16, 0))


def test_evening_shift_day_keeps_the_night_restriction():
    """14:00-22:00 aksam vardiyasi gece vardiyasi degil; o gun de 07:00 kisiti gecerli."""
    timeline = build_timeline([local_shift(25, 14, 25, 22)], "Europe/Istanbul")

    tuesday = [s for s in find_free_slots(timeline, WEEK_START, "Europe/Istanbul") if s[0] == 1]

    assert tuesday, "Sali icin slot bekleniyordu"
    assert all(start.hour >= 7 for _, start, _ in tuesday)


def test_overnight_shift_day_yields_a_slot_after_waking():
    """Gece vardiyasindan cikan kisi uyandiktan sonra bos zamana sahip olmali."""
    timeline = build_timeline([local_shift(25, 23, 26, 7)], "Europe/Istanbul")

    wednesday = [s for s in find_free_slots(timeline, WEEK_START, "Europe/Istanbul") if s[0] == 2]

    assert any(start >= IST.localize(datetime(2026, 8, 26, 16, 0)) for _, start, _ in wednesday)
    assert all(start.hour >= 7 for _, start, _ in wednesday)


def test_timezone_parameter_controls_local_time():
    """Ayni anlik zaman, farkli bolgede farkli yerel saate dusmeli."""
    events = [
        {
            "start": "2026-08-24T06:00:00Z",
            "end": "2026-08-24T15:00:00Z",
        }
    ]

    istanbul = build_timeline(events, "Europe/Istanbul")
    london = build_timeline(events, "Europe/London")

    istanbul_shift = next(s for s, _, kind in istanbul if kind == "shift")
    london_shift = next(s for s, _, kind in london if kind == "shift")

    assert istanbul_shift.hour == 9
    assert london_shift.hour == 7


def test_unknown_timezone_is_rejected():
    with pytest.raises(pytz.UnknownTimeZoneError):
        build_timeline([day_shift(24)], "Mars/Olympus")


def test_free_slots_are_keyed_by_day_index():
    """Backend dil bagimsiz: gun adi degil 0-6 indeksi doner."""
    timeline = build_timeline([day_shift(24)], "Europe/Istanbul")

    slots = find_free_slots(timeline, WEEK_START, "Europe/Istanbul")

    indices = {day for day, _, _ in slots}
    assert indices <= set(range(7))
    assert 0 in indices  # Pazartesi
    assert all(isinstance(day, int) for day, _, _ in slots)
