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


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

INV_MONTH_MAP = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
}


def _extract_mfg_date(text: str) -> Optional[str]:
    """
    Extract manufacturing/packaging date from OCR text.
    Supports textual month abbreviations (e.g., 'Mfg: DEC 2026', 'Packed on: AUG-2026')
    as well as numeric formats (e.g., 'Mfg: 12/2026', '15/08/2026').
    Requires explicit manufacturing context prefixes.
    """
    if not text or not text.strip():
        return None

    # Priority 1: Textual Month (e.g., Mfg: DEC 2026, Manufactured: DECEMBER 2026, Packed: AUG-2026)
    textual_pattern = r"(?:mfg|mfd|manufactured|pkd|packed|pkg|dop)\s*(?:date|on)?\s*[:\.-]?\s*\b([a-zA-Z]{3,9})[\s\.-]+(\d{2,4})\b"
    match = re.search(textual_pattern, text, re.IGNORECASE)
    if match:
        month_str, year_str = match.group(1).strip(), match.group(2).strip()
        if month_str.lower() in MONTH_MAP:
            return f"{month_str.upper()} {year_str}"

    # Priority 2: Numeric Date (e.g., Mfg: 12/2026, Pkd: 15/08/2026)
    numeric_pattern = r"(?:mfg|mfd|manufactured|pkd|packed|pkg|dop)\s*(?:date|on)?\s*[:\.-]?\s*\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4})\b"
    match = re.search(numeric_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def _extract_expiry_date(text: str, mfg_date: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """
    Extract expiry date directly from OCR text or calculate from explicit 'Best Before X Months' statement.
    Returns Tuple[expiry_date_str, is_derived_boolean].
    """
    if not text or not text.strip():
        return None, False

    # Direct Expiry Pattern (Textual or Numeric, e.g. Exp: DEC 2027, Best Before 15/08/2027)
    direct_textual = r"(?:exp|expiry|best\s*before|use\s*by)\s*(?:date|on)?\s*[:\.-]?\s*\b([a-zA-Z]{3,9})[\s\.-]+(\d{2,4})\b"
    match = re.search(direct_textual, text, re.IGNORECASE)
    if match:
        month_str, year_str = match.group(1).strip(), match.group(2).strip()
        if month_str.lower() in MONTH_MAP:
            return f"{month_str.upper()} {year_str}", False

    direct_numeric = r"(?:exp|expiry|best\s*before|use\s*by)\s*(?:date|on)?\s*[:\.-]?\s*\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4})\b"
    match = re.search(direct_numeric, text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), False

    # Duration Calculation Pattern (e.g., Best Before 12 Months, Use within 6 months)
    # Strictly requires 'best before' / 'use by' / 'expiry' context
    duration_pattern = r"(?:best\s*before|use\s*by|use\s*within|expiry\s*within)\s*(?:within|of)?\s*(\d{1,2})\s*months?\b"
    match = re.search(duration_pattern, text, re.IGNORECASE)
    if match and mfg_date:
        months_to_add = int(match.group(1))
        # Check textual mfg_date (e.g., DEC 2026)
        mfg_match = re.match(r"^([a-zA-Z]{3,9})\s+(\d{4})$", mfg_date.strip())
        if mfg_match and mfg_match.group(1).lower() in MONTH_MAP:
            start_m = MONTH_MAP[mfg_match.group(1).lower()]
            start_y = int(mfg_match.group(2))
            total_m = (start_m - 1) + months_to_add
            new_m = (total_m % 12) + 1
            new_y = start_y + (total_m // 12)
            month_abbr = INV_MONTH_MAP.get(new_m, f"{new_m:02d}")
            return f"{month_abbr} {new_y}", True

        # Check numeric mfg_date (e.g., 12/2026 or 15/08/2026)
        num_parts = [p for p in re.split(r"[/-]", mfg_date.strip()) if p.isdigit()]
        if len(num_parts) >= 2:
            try:
                start_m = int(num_parts[0]) if len(num_parts) == 2 else int(num_parts[1])
                start_y = int(num_parts[-1])
                if 1 <= start_m <= 12 and start_y > 1000:
                    total_m = (start_m - 1) + months_to_add
                    new_m = (total_m % 12) + 1
                    new_y = start_y + (total_m // 12)
                    month_abbr = INV_MONTH_MAP.get(new_m, f"{new_m:02d}")
                    return f"{month_abbr} {new_y}", True
            except Exception:
                pass

    return None, False


MANUFACTURER_ROLE_PREFIXES = [
    r"(?:manufactured\s*(?:&|and|/)\s*packed\s*by|packed\s*(?:&|and|/)\s*manufactured\s*by)\s*[:\.-]?",
    r"(?:manufactured\s*by|manufactured\s*at|manufactured\s*in|mfg\.?\s*by|produced\s*by|made\s*by|manufacturer|factory)\s*[:\.-]?",
    r"(?:packed\s*by|packed\s*at|packed\s*in|pkd\.?\s*by)\s*[:\.-]?",
]

MANUFACTURER_BOUNDARIES = [
    r"\b(?:marketed\s*by|marketed\s*at|distributed\s*by|imported\s*by|importer)\b",
    r"\b(?:customer\s*care|consumer\s*care|care\s*line|toll\s*free|contact\s*us|feedback|email|phone|helpline)\b",
    r"\b(?:mrp|max\s*retail\s*price|maximum\s*retail\s*price|price)\b",
    r"\b(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol|net\s*content|contents)\b",
    r"\b(?:mfg\s*date|mfd|manufacturing\s*date|exp|expiry|best\s*before|use\s*by)\b",
    r"\b(?:batch\s*no|batch|lot\s*no|lot)\b",
    r"\b(?:country\s*of\s*origin|made\s*in|product\s*of)\b",
    r"\b(?:fssai|lic\s*no|licence|license)\b",
    r"\b(?:ingredients|nutrition|nutritional)\b",
    r"\b(?:www\.|http://|https://)\b",
]


def _extract_manufacturer_name_address(text: str) -> Optional[str]:
    """
    Extract Manufacturer/Packer Name & Address across multiple lines.
    Terminates extraction strictly at semantic boundaries (Marketed by, Customer Care, MRP, Net Qty, etc.)
    to preserve role separation and prevent entity contamination.
    """
    if not text or not text.strip():
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    start_idx = -1
    prefix_matched = None

    for idx, line in enumerate(lines):
        for pattern in MANUFACTURER_ROLE_PREFIXES:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                start_idx = idx
                prefix_matched = match
                break
        if start_idx != -1:
            break

    if start_idx == -1:
        return None

    collected_parts = []

    # Check text after prefix on the starting line
    start_line = lines[start_idx]
    after_prefix = start_line[prefix_matched.end():].strip()
    after_prefix = re.sub(r"^[:\.-]+", "", after_prefix).strip()
    if after_prefix:
        collected_parts.append(after_prefix)

    # Collect subsequent lines until a boundary line is reached
    max_lines_to_read = 4
    for idx in range(start_idx + 1, min(len(lines), start_idx + 1 + max_lines_to_read)):
        current_line = lines[idx]

        # Stop if line hits any boundary
        hit_boundary = False
        for boundary in MANUFACTURER_BOUNDARIES:
            if re.search(boundary, current_line, re.IGNORECASE):
                hit_boundary = True
                break

        if not hit_boundary:
            for pattern in MANUFACTURER_ROLE_PREFIXES:
                if re.search(pattern, current_line, re.IGNORECASE):
                    hit_boundary = True
                    break

        if hit_boundary:
            break

        if current_line:
            collected_parts.append(current_line)

    if not collected_parts:
        return None

    result = ", ".join(collected_parts)
    result = re.sub(r"\s*,\s*,", ",", result)
    result = result.strip(" ,.-")
    return result if len(result) > 2 else None


CONSUMER_CARE_ROLE_PREFIXES = [
    r"(?:customer\s*care|consumer\s*care|consumer\s*care\s*executive|customer\s*service|care\s*line|care\s*helpline|toll\s*free|contact\s*us|feedback|help\s*line)\s*[:\.-]?",
]

CONSUMER_CARE_BOUNDARIES = [
    r"\b(?:manufactured\s*by|manufactured\s*at|manufactured\s*in|mfg\.?\s*by|produced\s*by|made\s*by|manufacturer|factory|packed\s*by|pkd\.?\s*by)\b",
    r"\b(?:marketed\s*by|marketed\s*at|distributed\s*by|imported\s*by|importer)\b",
    r"\b(?:mrp|max\s*retail\s*price|maximum\s*retail\s*price|price)\b",
    r"\b(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol|net\s*content|contents)\b",
    r"\b(?:mfg\s*date|mfd|manufacturing\s*date|exp|expiry|best\s*before|use\s*by)\b",
    r"\b(?:batch\s*no|batch|lot\s*no|lot)\b",
    r"\b(?:country\s*of\s*origin|made\s*in|product\s*of)\b",
    r"\b(?:fssai|lic\s*no|licence|license)\b",
    r"\b(?:ingredients|nutrition|nutritional)\b",
    r"\b(?:usp|unit\s*sale\s*price|unit\s*price|price\s*per)\b",
]


def _extract_consumer_care(text: str) -> Optional[str]:
    """
    Extract Consumer Care details (Executive, Toll-Free Phone, Email, Website) across multiple lines.
    Terminates extraction strictly at semantic boundaries (Manufactured by, Marketed by, MRP, Net Qty, etc.)
    to prevent entity contamination.
    """
    if not text or not text.strip():
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    start_idx = -1
    prefix_matched = None

    for idx, line in enumerate(lines):
        for pattern in CONSUMER_CARE_ROLE_PREFIXES:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                start_idx = idx
                prefix_matched = match
                break
        if start_idx != -1:
            break

    collected_parts = []

    if start_idx != -1:
        start_line = lines[start_idx]
        after_prefix = start_line[prefix_matched.end():].strip()
        after_prefix = re.sub(r"^[:\.-]+", "", after_prefix).strip()
        if after_prefix:
            collected_parts.append(after_prefix)

        max_lines_to_read = 4
        for idx in range(start_idx + 1, min(len(lines), start_idx + 1 + max_lines_to_read)):
            current_line = lines[idx]

            hit_boundary = False
            for boundary in CONSUMER_CARE_BOUNDARIES:
                if re.search(boundary, current_line, re.IGNORECASE):
                    hit_boundary = True
                    break

            if hit_boundary:
                break

            if current_line:
                collected_parts.append(current_line)

    if not collected_parts:
        match = re.search(r"\b(1800[-\s]?\d{3}[-\s]?\d{4})\b", text)
        if match:
            return match.group(1)
        match = re.search(r"\b([a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9.-]+\.)+[a-zA-Z]{2,})\b", text)
        if match:
            return match.group(1)
        return None

    result = ", ".join(collected_parts)
    result = re.sub(r"\s*,\s*,", ",", result)
    result = result.strip(" ,.-")
    return result if len(result) > 2 else None


def extract_entities_with_evidence(raw_text: str, normalized_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured entities with complete evidence tracing:
    - value
    - source ("IMAGE" / "BARCODE_CATALOG" / "INFERENCE")
    - raw_snippet (exact raw OCR text line matched)
    - normalized_snippet (normalized text line matched)
    - confidence (estimated extraction confidence score)
    - normalization_applied (boolean)
    """
    norm_text = normalized_text or raw_text or ""
    simple_extracted = extract_entities_from_text(norm_text)
    detailed = {}

    raw_lines = [line.strip() for line in (raw_text or "").split("\n") if line.strip()]
    norm_lines = [line.strip() for line in norm_text.split("\n") if line.strip()]

    for key, val in simple_extracted.items():
        if val is None:
            detailed[key] = {
                "value": None,
                "source": "not_detected",
                "raw_snippet": None,
                "normalized_snippet": None,
                "confidence": 0.0,
                "normalization_applied": False,
            }
            continue

        raw_snippet = None
        for line in raw_lines:
            if val.lower() in line.lower() or key.replace("_", " ") in line.lower():
                raw_snippet = line
                break

        norm_snippet = None
        for line in norm_lines:
            if val.lower() in line.lower() or key.replace("_", " ") in line.lower():
                norm_snippet = line
                break

        normalization_applied = raw_snippet != norm_snippet if raw_snippet and norm_snippet else False

        source = "IMAGE"
        if key == "expiry_date" and "best before" in norm_text.lower() and not any(val.lower() in l.lower() for l in raw_lines):
            source = "INFERENCE"

        detailed[key] = {
            "value": val,
            "source": source,
            "raw_snippet": raw_snippet or f"Text contains '{val}'",
            "normalized_snippet": norm_snippet or raw_snippet or f"Text contains '{val}'",
            "confidence": 0.95 if len(val) > 2 else 0.85,
            "normalization_applied": normalization_applied,
        }

    return detailed


COUNTRY_ORIGIN_PREFIXES = [
    r"(?:country\s*of\s*origin|country\s*of\s*origin\s*code|origin\s*country)\s*[:\.-]?",
    r"(?:made\s*in|product\s*of|produced\s*in|manufactured\s*in|imported\s*from)\s*[:\.-]?",
]

ORIGIN_BOUNDARIES = [
    r"\b(?:manufactured\s*by|manufactured\s*at|mfg\.?\s*by|produced\s*by|made\s*by|manufacturer|factory|packed\s*by|pkd\.?\s*by)\b",
    r"\b(?:marketed\s*by|marketed\s*at|distributed\s*by|imported\s*by|importer)\b",
    r"\b(?:customer\s*care|consumer\s*care|care\s*line|toll\s*free|contact\s*us|feedback|email|phone|helpline)\b",
    r"\b(?:mrp|max\s*retail\s*price|maximum\s*retail\s*price|price)\b",
    r"\b(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol|net\s*content|contents)\b",
    r"\b(?:mfg\s*date|mfd|manufacturing\s*date|exp|expiry|best\s*before|use\s*by)\b",
    r"\b(?:batch\s*no|batch|lot\s*no|lot)\b",
    r"\b(?:fssai|lic\s*no|licence|license)\b",
    r"\b(?:ingredients|nutrition|nutritional)\b",
    r"\b(?:usp|unit\s*sale\s*price|unit\s*price|price\s*per)\b",
    r"\b(?:www\.|http://|https://)\b",
]


def _extract_country_of_origin(text: str) -> Optional[str]:
    """
    Extract Country of Origin (e.g. 'Republic of India', 'United States of America', 'India')
    using explicit origin headers (Country of Origin, Made in, Product of, etc.).
    Terminates extraction strictly before unrelated packaging fields (Manufactured by, MRP, Net Qty, etc.)
    to prevent entity contamination.
    """
    if not text or not text.strip():
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        for prefix_pat in COUNTRY_ORIGIN_PREFIXES:
            match = re.search(prefix_pat, line, re.IGNORECASE)
            if match:
                remainder = line[match.end():].strip()
                remainder = re.sub(r"^[:\.-]+", "", remainder).strip()
                if not remainder:
                    continue

                for boundary in ORIGIN_BOUNDARIES:
                    b_match = re.search(boundary, remainder, re.IGNORECASE)
                    if b_match:
                        remainder = remainder[:b_match.start()].strip()

                remainder = re.sub(r"[\.,;\-:]+$", "", remainder).strip()
                if remainder and len(remainder) >= 2:
                    return remainder

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
        "manufacturer_name_address": None,
    }

    if not text or not text.strip():
        return extracted

    # Fallback default regex patterns if model file is unreadable
    default_patterns = {
        "mrp": [r"(?:mrp|max\s*retail\s*price|price)\s*[:\.-]?\s*(?:rs\.?|₹)?\s*([\d\.,]+)"],
        "unit_sale_price": [r"(?:unit\s*sale\s*price|unit\s*price)\s*[:\.-]?\s*([^\n,]+)"],
        "net_quantity": [r"(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|gm))"],
        "fssai_lic": [r"(?:fssai|lic)\s*(?:no\.?|num)?\s*[:\.-]?\s*(\d{14})"],
        "consumer_care": [r"(?:customer\s*care|consumer\s*care|care\s*line|toll\s*free)\s*[:\.-]?\s*([^\n,]+)"],
    }

    active_patterns = patterns if patterns else default_patterns

    # 1. Custom Extractor for Net Quantity
    extracted["net_quantity"] = _extract_net_quantity(text)

    # 2. Custom Extractor for Manufacturing Date
    extracted["mfg_date"] = _extract_mfg_date(text)

    # 3. Custom Extractor for Expiry Date (Direct + Best Before calculation)
    exp_val, _ = _extract_expiry_date(text, extracted["mfg_date"])
    extracted["expiry_date"] = exp_val

    # 4. Custom Extractor for Manufacturer Name & Address
    extracted["manufacturer_name_address"] = _extract_manufacturer_name_address(text)

    # 5. Custom Extractor for Consumer Care Details
    extracted["consumer_care"] = _extract_consumer_care(text)

    # 6. Custom Extractor for Country of Origin
    extracted["country_of_origin"] = _extract_country_of_origin(text)

    # 7. Extract remaining entities
    for entity_key, regex_list in active_patterns.items():
        if entity_key in ("net_quantity", "mfg_date", "expiry_date", "manufacturer_name_address", "consumer_care", "country_of_origin"):
            continue

        for pattern in regex_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                extracted[entity_key] = val.strip()
                break

    return extracted
