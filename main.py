from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta, timezone
import pytz
import uvicorn
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
import json
import time
import platform
import traceback

# Environment variables
load_dotenv()

# Tesseract configuration for cross-platform compatibility (fallback)
import pytesseract
if platform.system() == "Windows":
    pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Linux (Docker) uses default path, no configuration needed

# Nanonets OCR Service (primary)
from services.ocr_service import process_ocr_image, is_ocr_available
from services.timeline_builder import build_timeline, find_free_slots
from services.ai_planner import (
    ActivityPlanItem,
    apply_activity_plan,
    create_gemini_activity_prompt,
    generate_basic_plan,
    parse_activity_plan,
)

app = FastAPI(
    title="Vardiya OCR to ICS",
    description="Vardiya görselinizi AI destekli OCR ile tarayıp ICS takvim formatına dönüştüren web uygulaması"
)

# Limitler
# 2000x2000 PNG bir crop'un base64 karsiligina yer birakir, sinirsiz payload'i keser
MAX_IMAGE_BASE64_LENGTH = 12_000_000
MAX_OCR_PROMPT_LENGTH = 2_000
GEMINI_TIMEOUT_SECONDS = 30.0

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
    image_base64: str = Field(..., max_length=MAX_IMAGE_BASE64_LENGTH)
    prompt: Optional[str] = Field(default=None, max_length=MAX_OCR_PROMPT_LENGTH)

class PlanRequest(BaseModel):
    start_date: str
    shift_text: str
    shift_events: List[ShiftEvent]
    activities: Dict[str, Activity]

# YENİ MİMARİ FONKSİYONLARI

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
    return templates.TemplateResponse(request, "index.html")

def _week_start_from(start_date: str) -> date:
    """'YYYY-MM-DD' girdisini haftanin Pazartesi'sine normalize eder."""
    try:
        parsed = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="start_date 'YYYY-MM-DD' formatinda olmali",
        )
    return parsed - timedelta(days=parsed.weekday())


async def _request_activity_plan(free_slots, activities) -> List[ActivityPlanItem]:
    """
    Gemini'den aktivite dagilimi ister.

    Model cagrisindaki her hata (anahtar yok, timeout, bozuk JSON, gecersiz
    satirlar) bos liste ile sonuclanir; cagiran taraf kural tabanli plana duser.
    """
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_gemini_api_key_here":
        print("INFO: Gemini API anahtari yok, kural tabanli plan kullanilacak")
        return []

    prompt = create_gemini_activity_prompt(free_slots, activities)

    try:
        started = time.time()
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        print(f"INFO: Gemini yanit verdi ({time.time() - started:.2f}s)")
    except asyncio.TimeoutError:
        print(f"WARNING: Gemini {GEMINI_TIMEOUT_SECONDS}s icinde yanit vermedi")
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


@app.post("/generate-plan")
async def generate_plan(plan_data: PlanRequest):
    """Vardiya ve aktivite verilerinden haftalik plan ICS'i uretir."""
    try:
        week_start = _week_start_from(plan_data.start_date)

        # 1. Timeline (vardiya + uyku)
        timeline = build_timeline(
            [event.model_dump() for event in plan_data.shift_events]
        )

        # 2. Bos slotlar - hafta start_date'ten kurulur, izin gunleri dahil
        free_slots = find_free_slots(timeline, week_start)
        print(
            f"INFO: {len(plan_data.shift_events)} vardiya -> "
            f"{len(timeline)} blok, {len(free_slots)} bos slot"
        )

        # 3. Aktivite dagilimi (AI, basarisizsa kural tabanli)
        activity_plan = await _request_activity_plan(free_slots, plan_data.activities)

        if activity_plan:
            activity_events = apply_activity_plan(free_slots, activity_plan)
            plan_source = "ai"
        else:
            activity_events = generate_basic_plan(free_slots, plan_data.activities)
            plan_source = "fallback"

        print(f"INFO: {len(activity_events)} aktivite yerlestirildi ({plan_source})")

        # 4. ICS
        final_ics = generate_final_ics(timeline, activity_events)

        return {
            "status": "success",
            "message": "Plan olusturuldu",
            "plan_source": plan_source,
            "ics_content": final_ics,
            "download_ready": True,
        }

    except HTTPException:
        raise
    except Exception:
        # Ic hata detayi istemciye sizmaz; tam iz sunucu log'unda kalir
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Plan olusturulamadi. Lutfen tekrar deneyin.",
        )


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
            # Saglayici hatasi log'da kalir, istemciye detay gitmez
            print(f"ERROR: OCR failed: {result['error']}")
            raise HTTPException(
                status_code=502,
                detail="OCR servisi yanit veremedi. Lutfen tekrar deneyin veya metni elle girin.",
            )

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="OCR islenemedi. Lutfen tekrar deneyin veya metni elle girin.",
        )


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
