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
    from services.models import CalendarLabels

    return generate_final_ics(TIMELINE, ACTIVITIES, CalendarLabels(shift="Vardiya", sleep="Uyku"))


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
    # floating time: DTSTART/DTEND'de UTC isareti yok (DTSTAMP haric)
    stamps = [ln for ln in ics.splitlines() if ln.startswith(("DTSTART:", "DTEND:"))]
    assert stamps and not any(ln.endswith("Z") for ln in stamps)


def test_events_have_unique_uids():
    ics = generate()

    uids = [line for line in ics.splitlines() if line.startswith("UID:")]
    assert len(uids) == ics.count("BEGIN:VEVENT")
    assert len(set(uids)) == len(uids)


# --- RFC 5545 uyumu (backlog madde 6) ---


def test_special_characters_in_summary_are_escaped():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics([], [(dt(24, 18), dt(24, 20), "Spor, Kitap; Oyun")], CalendarLabels())

    assert "SUMMARY:Spor\\, Kitap\\; Oyun" in ics


def test_backslash_in_summary_is_escaped_first():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics([], [(dt(24, 18), dt(24, 20), "C:\\Plan")], CalendarLabels())

    assert "SUMMARY:C:\\\\Plan" in ics


def test_newline_in_summary_cannot_inject_a_property():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics([], [(dt(24, 18), dt(24, 20), "Spor\nDESCRIPTION:enjekte")], CalendarLabels())

    assert ics.count("BEGIN:VEVENT") == 1
    assert "\nDESCRIPTION:enjekte" not in ics
    assert "SUMMARY:Spor\\nDESCRIPTION:enjekte" in ics


def test_every_event_has_a_dtstamp():
    ics = generate()

    assert ics.count("DTSTAMP:") == ics.count("BEGIN:VEVENT")


def test_lines_are_folded_at_75_octets():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics([], [(dt(24, 18), dt(24, 20), "A" * 200)], CalendarLabels())

    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, line


def test_folded_continuation_lines_start_with_a_space():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics([], [(dt(24, 18), dt(24, 20), "A" * 200)], CalendarLabels())

    summary_lines = [ln for ln in ics.split("\r\n") if ln.startswith("SUMMARY:")]
    assert len(summary_lines) == 1
    index = ics.split("\r\n").index(summary_lines[0])
    assert ics.split("\r\n")[index + 1].startswith(" ")


def test_lines_end_with_crlf():
    ics = generate()

    assert "BEGIN:VCALENDAR\r\n" in ics
    assert "\n" not in ics.replace("\r\n", "")


def test_events_starting_in_the_same_minute_get_distinct_uids():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics(
        [], [(dt(24, 18), dt(24, 20), "Spor"), (dt(24, 18), dt(24, 19), "Kitap")], CalendarLabels()
    )

    uids = [ln for ln in ics.split("\r\n") if ln.startswith("UID:")]
    assert len(set(uids)) == 2


def test_block_labels_come_from_the_request():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics(
        TIMELINE, [], CalendarLabels(shift="Schicht", sleep="Schlaf")
    )

    assert "SUMMARY:Schicht" in ics
    assert "SUMMARY:Schlaf" in ics
    assert "SUMMARY:Vardiya" not in ics


def test_labels_are_escaped_like_any_other_text():
    from services.ics_generator import generate_final_ics
    from services.models import CalendarLabels

    ics = generate_final_ics(TIMELINE, [], CalendarLabels(shift="Work, shift", sleep="Sleep"))

    assert "SUMMARY:Work\\, shift" in ics
