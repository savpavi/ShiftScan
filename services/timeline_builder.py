"""
Timeline Builder Service
Vardiya ve uyku bloklarından zaman çizelgesi oluşturur
"""

from typing import List, Tuple, Dict
from datetime import date, datetime, time, timedelta
import pytz

# Gece aktivite yasagi: bu saatten once slot uretilmez
NIGHT_END_HOUR = 7


def build_timeline(
    shift_events: List[Dict], timezone: str
) -> List[Tuple[datetime, datetime, str]]:
    """
    Vardiya ve uyku bloklarından timeline oluştur

    Args:
        shift_events: ShiftEvent listesi (dict formatında)
        timezone: Zaman dilimi (pytz formatında, örneğin 'Europe/Istanbul')

    Returns:
        Timeline listesi: [(start, end, block_type), ...]
    """
    timeline = []
    local_tz = pytz.timezone(timezone)
    
    for event in shift_events:
        # ISO string'i datetime'a çevir (UTC'den geliyor)
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))

        # UTC'den hedef zaman dilimine çevir
        if start_dt.tzinfo is not None:
            start_dt = start_dt.astimezone(local_tz)
        else:
            start_dt = local_tz.localize(start_dt)

        if end_dt.tzinfo is not None:
            end_dt = end_dt.astimezone(local_tz)
        else:
            end_dt = local_tz.localize(end_dt)
        
        # Vardiya bloğu
        timeline.append((start_dt, end_dt, "shift"))
        
        # INSANI UYKU MANTIGI
        # Uyku her zaman vardiyayi *izleyen* dinlenmedir, oncesindeki degil.
        overnight = start_dt.date() != end_dt.date()  # gece vardiyasi, ertesi sabah biter

        if overnight or end_dt.hour >= 22:
            # Is cikisindan 1 saat sonra uyku (gece vardiyasindan cikan kisi
            # ayni sabah uyur, gec biten vardiyanin uykusu da hemen ardindan gelir)
            sleep_start = end_dt + timedelta(hours=1)
        else:
            # Normal gunduz/aksam vardiyasi: vardiyayi izleyen gece 00:30
            sleep_start = local_tz.localize(
                datetime.combine(end_dt.date() + timedelta(days=1), time(hour=0, minute=30))
            )

        sleep_end = sleep_start + timedelta(hours=8)
        timeline.append((sleep_start, sleep_end, "sleep"))
    
    # Kronolojik sırala
    timeline.sort(key=lambda x: x[0])
    return timeline


def find_free_slots(
    timeline: List[Tuple[datetime, datetime, str]],
    week_start: date,
    timezone: str,
) -> List[Tuple[int, datetime, datetime]]:
    """
    Timeline'daki bos zaman slotlarini bul

    Hafta, ilk vardiyadan degil acikca verilen week_start'tan kurulur; boylece
    hic vardiyasi olmayan izin gunleri de planlamaya dahil olur.

    Gece aktivite yasagi: gunun ilk slotu NIGHT_END_HOUR'dan once baslamaz.

    Args:
        timeline: Timeline listesi
        week_start: Haftanin ilk gunu (Pazartesi)
        timezone: Zaman dilimi (pytz formatında, örneğin 'Europe/Istanbul')

    Returns:
        Free slots listesi: [(day_index, start, end), ...] - day_index 0-6, Pazartesi=0
    """
    free_slots = []
    local_tz = pytz.timezone(timezone)

    for day_offset in range(7):
        current_day = week_start + timedelta(days=day_offset)

        # Gun sinirlari: [00:00, ertesi gun 00:00) - yarim acik aralik
        day_start = local_tz.localize(datetime.combine(current_day, time.min))
        day_end = local_tz.localize(
            datetime.combine(current_day + timedelta(days=1), time.min)
        )

        # Gece kisiti her gun gecerli. Gece vardiyasinin kendisi zaten bir blok
        # oldugu icin ayri bir istisna gerekmiyor; onceki kural aksam vardiyasini
        # gece vardiyasi sanip tum geceyi aktiviteye aciyordu.
        earliest = local_tz.localize(
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
                free_slots.append((day_offset, cursor, block_start))
            cursor = max(cursor, block_end)

        if cursor < day_end:
            free_slots.append((day_offset, cursor, day_end))

    return free_slots
