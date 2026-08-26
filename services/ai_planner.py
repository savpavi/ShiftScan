"""
AI Planner Service
Google Gemini API ile akıllı aktivite planlama
"""

from typing import Any, List, Tuple
from datetime import datetime, timedelta
import os
import json
import asyncio
import time

from pydantic import BaseModel, Field, ValidationError

from services.models import DEFAULT_SESSION_HOURS, PREFERRED_WINDOWS, ActivityGoal

# Gemini API yapılandırması opsiyonel
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


# Tek bir aktivite yerlestirmesi icin ust sinir (bir gunun tamami)
MAX_ACTIVITY_HOURS = 24


class ActivityPlanItem(BaseModel):
    """Modelin dondurdugu tek bir plan satiri."""

    day_index: int = Field(ge=0, le=6)
    activity_id: str
    hours: float = Field(gt=0, le=MAX_ACTIVITY_HOURS)


def parse_activity_plan(raw: Any, known_ids: set) -> List[ActivityPlanItem]:
    """
    Dil modelinden gelen ham plan ciktisini dogrular.

    Model ciktisi guvenilmez: alan eksik olabilir, sayi string gelebilir,
    liste yerine dict donebilir, uydurma bir aktivite id'si gelebilir.
    Gecerli satirlar korunur, gecersizler atlanir; exception yukselmez.

    Args:
        raw: json.loads ciktisi (herhangi bir tip olabilir)
        known_ids: istekteki gecerli aktivite id'leri

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
            item = ActivityPlanItem.model_validate(entry)
        except ValidationError as exc:
            print(f"WARNING: Gecersiz plan satiri atlandi: {entry} ({exc.error_count()} hata)")
            continue

        if item.activity_id not in known_ids:
            print(f"WARNING: Bilinmeyen aktivite id'si atlandi: {item.activity_id}")
            continue

        items.append(item)

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
    goals: List[ActivityGoal]
) -> str:
    """Kullanicinin tanimladigi hedeflerden dil bagimsiz bir prompt uretir."""
    slot_summary = "FREE TIME (day index 0 = Monday):\n"
    day_totals = {}

    for day_index, start, end in free_slots:
        duration = (end - start).total_seconds() / 3600
        day_totals[day_index] = day_totals.get(day_index, 0) + duration

    for day_index in sorted(day_totals):
        slot_summary += f"- day {day_index}: {day_totals[day_index]:.1f} hours free\n"

    activity_goals = "ACTIVITY GOALS:\n"
    for goal in goals:
        if goal.unit == "days":
            amount = f"{goal.amount:g} days per week, {DEFAULT_SESSION_HOURS:g} hour each"
        else:
            amount = f"{goal.amount:g} hours per week"

        if goal.preferred == "any":
            window = "no time preference"
        else:
            start_hour, end_hour = PREFERRED_WINDOWS[goal.preferred]
            window = f"prefer {goal.preferred} ({start_hour:02d}:00-{end_hour:02d}:00)"

        activity_goals += f'- id {goal.id} "{goal.name}": {amount}, {window}\n'

    return f"""You are a scheduling assistant. Distribute the activities below across the free time.

{slot_summary}
{activity_goals}
RULES:
- Do not overlap activities.
- Keep activities in waking hours; avoid 01:00-06:00.
- Respect each activity's preferred window when the free time allows it.
- Do not schedule demanding activities right after a shift ends.

