"""
Custom Package Label Entity Extractor Service.

Loads trained weights from backend/models/label_classifier_weights.json
and performs domain-specific Entity Recognition (NER) on OCR-extracted label text.

Extracts structured entities:
  - MRP (Max Retail Price)
  - Unit Sale Price
  - Manufacturing / Packaging Date
  - Expiry / Best Before Date
  - Net Quantity / Weight
  - FSSAI License Number
  - Country of Origin
  - Consumer Care Contact
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Path to trained model weights
WEIGHTS_PATH = Path(__file__).parent.parent / "models" / "label_classifier_weights.json"

_MODEL_DATA: Optional[Dict[str, Any]] = None


def _load_model_weights() -> Dict[str, Any]:
    """Load trained label classification rules and weights."""
    global _MODEL_DATA
    if _MODEL_DATA is None:
        if WEIGHTS_PATH.exists():
            try:
                with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
                    _MODEL_DATA = json.load(f)
                logger.info("Loaded custom label entity model weights (v%s)", _MODEL_DATA.get("model_version"))
            except Exception as exc:
                logger.error("Failed to load trained model weights: %s", exc)
                _MODEL_DATA = {}
        else:
            logger.warning("Model weights file not found at %s. Using default patterns.", WEIGHTS_PATH)
            _MODEL_DATA = {}
    return _MODEL_DATA


def _extract_net_quantity(text: str) -> Optional[str]:
    """
    Extract net quantity with strict priority:
    1. Explicit declarations (Net Content, Net Quantity, Net Wt, Net Weight, Net Vol, etc.)
    2. Standalone quantity declarations strictly excluding USP / Unit Sale Price lines.
    """
    if not text or not text.strip():
        return None

    # Priority 1: Explicit prefixes
    explicit_patterns = [
        r"(?:net\s*(?:content|contents|quantity|qty|weight|wt|volume|vol)(?:\s*\([^)]*\))?)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|litres|litre|gm|pcs|pieces|nos)\b(?:\s*\([\d\.]+\s*(?:g|kg|ml|l|ltr|gm)\))?)",
        r"(?:net\s*(?:content|contents|quantity|qty|weight|wt|volume|vol)(?:\s*\([^)]*\))?)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|litres|litre|gm|pcs|pieces|nos)\b)",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Ensure it is not matching a USP string like 2.60/ml
            if not re.search(r"(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price)\s*[:\.-]?\s*" + re.escape(val), text, re.IGNORECASE):
                return val

    # Priority 2: Standalone quantity (Filtering out lines/fragments with USP/price per unit)
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        if not re.search(r"\b(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price|per\s*(?:g|ml|kg|l|ltr)|/\s*(?:g|ml|kg|l|ltr))\b", line, re.IGNORECASE):
            clean_lines.append(line)
        else:
            cleaned_line = re.sub(r"(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price)\s*[:\.-]?\s*[^,\n]+", "", line, flags=re.IGNORECASE)
            cleaned_line = re.sub(r"\b[\d\.]+\s*(?:per|/)\s*(?:g|ml|kg|l|ltr)\b", "", cleaned_line, flags=re.IGNORECASE)
            clean_lines.append(cleaned_line)

    clean_text = "\n".join(clean_lines)

    fallback_pattern = r"\b([\d\.]+\s*(?:g|kg|ml|l|ltr|gm))\b"
    for match in re.finditer(fallback_pattern, clean_text, re.IGNORECASE):
        val = match.group(1).strip()
        match_start = match.start()
        prefix_window = clean_text[max(0, match_start - 30):match_start]
        if not re.search(r"(?:usp|unit|per|/)\s*$", prefix_window, re.IGNORECASE):
            return val

    return None


def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Apply trained entity recognition patterns to OCR extracted text.

    Args:
        text: Raw OCR extracted text string.

    Returns:
        Structured entity dictionary containing detected label declarations.
    """
    model_data = _load_model_weights()
    patterns = model_data.get("patterns", {})

    extracted = {
        "mrp": None,
        "unit_sale_price": None,
        "mfg_date": None,
        "expiry_date": None,
        "net_quantity": None,
        "fssai_lic": None,
        "country_of_origin": None,
        "consumer_care": None,
    }

    if not text or not text.strip():
        return extracted

    # Fallback default regex patterns if model file is unreadable
    default_patterns = {
        "mrp": [r"(?:mrp|max\s*retail\s*price|price)\s*[:\.-]?\s*(?:rs\.?|₹)?\s*([\d\.,]+)"],
        "unit_sale_price": [r"(?:unit\s*sale\s*price|unit\s*price)\s*[:\.-]?\s*([^\n,]+)"],
        "mfg_date": [r"(?:mfg|manufactured|pkd|packed|dop)\s*(?:date)?\s*[:\.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4})"],
        "expiry_date": [r"(?:exp|expiry|best\s*before|use\s*by)\s*(?:date)?\s*[:\.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4}|\d+\s*months?)"],
        "net_quantity": [r"(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|gm))"],
        "fssai_lic": [r"(?:fssai|lic)\s*(?:no\.?|num)?\s*[:\.-]?\s*(\d{14})"],
        "country_of_origin": [r"(?:country\s*of\s*origin|made\s*in|product\s*of)\s*[:\.-]?\s*([a-zA-Z]+)"],
        "consumer_care": [r"(?:customer\s*care|consumer\s*care|care\s*line|toll\s*free)\s*[:\.-]?\s*([^\n,]+)"],
    }

    active_patterns = patterns if patterns else default_patterns

    for entity_key, regex_list in active_patterns.items():
        if entity_key == "net_quantity":
            extracted["net_quantity"] = _extract_net_quantity(text)
            continue

        for pattern in regex_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                extracted[entity_key] = val.strip()
                break

    return extracted
