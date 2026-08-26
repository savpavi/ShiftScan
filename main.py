from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date, timedelta
import uvicorn
from dotenv import load_dotenv
import traceback

# Environment variables
load_dotenv()

# Nanonets OCR Service (primary)
from services.ocr_service import process_ocr_image, is_ocr_available
from services.timeline_builder import build_timeline, find_free_slots
from services.ics_generator import generate_final_ics
from services.models import CalendarLabels
from services.ai_planner import (
    apply_activity_plan,
    configure_gemini,
    generate_basic_plan,
    get_gemini_activity_plan,
    is_gemini_configured,
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

# Google Gemini API Configuration (opsiyonel - yoksa kural tabanli plan devreye girer)
configure_gemini()

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
    labels: CalendarLabels = CalendarLabels()

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
        activity_plan = await get_gemini_activity_plan(
            free_slots, plan_data.activities, timeout=GEMINI_TIMEOUT_SECONDS
        )

        if activity_plan:
            activity_events = apply_activity_plan(free_slots, activity_plan)
            plan_source = "ai"
        else:
            activity_events = generate_basic_plan(free_slots, plan_data.activities)
            plan_source = "fallback"

        print(f"INFO: {len(activity_events)} aktivite yerlestirildi ({plan_source})")

        # 4. ICS
        final_ics = generate_final_ics(timeline, activity_events, plan_data.labels)

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
        "gemini_configured": is_gemini_configured(),
        "ocr_available": is_ocr_available()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
