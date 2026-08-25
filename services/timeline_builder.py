"""
Timeline Builder Service
Vardiya ve uyku bloklarından zaman çizelgesi oluşturur
"""

from typing import List, Tuple, Dict
from datetime import date, datetime, time, timedelta
import pytz

from .shift_parser import DAY_NAMES

# Gece aktivite yasagi: bu saatten once slot uretilmez (gece vardiyasi gunleri haric)
NIGHT_END_HOUR = 7


def build_timeline(shift_events: List[Dict]) -> List[Tuple[datetime, datetime, str]]:
    """
    Vardiya ve uyku bloklarından timeline oluştur (Europe/Istanbul timezone)
    
    Args:
        shift_events: ShiftEvent listesi (dict formatında)
    
    Returns:
        Timeline listesi: [(start, end, block_type), ...]
    """
    timeline = []
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    
    for event in shift_events:
        # ISO string'i datetime'a çevir (UTC'den geliyor)
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        
        # UTC'den Istanbul'a çevir
        if start_dt.tzinfo is not None:
            start_dt = start_dt.astimezone(istanbul_tz)
        else:
            start_dt = istanbul_tz.localize(start_dt)
            
        if end_dt.tzinfo is not None:
            end_dt = end_dt.astimezone(istanbul_tz)
        else:
            end_dt = istanbul_tz.localize(end_dt)
        
        # Vardiya bloğu
        timeline.append((start_dt, end_dt, "shift"))
        
        # İNSANİ UYKU MANTIĞI
        shift_end_hour = end_dt.hour
        
        if shift_end_hour < 22:  # 22:00'den önce biten vardiyalar
            # O günün gecesine uyku (00:30 - 08:30)
            sleep_date = end_dt.date()
            sleep_start = istanbul_tz.localize(datetime.combine(sleep_date, datetime.min.time()).replace(hour=0, minute=30))
            sleep_end = sleep_start + timedelta(hours=8)  # 00:30 - 08:30
        else:  # 22:00'den sonra biten vardiyalar
            # İş çıkışından 1 saat sonra uyku
            sleep_start = end_dt + timedelta(hours=1)
            sleep_end = sleep_start + timedelta(hours=8)
        
        timeline.append((sleep_start, sleep_end, "sleep"))
    
    # Kronolojik sırala
    timeline.sort(key=lambda x: x[0])
    return timeline


def find_free_slots(
    timeline: List[Tuple[datetime, datetime, str]],
    week_start: date,
) -> List[Tuple[str, datetime, datetime]]:
    """
    Timeline'daki bos zaman slotlarini bul (Europe/Istanbul timezone)

    Hafta, ilk vardiyadan degil acikca verilen week_start'tan kurulur; boylece
    hic vardiyasi olmayan izin gunleri de planlamaya dahil olur.

    Gece aktivite yasagi: gunun ilk slotu NIGHT_END_HOUR'dan once baslamaz.
    Gece vardiyasi biten gunlerde bu kisit uygulanmaz.

    Args:
        timeline: Timeline listesi
        week_start: Haftanin ilk gunu (Pazartesi)

    Returns:
        Free slots listesi: [(day_name, start, end), ...]
    """
    free_slots = []
    istanbul_tz = pytz.timezone('Europe/Istanbul')

    # Gece vardiyasi biten gunlerde gece kisiti devre disi
    night_shift_days = {
        end.date()
        for start, end, block_type in timeline
        if block_type == "shift" and end.hour >= 22
    }

    for day_offset in range(7):
        current_day = week_start + timedelta(days=day_offset)
        day_name = DAY_NAMES[day_offset]

        # Gun sinirlari: [00:00, ertesi gun 00:00) - yarim acik aralik
        day_start = istanbul_tz.localize(datetime.combine(current_day, time.min))
        day_end = istanbul_tz.localize(
            datetime.combine(current_day + timedelta(days=1), time.min)
        )

        if current_day in night_shift_days:
            earliest = day_start
        else:
            earliest = istanbul_tz.localize(
                datetime.combine(current_day, time(hour=NIGHT_END_HOUR))
            )

        # O gune denk gelen bloklari gun sinirlarina kirp
        day_blocks = sorted(
            (
                (max(start, day_start), min(end, day_end), block_type)
                for start, end, block_type in timeline
                if start < day_end and end > day_start
            ),
            key=lambda block: block[0],
        )

        cursor = earliest
        for block_start, block_end, _ in day_blocks:
            if block_start > cursor:
                free_slots.append((day_name, cursor, block_start))
            cursor = max(cursor, block_end)

        if cursor < day_end:
            free_slots.append((day_name, cursor, day_end))

    return free_slots
