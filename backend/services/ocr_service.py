"""
OCR Service — Dual-mode text extraction.

Supports two providers via the OCR_PROVIDER environment variable:
  - 'local'  → EasyOCR (English + Hindi), model loaded once at startup
  - 'cloud'  → OCR.space free API

The rest of the app calls extract_text(image) without knowing which backend runs.
"""

import io
import re
import base64
import logging
import os
from typing import Optional

import httpx
import cv2
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
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass

        logger.info("[OCR] local reader initialization started (en, cpu, single-thread)...")
        _reader = easyocr.Reader(["en"], gpu=False)
        logger.info("[OCR] local reader initialized successfully")
    else:
        logger.info("[OCR] local reader reused from singleton cache")
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
    """
    url = "https://api.ocr.space/parse/image"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "base64Image": f"data:image/png;base64,{b64_image}",
        "language": "eng",
        "isOverlayRequired": "false",
        "OCREngine": "2",
    }

    headers = {"apikey": _ocr_space_api_key()}
    logger.info("[OCR] cloud attempt started (payload size: %d bytes)", len(b64_image))

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data=payload, headers=headers)
            logger.info("[OCR] cloud response status=%d", response.status_code)
            response.raise_for_status()

        result = response.json()
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            logger.warning("[OCR] cloud returned no parsed results: %s", result.get("ErrorMessage"))
            return ""

        texts = [r.get("ParsedText", "") for r in parsed_results]
        return " ".join(texts).strip()

    except Exception as exc:
        logger.warning("[OCR] cloud failure reason=%s", exc)
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

    image_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        logger.error("Failed to decode image bytes")
        return ""

    reader = _get_reader()
    results = reader.readtext(image, batch_size=1, canvas_size=1280, mag_ratio=1.0)

    # results is a list of (bbox, text, prob)
    texts = [text for (_, text, prob) in results if prob > 0.3]
    return " ".join(texts)


def _extract_local_with_scores(image_bytes: bytes) -> dict:
    """Run EasyOCR and return detections with confidence and bounding boxes."""
    import numpy as np
    import gc

    image_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        return {
            "provider": "local",
            "full_text": "",
            "detections": [],
            "average_confidence": 0.0,
        }

    try:
        reader = _get_reader()
        results = reader.readtext(image, batch_size=1, canvas_size=1280, mag_ratio=1.0)

        detections = []
        for bbox, text, confidence in results:
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
    finally:
        del image, image_array
        gc.collect()


def _extract_cloud_with_scores(image_bytes: bytes) -> dict:
    """Call OCR.space and return detections with confidence (where available)."""
    url = "https://api.ocr.space/parse/image"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "base64Image": f"data:image/png;base64,{b64_image}",
        "language": "eng",
        "isOverlayRequired": "true",
        "OCREngine": "2",
    }
    headers = {"apikey": _ocr_space_api_key()}
    logger.info("[OCR] cloud attempt started (payload size: %d bytes)", len(b64_image))

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data=payload, headers=headers)
            logger.info("[OCR] cloud response status=%d", response.status_code)
            response.raise_for_status()

        result = response.json()
        parsed = result.get("ParsedResults", [])
        if not parsed:
            return {
                "provider": "cloud",
                "full_text": "",
                "detections": [],
                "average_confidence": 0.0,
            }

        detections = []
        for block in parsed:
            text = block.get("ParsedText", "")
            confidence = 0.95

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

    except Exception as exc:
        logger.warning("[OCR] cloud failure reason=%s", exc)
        raise


from services.image_processor import enhance_image_for_ocr
from services.entity_extractor import extract_entities_from_text


# ---------------------------------------------------------------------------
# Public API — the only function the rest of the app should call
# ---------------------------------------------------------------------------
def extract_text(image: bytes) -> str:
    """
    Extract text from a product-label image.
    Automatically applies OpenCV enhancement and falls back to local EasyOCR.
    """
    enhanced_image, _ = enhance_image_for_ocr(image)
    provider = settings.OCR_PROVIDER.lower()

    if provider == "cloud":
        try:
            return _extract_cloud(enhanced_image)
        except Exception as exc:
            logger.warning("Cloud OCR failed (%s), falling back to local EasyOCR...", exc)
            return _extract_local(enhanced_image)
    elif provider == "local":
        return _extract_local(enhanced_image)
    else:
        raise RuntimeError(
            f"Unknown OCR_PROVIDER '{provider}'. "
            "Set OCR_PROVIDER to 'local' or 'cloud' in your .env file."
        )


def normalize_ocr_text_contextual(raw_text: str) -> str:
    """
    Perform conservative domain-aware OCR normalization for entity extraction & rule matching.
    Raw OCR text remains untouched separately.
    Contextual corrections:
      - 'MOP ₹' / 'MOP Rs' -> 'MRP ₹' / 'MRP Rs' (when followed by currency/numbers)
      - 'Mktd by' -> 'Marketed by'
      - 'Mfd by' -> 'Manufactured by'
      - 'Net Conten' -> 'Net Content'
    """
    if not raw_text:
        return ""
    text = raw_text

    # 1. MOP -> MRP when followed by currency or price digits
    text = re.sub(r"\bMOP\b(?=\s*(?:rs\.?|₹|inr|\d))", "MRP", text, flags=re.IGNORECASE)

    # 2. Common abbreviations
    text = re.sub(r"\bMktd\s*by\b", "Marketed by", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMfd\s*by\b", "Manufactured by", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNet\s*Conten\b", "Net Content", text, flags=re.IGNORECASE)

    return text


def extract_text_with_scores(image: bytes) -> dict:
    """
    Extract text from an image, run custom package entity extractor model,
    and return detections with confidence scores.
    Always returns a valid dictionary and never raises uncaught exceptions.
    """
    enhanced_image, was_enhanced = enhance_image_for_ocr(image)
    provider = settings.OCR_PROVIDER.lower()
    res = None

    if provider == "cloud":
        try:
            res = _extract_cloud_with_scores(enhanced_image)
        except Exception as exc:
            logger.warning("[OCR] cloud OCR failed (%s), initiating safe local fallback...", exc)
            logger.info("[OCR] local fallback started")
            try:
                res = _extract_local_with_scores(enhanced_image)
                res["provider"] = "local (fallback)"
            except Exception as local_exc:
                logger.error("[OCR] local fallback also encountered error: %s", local_exc)
                res = {
                    "provider": "unavailable",
                    "full_text": "",
                    "detections": [],
                    "average_confidence": 0.0,
                    "error": f"Cloud and local OCR unavailable: {str(local_exc)}"
                }
    elif provider == "local":
        logger.info("[OCR] local OCR started")
        try:
            res = _extract_local_with_scores(enhanced_image)
        except Exception as local_exc:
            logger.error("[OCR] local OCR encountered error: %s", local_exc)
            res = {
                "provider": "local (error)",
                "full_text": "",
                "detections": [],
                "average_confidence": 0.0,
                "error": str(local_exc)
            }
    else:
        res = {
            "provider": "unknown",
            "full_text": "",
            "detections": [],
            "average_confidence": 0.0,
            "error": f"Unknown OCR_PROVIDER '{provider}'"
        }

    res["enhanced"] = was_enhanced
    raw_full_text = res.get("full_text", "")
    normalized_full_text = normalize_ocr_text_contextual(raw_full_text)

    res["full_text"] = raw_full_text
    res["normalized_full_text"] = normalized_full_text
    res["extracted_entities"] = extract_entities_from_text(normalized_full_text)
    return res


def preload_model() -> None:
    """
    Eagerly load the EasyOCR model at application startup.

    Call this once in main.py when OCR_PROVIDER=local so the first
    user request doesn't pay the model-loading penalty.
    """
    if settings.OCR_PROVIDER.lower() == "local":
        _get_reader()
