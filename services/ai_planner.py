"""
AI Planner Service
Google Gemini API ile akıllı aktivite planlama
"""

from typing import Any, List, Tuple, Dict
from datetime import datetime, timedelta
import os
import json
import asyncio
import time

from pydantic import BaseModel, Field, ValidationError

# Gemini API yapılandırması opsiyonel
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


# Aktivite haritası
ACTIVITY_MAP = {
    'content-production': 'İçerik Üretimi',
    'sports': 'Spor',
    'reading': 'Kitap Okuma',
    'social': 'Sosyal Yaşam / Arkadaşlar',
    'gaming': 'Oyun / Dinlenme'
}


# Tek bir aktivite yerlestirmesi icin ust sinir (bir gunun tamami)
MAX_ACTIVITY_HOURS = 24


class ActivityPlanItem(BaseModel):
    """Modelin dondurdugu tek bir plan satiri."""

    day_index: int = Field(ge=0, le=6)
    activity: str
    hours: float = Field(gt=0, le=MAX_ACTIVITY_HOURS)


def parse_activity_plan(raw: Any) -> List[ActivityPlanItem]:
    """
    Dil modelinden gelen ham plan ciktisini dogrular.

    Model ciktisi guvenilmez: alan eksik olabilir, sayi string gelebilir,
    liste yerine dict donebilir. Gecerli satirlar korunur, gecersizler
    atlanir; hicbir durumda exception yukselmez.

    Args:
        raw: json.loads ciktisi (herhangi bir tip olabilir)

    Returns:
        Dogrulanmis plan satirlari (bos olabilir)
    """
    if not isinstance(raw, list):
        print(f"WARNING: Plan ciktisi liste degil ({type(raw).__name__}), yok sayildi")
        return []

    items: List[ActivityPlanItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            print(f"WARNING: Plan satiri dict degil ({type(entry).__name__}), atlandi")
            continue
        try:
            items.append(ActivityPlanItem(**entry))
        except ValidationError as exc:
            print(f"WARNING: Gecersiz plan satiri atlandi: {entry} ({exc.error_count()} hata)")

    return items


def is_gemini_configured() -> bool:
    """Gemini API'nin yapılandırılıp yapılandırılmadığını kontrol eder"""
    if not GEMINI_AVAILABLE:
        return False
    
    api_key = os.getenv("GOOGLE_API_KEY")
    return bool(api_key and api_key != "your_gemini_api_key_here")


def configure_gemini():
    """Gemini API'yi yapılandırır"""
    if not GEMINI_AVAILABLE:
        print("WARNING: google-generativeai package not installed")
        return False
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("WARNING: GOOGLE_API_KEY not found! Set API key in .env file.")
        return False
    
    genai.configure(api_key=api_key)
    print("SUCCESS: Google Gemini API configured")
    return True


def create_gemini_activity_prompt(
    free_slots: List[Tuple[int, datetime, datetime]],
    activities: Dict
) -> str:
    """
    Gemini için sadece aktivite dağılımı isteyen prompt oluşturur

    Args:
        free_slots: Boş zaman slotları
        activities: Aktivite hedefleri

    Returns:
        Prompt string
    """
    # Boş slotları özetle
    slot_summary = "FREE TIME (day index 0 = Monday):\n"
    day_totals = {}

    for day_index, start, end in free_slots:
        duration = (end - start).total_seconds() / 3600
        day_totals[day_index] = day_totals.get(day_index, 0) + duration

    for day_index in sorted(day_totals):
        slot_summary += f"- day {day_index}: {day_totals[day_index]:.1f} hours free\n"
    
    # Aktivite hedefleri
    activity_goals = "AKTİVİTE HEDEFLERİ:\n"
    
    for key, activity in activities.items():
        activity_name = ACTIVITY_MAP.get(key, key)
        # activity dict veya object olabilir
        activity_value = activity.get('value') if isinstance(activity, dict) else activity.value
        activity_type = activity.get('type') if isinstance(activity, dict) else activity.type
        unit = 'gün' if activity_type == 'days' else 'saat'
        activity_goals += f"- {activity_name}: Haftada {activity_value} {unit}\n"
    
    prompt = f"""ZAMAN YÖNETİMİ ASISTANI: Haftalık aktivite dağılımı yapmanı istiyorum.

{slot_summary}
{activity_goals}

KURALLAR:
- Her aktiviteyi uygun günlere dağıt
- Çakışma olmasın
- İNSANİ YAŞAM STANDARTLARINA göre planla
- 'Sosyal Yaşam / Arkadaşlar' aktivitesi asla sabah 04:00 - 08:00 arasına konulamaz. Genellikle akşam saatlerine (18:00-23:00) koyulmalıdır.
- 'Spor' sabah erken (06:00-09:00) veya iş çıkışı olabilir.
- 'İçerik Üretimi' gündüz saatlerine (09:00-18:00) öncelik ver.
- 'Kitap Okuma' akşam dinlenme saatlerine uygun.
- Aktiviteleri insanların uyanık olduğu saatlere yerleştir (gece 01:00-06:00 kaçının).
- Enerji verimliliğini düşün (gece vardiyası sonrası ağır spor koyma).

Çıktıyı SADECE JSON formatında ver, başka açıklama yok:
[
  {{"day_index": 0, "activity": "Spor", "hours": 1}},
  {{"day_index": 1, "activity": "İçerik Üretimi", "hours": 2}}
]"""
    
    return prompt


async def get_gemini_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    activities: Dict,
    timeout: float = 30.0,
) -> List[ActivityPlanItem]:
    """
    Gemini'den aktivite dagilimi ister ve dogrulanmis satirlari dondurur.

    Her hata (anahtar yok, timeout, ag hatasi, bozuk JSON, gecersiz satir) bos
    liste ile sonuclanir; cagiran taraf kural tabanli plana duser.

    Args:
        free_slots: Bos zaman slotlari
        activities: Aktivite hedefleri
        timeout: API timeout suresi (saniye)

    Returns:
        Dogrulanmis plan satirlari (bos olabilir)
    """
    if not is_gemini_configured():
        print("INFO: Gemini yapilandirilmamis, kural tabanli plan kullanilacak")
        return []

    prompt = create_gemini_activity_prompt(free_slots, activities)

    try:
        started = time.time()
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=timeout,
        )
        print(f"INFO: Gemini yanit verdi ({time.time() - started:.2f}s)")
    except asyncio.TimeoutError:
        print(f"WARNING: Gemini {timeout}s icinde yanit vermedi")
        return []
    except Exception as exc:
        print(f"WARNING: Gemini cagrisi basarisiz: {type(exc).__name__}: {exc}")
        return []

    if not response.text:
        print("WARNING: Gemini bos yanit dondu")
        return []

    json_text = response.text.strip()
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif "```" in json_text:
        json_text = json_text.split("```")[1].split("```")[0].strip()

    try:
        raw_plan = json.loads(json_text)
    except json.JSONDecodeError as exc:
        print(f"WARNING: Gemini gecersiz JSON dondu: {exc}")
        return []

    return parse_activity_plan(raw_plan)


