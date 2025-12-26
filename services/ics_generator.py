"""
ICS Generator Service
ICS takvim dosyası oluşturma işlemleri
"""

from typing import List, Tuple, Dict
from datetime import datetime


def generate_ics_header() -> str:
    """ICS dosya başlığını oluşturur"""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Vardiya Takvimi//TR
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


def generate_simple_ics(events: List[Dict]) -> str:
    """
    Basit vardiya ICS'i oluştur (AI olmadan)
    
    Args:
        events: Event listesi (title, start, end, original_line)
    
    Returns:
        ICS dosya içeriği
    """
    ics = generate_ics_header()
    
    for i, event in enumerate(events):
        start = event.get('start')
        end = event.get('end')
        title = event.get('title', 'Vardiya')
        original_line = event.get('original_line', '')
        
        uid = f"vardiya-{start.strftime('%Y%m%dT%H%M%S')}" if isinstance(start, datetime) else f"vardiya-{i}"
        
        if isinstance(start, datetime) and isinstance(end, datetime):
            ics += generate_ics_event(uid, start, end, title, original_line)
    
    ics += "END:VCALENDAR"
    return ics


def format_ics_date(date: datetime) -> str:
    """Datetime'ı ICS formatına çevirir"""
    return date.strftime('%Y%m%dT%H%M%S')


def clean_ics_response(response_text: str) -> str:
    """Gemini yanıtını temizleyerek saf ICS formatı elde eder"""
    
    # Code block işaretlerini kaldır
    if "```" in response_text:
        lines = response_text.split('\n')
        ics_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line.strip().startswith('```'):
                ics_lines.append(line)
        
        response_text = '\n'.join(ics_lines)
    
    # BEGIN:VCALENDAR ile başlayan kısmı al
    if "BEGIN:VCALENDAR" in response_text:
        start_idx = response_text.find("BEGIN:VCALENDAR")
        response_text = response_text[start_idx:]
    
    # END:VCALENDAR ile biten kısmı al
    if "END:VCALENDAR" in response_text:
        end_idx = response_text.rfind("END:VCALENDAR") + len("END:VCALENDAR")
        response_text = response_text[:end_idx]
    
    return response_text.strip()
