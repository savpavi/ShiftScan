"""
Timeline Builder Service
Vardiya ve uyku bloklarından zaman çizelgesi oluşturur
"""

from typing import List, Tuple, Dict
from datetime import datetime, timedelta
import pytz


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
        start_str = event.get('start', event.start if hasattr(event, 'start') else '')
        end_str = event.get('end', event.end if hasattr(event, 'end') else '')
        
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
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


def find_free_slots(timeline: List[Tuple[datetime, datetime, str]]) -> List[Tuple[str, datetime, datetime]]:
    """
    Timeline'daki boş zaman slotlarını bul (Europe/Istanbul timezone) - INSOMNIA FİLTRESİ ile
    
    Args:
        timeline: Timeline listesi
    
    Returns:
        Free slots listesi: [(day_name, start, end), ...]
    """
    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    free_slots = []
    
    # Haftanın her günü için kontrol et
    base_date = timeline[0][0].date() if timeline else datetime.now().date()
    week_start = base_date - timedelta(days=base_date.weekday())
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    
    # O günki gece vardiyası var mı?
    night_shift_days = set()
    for start, end, block_type in timeline:
        if block_type == "shift" and end.hour >= 22:  # 22:00'den sonra biten vardiya
            night_shift_days.add(end.date())
    
    for day_offset in range(7):
        current_day = week_start + timedelta(days=day_offset)
        day_name = day_names[day_offset]
        
        # Günün başlangıcı ve sonu (Istanbul timezone)
        day_start = istanbul_tz.localize(datetime.combine(current_day, datetime.min.time()))
        day_end = istanbul_tz.localize(datetime.combine(current_day, datetime.max.time()))
        
        # O günki blokları filtrele
        day_blocks = [
            (max(start, day_start), min(end, day_end), block_type)
            for start, end, block_type in timeline
            if start < day_end and end > day_start
        ]
        day_blocks.sort(key=lambda x: x[0])
        
        # Boş slotları hesapla
        current_time = day_start
        for block_start, block_end, block_type in day_blocks:
            if current_time < block_start:
                potential_slot = (day_name, current_time, block_start)
                
                # INSOMNIA FİLTRESİ: Gece 00:00-07:00 arası slotları kontrol et
                slot_start_hour = current_time.hour
                slot_end_hour = block_start.hour
                
                # Eğer bu gece vardiyası günü DEĞİLSE ve slot geceye denk geliyorsa, atla
                is_night_shift_day = current_day in night_shift_days
                
                if not is_night_shift_day:
                    # Gece 00:00-07:00 arası slotları filtrele
                    if slot_start_hour >= 0 and slot_start_hour < 7:
                        current_time = block_end
                        continue
                    
                    # Eğer slot geceye sızıyorsa, kırp
                    if slot_start_hour < 7 and slot_end_hour > 7:
                        cropped_start = istanbul_tz.localize(datetime.combine(current_day, datetime.min.time()).replace(hour=7))
                        if cropped_start < block_start:
                            free_slots.append((day_name, cropped_start, block_start))
                    elif slot_start_hour >= 7:
                        free_slots.append(potential_slot)
                else:
                    free_slots.append(potential_slot)
                    
            current_time = max(current_time, block_end)
        
        # Gün sonuna kadar kalan boşluk
        if current_time < day_end:
            slot_start_hour = current_time.hour
            is_night_shift_day = current_day in night_shift_days
            
            if not is_night_shift_day and slot_start_hour >= 0 and slot_start_hour < 7:
                pass  # Gece slotunu atla
            else:
                free_slots.append((day_name, current_time, day_end))
    
    return free_slots
