"""Kaynakları sınırlanmış legacy Nanonets OCR servisi."""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
from typing import Optional

from services.schedule_extraction import MAX_IMAGE_BYTES, validate_image

try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    Client = None
    handle_file = None
    GRADIO_AVAILABLE = False


MULTIMODAL_OCR_SPACE = "prithivMLmods/Multimodal-OCR"
OCR_DEADLINE_SECONDS = 45.0
MAX_CONCURRENT_JOBS = 2
DEFAULT_OCR_PROMPT = """Extract the shift schedule from this image.
Return ONLY the time values and OFF indicators in order, one per line.
Example output format:
09:00-18:00
09:00-18:00
OFF
14:00-22:00

Do NOT use HTML, tables, or markdown. Just plain text, one entry per line."""
_SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


class OCRService:
    def __init__(self):
        self._client: Optional[Client] = None
        self._client_lock = asyncio.Lock()
        self._jobs = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

    async def _get_client(self) -> Client:
        if not GRADIO_AVAILABLE:
            raise RuntimeError("gradio_client not installed")
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = await asyncio.to_thread(Client, MULTIMODAL_OCR_SPACE)
        return self._client

    async def process_image_base64(
        self,
        image_base64: str,
        prompt: str = DEFAULT_OCR_PROMPT,
        model: str = "Nanonets-OCR2-3B",
    ) -> dict:
        temp_path = None
        job_holder: dict = {}
        try:
            image = await asyncio.to_thread(validate_image, image_base64)
            image_bytes = base64.b64decode(image["data"], validate=True)
            with tempfile.NamedTemporaryFile(
                suffix=_SUFFIXES[image["mime_type"]], delete=False
            ) as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
            return await asyncio.wait_for(
                self._process_image_file(temp_path, prompt, model, job_holder),
                timeout=OCR_DEADLINE_SECONDS,
            )
        except (TimeoutError, asyncio.TimeoutError):
            await self._cancel_job(job_holder.get("job"))
            return {"success": False, "text": "", "error": "OCR isteği zaman aşımına uğradı."}
        except Exception:
            await self._cancel_job(job_holder.get("job"))
            return {"success": False, "text": "", "error": "OCR işlemi başarısız oldu."}
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass

    async def process_image_file(
        self,
        image_path: str,
        prompt: str = DEFAULT_OCR_PROMPT,
        model: str = "Nanonets-OCR2-3B",
    ) -> dict:
        try:
            encoded = await asyncio.to_thread(self._read_image, image_path)
        except Exception:
            return {"success": False, "text": "", "error": "OCR işlemi başarısız oldu."}
        return await self.process_image_base64(encoded, prompt, model)

    @staticmethod
    def _read_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            content = image_file.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise ValueError("image too large")
        return base64.b64encode(content).decode("ascii")

    async def _process_image_file(
        self, image_path: str, prompt: str, model: str, job_holder: dict
    ) -> dict:
        async with self._jobs:
            client = await self._get_client()
            job = await asyncio.to_thread(
                client.submit,
                model_name=model,
                text=prompt,
                image=handle_file(image_path),
                max_new_tokens=1024,
                temperature=0.3,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                api_name="/generate_image",
            )
            job_holder["job"] = job
            try:
                result = await asyncio.to_thread(job.result, timeout=OCR_DEADLINE_SECONDS)
            except TimeoutError:
                await self._cancel_job(job)
                raise
            if isinstance(result, tuple):
                text = result[0] or (result[1] if len(result) > 1 else "")
            else:
                text = str(result)
            return {"success": True, "text": str(text).strip(), "error": None}

    @staticmethod
    async def _cancel_job(job) -> None:
        if job is None or not hasattr(job, "cancel"):
            return
        try:
            await asyncio.to_thread(job.cancel)
        except Exception:
            pass

    def is_available(self) -> bool:
        return GRADIO_AVAILABLE


ocr_service = OCRService()


async def process_ocr_image(image_base64: str, prompt: str = DEFAULT_OCR_PROMPT) -> dict:
    return await ocr_service.process_image_base64(image_base64, prompt)


def is_ocr_available() -> bool:
    return ocr_service.is_available()
