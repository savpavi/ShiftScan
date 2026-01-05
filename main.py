from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
import pytz
import uvicorn
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
import time
import platform

# Environment variables
load_dotenv()

# Tesseract configuration for cross-platform compatibility (fallback)
import pytesseract
if platform.system() == "Windows":
    pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Linux (Docker) uses default path, no configuration needed

# Nanonets OCR Service (primary)
from services.ocr_service import process_ocr_image, is_ocr_available

app = FastAPI(
    title="Vardiya OCR to ICS",
    description="Vardiya görselinizi AI destekli OCR ile tarayıp ICS takvim formatına dönüştüren web uygulaması"
)

# Google Gemini API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_gemini_api_key_here":
    print("WARNING: GOOGLE_API_KEY not found! Set API key in .env file.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("SUCCESS: Google Gemini API configured")

# Static files ve templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic modelleri
class ShiftEvent(BaseModel):
    title: str
    start: str
    end: str
    original_line: str

class Activity(BaseModel):
    value: int
    type: str  # 'hours' veya 'days'

class OCRRequest(BaseModel):
    image_base64: str
    prompt: Optional[str] = None

class PlanRequest(BaseModel):
    start_date: str
    shift_text: str
    shift_events: List[ShiftEvent]
    activities: Dict[str, Activity]

# YENİ MİMARİ FONKSİYONLARI

def build_timeline(shift_events: List[ShiftEvent]) -> List[Tuple[datetime, datetime, str]]:
    """Vardiya ve uyku bloklarından timeline oluştur (Europe/Istanbul timezone)"""
    timeline = []
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    
    for event in shift_events:
        # ISO string'i datetime'a çevir (UTC'den geliyor)
        start_dt = datetime.fromisoformat(event.start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event.end.replace('Z', '+00:00'))
        
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
        
        if shift_end_hour < 22:  # 22:00'den önce biten varkiyalar
            # O günün gecesine uyku (00:30 - 08:30)
            sleep_date = end_dt.date()
            sleep_start = istanbul_tz.localize(datetime.combine(sleep_date, datetime.min.time()).replace(hour=0, minute=30))
            sleep_end = sleep_start + timedelta(hours=8)  # 00:30 - 08:30
        else:  # 22:00'den sonra biten varkiyalar
            # İş çıkışından 1 saat sonra uyku
            sleep_start = end_dt + timedelta(hours=1)
            sleep_end = sleep_start + timedelta(hours=8)
        
        timeline.append((sleep_start, sleep_end, "sleep"))
    
    # Kronolojik sırala
    timeline.sort(key=lambda x: x[0])
    return timeline

def find_free_slots(timeline: List[Tuple[datetime, datetime, str]]) -> List[Tuple[str, datetime, datetime]]:
    """Timeline'daki boş zaman slotlarını bul (Europe/Istanbul timezone) - INSOMNIA FİLTRESİ ile"""
    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    free_slots = []
    
    # Haftanın her günü için kontrol et
    base_date = timeline[0][0].date() if timeline else datetime.now().date()
    week_start = base_date - timedelta(days=base_date.weekday())
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    
    # O günki gece vardiyası var mı?
    night_shift_days = set()
    for start, end, block_type in timeline:
        if block_type == "shift" and end.hour >= 22:  # 22:00'den sonra biten varkiya
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
                        print(f"INSOMNIA FİLTRESİ: {day_name} {current_time.strftime('%H:%M')}-{block_start.strftime('%H:%M')} atlandı (gece aktivitesi yasak)")
                        current_time = block_end  # Bu slotu atla, bir sonraki bloğa devam et
                        continue
                    
                    # Eğer slot geceye sızıyorsa, kırp
                    if slot_start_hour < 7 and slot_end_hour > 7:
                        # Sadece 07:00'den sonraki kısmı al
                        cropped_start = istanbul_tz.localize(datetime.combine(current_day, datetime.min.time()).replace(hour=7))
                        if cropped_start < block_start:
                            print(f"INSOMNIA FİLTRESİ: {day_name} slot kırpıldı {current_time.strftime('%H:%M')}-{cropped_start.strftime('%H:%M')} -> {cropped_start.strftime('%H:%M')}-{block_start.strftime('%H:%M')}")
                            free_slots.append((day_name, cropped_start, block_start))
                    elif slot_start_hour >= 7:  # Tamamen gündüz slotu
                        free_slots.append(potential_slot)
                else:
                    # Gece vardiyası günü - tüm slotlar müsait
                    free_slots.append(potential_slot)
                    
            current_time = max(current_time, block_end)
        
        # Gün sonuna kadar kalan boşluk
        if current_time < day_end:
            # INSOMNIA FİLTRESİ: Gün sonu boşluğunu kontrol et
            slot_start_hour = current_time.hour
            is_night_shift_day = current_day in night_shift_days
            
            if not is_night_shift_day and slot_start_hour >= 0 and slot_start_hour < 7:
                print(f"INSOMNIA FİLTRESİ: {day_name} gün sonu boşluğu atlandı {current_time.strftime('%H:%M')}-{day_end.strftime('%H:%M')} (gece aktivitesi yasak)")
            else:
                free_slots.append((day_name, current_time, day_end))
    
    return free_slots

def create_gemini_activity_prompt(free_slots: List[Tuple[str, datetime, datetime]], activities: Dict[str, Activity]) -> str:
    """Gemini için sadece aktivite dağılımı isteyen prompt"""
    
    # Boş slotları özetle
    slot_summary = "BOŞ ZAMAN ARALIKLARI:\n"
    day_totals = {}
    
    for day_name, start, end in free_slots:
        duration = (end - start).total_seconds() / 3600  # saat
        if day_name not in day_totals:
            day_totals[day_name] = 0
        day_totals[day_name] += duration
    
    for day, total_hours in day_totals.items():
        slot_summary += f"- {day}: {total_hours:.1f} saat boş\n"
    
    # Aktivite hedefleri
    activity_goals = "AKTİVİTE HEDEFLERİ:\n"
    activity_map = {
        'content-production': 'İçerik Üretimi',
        'sports': 'Spor',
        'reading': 'Kitap Okuma',
        'social': 'Sosyal Yaşam / Arkadaşlar',
        'gaming': 'Oyun / Dinlenme'
    }
    
    for key, activity in activities.items():
        activity_name = activity_map.get(key, key)
        unit = 'gün' if activity.type == 'days' else 'saat'
        activity_goals += f"- {activity_name}: Haftada {activity.value} {unit}\n"
    
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
  {{"day": "Pazartesi", "activity": "Spor", "hours": 1}},
  {{"day": "Salı", "activity": "İçerik Üretimi", "hours": 2}}
]"""
    
    return prompt

def apply_activity_plan(free_slots: List[Tuple[str, datetime, datetime]], activity_plan: List[Dict]) -> List[Tuple[datetime, datetime, str]]:
    """Aktivite planını boş slotlara çakışma olmadan yerleştir"""
    activity_events = []
    activity_map = {
        'content-production': 'İçerik Üretimi',
        'sports': 'Spor',
        'reading': 'Kitap Okuma',
        'social': 'Sosyal Yaşam / Arkadaşlar',
        'gaming': 'Oyun / Dinlenme'
    }
    
    # Gün bazında boş slotları grupla ve kullanılabilir slot listesi oluştur
    available_slots = []
    for day_name, start, end in free_slots:
        # Her boş slotu ayrı bir eleman olarak ekle
        available_slots.append({
            'day': day_name,
            'start': start,
            'end': end,
            'duration': (end - start).total_seconds() / 3600,  # saat
            'used_until': start  # bu slotta ne kadar kullanıldı
        })
    
    print(f"DEBUG: Available slots before placement: {len(available_slots)}")
    for i, slot in enumerate(available_slots):
        print(f"  Slot {i}: {slot['day']} {slot['start'].strftime('%H:%M')}-{slot['end'].strftime('%H:%M')} ({slot['duration']:.1f}h)")
    
    # Aktiviteleri yerleştir
    for plan_item in activity_plan:
        day = plan_item.get('day')
        activity_key = plan_item.get('activity')
        hours_needed = plan_item.get('hours', 0)
        
        # Aktivite adını bul
        activity_name = None
        for key, name in activity_map.items():
            if name.lower() == activity_key.lower() or key.lower() == activity_key.lower():
                activity_name = name
                break
        
        if not activity_name or hours_needed <= 0:
            continue
        
        print(f"DEBUG: Placing {activity_name} for {hours_needed}h on {day}")
        
        # O gün için uygun slotları bul
        day_slots = [slot for slot in available_slots if slot['day'] == day]
        remaining_hours = hours_needed
        
        for slot in day_slots:
            if remaining_hours <= 0:
                break
            
            # Bu slotta ne kadar yer var?
            available_in_slot = slot['end'] - slot['used_until']
            available_hours = available_in_slot.total_seconds() / 3600
            
            if available_hours <= 0:
                continue
            
            # Bu slotta kaç saat yerleştirebiliriz?
            hours_to_place = min(remaining_hours, available_hours)
            
            activity_start = slot['used_until']
            activity_end = activity_start + timedelta(hours=hours_to_place)
            
            activity_events.append((activity_start, activity_end, activity_name))
            print(f"  Placed: {activity_start.strftime('%H:%M')}-{activity_end.strftime('%H:%M')} ({hours_to_place:.1f}h)")
            
            # Slotu güncelle
            slot['used_until'] = activity_end
            remaining_hours -= hours_to_place
        
        if remaining_hours > 0:
            print(f"  WARNING: Could only place {hours_needed - remaining_hours:.1f}h out of {hours_needed:.1f}h for {activity_name}")
    
    print(f"DEBUG: Created {len(activity_events)} activity events total")
    return activity_events

def generate_final_ics(timeline: List[Tuple[datetime, datetime, str]], activity_events: List[Tuple[datetime, datetime, str]]) -> str:
    """Timeline ve aktivitelerden son ICS'i oluştur (Floating Time - Europe/Istanbul)"""
    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Shift Planner//TR
