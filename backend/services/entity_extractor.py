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
        for pattern in regex_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                extracted[entity_key] = val.strip()
                break

    return extracted
