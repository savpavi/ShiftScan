"""/generate-plan ve /ocr endpoint davranislari."""

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def plan_body(**overrides) -> dict:
    body = {
        "start_date": "2026-08-24",
        "timezone": "Europe/Istanbul",
        "shift_events": [
            {"start": "2026-08-24T09:00:00+03:00", "end": "2026-08-24T18:00:00+03:00"}
        ],
        "activities": [
            {"id": "a1", "name": "Reading", "amount": 2, "unit": "hours"}
        ],
        "labels": {"shift": "Shift", "sleep": "Sleep"},
    }
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Testler gercek Gemini cagrisi yapmasin."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


def test_generate_plan_falls_back_when_ai_unavailable():
    """Gemini yoksa endpoint 500 atmamali, kural tabanli plana dusmeli."""
    response = client.post("/generate-plan", json=plan_body())

    assert response.status_code == 200
    assert response.json()["plan_source"] == "fallback"
    assert response.json()["ics_content"].startswith("BEGIN:VCALENDAR")


def test_generate_plan_rejects_invalid_start_date():
    response = client.post("/generate-plan", json=plan_body(start_date="24/08/2026"))

    assert response.status_code == 400


def test_generate_plan_does_not_leak_internal_errors(monkeypatch):
    """Beklenmedik hata istemciye ic detay sizdirmamali."""
    def boom(*args, **kwargs):
        raise RuntimeError("psycopg2 connection to 10.0.0.5 failed: bad password")

    monkeypatch.setattr(main, "generate_final_ics", boom)

    response = client.post("/generate-plan", json=plan_body())

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "psycopg2" not in detail
    assert "10.0.0.5" not in detail


def test_ocr_rejects_oversized_image():
    """Sinirsiz base64 payload kabul edilmemeli."""
    oversized = "A" * (main.MAX_IMAGE_BASE64_LENGTH + 1)

    response = client.post("/ocr", json={"image_base64": oversized})

    assert response.status_code == 422


def test_ocr_rejects_oversized_prompt():
    response = client.post(
        "/ocr",
        json={"image_base64": "AAAA", "prompt": "x" * (main.MAX_OCR_PROMPT_LENGTH + 1)},
    )

    assert response.status_code == 422


SECRET_ERROR = "gradio: connection to https://internal.host/xyz refused (token abc123)"


def test_ocr_failure_does_not_leak_provider_error(monkeypatch):
    async def failing_ocr(*args, **kwargs):
        return {"success": False, "text": "", "error": SECRET_ERROR}

    monkeypatch.setattr(main, "is_ocr_available", lambda: True)
    monkeypatch.setattr(main, "process_ocr_image", failing_ocr)

    response = client.post("/ocr", json={"image_base64": "AAAA"})

    assert response.status_code == 502
    assert "internal.host" not in response.json()["detail"]
    assert "abc123" not in response.json()["detail"]


def test_ocr_unexpected_exception_does_not_leak(monkeypatch):
    async def exploding_ocr(*args, **kwargs):
        raise RuntimeError(SECRET_ERROR)

    monkeypatch.setattr(main, "is_ocr_available", lambda: True)
    monkeypatch.setattr(main, "process_ocr_image", exploding_ocr)

    response = client.post("/ocr", json={"image_base64": "AAAA"})

    assert response.status_code == 500
    assert "internal.host" not in response.json()["detail"]


def test_home_page_renders():
    """Ana sayfa guncel starlette ile de render olmali."""
    response = client.get("/")

    assert response.status_code == 200
    assert "ShiftScan" in response.text or "Vardiya" in response.text


def test_unknown_timezone_returns_400():
    response = client.post("/generate-plan", json=plan_body(timezone="Mars/Olympus"))

    assert response.status_code == 400
    assert "timezone" in response.json()["detail"].lower()


def test_empty_activity_list_is_rejected():
    response = client.post("/generate-plan", json=plan_body(activities=[]))

    assert response.status_code == 422


def test_too_many_activities_are_rejected():
    many = [
        {"id": f"a{i}", "name": f"Activity {i}", "amount": 1, "unit": "hours"}
        for i in range(21)
    ]

    response = client.post("/generate-plan", json=plan_body(activities=many))

    assert response.status_code == 422


def test_duplicate_activity_ids_are_rejected():
    duplicated = [
        {"id": "a1", "name": "One", "amount": 1, "unit": "hours"},
        {"id": "a1", "name": "Two", "amount": 1, "unit": "hours"},
    ]

    response = client.post("/generate-plan", json=plan_body(activities=duplicated))

    assert response.status_code == 422