def apply_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    activity_plan: List[ActivityPlanItem]
) -> List[Tuple[datetime, datetime, str]]:
    """
    Aktivite planını boş slotlara çakışma olmadan yerleştirir

    Args:
        free_slots: Boş zaman slotları
        activity_plan: Dogrulanmis plan satirlari (bkz. parse_activity_plan)

    Returns:
        Aktivite etkinlikleri listesi
    """
    activity_events = []

    # Gün bazında boş slotları grupla
    available_slots = []
    for day_index, start, end in free_slots:
        available_slots.append({
            'day': day_index,
            'start': start,
            'end': end,
            'duration': (end - start).total_seconds() / 3600,
            'used_until': start
        })

    # Aktiviteleri yerleştir
    for plan_item in activity_plan:
        day = plan_item.day_index
        activity_key = plan_item.activity
        hours_needed = plan_item.hours

        # Aktivite adını bul
        activity_name = None
        for key, name in ACTIVITY_MAP.items():
            if activity_key.lower() in (name.lower(), key.lower()):
                activity_name = name
                break

        if not activity_name:
            print(f"WARNING: Bilinmeyen aktivite '{activity_key}' atlandi")
            continue
        
        # O gün için uygun slotları bul
        day_slots = [slot for slot in available_slots if slot['day'] == day]
        remaining_hours = hours_needed
        
        for slot in day_slots:
            if remaining_hours <= 0:
                break
            
            available_in_slot = slot['end'] - slot['used_until']
            available_hours = available_in_slot.total_seconds() / 3600
            
            if available_hours <= 0:
                continue
            
            hours_to_place = min(remaining_hours, available_hours)
            
            activity_start = slot['used_until']
            activity_end = activity_start + timedelta(hours=hours_to_place)
            
            activity_events.append((activity_start, activity_end, activity_name))
            
            slot['used_until'] = activity_end
            remaining_hours -= hours_to_place
    
    return activity_events


def generate_basic_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    activities: Dict
) -> List[Tuple[datetime, datetime, str]]:
    """
    API olmadan basit aktivite planı oluşturur (fallback)
    
    Args:
        free_slots: Boş zaman slotları
        activities: Aktivite hedefleri
    
    Returns:
        Aktivite etkinlikleri listesi
    """
    activity_events = []
    
    # Aktiviteleri basit bir şekilde dağıt
    activity_list = []
    for key, activity in activities.items():
        activity_name = ACTIVITY_MAP.get(key, key)
        activity_value = activity.get('value') if isinstance(activity, dict) else activity.value
        activity_type = activity.get('type') if isinstance(activity, dict) else activity.type
        
        if activity_type == 'hours':
            hours = activity_value
        else:  # days
            hours = activity_value * 1  # Her gün için 1 saat varsay
        
        activity_list.append({'name': activity_name, 'hours': hours})
    
    # Slotlara dağıt
    slot_index = 0
    for activity in activity_list:
        remaining = activity['hours']
        
        while remaining > 0 and slot_index < len(free_slots):
            _, start, end = free_slots[slot_index]
            slot_duration = (end - start).total_seconds() / 3600
            
            hours_to_use = min(remaining, slot_duration, 2)  # Max 2 saat blok
            
            if hours_to_use > 0:
                activity_end = start + timedelta(hours=hours_to_use)
                activity_events.append((start, activity_end, activity['name']))
                remaining -= hours_to_use
            
            slot_index += 1
    
    return activity_events
