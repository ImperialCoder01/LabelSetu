"""
OCR Service — Dual-mode text extraction.

Supports two providers via the OCR_PROVIDER environment variable:
  - 'local'  → EasyOCR (English + Hindi), model loaded once at startup
  - 'cloud'  → OCR.space free API

The rest of the app calls extract_text(image) without knowing which backend runs.
"""

import io
import base64
import logging
import os
from typing import Optional

import httpx
from PIL import Image

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded EasyOCR reader (imported only in local mode)
# ---------------------------------------------------------------------------
_reader = None


def _get_reader():
    """Return the singleton EasyOCR reader, creating it on first call."""
    global _reader
    if _reader is None:
        import easyocr

        logger.info("Loading EasyOCR model (en + hi) … this may take a moment on first run")
        _reader = easyocr.Reader(["en", "hi"], gpu=False)  # set gpu=True if CUDA available
        logger.info("EasyOCR model loaded")
    return _reader


# ---------------------------------------------------------------------------
# Cloud mode helpers
# ---------------------------------------------------------------------------
def _ocr_space_api_key() -> str:
    """Return the OCR.space API key from settings."""
    key = settings.OCR_API_KEY
    if not key:
        raise RuntimeError(
            "OCR_API_KEY is not set. "
            "Get a free key at https://ocr.space/ocrapi/freekey and add it to .env"
        )
    return key


def _extract_cloud(image_bytes: bytes) -> str:
    """
    Send image bytes to the OCR.space API and return extracted text.

    Uses the free tier: https://ocr.space/ocrapi
    """
    url = "https://api.ocr.space/parse/image"

    # OCR.space accepts base64-encoded images
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "base64Image": f"data:image/png;base64,{b64_image}",
        "language": "eng",  # OCR.space free tier supports eng; Hindi needs a paid plan
        "isOverlayRequired": "false",
        "OCREngine": "2",  # Engine 2 is better for printed text / labels
    }

    headers = {"apikey": _ocr_space_api_key()}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, data=payload, headers=headers)
            response.raise_for_status()

        result = response.json()

        # OCR.space wraps the result in "ParsedResults"
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            logger.warning("OCR.space returned no parsed results: %s", result.get("ErrorMessage"))
            return ""

        # Concatenate all parsed text blocks
        texts = [r.get("ParsedText", "") for r in parsed_results]
        return " ".join(texts).strip()

    except httpx.HTTPStatusError as exc:
        logger.error("OCR.space HTTP error %s: %s", exc.response.status_code, exc.response.text)
        raise RuntimeError(f"OCR.space API error: {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error("OCR.space request failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Local mode helpers
# ---------------------------------------------------------------------------
def _extract_local(image_bytes: bytes) -> str:
    """
    Run EasyOCR on raw image bytes and return extracted text.

    The EasyOCR reader is loaded once and reused across requests.
    """
    import numpy as np

    image = Image.open(io.BytesIO(image_bytes))

    # EasyOCR expects RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    image_array = np.array(image)

    reader = _get_reader()
    results = reader.readtext(image_array)

    # Filter by confidence and join
    extracted = [text for (_, text, confidence) in results if confidence > 0.3]
    return " ".join(extracted)


def _extract_local_with_scores(image_bytes: bytes) -> dict:
    """Run EasyOCR and return detections with bounding boxes and confidence."""
    import numpy as np

    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")

    image_array = np.array(image)
    reader = _get_reader()
    results = reader.readtext(image_array)

    detections = []
    for (bbox, text, confidence) in results:
        # Convert numpy arrays to plain Python lists for JSON serialization
        bbox_list = [[int(pt[0]), int(pt[1])] for pt in bbox]
        detections.append({
            "text": text,
            "confidence": round(float(confidence), 4),
            "bbox": bbox_list,
        })

    full_text = " ".join(d["text"] for d in detections if d["confidence"] > 0.3)
    confidences = [d["confidence"] for d in detections]
    avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    return {
        "provider": "local",
        "full_text": full_text,
        "detections": detections,
        "average_confidence": avg,
    }


def _extract_cloud_with_scores(image_bytes: bytes) -> dict:
    """Call OCR.space and return detections with confidence (where available)."""
    url = "https://api.ocr.space/parse/image"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "base64Image": f"data:image/png;base64,{b64_image}",
        "language": "eng",
        "isOverlayRequired": "true",  # needed for per-line confidence
        "OCREngine": "2",
    }
    headers = {"apikey": _ocr_space_api_key()}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, data=payload, headers=headers)
            response.raise_for_status()

        result = response.json()
        parsed = result.get("ParsedResults", [])
        if not parsed:
            return {"provider": "cloud", "full_text": "", "detections": [], "average_confidence": 0.0}

        detections = []
        for block in parsed:
            text = block.get("ParsedText", "")
            # OCR.space returns Words or LineOverlay with confidence
            line_conf = block.get("FileParseExitCode")
            confidence = 0.95  # default when not provided per-line

            # Try to extract per-word confidence from LineOverlay
            line_overlay = block.get("LineOverlay", [])
            if line_overlay:
                words = line_overlay[0].get("Words", []) if line_overlay else []
                for w in words:
                    detections.append({
                        "text": w.get("WordText", ""),
                        "confidence": round(float(w.get("WordConf", 0)) / 100.0, 4),
                        "bbox": None,
                    })
            else:
                detections.append({
                    "text": text.strip(),
                    "confidence": confidence,
                    "bbox": None,
                })

        full_text = " ".join(d["text"] for d in detections if d["confidence"] > 0.3)
        confidences = [d["confidence"] for d in detections]
        avg = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        return {
            "provider": "cloud",
            "full_text": full_text,
            "detections": detections,
            "average_confidence": avg,
        }

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"OCR.space API error: {exc.response.status_code}") from exc
    except Exception as exc:
        raise


