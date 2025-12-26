"""
Vardiya Parser Service
Metin ve görsel verilerinden vardiya bilgilerini çıkarır
"""

from typing import List, Dict, Optional
from datetime import datetime
import re


# Gün haritası
DAY_MAP = {
    'pzt': 0, 'pazartesi': 0, 'mon': 0, 'monday': 0,
    'sal': 1, 'salı': 1, 'sali': 1, 'tue': 1, 'tuesday': 1,
    'çar': 2, 'çarşamba': 2, 'carsamba': 2, 'wed': 2, 'wednesday': 2,
    'per': 3, 'perşembe': 3, 'persembe': 3, 'thu': 3, 'thursday': 3,
    'cum': 4, 'cuma': 4, 'fri': 4, 'friday': 4,
    'cmt': 5, 'cumartesi': 5, 'sat': 5, 'saturday': 5,
    'paz': 6, 'pazar': 6, 'sun': 6, 'sunday': 6
}

# İzin anahtar kelimeleri
IGNORE_KEYWORDS = ['off', 'izin', 'İzin', 'boş', 'bos', 'tatil', 'yıllık', 'rapor', 'leave', 'holiday']

# Gün isimleri (Türkçe)
DAY_NAMES = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def parse_line_to_shifts(line: str) -> str:
    """HAM OCR metnini vardiya formatına çevirir"""
    line = line.replace('\n', ' ')

    combined_regex = r'(\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2})|(OFF|İZİN|IZIN|BOŞ|BOS|TATİL|RAPOR)'
    matches = re.findall(combined_regex, line, re.IGNORECASE)
    
    if not matches or len(matches) == 0:
        return f"Vardiya formatı algılanamadı.\n{line}"

    days = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
    result = ""
    
    flat_matches = [m[0] or m[1] for m in matches]
    
    for index, match in enumerate(flat_matches[:7]):
        if index < len(days):
            clean_match = match.replace('.', ':').upper()
            result += f"{days[index]} {clean_match}\n"
    
    return result.strip()


def parse_text(text: str, base_date: datetime) -> List[Dict]:
    """
    Vardiya metnini parse edip event listesine çevirir
    
    Args:
        text: Vardiya metni
        base_date: Haftanın başlangıç tarihi (Pazartesi)
    
    Returns:
        List of event dictionaries
    """
    lines = text.split('\n')
    events = []
    
    day_regex = r'(Pzt|Pazartesi|Sal|Salı|Sali|Çar|Çarşamba|Carsamba|Per|Perşembe|Persembe|Cum|Cuma|Cmt|Cumartesi|Paz|Pazar|Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
    time_regex = r'(\d{1,2})[:.]?(\d{2})?\s*-\s*(\d{1,2})[:.]?(\d{2})?'

    for line in lines:
        lower_line = line.lower()
        day_match = re.search(day_regex, line, re.IGNORECASE)
        time_match = re.search(time_regex, line)

        if day_match:
            day_name = day_match.group(0).lower()
            day_index = -1
            
            for key, val in DAY_MAP.items():
                if day_name.startswith(key):
                    day_index = val
                    break

            if day_index != -1:
                from datetime import timedelta
                event_date = base_date + timedelta(days=day_index)
                
                is_off = any(kw.lower() in lower_line for kw in IGNORE_KEYWORDS)

                if not is_off and time_match:
                    start_h = int(time_match.group(1))
                    start_m = int(time_match.group(2)) if time_match.group(2) else 0
                    end_h = int(time_match.group(3))
                    end_m = int(time_match.group(4)) if time_match.group(4) else 0

                    end_date = event_date
                    if end_h < start_h or (end_h == start_h and end_m < start_m):
                        end_date = event_date + timedelta(days=1)

                    start_datetime = datetime.combine(event_date, datetime.min.time())
                    start_datetime = start_datetime.replace(hour=start_h, minute=start_m)
                    
                    end_datetime = datetime.combine(end_date, datetime.min.time())
                    end_datetime = end_datetime.replace(hour=end_h, minute=end_m)

                    events.append({
                        'title': 'Vardiya',
                        'start': start_datetime,
                        'end': end_datetime,
                        'original_line': line.strip()
                    })
    
    return events


def get_day_index(day_name: str) -> int:
    """Gün adından index döndürür"""
    day_name_lower = day_name.lower()
    for key, val in DAY_MAP.items():
        if day_name_lower.startswith(key):
            return val
    return -1


def get_day_name(index: int) -> str:
    """Index'ten gün adı döndürür"""
    if 0 <= index < len(DAY_NAMES):
        return DAY_NAMES[index]
    return ""
