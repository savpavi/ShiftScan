"""
OCR Service - Nanonets-OCR2-3B via Gradio Client
HuggingFace Space: prithivMLmods/Multimodal-OCR
"""

import asyncio
import base64
import tempfile
import os
from typing import Optional
from PIL import Image
import io

# Gradio Client import
try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    print("WARNING: gradio_client not installed. Run: pip install gradio_client")


# HuggingFace Space URL
MULTIMODAL_OCR_SPACE = "prithivMLmods/Multimodal-OCR"

# Default OCR prompt for shift schedules
DEFAULT_OCR_PROMPT = """Extract the shift schedule from this image.
Return ONLY the time values and OFF indicators in order, one per line.
Example output format:
09:00-18:00
09:00-18:00
OFF
14:00-22:00

Do NOT use HTML, tables, or markdown. Just plain text, one entry per line."""


class OCRService:
    """Nanonets-OCR2-3B based OCR service using Gradio Client"""

    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False

    def _get_client(self) -> Client:
        """Lazy initialization of Gradio client"""
        if not GRADIO_AVAILABLE:
            raise RuntimeError("gradio_client not installed")

        if self._client is None:
            try:
                self._client = Client(MULTIMODAL_OCR_SPACE)
                self._initialized = True
                print(f"INFO: Connected to HuggingFace Space: {MULTIMODAL_OCR_SPACE}")
            except Exception as e:
                print(f"ERROR: Failed to connect to HuggingFace Space: {e}")
                raise

        return self._client

    async def process_image_base64(
        self,
        image_base64: str,
        prompt: str = DEFAULT_OCR_PROMPT,
        model: str = "Nanonets-OCR2-3B"
    ) -> dict:
        """
        Process base64 encoded image through Nanonets-OCR2-3B

        Args:
            image_base64: Base64 encoded image (with or without data URI prefix)
            prompt: OCR prompt/query
            model: Model to use (default: Nanonets-OCR2-3B)

        Returns:
            dict with 'success', 'text', 'error' keys
        """
        try:
            # Remove data URI prefix if present
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]

            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_base64)

            # Create temp file for the image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(image_bytes)
                tmp_path = tmp_file.name

            try:
                # Process through Gradio
                result = await self._process_image_file(tmp_path, prompt, model)
                return result
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }

    async def process_image_file(
        self,
        image_path: str,
        prompt: str = DEFAULT_OCR_PROMPT,
        model: str = "Nanonets-OCR2-3B"
    ) -> dict:
        """
        Process image file through Nanonets-OCR2-3B

        Args:
            image_path: Path to image file
            prompt: OCR prompt/query
            model: Model to use

        Returns:
            dict with 'success', 'text', 'error' keys
        """
        return await self._process_image_file(image_path, prompt, model)

    async def _process_image_file(
        self,
        image_path: str,
        prompt: str,
        model: str
    ) -> dict:
        """Internal method to process image file"""
        try:
            client = self._get_client()

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_predict,
                client,
                image_path,
                prompt,
                model
            )

            return result

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }

    def _sync_predict(
        self,
        client: Client,
        image_path: str,
        prompt: str,
        model: str
    ) -> dict:
        """Synchronous prediction call"""
        try:
            # Call the Gradio Space predict function
            # API endpoint: /predict with parameters:
            # - model_name: str (model selection)
            # - text: str (prompt/query)
            # - image: filepath (image to process)
            # - max_new_tokens: int
            # - temperature: float
            # - top_p: float
            # - top_k: int
            # - repetition_penalty: float

            result = client.predict(
                model_name=model,
                text=prompt,
                image=handle_file(image_path),
                max_new_tokens=1024,
                temperature=0.3,  # Lower temperature for more accurate OCR
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                api_name="/generate_image"
            )

            # Result is tuple: (raw_output, markdown_output)
            if isinstance(result, tuple) and len(result) >= 1:
                text = result[0] if result[0] else (result[1] if len(result) > 1 else '')
            else:
                text = str(result)

            return {
                'success': True,
                'text': text.strip(),
                'error': None
            }

        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: Gradio prediction failed: {error_msg}")
            return {
                'success': False,
                'text': '',
                'error': error_msg
            }

    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return GRADIO_AVAILABLE


# Singleton instance
ocr_service = OCRService()


# Convenience functions
async def process_ocr_image(
    image_base64: str,
    prompt: str = DEFAULT_OCR_PROMPT
) -> dict:
    """
    Process an image for OCR

    Args:
        image_base64: Base64 encoded image
        prompt: Optional custom prompt

    Returns:
        dict with 'success', 'text', 'error' keys
    """
    return await ocr_service.process_image_base64(image_base64, prompt)


def is_ocr_available() -> bool:
    """Check if Nanonets OCR is available"""
    return ocr_service.is_available()
