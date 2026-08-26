"""
ICS Generator Service
RFC 5545 uyumlu ICS takvim dosyasi olusturma islemleri
"""

from typing import List, Tuple
from datetime import datetime, timezone
from services.models import CalendarLabels

# RFC 5545 icerik satiri siniri: 75 oktet (CRLF haric)
MAX_LINE_OCTETS = 75


def escape_text(value: str) -> str:
    """RFC 5545 TEXT kacisi: ters bolu, noktali virgul, virgul ve satir sonu.

    Kacis olmadan bir aktivite adindaki satir sonu yeni bir ICS ozelligi
    enjekte edebilir; ters bolu once kacirilmalidir.
    """
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )


def fold_line(line: str) -> str:
    """Uzun icerik satirini 75 oktette katlar; devam satirlari bosluk ile baslar."""
    encoded = line.encode("utf-8")
    if len(encoded) <= MAX_LINE_OCTETS:
        return line

    chunks: List[str] = []
    current = ""
    current_octets = 0
    limit = MAX_LINE_OCTETS

    for char in line:
        char_octets = len(char.encode("utf-8"))
        if current_octets + char_octets > limit:
            chunks.append(current)
            current = char
            current_octets = char_octets
            limit = MAX_LINE_OCTETS - 1  # devam satirlarinda bastaki bosluk sayilir
        else:
            current += char
            current_octets += char_octets

    chunks.append(current)
    return "\r\n ".join(chunks)


def generate_ics_header() -> str:
    """ICS dosya basligini olusturur"""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ShiftScan//TR",
        "CALSCALE:GREGORIAN",
    ]
    return "".join(line + "\r\n" for line in lines)


def generate_ics_event(
    uid: str,
    start: datetime,
    end: datetime,
    summary: str,
    description: str = "",
    dtstamp: datetime = None
) -> str:
    """
    Tek bir ICS event olusturur

    Args:
        uid: Unique identifier
        start: Baslangic zamani (floating local time)
        end: Bitis zamani (floating local time)
        summary: Etkinlik adi
        description: Aciklama (opsiyonel)
        dtstamp: Olusturulma damgasi (UTC); verilmezse simdiki zaman

    Returns:
        ICS event string
    """
    stamp = dtstamp or datetime.now(timezone.utc)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{escape_text(uid)}",
        f"DTSTAMP:{stamp.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{escape_text(summary)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{escape_text(description)}")
    lines.append("END:VEVENT")

    return "".join(fold_line(line) + "\r\n" for line in lines)


def generate_final_ics(
    timeline: List[Tuple[datetime, datetime, str]],
    activity_events: List[Tuple[datetime, datetime, str]],
    labels: CalendarLabels
) -> str:
    """
    Timeline ve aktivitelerden son ICS'i olustur (floating local time)

    Args:
        timeline: Vardiya ve uyku bloklari
        activity_events: Aktivite etkinlikleri
        labels: Vardiya ve uyku blok etiketleri

    Returns:
        Tam ICS dosya icerigi
    """
    stamp = datetime.now(timezone.utc)
    ics = generate_ics_header()

    # Timeline bloklarini ekle (vardiya + uyku)
    for index, (start, end, block_type) in enumerate(timeline):
        summary = labels.shift if block_type == "shift" else labels.sleep
        uid = f"{block_type}-{start.strftime('%Y%m%d%H%M')}-{index}@shiftscan"
        ics += generate_ics_event(uid, start, end, summary, dtstamp=stamp)

    # Aktivite olaylarini ekle
    for index, (start, end, activity_name) in enumerate(activity_events):
        uid = f"activity-{start.strftime('%Y%m%d%H%M')}-{index}@shiftscan"
        ics += generate_ics_event(uid, start, end, activity_name, dtstamp=stamp)

    ics += "END:VCALENDAR\r\n"
    return ics
