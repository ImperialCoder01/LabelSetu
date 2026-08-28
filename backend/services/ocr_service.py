"""
OCR Service — Cloud text extraction via OCR.space.

Extracts text from packaging images via OCR.space API, applies domain-aware
contextual text normalization, and runs entity extraction.
"""

import io
import re
import base64
import logging
from typing import Optional

import httpx

from config import settings
from services.image_processor import enhance_image_for_ocr
from services.entity_extractor import extract_entities_from_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cloud OCR (OCR.space) helpers
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


def _extract_cloud_with_scores(image_bytes: bytes) -> dict:
    """Call OCR.space and return detections with confidence scores."""
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


# ---------------------------------------------------------------------------
# Normalization & Public APIs
# ---------------------------------------------------------------------------
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


def extract_text(image: bytes) -> str:
    """
    Extract text from a product-label image using OCR.space.
    Automatically applies OpenCV enhancement. Returns empty string on failure.
    """
    enhanced_image, _ = enhance_image_for_ocr(image)
    try:
        return _extract_cloud(enhanced_image)
    except Exception as exc:
        logger.warning("[OCR] Cloud OCR failed (%s)", exc)
        return ""


def extract_text_with_scores(image: bytes) -> dict:
    """
    Extract text from an image using OCR.space, run custom package entity extractor model,
    and return detections with confidence scores.
    Always returns a valid dictionary and never raises uncaught exceptions.
    """
    enhanced_image, was_enhanced = enhance_image_for_ocr(image)
    try:
        res = _extract_cloud_with_scores(enhanced_image)
    except Exception as exc:
        logger.warning("[OCR] Cloud OCR failed (%s), returning safe unavailable structure", exc)
        res = {
            "provider": "cloud (unavailable)",
            "full_text": "",
            "detections": [],
            "average_confidence": 0.0,
            "error": f"Cloud OCR unavailable: {str(exc)}"
        }

    res["enhanced"] = was_enhanced
    raw_full_text = res.get("full_text", "")
    normalized_full_text = normalize_ocr_text_contextual(raw_full_text)

    res["full_text"] = raw_full_text
    res["normalized_full_text"] = normalized_full_text
    res["extracted_entities"] = extract_entities_from_text(normalized_full_text)
    return res


def preload_model() -> None:
    """No-op kept for backwards compatibility."""
    pass