CALSCALE:GREGORIAN
"""
    
    # Timeline bloklarını ekle (vardiya + uyku)
    for start, end, block_type in timeline:
        summary = "Vardiya" if block_type == "shift" else "Uyku"
        uid = f"{block_type}-{start.strftime('%Y%m%d%H%M')}"
        
        # Floating Time formatı - timezone bilgisi olmadan
        ics += f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{summary}
END:VEVENT
"""
    
    # Aktivite olaylarını ekle
    for start, end, activity_name in activity_events:
        uid = f"activity-{start.strftime('%Y%m%d%H%M')}"
        
        # Floating Time formatı - timezone bilgisi olmadan
        ics += f"""BEGIN:VEVENT
UID:{uid}
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{activity_name}
END:VEVENT
"""
    
    ics += "END:VCALENDAR"
    return ics

def generate_base_ics(shift_events: List[ShiftEvent]) -> str:
    """Vardiya ve uyku saatlerini içeren temel ICS'i oluştur"""
    
    base_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Shift Planner//TR
CALSCALE:GREGORIAN
"""
    
    # Vardiya olaylarını ekle
    for i, event in enumerate(shift_events):
        start_dt = datetime.fromisoformat(event.start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event.end.replace('Z', '+00:00'))
        
        base_ics += f"""BEGIN:VEVENT
