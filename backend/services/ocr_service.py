"""
OCR Service — OCR.space Cloud Text Extraction & Entity Extraction Pipeline.

Extracts text from packaging images via OCR.space, enhances image clarity,
normalizes extracted tokens contextually, and applies entity extraction.
"""

import os
import base64
import logging
import re
from typing import Optional
import httpx

from config import settings
from services.image_processor import enhance_image_for_ocr
from services.entity_extractor import extract_entities_from_text

logger = logging.getLogger(__name__)


def _ocr_space_api_key() -> str:
    """Retrieve OCR.space API key from settings or environment."""
    key = getattr(settings, "OCR_SPACE_API_KEY", "") or getattr(settings, "OCR_API_KEY", "") or os.getenv("OCR_SPACE_API_KEY", "") or os.getenv("OCR_API_KEY", "")
    return key.strip()


def _extract_cloud(image_bytes: bytes) -> str:
    """Send image to OCR.space API and return raw extracted text string."""
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
        parsed = result.get("ParsedResults", [])
        if parsed:
            raw_text = parsed[0].get("ParsedText", "").replace("\r\n", "\n").strip()
            return raw_text
        return ""
    except Exception as exc:
        logger.warning("[OCR] cloud failure reason=%s", exc)
        raise


def _extract_cloud_with_scores(image_bytes: bytes) -> dict:
    """Call OCR.space and return detections with confidence scores, preserving line breaks."""
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
        raw_text_blocks = []
        for block in parsed:
            block_text = (block.get("ParsedText") or "").replace("\r\n", "\n").strip()
            if block_text:
                raw_text_blocks.append(block_text)

            overlay = block.get("TextOverlay") or block.get("LineOverlay") or {}
            lines_data = []
            if isinstance(overlay, dict):
                lines_data = overlay.get("Lines", [])
            elif isinstance(overlay, list):
                lines_data = overlay

            if lines_data:
                for line_item in lines_data:
                    words = line_item.get("Words", []) if isinstance(line_item, dict) else []
                    if words:
                        for w in words:
                            w_text = w.get("WordText", "")
                            if w_text.strip():
                                detections.append({
                                    "text": w_text.strip(),
                                    "confidence": round(float(w.get("WordConf", 95.0)) / 100.0, 4),
                                    "bbox": {
                                        "left": w.get("Left"),
                                        "top": w.get("Top"),
                                        "height": w.get("Height"),
                                        "width": w.get("Width"),
                                    } if "Left" in w else None,
                                })
                    elif isinstance(line_item, dict) and line_item.get("LineText"):
                        detections.append({
                            "text": line_item["LineText"].strip(),
                            "confidence": 0.95,
                            "bbox": None,
                        })
            else:
                for line in block_text.split("\n"):
                    if line.strip():
                        detections.append({
                            "text": line.strip(),
                            "confidence": 0.95,
                            "bbox": None,
                        })

        full_text = "\n".join(raw_text_blocks).strip()
        confidences = [d["confidence"] for d in detections if d.get("confidence")]
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