Return ONLY JSON, no other text. Use the activity ids above, never the names:
[
  {{"day_index": 0, "activity_id": "a1", "hours": 1}}
]"""


async def get_gemini_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    goals: List[ActivityGoal],
    known_ids: set,
    timeout: float = 30.0,
) -> List[ActivityPlanItem]:
    """
    Gemini'den aktivite dagilimi ister ve dogrulanmis satirlari dondurur.

    Her hata (anahtar yok, timeout, ag hatasi, bozuk JSON, gecersiz satir) bos
    liste ile sonuclanir; cagiran taraf kural tabanli plana duser.

    Args:
        free_slots: Bos zaman slotlari
        goals: Aktivite hedefleri
        known_ids: istekteki gecerli aktivite id'leri
        timeout: API timeout suresi (saniye)

    Returns:
        Dogrulanmis plan satirlari (bos olabilir)
    """
    if not is_gemini_configured():
        print("INFO: Gemini yapilandirilmamis, kural tabanli plan kullanilacak")
        return []

    prompt = create_gemini_activity_prompt(free_slots, goals)

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

    return parse_activity_plan(raw_plan, known_ids)


def apply_activity_plan(
    free_slots: List[Tuple[int, datetime, datetime]],
    activity_plan: List[ActivityPlanItem],
    goals: List[ActivityGoal]
) -> List[Tuple[datetime, datetime, str]]:
    """
    Aktivite planını boş slotlara çakışma olmadan yerleştirir

    Args:
        free_slots: Boş zaman slotları
        activity_plan: Dogrulanmis plan satirlari (bkz. parse_activity_plan)
        goals: Aktivite hedefleri (id -> ad cozumu icin)

    Returns:
        Aktivite etkinlikleri listesi
    """
    names = {goal.id: goal.name for goal in goals}
    activity_events = []

    # Gün bazında boş slotları grupla
    available_slots = []
    for day_index, start, end in free_slots:
        available_slots.append({
            'day_index': day_index,
            'start': start,
            'end': end,
            'duration': (end - start).total_seconds() / 3600,
            'used_until': start
        })

    # Aktiviteleri yerleştir
    for plan_item in activity_plan:
        activity_name = names.get(plan_item.activity_id)
        if not activity_name:
            print(f"WARNING: Bilinmeyen aktivite id'si '{plan_item.activity_id}' atlandi")
            continue

        day = plan_item.day_index
        hours_needed = plan_item.hours

        # O gün için uygun slotları bul
        day_slots = [slot for slot in available_slots if slot['day_index'] == day]
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
    goals: List[ActivityGoal]
) -> List[Tuple[datetime, datetime, str]]:
    """
    API olmadan basit aktivite plani olusturur (fallback).

    Tercih edilen pencereye denk gelen slotlar once denenir; aktivite oraya
    sigmazsa herhangi bir bos slota konur. Yerlesemeyen saatler sessizce
    dusulur - kullaniciya bildirmek backlog madde 8.
    """
    activity_events = []
    used_until = {index: start for index, (_, start, _) in enumerate(free_slots)}

    def slot_matches(slot_index: int, preferred: str) -> bool:
        if preferred == "any":
            return True
        window_start_hour, window_end_hour = PREFERRED_WINDOWS[preferred]
        _, start, end = free_slots[slot_index]
        # find_free_slots closes a day's final slot at the NEXT day's 00:00,
        # so comparing raw .hour values (as before) reads that endpoint as
        # hour 0 and hides the whole after-shift/evening block. Compare real
        # intervals instead: anchor the window to the slot's start date and
        # test for overlap. The end<=start guard covers a slot that wraps
        # past midnight without its own date rollover.
        day_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = day_start + timedelta(hours=window_start_hour)
        window_end = day_start + timedelta(hours=window_end_hour)
        slot_end = end if end > start else end + timedelta(days=1)
        return max(start, window_start) < min(slot_end, window_end)

    for goal in goals:
        preferred_order = [i for i in range(len(free_slots)) if slot_matches(i, goal.preferred)]
        fallback_order = [i for i in range(len(free_slots)) if i not in preferred_order]
        ordered_slots = preferred_order + fallback_order

        if goal.unit == "days":
            # "N days per week" is N distinct day-sessions of
            # DEFAULT_SESSION_HOURS each, not a single N*DEFAULT_SESSION_HOURS
            # block - one session per day_index, never two on the same day.
            sessions_needed = int(goal.amount)
            used_days = set()

            for slot_index in ordered_slots:
                if sessions_needed <= 0:
                    break

                day_index, _, slot_end = free_slots[slot_index]
                if day_index in used_days:
                    continue

                cursor = used_until[slot_index]
                available = (slot_end - cursor).total_seconds() / 3600
                if available < DEFAULT_SESSION_HOURS:
                    continue

                activity_end = cursor + timedelta(hours=DEFAULT_SESSION_HOURS)
                activity_events.append((cursor, activity_end, goal.name))
                used_until[slot_index] = activity_end
                used_days.add(day_index)
                sessions_needed -= 1
        else:
            remaining = goal.amount

            for slot_index in ordered_slots:
                if remaining <= 0:
                    break

                _, _, slot_end = free_slots[slot_index]
                cursor = used_until[slot_index]
                available = (slot_end - cursor).total_seconds() / 3600
                if available <= 0:
                    continue

                hours_to_use = min(remaining, available, 2)
                activity_end = cursor + timedelta(hours=hours_to_use)
                activity_events.append((cursor, activity_end, goal.name))
                used_until[slot_index] = activity_end
                remaining -= hours_to_use

    return activity_events