UID:vardiya-{i}-{start_dt.strftime('%Y%m%d%H%M')}
DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}
DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{event.title}
DESCRIPTION:Vardiya - DEĞİŞTİRME
END:VEVENT
"""
        
        # Vardiya bitiminden sonraki 7 saat uyku
        sleep_start = end_dt
        sleep_end = sleep_start.replace(hour=sleep_start.hour + 7) if sleep_start.hour + 7 < 24 else sleep_start.replace(day=sleep_start.day + 1, hour=(sleep_start.hour + 7) - 24)
        
        base_ics += f"""BEGIN:VEVENT
UID:uyku-{i}-{sleep_start.strftime('%Y%m%d%H%M')}
DTSTART:{sleep_start.strftime('%Y%m%dT%H%M%S')}
DTEND:{sleep_end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:Uyku
DESCRIPTION:Vardiya sonrası uyku - DEĞİŞTİRME
END:VEVENT
"""
    
    base_ics += "END:VCALENDAR"
    return base_ics

def create_gemini_prompt(base_ics: str, activities: Dict[str, Activity]) -> str:
    """Gemini için prompt oluştur - Ruthless Life OS mantığıyla"""
    
    # Aktivite bilgilerini formatla
    activity_info = "HEDEFLER VE AKTİVİTELER:\n"
    activity_map = {
        'content-production': 'İçerik Üretimi (Blog/Video)',
        'sports': 'Spor',
        'reading': 'Kitap Okuma', 
        'social': 'Arkadaş/Sosyal Zaman',
        'gaming': 'Oyun / Dinlenme'
    }
    
    for key, activity in activities.items():
        activity_name = activity_map.get(key, key)
        unit = 'gün' if activity.type == 'days' else 'saat'
        activity_info += f"- [{activity_name}]: Haftada {activity.value} {unit}\n"

    # RUTHLESS PROMPT
    system_prompt = """SEN ACIMASIZ VE MATEMATİKSEL DÜŞÜNEN BİR LOJİSTİK PLANLAMA ASİSTANISIN.
Yaratıcı olma, kurallara %100 uy.

GÖREVİN:
Aşağıdaki ICS verisindeki [VARDIYA_VERISI] (İş ve Uyku) senin "Kırmızı Bölgelerin"dir. Bunlara ASLA dokunma.
Geriye kalan "MÜSAİT SLOTLAR"a aşağıdaki hedefleri 4 adımlı algoritmaya göre yerleştir.

ALGORİTMA:

ADIM 1: KIRMIZI BÖLGELERİ KORU
- Mevcut VEVENT bloklarını (Vardiya ve Uyku) aynen KORU.
- Asla bu saatlere çakışan etkinlik koyma.

ADIM 2: ENERJİ YÖNETİMİ (Müsait Slot Analizi)
- Eğer müsait slot GÜNDÜZ (09:00 - 18:00) arasındaysa ve uykudan yeni kalkılmışsa: "YÜKSEK ENERJİ"
- Eğer müsait slot GECEYE denk geliyorsa veya mesai öncesi kısıtlı zamansa: "DÜŞÜK ENERJİ"

ADIM 3: AKTİVİTE YERLEŞTİRME KURALLARI
Aşağıdaki hedefleri uygun enerji slotlarına yerleştir:
1. SPOR: Sadece YÜKSEK ENERJİ slotlarına. (Haftada belirtilen sıklıkta, en az 1 saat)
2. İÇERİK ÜRETİMİ: Sadece YÜKSEK ENERJİ slotlarına. (Haftada toplam belirtilen süre)
3. KİTAP OKUMA: DÜŞÜK ENERJİ slotlarına. (Her gün en az 30 dk)
4. SOSYAL/OYUN: DÜŞÜK ENERJİ slotlarına.

ADIM 4: ÇIKTI FORMATI
- Çıktı TAM BİR ICS DOSYASI olmalıdır.
- Mevcut etkinlikleri koru, yenilerini ekle.
- Yeni etkinliklerin SUMMARY kısmı sadece aktivite adını içermeli.
- DESCRIPTION kısmına "Enerji: Yüksek" veya "Enerji: Düşük" notunu ekle.

MEVCUT ICS (DEĞİŞTİRME, SADECE EKLE):"""
    
    return f"{system_prompt}\n\n{base_ics}\n\n{activity_info}\n\nYUKARIDAKİ KURALLARA GÖRE TAM ICS DOSYASINI OLUŞTUR:"

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

@app.get("/")
async def home(request: Request):
    """Ana sayfayı render eder"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-plan")