# ---------------------------------------------------------------------------
# Public API — the only function the rest of the app should call
# ---------------------------------------------------------------------------
def extract_text(image: bytes) -> str:
    """
    Extract text from a product-label image.

    Args:
        image: Raw image bytes (PNG / JPEG).

    Returns:
        Extracted text as a single string, or empty string if nothing found.

    Raises:
        RuntimeError: If the configured provider fails.
    """
    provider = settings.OCR_PROVIDER.lower()

    if provider == "cloud":
        return _extract_cloud(image)
    elif provider == "local":
        return _extract_local(image)
    else:
        raise RuntimeError(
            f"Unknown OCR_PROVIDER '{provider}'. "
            "Set OCR_PROVIDER to 'local' or 'cloud' in your .env file."
        )


def extract_text_with_scores(image: bytes) -> dict:
    """
    Extract text from an image and return individual detections with
    bounding boxes and confidence scores.

    Args:
        image: Raw image bytes (PNG / JPEG).

    Returns:
        {
          "provider": "local" | "cloud",
          "full_text": "...",
          "detections": [
            {"text": "...", "confidence": 0.95, "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]},
            ...
          ],
          "average_confidence": 0.92
        }
    """
    provider = settings.OCR_PROVIDER.lower()

    if provider == "local":
        return _extract_local_with_scores(image)
    elif provider == "cloud":
        return _extract_cloud_with_scores(image)
    else:
        raise RuntimeError(
            f"Unknown OCR_PROVIDER '{provider}'. "
            "Set OCR_PROVIDER to 'local' or 'cloud' in your .env file."
        )


def preload_model() -> None:
    """
    Eagerly load the EasyOCR model at application startup.

    Call this once in main.py when OCR_PROVIDER=local so the first
    user request doesn't pay the model-loading penalty.
    """
    if settings.OCR_PROVIDER.lower() == "local":
        _get_reader()
