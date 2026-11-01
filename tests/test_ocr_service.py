import asyncio
import base64
import io
import threading
import time

from PIL import Image


def _image_data(fmt="PNG"):
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format=fmt)
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt]
    return f"data:{mime};base64," + base64.b64encode(output.getvalue()).decode()


class _Job:
    def __init__(self, result=("09:00-18:00", ""), delay=0):
        self.value = result
        self.delay = delay
        self.cancelled = False
        self.timeout = None

    def result(self, timeout=None):
        self.timeout = timeout
        if self.delay:
            time.sleep(self.delay)
            raise TimeoutError("late")
        return self.value

    def cancel(self):
        self.cancelled = True


class _Client:
    def __init__(self, job, paths, active=None):
        self.job = job
        self.paths = paths
        self.active = active

    def submit(self, **kwargs):
        self.paths.append(kwargs["image"])
        if self.active is not None:
            with self.active["lock"]:
                self.active["current"] += 1
                self.active["peak"] = max(self.active["peak"], self.active["current"])
        return self.job


def test_client_initialization_does_not_block_event_loop(monkeypatch):
    from services import ocr_service

    def slow_client(_space):
        time.sleep(0.05)
        return _Client(_Job(), [])

    monkeypatch.setattr(ocr_service, "GRADIO_AVAILABLE", True)
    monkeypatch.setattr(ocr_service, "Client", slow_client)
    monkeypatch.setattr(ocr_service, "handle_file", lambda path: path)
    service = ocr_service.OCRService()

    async def scenario():
        ticks = 0
        task = asyncio.create_task(service.process_image_base64(_image_data()))
        while not task.done():
            ticks += 1
            await asyncio.sleep(0.005)
        return ticks, await task

    ticks, result = asyncio.run(scenario())
    assert ticks >= 3
    assert result["success"] is True


def test_validated_mime_selects_matching_temp_suffix(monkeypatch):
    from services import ocr_service

    paths = []
    monkeypatch.setattr(ocr_service, "GRADIO_AVAILABLE", True)
    monkeypatch.setattr(ocr_service, "Client", lambda _space: _Client(_Job(), paths))
    monkeypatch.setattr(ocr_service, "handle_file", lambda path: path)
    result = asyncio.run(ocr_service.OCRService().process_image_base64(_image_data("JPEG")))
    assert result == {"success": True, "text": "09:00-18:00", "error": None}
    assert paths[0].endswith(".jpg")


def test_invalid_image_is_rejected_before_gradio(monkeypatch):
    from services import ocr_service

    called = False

    def client(_space):
        nonlocal called
        called = True

    monkeypatch.setattr(ocr_service, "Client", client)
    result = asyncio.run(ocr_service.OCRService().process_image_base64("bm90LWEtcmVhbC1pbWFnZQ=="))
    assert result["success"] is False
    assert called is False


def test_timeout_cancels_submitted_job_and_sanitizes_error(monkeypatch):
    from services import ocr_service

    job = _Job(delay=0.05)
    monkeypatch.setattr(ocr_service, "GRADIO_AVAILABLE", True)
    monkeypatch.setattr(ocr_service, "Client", lambda _space: _Client(job, []))
    monkeypatch.setattr(ocr_service, "handle_file", lambda path: path)
    monkeypatch.setattr(ocr_service, "OCR_DEADLINE_SECONDS", 0.01)
    result = asyncio.run(ocr_service.OCRService().process_image_base64(_image_data()))
    assert result == {"success": False, "text": "", "error": "OCR isteği zaman aşımına uğradı."}
    assert job.cancelled is True


def test_at_most_two_legacy_jobs_run_concurrently(monkeypatch):
    from services import ocr_service

    active = {"current": 0, "peak": 0, "lock": threading.Lock()}

    class TrackingJob(_Job):
        def result(self, timeout=None):
            time.sleep(0.03)
            with active["lock"]:
                active["current"] -= 1
            return self.value

    monkeypatch.setattr(ocr_service, "GRADIO_AVAILABLE", True)
    monkeypatch.setattr(
        ocr_service, "Client", lambda _space: _Client(TrackingJob(), [], active)
    )
    monkeypatch.setattr(ocr_service, "handle_file", lambda path: path)
    service = ocr_service.OCRService()

    async def scenario():
        return await asyncio.gather(*(service.process_image_base64(_image_data()) for _ in range(4)))

    results = asyncio.run(scenario())
    assert all(item["success"] for item in results)
    assert active["peak"] == 2
