from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, timedelta
import asyncio
import uvicorn
import pytz
from dotenv import load_dotenv
import traceback
import hashlib
import os
from pathlib import Path

# Environment variables
load_dotenv()

# Nanonets OCR Service (primary)
from services.ocr_service import process_ocr_image, is_ocr_available
from services.timeline_builder import build_timeline, find_free_slots
from services.ics_generator import generate_final_ics
from services.models import MAX_ACTIVITIES, ActivityGoal, CalendarLabels
from services.shift_validation import ShiftEvent, validate_shifts
from services.account_routes import router as account_router
from services.provider_routes import router as provider_router
from services.accounts import current_user, get_store, require_csrf
from services.providers import generate_json, ProviderError
from services.schedule_extraction import validate_image, normalize_schedule, extraction_prompt
from services.usage_limits import provider_job
from services.ai_planner import (
    place_activity_plan,
    configure_gemini,
    place_basic_plan,
    get_gemini_activity_plan,
    is_gemini_configured,
    create_gemini_activity_prompt,
    parse_activity_plan,
)

from contextlib import asynccontextmanager
from services.chatgpt import router as chatgpt_router, shutdown as shutdown_chatgpt


@asynccontextmanager
async def lifespan(app):
    yield
    await shutdown_chatgpt()


app = FastAPI(
    lifespan=lifespan,
    title="Shift Schedule OCR to ICS",
    description="A web app that scans your shift schedule image with AI-powered OCR and converts it into ICS calendar format"
)

app.include_router(account_router)
app.include_router(provider_router)
app.include_router(chatgpt_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic varsayılanı parola/API anahtarı içeren input alanını echo eder.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]}, headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def private_responses(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH'}:
        limit = 12_100_000 if request.url.path in {'/ocr', '/api/ocr/extract'} else 32_768
        async def read_limited():
            chunks = bytearray()
            async for chunk in request.stream():
                chunks.extend(chunk)
                if len(chunks) > limit:
                    return None
            return bytes(chunks)
        try:
            body = await asyncio.wait_for(read_limited(), timeout=15)
        except asyncio.TimeoutError:
            return JSONResponse({'detail': 'İstek gövdesi zamanında alınamadı.'}, status_code=408, headers={'Cache-Control':'no-store'})
        if body is None:
            return JSONResponse({'detail': 'İstek boyutu sınırı aşıldı.'}, status_code=413, headers={'Cache-Control':'no-store'})
        request._body = body
    response = await call_next(request)
    if request.url.path.startswith(("/api/", "/ocr", "/health", "/generate-plan")):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response

# Limitler
# 2000x2000 PNG bir crop'un base64 karsiligina yer birakir, sinirsiz payload'i keser
MAX_IMAGE_BASE64_LENGTH = 12_000_000
MAX_OCR_PROMPT_LENGTH = 2_000
GEMINI_TIMEOUT_SECONDS = 30.0

# Google Gemini API Configuration (opsiyonel - yoksa kural tabanli plan devreye girer)
if os.getenv("SHIFTSCAN_DEMO_AI") == "true":
    configure_gemini()

# Static files ve templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _static_version() -> str:
    """Service worker cache surumu: deploy commit'i, yoksa static icerik hash'i."""
    commit = os.getenv("SOURCE_COMMIT")
    if commit:
        return commit[:12]
    digest = hashlib.sha1()
    for path in sorted(list(Path("static").rglob("*")) + list(Path("templates").rglob("*"))):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


STATIC_VERSION = _static_version()
SW_TEMPLATE = Path("templates/sw.js").read_text(encoding="utf-8")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Surum damgali service worker; tarayici her kontrolde taze halini alir."""
    return Response(
        SW_TEMPLATE.replace("__SW_VERSION__", STATIC_VERSION),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )

# Pydantic modelleri
class OCRRequest(BaseModel):
    model_config = {"extra": "forbid"}

    image_base64: str = Field(..., max_length=MAX_IMAGE_BASE64_LENGTH)
    prompt: Optional[str] = Field(default=None, max_length=MAX_OCR_PROMPT_LENGTH)

class PlanRequest(BaseModel):
    model_config = {"extra": "forbid"}

    start_date: str
    timezone: str = "UTC"
    connection_id: Optional[str] = Field(default=None, min_length=1, max_length=80)
    shift_events: List[ShiftEvent] = Field(max_length=56)
    activities: List[ActivityGoal] = Field(min_length=1, max_length=MAX_ACTIVITIES)
    labels: CalendarLabels = CalendarLabels()

    @field_validator("activities")
    @classmethod
    def ids_must_be_unique(cls, goals: List[ActivityGoal]) -> List[ActivityGoal]:
        ids = [goal.id for goal in goals]
        if len(set(ids)) != len(ids):
            raise ValueError("activity ids must be unique")
        return goals

@app.get("/")
async def home(request: Request):
    """Ana sayfayı render eder"""
    return templates.TemplateResponse(request, "index.html", {"v": STATIC_VERSION})

def _week_start_from(start_date: str) -> date:
    """'YYYY-MM-DD' girdisini haftanin Pazartesi'sine normalize eder."""
    try:
        parsed = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="start_date must be in 'YYYY-MM-DD' format",
        )
    return parsed - timedelta(days=parsed.weekday())


def _validate_timezone(name: str) -> str:
    """Bilinmeyen bolge 500 yerine 400 olarak donmeli."""
    try:
        pytz.timezone(name)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail=f"Unknown timezone: {name}")
    return name