async def generate_plan(plan_data: PlanRequest):
    """Vardiya ve aktivite verilerini alarak Python-kontrollü plan oluşturur"""
    try:
        print("İstek alındı...")
        print(f"DEBUG: Received request data: {plan_data}")
        
        print("Veriler işleniyor...")
        
        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_gemini_api_key_here":
            print("ERROR: Google Gemini API key not configured")
            raise HTTPException(status_code=500, detail="Google Gemini API key yapılandırılmamış")
        
        print("INFO: Plan creation request received:")
        print(f"Start date: {plan_data.start_date}")
        print(f"Shift events: {len(plan_data.shift_events)} items")
        print(f"Activities: {plan_data.activities}")
        
        # 1. ADIM: Timeline oluştur (vardiya + uyku)
        print("DEBUG: Building timeline with shifts and sleep...")
        timeline = build_timeline(plan_data.shift_events)
        print(f"DEBUG: Timeline created with {len(timeline)} blocks")
        
        # Timeline'ı göster
        for start, end, block_type in timeline:
            print(f"  {block_type}: {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%Y-%m-%d %H:%M')}")
        
        # 2. ADIM: Boş slotları bul
        print("DEBUG: Finding free slots...")
        free_slots = find_free_slots(timeline)
        print(f"DEBUG: Found {len(free_slots)} free slots")
        
        # Boş slot özetini göster
        day_totals = {}
        for day_name, start, end in free_slots:
            duration = (end - start).total_seconds() / 3600
            if day_name not in day_totals:
                day_totals[day_name] = 0
            day_totals[day_name] += duration
        
        for day, total_hours in day_totals.items():
            print(f"  {day}: {total_hours:.1f} hours free")
        
        # 3. ADIM: Gemini'den aktivite dağılımı iste (JSON)
        print("Gemini API çağrılıyor...")
        gemini_start_time = time.time()
        print(f"Gemini API çağrı zamanı: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("DEBUG: Creating Gemini prompt for activity distribution...")
        prompt = create_gemini_activity_prompt(free_slots, plan_data.activities)
        print(f"DEBUG: Prompt length: {len(prompt)} characters")
        
        print("INFO: Sending request to Gemini API...")
        
        # Gemini API çağrısı
        print("DEBUG: Initializing Gemini model...")
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("DEBUG: Model initialized, generating content...")
        
        # Timeout ile Gemini çağrısı
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            print("ERROR: Gemini API çağrısı 30 saniye içinde zaman aşımına uğradı!")
            raise HTTPException(status_code=504, detail="Gemini API çağrısı zaman aşımına uğradı. Lütfen tekrar deneyin.")
        
        gemini_end_time = time.time()
        gemini_duration = gemini_end_time - gemini_start_time
        print(f"Gemini yanıt verdi... (Süre: {gemini_duration:.2f} saniye)")
        
        if not response.text:
            print("ERROR: Gemini API returned empty response")
            raise HTTPException(status_code=500, detail="Gemini API returned empty response")
        
        print(f"DEBUG: Gemini response received, length: {len(response.text)}")
        print("DEBUG: Gemini response:")
        print(response.text)
        
        # JSON parse et
        try:
            import json
            # JSON temizle
            json_text = response.text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            activity_plan = json.loads(json_text)
            print(f"DEBUG: Parsed {len(activity_plan)} activity items")
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse Gemini JSON response: {e}")
            print(f"Raw response: {response.text}")
            print("ERROR: Gemini API'den geçersiz JSON formatı alındı!")
            raise HTTPException(status_code=500, detail="Gemini returned invalid JSON")
        
        # 4. ADIM: Aktiviteleri slotlara yerleştir (Python kontrolü)
        print("DEBUG: Applying activity plan to free slots...")
        activity_events = apply_activity_plan(free_slots, activity_plan)
        print(f"DEBUG: Created {len(activity_events)} activity events")
        
        # Aktivite olaylarını göster
        for start, end, activity_name in activity_events:
            print(f"  {activity_name}: {start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%Y-%m-%d %H:%M')}")
        
        # 5. ADIM: Son ICS'i oluştur (tamamen Python)
        print("ICS oluşturuluyor...")
        final_ics = generate_final_ics(timeline, activity_events)
        
        print("SUCCESS: Final ICS generated")
        print(f"Final ICS content length: {len(final_ics)} characters")
        print("Final ICS preview:")
        print(final_ics[:500] + "..." if len(final_ics) > 500 else final_ics)
        
        return {
            "status": "success",
            "message": "Plan başarıyla oluşturuldu (Python kontrollü)",
            "ics_content": final_ics,
            "download_ready": True
        }
        
    except HTTPException as he:
        print(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        import traceback
        print(f"ERROR: Plan creation failed with unexpected error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        
        print(f"ERROR: Beklenmedik hata oluştu: {type(e).__name__} - {str(e)}")
        
        if "API key" in str(e):
            print("ERROR: API anahtar hatası tespit edildi!")
            raise HTTPException(status_code=500, detail="Google Gemini API key error. Check .env file.")
        raise HTTPException(status_code=500, detail=f"Plan creation error: {str(e)}")

@app.get("/download-plan/{plan_id}")
async def download_plan(plan_id: str):
    """ICS dosyasını indirir (şimdilik placeholder)"""
    try:
        # Şimdilik basit bir ICS şablonu dön
        ics_template = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Shift Planner//TR
CALSCALE:GREGORIAN
BEGIN:VEVENT
DTSTAMP:20250101T000000Z
DTSTART:20250101T090000Z
DTEND:20250101T170000Z
SUMMARY:Test Event
DESCRIPTION:Generated by Shift Planner
END:VEVENT
END:VCALENDAR"""
        
        return Response(
            content=ics_template,
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=weekly_plan.ics"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İndirme hatası: {str(e)}")

@app.post("/ocr")
async def perform_ocr(request: OCRRequest):
    """
    OCR endpoint using Nanonets-OCR2-3B via HuggingFace Space

    Args:
        request: OCRRequest with image_base64 and optional prompt

    Returns:
        OCR result with extracted text
    """
    try:
        if not is_ocr_available():
            raise HTTPException(
                status_code=503,
                detail="OCR service unavailable. gradio_client not installed."
            )

        print("INFO: OCR request received")
        print(f"INFO: Image data length: {len(request.image_base64)} chars")

        # Default prompt optimized for shift schedules
        prompt = request.prompt or """Extract all text from this image.
Focus on:
- Time ranges (like 09:00-18:00, 9:00-17:00)
- Day names or abbreviations
- OFF, leave, izin, tatil indicators
Return the raw text exactly as it appears, preserving the layout."""

        # Process through Nanonets OCR
        result = await process_ocr_image(request.image_base64, prompt)

        if result['success']:
            print(f"SUCCESS: OCR completed, text length: {len(result['text'])}")
            return {
                "status": "success",
                "text": result['text'],
                "model": "Nanonets-OCR2-3B"
            }
        else:
            print(f"ERROR: OCR failed: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed: {result['error']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected OCR error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR error: {str(e)}")


@app.get("/ocr/status")
async def ocr_status():
    """Check OCR service availability"""
    return {
        "available": is_ocr_available(),
        "model": "Nanonets-OCR2-3B",
        "provider": "HuggingFace Space (prithivMLmods/Multimodal-OCR)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Shift to ICS Converter is running",
        "gemini_configured": bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your_gemini_api_key_here"),
        "ocr_available": is_ocr_available()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
