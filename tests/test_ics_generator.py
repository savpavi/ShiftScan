"""generate_final_ics ciktisinin yapisi (ICS uretimi tekillestirilirken guvenlik agi)."""

from datetime import datetime

import pytz

IST = pytz.timezone("Europe/Istanbul")


def dt(day: int, hour: int, minute: int = 0):
    return IST.localize(datetime(2026, 8, day, hour, minute))


TIMELINE = [
    (dt(24, 0, 30), dt(24, 8, 30), "sleep"),
    (dt(24, 9), dt(24, 18), "shift"),
]
ACTIVITIES = [(dt(24, 18), dt(24, 20), "Spor")]


def generate():
    from services.ics_generator import generate_final_ics

    return generate_final_ics(TIMELINE, ACTIVITIES)


def test_calendar_is_wrapped_correctly():
    ics = generate()

    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "VERSION:2.0" in ics
    assert "CALSCALE:GREGORIAN" in ics


def test_every_block_becomes_an_event():
    ics = generate()

    assert ics.count("BEGIN:VEVENT") == len(TIMELINE) + len(ACTIVITIES)
    assert ics.count("END:VEVENT") == ics.count("BEGIN:VEVENT")


def test_block_types_map_to_summaries():
    ics = generate()

    assert "SUMMARY:Vardiya" in ics
    assert "SUMMARY:Uyku" in ics
    assert "SUMMARY:Spor" in ics


def test_local_times_are_emitted_without_timezone_suffix():
    ics = generate()

    assert "DTSTART:20260824T090000" in ics
    assert "DTEND:20260824T180000" in ics
    assert "Z\n" not in ics  # floating time, UTC isareti yok


def test_events_have_unique_uids():
    ics = generate()

    uids = [line for line in ics.splitlines() if line.startswith("UID:")]
    assert len(uids) == ics.count("BEGIN:VEVENT")
    assert len(set(uids)) == len(uids)
