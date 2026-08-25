"""
ICS Generator Service
ICS takvim dosyası oluşturma işlemleri
"""

from typing import List, Tuple
from datetime import datetime


def generate_ics_header() -> str:
    """ICS dosya başlığını oluşturur"""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ShiftScan//TR
CALSCALE:GREGORIAN
"""


def generate_ics_event(
    uid: str,
    start: datetime,
    end: datetime,
    summary: str,
    description: str = ""
) -> str:
    """
    Tek bir ICS event oluşturur
    
    Args:
        uid: Unique identifier
        start: Başlangıç zamanı
        end: Bitiş zamanı
        summary: Etkinlik adı
        description: Açıklama (opsiyonel)
    
    Returns:
        ICS event string
    """
    event = f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{summary}
"""
    if description:
        event += f"DESCRIPTION:{description}\n"
    
    event += "END:VEVENT\n"
    return event


def generate_final_ics(
    timeline: List[Tuple[datetime, datetime, str]],
    activity_events: List[Tuple[datetime, datetime, str]]
) -> str:
    """
    Timeline ve aktivitelerden son ICS'i oluştur (Floating Time - Europe/Istanbul)
    
    Args:
        timeline: Vardiya ve uyku blokları
        activity_events: Aktivite etkinlikleri
    
    Returns:
        Tam ICS dosya içeriği
    """
    ics = generate_ics_header()
    
    # Timeline bloklarını ekle (vardiya + uyku)
    for start, end, block_type in timeline:
        summary = "Vardiya" if block_type == "shift" else "Uyku"
        uid = f"{block_type}-{start.strftime('%Y%m%d%H%M')}"
        ics += generate_ics_event(uid, start, end, summary)
    
    # Aktivite olaylarını ekle
    for start, end, activity_name in activity_events:
        uid = f"activity-{start.strftime('%Y%m%d%H%M')}"
        ics += generate_ics_event(uid, start, end, activity_name)
    
    ics += "END:VCALENDAR"
    return ics