@app.post("/generate-plan")
async def generate_plan(plan_data: PlanRequest, request: Request):
    """Vardiya ve aktivite verilerinden haftalik plan ICS'i uretir."""
    try:
        week_start = _week_start_from(plan_data.start_date)
        timezone = _validate_timezone(plan_data.timezone)

        try:
            validate_shifts([event.model_dump() for event in plan_data.shift_events], week_start, timezone)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

        # 1. Timeline (vardiya + uyku)
        timeline = build_timeline(
            [event.model_dump() for event in plan_data.shift_events],
            timezone,
        )

        # 2. Bos slotlar - hafta start_date'ten kurulur, izin gunleri dahil
        free_slots = find_free_slots(timeline, week_start, timezone)
        print(
            f"INFO: {len(plan_data.shift_events)} vardiya -> "
            f"{len(timeline)} blok, {len(free_slots)} bos slot"
        )

        # 3. Aktivite dagilimi (AI, basarisizsa kural tabanli)
        known_ids = {goal.id for goal in plan_data.activities}
        activity_plan = []
        fallback_reason = None
        if plan_data.connection_id:
            user = current_user(request)
            require_csrf(request)
            store = get_store()
            connection = store.get_connection(user['id'], plan_data.connection_id)
            prompt = create_gemini_activity_prompt(free_slots, plan_data.activities)
            prompt += '\nReturn a JSON object with a "plan" key containing the array above.'
            try:
                async with provider_job(store.path, user['id']):
                    raw = await asyncio.wait_for(generate_json(connection, prompt), timeout=50)
                activity_plan = parse_activity_plan(raw.get('plan', []) if isinstance(raw, dict) else raw, known_ids)
                if not activity_plan:
                    fallback_reason = 'invalid_output'
            except ProviderError as exc:
                fallback_reason = exc.code
            except asyncio.TimeoutError:
                fallback_reason = 'timeout'
        elif os.getenv('SHIFTSCAN_DEMO_AI') == 'true':
            activity_plan = await get_gemini_activity_plan(
                free_slots, plan_data.activities, known_ids, timeout=GEMINI_TIMEOUT_SECONDS
            )

        if activity_plan:
            activity_events, unplaced = place_activity_plan(
                free_slots, activity_plan, plan_data.activities
            )
            plan_source = "ai"
        else:
            activity_events, unplaced = place_basic_plan(free_slots, plan_data.activities)
            plan_source = "fallback"

        print(
            f"INFO: {len(activity_events)} aktivite yerlestirildi ({plan_source}), "
            f"{len(unplaced)} hedef eksik kaldi"
        )

        # 4. ICS
        final_ics = generate_final_ics(timeline, activity_events, plan_data.labels)

        return {
            "status": "success",
            "message": "Plan generated",
            "plan_source": plan_source,
            "fallback_reason": fallback_reason,
            "unplaced": unplaced,
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
            detail="Failed to generate plan. Please try again.",
        )


class ExtractRequest(BaseModel):
    model_config = {"extra": "forbid"}
    connection_id: str = Field(min_length=1, max_length=80)
    start_date: str = Field(max_length=10)
    image_base64: str = Field(min_length=1, max_length=MAX_IMAGE_BASE64_LENGTH)


@app.post('/api/ocr/extract')
async def extract_schedule(body: ExtractRequest, request: Request):
    user = current_user(request)
    require_csrf(request)
    store = get_store()
    connection = store.get_connection(user['id'], body.connection_id)
    week_start = _week_start_from(body.start_date)
    try:
        image = await asyncio.to_thread(validate_image, body.image_base64)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    try:
        async with provider_job(store.path, user['id']):
            raw = await asyncio.wait_for(generate_json(connection, extraction_prompt(week_start), image=image), timeout=50)
        return normalize_schedule(raw, week_start)
    except ProviderError as exc:
        raise HTTPException(exc.status_code, {"code": exc.code, "message": exc.message}) from None
    except asyncio.TimeoutError:
        raise HTTPException(504, 'Tarama zaman aşımına uğradı. Yeniden deneyin veya yerel OCR kullanın.') from None
    except ValueError:
        raise HTTPException(502, 'Görselden geçerli bir vardiya tablosu çıkarılamadı. Başka bir model veya daha net görsel deneyin.') from None


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
        if os.getenv("SHIFTSCAN_LEGACY_OCR") != "true":
            raise HTTPException(503, "Eski OCR servisi kapalı. Cihazda OCR veya kendi sağlayıcı bağlantınızı kullanın.")
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
                detail="OCR service did not respond. Please try again or enter the text manually.",
            )

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to process OCR. Please try again or enter the text manually.",
        )


@app.get("/ocr/status")
async def ocr_status():
    """Check OCR service availability"""
    return {
        "available": os.getenv("SHIFTSCAN_LEGACY_OCR") == "true" and is_ocr_available(),
        "modes": ["local", "user_provider"],
        "model": "Nanonets-OCR2-3B",
        "provider": "HuggingFace Space (prithivMLmods/Multimodal-OCR)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Shift to ICS Converter is running",
        "gemini_configured": os.getenv("SHIFTSCAN_DEMO_AI") == "true" and is_gemini_configured(),
        "ocr_available": os.getenv("SHIFTSCAN_LEGACY_OCR") == "true" and is_ocr_available()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
