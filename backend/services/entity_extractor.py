"""
Custom Package Label Entity Extractor Service.

Loads trained weights from backend/models/label_classifier_weights.json
and performs domain-specific Entity Recognition (NER) on OCR-extracted label text.

Extracts structured physical packaging entities:
  - Product Name / Commodity Name
  - Brand Name
  - Product Category / Commodity Type
  - MRP (Max Retail Price)
  - Unit Sale Price (USP)
  - Net Quantity / Weight / Volume
  - Manufacturing / Packaging Date
  - Expiry / Best Before / Use By Date
  - Batch / Lot / Control Number
  - Manufacturer Name & Complete Address
  - Packer Name & Address
  - Importer Name & Address
  - Country of Origin
  - Consumer Care / Grievance Helpline Details
  - FSSAI License Number
  - Ingredients List
  - Vegetarian / Non-Vegetarian Declaration
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

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

# Master Shared Semantic Boundary Registry
SHARED_SEMANTIC_BOUNDARIES = [
    r"\b(?:manufactured\s*(?:&|and|/)?\s*packed\s*by|packed\s*(?:&|and|/)?\s*manufactured\s*by)\b",
    r"\b(?:manufactured\s*by|manufactured\s*at|manufactured\s*in|mfg\.?\s*by|produced\s*by|made\s*by|manufacturer|factory|packed\s*by|pkd\.?\s*by)\b",
    r"\b(?:marketed\s*by|marketed\s*at|distributed\s*by|imported\s*by|importer)\b",
    r"\b(?:customer\s*care|consumer\s*care|consumer\s*care\s*executive|customer\s*service|care\s*line|care\s*helpline|toll\s*free|contact\s*us|feedback|help\s*line)\b",
    r"\b(?:mrp|max\s*retail\s*price|maximum\s*retail\s*price|price)\b",
    r"\b(?:net\s*wt|net\s*weight|net\s*qty|net\s*quantity|net\s*vol|net\s*content|contents)\b",
    r"\b(?:mfg\s*date|mfd|manufacturing\s*date|exp|expiry|best\s*before|use\s*by|use\s*within|date\s*of\s*mfg|date\s*of\s*packing)\b",
    r"\b(?:batch\s*no|batch|lot\s*no|lot)\b",
    r"\b(?:country\s*of\s*origin|origin\s*country|made\s*in|product\s*of)\b",
    r"\b(?:fssai|lic\s*no|licence|license)\b",
    r"\b(?:ingredients|nutrition|nutritional)\b",
    r"\b(?:usp|unit\s*sale\s*price|unit\s*price|price\s*per)\b",
    r"\b(?:www\.|http://|https://)\b",
]

# Common FMCG category keywords
CATEGORY_KEYWORDS = [
    "salt", "butter", "biscuits", "biscuit", "cookies", "cookie", "rusk", "chips", "namkeen",
    "noodles", "noodle", "pasta", "macaroni", "vermicelli", "sauce", "ketchup", "jam", "spread",
    "mayonnaise", "oil", "sunflower oil", "mustard oil", "groundnut oil", "soyabean oil", "olive oil",
    "ghee", "milk", "toned milk", "curd", "dahi", "paneer", "cheese", "cream", "dairy whitener",
    "tea", "green tea", "coffee", "instant coffee", "juice", "fruit juice", "drink", "beverage",
    "atta", "wheat flour", "maida", "besan", "rice", "basmati rice", "poha", "suji", "rava", "dalia",
    "sugar", "honey", "jaggery", "chocolate", "dark chocolate", "candy", "toffee", "wafer",
    "garam masala", "turmeric powder", "turmeric", "red chilli powder", "chilli powder", "coriander powder",
    "cumin powder", "spices", "masala", "powder", "soap", "body wash", "hand wash", "detergent",
    "detergent powder", "washing powder", "shampoo", "conditioner", "hair oil", "toothpaste",
    "tooth powder", "mouthwash", "face wash", "cream", "lotion", "moisturizer", "sunscreen",
    "talc", "talcum powder", "deodorant", "perfume", "cleaner", "dishwash", "floor cleaner"
]

DISCLAIMER_PATTERNS = [
    r"serving\s*suggestion",
    r"store\s*in\s*a\s*(?:cool|dry)",
    r"keep\s*away\s*from\s*direct\s*sunlight",
    r"images?\s*(?:are\s*)?(?:for\s*)?illustration",
    r"for\s*illustration\s*purposes?\s*only",
    r"100%\s*(?:pure|vegetarian|veg|natural|organic|genuine)",
    r"since\s*\d{4}",
    r"quality\s*(?:guaranteed|assured|seal)",
    r"an?\s*iso\s*\d+\s*(?:certified)?",
    r"registered\s*trademark",
    r"keep\s*(?:your\s*)?(?:city|environment)\s*clean",
    r"dispose\s*of\s*properly",
    r"recycle",
    r"www\.",
    r"https?://",
    r"@[\w\.-]+",
    r"fssai",
    r"lic\.?\s*no",
    r"mrp",
    r"net\s*(?:wt|weight|qty|quantity|vol|content)",
    r"mfg|mfd|exp|expiry|best\s*before|use\s*by",
    r"batch|lot",
    r"manufactured\s*by|marketed\s*by|packed\s*by|imported\s*by",
    r"customer\s*care|consumer\s*care|toll\s*free|1800\s*\d+",
    r"country\s*of\s*origin|made\s*in",
    r"ingredients?:",
    r"nutrition(?:al)?\s*(?:facts|information)?",
    r"usp\s*[:\.-]?\s*(?:rs|₹)",
]

PRODUCT_NAME_EXPLICIT_PREFIXES = [
    r"\b(?:product\s*name|productname|product-name|name\s*of\s*(?:the\s*)?(?:product|commodity)|nameofcommodity|commodity\s*name|commodity|item\s*name|generic\s*name|trade\s*name|product\s*description|description)\s*[:\.-]?",
    r"\b(?:product)\s*[:\.-]",
    r"\b(?:commodity)\s*[:\.-]",
]

CORPORATE_SUFFIXES = [
    r"\b(?:pvt\.?\s*ltd\.?|private\s*limited|ltd\.?|limited|llp|inc\.?|incorporated|corp\.?|corporation|co\.?|company|federation|industries)\b",
]


def _extract_labeled_block(
    text: str,
    role_prefixes: list,
    role_boundaries: list,
    max_continuation_lines: int = 4,
    join_separator: str = ", ",
    line_validator: Optional[callable] = None,
) -> Optional[str]:
    """
    Shared infrastructure helper to extract a labeled packaging block across single or multiple lines.
    """
    if not text or not text.strip():
        return None

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for idx, line in enumerate(lines):
        prefix_matched = None
        for pattern in role_prefixes:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                prefix_matched = match
                break
        if not prefix_matched:
            continue

        start_idx = idx
        collected_parts = []

        # 1. Check text after prefix on starting line
        start_line = lines[start_idx]
        after_prefix = start_line[prefix_matched.end():].strip()
        after_prefix = re.sub(r"^[:\.-]+", "", after_prefix).strip()

        same_line_boundary_hit = False
        if after_prefix:
            for b in role_boundaries:
                b_match = re.search(b, after_prefix, re.IGNORECASE)
                if b_match:
                    same_line_boundary_hit = True
                    after_prefix = after_prefix[:b_match.start()].strip()
                    break
            after_prefix = re.sub(r"[\.,;\-:]+$", "", after_prefix).strip()
            if after_prefix:
                if line_validator:
                    valid_val = line_validator(after_prefix)
                    if valid_val:
                        return valid_val
                else:
                    collected_parts.append(after_prefix)

        # 2. Collect subsequent lines if allowed
        if not same_line_boundary_hit and max_continuation_lines > 0:
            for c_idx in range(start_idx + 1, min(len(lines), start_idx + 1 + max_continuation_lines)):
                current_line = lines[c_idx]

                hit_boundary = False
                for boundary in role_boundaries:
                    if re.search(boundary, current_line, re.IGNORECASE):
                        hit_boundary = True
                        break

                if hit_boundary:
                    break

                if line_validator:
                    valid_val = line_validator(current_line)
                    if valid_val:
                        return valid_val
                    else:
                        break

                if current_line:
                    collected_parts.append(current_line)

        if collected_parts and not line_validator:
            result = join_separator.join(collected_parts)
            result = re.sub(r"\s*,\s*,", ",", result)
            result = result.strip(" ,.-")
            if len(result) >= 2:
                return result

    return None


def clean_product_name(name: str) -> str:
    """Format and clean a product name string."""
    name = re.sub(r"\s+", " ", name).strip(" ,.-–—:;")
    name = re.sub(r"\b(?:net\s*wt|net\s*weight|mrp|rs\.?|₹).*$", "", name, flags=re.IGNORECASE).strip(" ,.-")
    return name


def _extract_product_name(text: str) -> Optional[str]:
    """
    Extract product / commodity name from packaging text.
    Uses explicit labels, brand+category synthesis, and prominent front lines.
    Never fabricates a product name if evidence is absent.
    """
    if not text or not text.strip():
        return None

    # 1. Explicit declaration header (e.g. 'Product Name: ...', 'Commodity: ...', 'ProductName:')
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        for prefix in PRODUCT_NAME_EXPLICIT_PREFIXES:
            match = re.search(prefix, line, re.IGNORECASE)
            if match:
                remainder = line[match.end():].strip(" :.-")
                for disc in DISCLAIMER_PATTERNS:
                    d_match = re.search(r"\b" + disc + r"\b", remainder, re.IGNORECASE)
                    if d_match:
                        remainder = remainder[:d_match.start()].strip(" ,.-")
                if len(remainder) >= 2:
                    return clean_product_name(remainder)

    # 2. Extract prominent front-panel candidates
    candidate_lines = []
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in DISCLAIMER_PATTERNS):
            continue
        if re.match(r"^[\d\s\.,;:/\-–—₹\$%#@!\(\)\+=\*]+$", line):
            continue
        if re.match(r"^\d+\s*(?:g|kg|ml|l|ltr|gm|pcs|pieces|nos)\b", line, re.IGNORECASE):
            continue
        if re.match(r"^(?:rs\.?|inr|₹)\s*[\d\.,]+", line, re.IGNORECASE):
            continue

        words = [w for w in re.findall(r"[a-zA-Z0-9'&\-]+", line) if len(w) > 1 or w.lower() in ("a", "g")]
        if 1 <= len(words) <= 7:
            candidate_lines.append((line, words))

    if not candidate_lines:
        return None

    top_candidates = candidate_lines[:4]

    # Pattern 1: Line 0 already contains brand + category (e.g. "TATA SALT")
    line0_text, line0_words = top_candidates[0]
    line0_has_category = any(re.search(r"\b" + re.escape(cat) + r"\b", line0_text, re.IGNORECASE) for cat in CATEGORY_KEYWORDS)
    if line0_has_category and len(line0_words) >= 2:
        return clean_product_name(line0_text)

    # Pattern 2: Two consecutive lines forming Brand + Product (e.g. "AMUL" + "Pasteurised Butter")
    if len(top_candidates) >= 2:
        line1_text, line1_words = top_candidates[1]
        line1_has_category = any(re.search(r"\b" + re.escape(cat) + r"\b", line1_text, re.IGNORECASE) for cat in CATEGORY_KEYWORDS)
        if len(line0_words) <= 2 and (line1_has_category or len(line1_words) <= 3):
            combined = f"{line0_text} {line1_text}"
            return clean_product_name(combined)

    # Pattern 3: Any top candidate line containing category
    for line_text, words in top_candidates:
        if any(re.search(r"\b" + re.escape(cat) + r"\b", line_text, re.IGNORECASE) for cat in CATEGORY_KEYWORDS):
            return clean_product_name(line_text)

    # Pattern 4: First clean prominent candidate (2-5 words)
    for line_text, words in top_candidates:
        if 2 <= len(words) <= 5:
            return clean_product_name(line_text)

    # If only 1 word, only accept if >= 4 chars and not a modifier word
    if len(top_candidates[0][1]) == 1:
        w = top_candidates[0][1][0]
        if len(w) >= 4 and w.lower() not in ("free", "pack", "fresh", "crisp", "tasty", "special", "super", "extra", "best", "good"):
            return clean_product_name(top_candidates[0][0])

    return None


def _extract_brand(text: str, product_name: Optional[str] = None) -> Optional[str]:
    """Extract brand name from explicit label or product name."""
    if not text:
        return None

    # 1. Explicit Brand header
    brand_match = re.search(r"\b(?:brand\s*name|brand)\s*[:\.-]?\s*([a-zA-Z0-9&'\-\s]{2,30})\b", text, re.IGNORECASE)
    if brand_match:
        b_val = brand_match.group(1).strip(" ,.-")
        if b_val and not any(re.search(p, b_val, re.IGNORECASE) for p in DISCLAIMER_PATTERNS):
            # Clean corporate suffixes
            for suffix in CORPORATE_SUFFIXES:
                b_val = re.sub(suffix, "", b_val, flags=re.IGNORECASE).strip(" ,.-")
            if len(b_val) >= 2:
                return b_val

    # 2. Extract first token of product name if available
    if product_name:
        words = product_name.split()
        if words and len(words[0]) >= 2:
            candidate = words[0].strip(" ,.-")
            for suffix in CORPORATE_SUFFIXES:
                candidate = re.sub(suffix, "", candidate, flags=re.IGNORECASE).strip(" ,.-")
            if len(candidate) >= 2:
                return candidate

    return None


def _extract_category(text: str, product_name: Optional[str] = None) -> Optional[str]:
    """Extract product category / commodity type."""
    search_space = f"{product_name or ''} {text or ''}".lower()
    for cat in CATEGORY_KEYWORDS:
        if re.search(r"\b" + re.escape(cat) + r"\b", search_space):
            return cat.title()
    return None


def _extract_net_quantity(text: str) -> Optional[str]:
    """
    Extract net quantity with strict priority:
    1. Explicit Multi-Pack Printed Total (e.g. '2 N x 100 g = 200 g' -> '200 g').
    2. Explicit Net Quantity declarations (Net Content, Net Quantity, Net Wt, Net Weight, etc.).
    3. Standalone quantity declarations strictly excluding USP, MRP, and Batch lines.
    """
    if not text or not text.strip():
        return None

    # Field-specific contextual O/0 normalization for digits (e.g. 5OO g -> 500 g)
    clean_text_digits = re.sub(r"(?<=\d)[Oo](?=\s*(?:g|kg|ml|l|ltr|gm|pcs|pieces|nos))", "0", text)
    clean_text_digits = re.sub(r"(?<=\d)[Oo](?=[Oo]\s*(?:g|kg|ml|l|ltr|gm|pcs|pieces|nos))", "0", clean_text_digits)

    multi_pack_total_pattern = r"\b(?:\d+\s*[Nn]?\s*[xX*]\s*[\d\.]+\s*(?:g|kg|ml|l|ltr|gm|pcs|pieces|nos)\s*=\s*)([\d\.]+\s*(?:g|kg|ml|l|ltr|gm|pcs|pieces|nos)\b)"
    match = re.search(multi_pack_total_pattern, clean_text_digits, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if not re.search(r"(?:usp|unit\s*sale\s*price|unit\s*price)\s*[:\.-]?\s*" + re.escape(val), clean_text_digits, re.IGNORECASE):
            return val

    explicit_patterns = [
        r"(?:net\s*(?:content|contents|quantity|qty|weight|wt|volume|vol)(?:\s*\([^)]*\))?)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|litres|litre|gm|pcs|pieces|nos|n)\b(?:\s*\([\d\.]+\s*(?:g|kg|ml|l|ltr|gm)\))?)",
        r"(?:net\s*(?:content|contents|quantity|qty|weight|wt|volume|vol)(?:\s*\([^)]*\))?)\s*[:\.-]?\s*([\d\.]+\s*(?:g|kg|ml|l|ltr|litres|litre|gm|pcs|pieces|nos|n)\b)",
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, clean_text_digits, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if not re.search(r"(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price)\s*[:\.-]?\s*" + re.escape(val), clean_text_digits, re.IGNORECASE):
                return val

    lines = clean_text_digits.split("\n")
    clean_lines = []
    for line in lines:
        if not re.search(r"\b(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price|per\s*(?:g|ml|kg|l|ltr)|/\s*(?:g|ml|kg|l|ltr)|batch|lot|mrp|rs\.?|₹)\b", line, re.IGNORECASE):
            clean_lines.append(line)
        else:
            cleaned_line = re.sub(r"(?:usp|unit\s*sale\s*price|unit\s*selling\s*price|unit\s*price)\s*[:\.-]?\s*[^,\n]+", "", line, flags=re.IGNORECASE)
            cleaned_line = re.sub(r"\b[\d\.]+\s*(?:per|/)\s*(?:g|ml|kg|l|ltr)\b", "", cleaned_line, flags=re.IGNORECASE)
            cleaned_line = re.sub(r"\b(?:batch|lot|mrp)\s*[:\.-]?\s*[\w\.,]+", "", cleaned_line, flags=re.IGNORECASE)
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


MFG_PREFIX_PATTERN = r"(?:mfg|mfd|manufactured(?![\s\w]*by)|packed|pkd|pkg|dop|date\s*of\s*mfg|date\s*of\s*packing|manufacturing\s*date)\s*(?:date|on)?"
MFG_DATE_BOUNDARIES = SHARED_SEMANTIC_BOUNDARIES


def _match_date_in_str(s: str) -> Optional[str]:
    """Helper to check if a string contains a valid textual or numeric date."""
    if not s or not s.strip():
        return None

    textual_match = re.search(r"\b([a-zA-Z]{3,9})[\s\.-]+(\d{2,4})\b", s, re.IGNORECASE)
    if textual_match:
        m_str, y_str = textual_match.group(1).strip(), textual_match.group(2).strip()
        if m_str.lower() in MONTH_MAP:
            return f"{m_str.upper()} {y_str}"

    numeric_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4})\b", s, re.IGNORECASE)
    if numeric_match:
        return numeric_match.group(1).strip()

    return None


def _extract_mfg_date(text: str) -> Optional[str]:
    """Extract manufacturing/packaging date from OCR text."""
    return _extract_labeled_block(
        text,
        role_prefixes=[MFG_PREFIX_PATTERN],
        role_boundaries=MFG_DATE_BOUNDARIES,
        max_continuation_lines=1,
        line_validator=_match_date_in_str
    )


def _extract_expiry_date(text: str, mfg_date: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Extract expiry date directly or calculate from 'Best Before X Months' statement."""
    if not text or not text.strip():
        return None, False

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

    duration_pattern = r"(?:best\s*before|use\s*by|use\s*within|expiry\s*within)\s*[:\.-]?\s*(?:within|of)?\s*(\d{1,2})\s*months?\b"
    match = re.search(duration_pattern, text, re.IGNORECASE)
    if match and mfg_date:
        months_to_add = int(match.group(1))
        mfg_match = re.match(r"^([a-zA-Z]{3,9})\s+(\d{4})$", mfg_date.strip())
        if mfg_match and mfg_match.group(1).lower() in MONTH_MAP:
            start_m = MONTH_MAP[mfg_match.group(1).lower()]
            start_y = int(mfg_match.group(2))
            total_m = (start_m - 1) + months_to_add
            new_m = (total_m % 12) + 1
            new_y = start_y + (total_m // 12)
            month_abbr = INV_MONTH_MAP.get(new_m, f"{new_m:02d}")
            return f"{month_abbr} {new_y}", True

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
]

MANUFACTURER_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"manufactur|produced|made\s*by", b, re.IGNORECASE)
]


def _extract_manufacturer_name_address(text: str) -> Optional[str]:
    """Extract Manufacturer Name & Complete Address."""
    return _extract_labeled_block(
        text,
        role_prefixes=MANUFACTURER_ROLE_PREFIXES,
        role_boundaries=MANUFACTURER_BOUNDARIES,
        max_continuation_lines=4
    )


PACKER_ROLE_PREFIXES = [
    r"(?:packed\s*by|packed\s*at|packed\s*in|pkd\.?\s*by|packer)\s*[:\.-]?",
]

PACKER_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"packed|pkd", b, re.IGNORECASE)
]


def _extract_packer_name_address(text: str) -> Optional[str]:
    """Extract Packer Name & Address when separate from manufacturer."""
    return _extract_labeled_block(
        text,
        role_prefixes=PACKER_ROLE_PREFIXES,
        role_boundaries=PACKER_BOUNDARIES,
        max_continuation_lines=4
    )


IMPORTER_ROLE_PREFIXES = [
    r"(?:imported\s*by|imported\s*at|imported\s*in|importer)\s*[:\.-]?",
]

IMPORTER_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"imported|importer", b, re.IGNORECASE)
]


def _extract_importer_name_address(text: str) -> Optional[str]:
    """Extract Importer Name & Address for imported commodities."""
    return _extract_labeled_block(
        text,
        role_prefixes=IMPORTER_ROLE_PREFIXES,
        role_boundaries=IMPORTER_BOUNDARIES,
        max_continuation_lines=4
    )


CONSUMER_CARE_ROLE_PREFIXES = [
    r"(?:customer\s*care|consumer\s*care|consumer\s*care\s*executive|customer\s*service|care\s*line|care\s*helpline|toll\s*free|contact\s*us|feedback|help\s*line)\s*[:\.-]?",
]

CONSUMER_CARE_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"customer\s*care|consumer\s*care|care\s*line|helpline|toll\s*free|contact\s*us|feedback", b, re.IGNORECASE)
]


def _extract_consumer_care(text: str) -> Optional[str]:
    """Extract Consumer Care details (Phone, Email, Postal Address)."""
    res = _extract_labeled_block(
        text,
        role_prefixes=CONSUMER_CARE_ROLE_PREFIXES,
        role_boundaries=CONSUMER_CARE_BOUNDARIES,
        max_continuation_lines=4
    )
    if res:
        return res

    match = re.search(r"\b(1800[-\s]?\d{3}[-\s]?\d{4})\b", text)
    if match:
        return match.group(1)
    match = re.search(r"\b([a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9.-]+\.)+[a-zA-Z]{2,})\b", text)
    if match:
        return match.group(1)
    return None


COUNTRY_ORIGIN_PREFIXES = [
    r"(?:country\s*of\s*origin|country\s*of\s*origin\s*code|origin\s*country)\s*[:\.-]?",
    r"(?:made\s*in|product\s*of|produced\s*in|manufactured\s*in|imported\s*from)\s*[:\.-]?",
]

ORIGIN_BOUNDARIES = SHARED_SEMANTIC_BOUNDARIES


def _extract_country_of_origin(text: str) -> Optional[str]:
    """Extract Country of Origin."""
    return _extract_labeled_block(
        text,
        role_prefixes=COUNTRY_ORIGIN_PREFIXES,
        role_boundaries=ORIGIN_BOUNDARIES,
        max_continuation_lines=1
    )


FSSAI_PREFIXES = [
    r"(?:fssai|lic)\s*(?:no\.?|num|licence|license)?\s*[:\.-]?",
]

FSSAI_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"fssai|lic", b, re.IGNORECASE)
]


def _match_fssai_in_str(s: str) -> Optional[str]:
    """Helper to check if a string contains a valid 14-digit FSSAI license number."""
    if not s or not s.strip():
        return None
    match = re.search(r"\b(\d{14})\b", s)
    if match:
        return match.group(1).strip()
    return None


def _extract_fssai_lic(text: str) -> Optional[str]:
    """Extract 14-digit FSSAI license number."""
    res = _extract_labeled_block(
        text,
        role_prefixes=FSSAI_PREFIXES,
        role_boundaries=FSSAI_BOUNDARIES,
        max_continuation_lines=1,
        line_validator=_match_fssai_in_str,
    )
    if res:
        return res

    match = re.search(r"\b(\d{14})\b", text)
    if match:
        return match.group(1).strip()
    return None


MRP_PREFIXES = [
    r"(?:m\.?r\.?p\.?|max\s*retail\s*price|maximum\s*retail\s*price)\s*[:\.-]?",
]

MRP_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"\bmrp\b|price", b, re.IGNORECASE)
]


def _match_mrp_in_str(s: str) -> Optional[str]:
    """Helper to check if a string contains a valid price digits value with field-specific normalization."""
    if not s or not s.strip():
        return None
    clean_s = re.sub(r"^(?:m\.?r\.?p\.?|max\s*retail\s*price|maximum\s*retail\s*price|price)\s*[:\.-]?", "", s.strip(), flags=re.IGNORECASE).strip()
    clean_s = re.sub(r"^(?:rs\.?|₹|inr)\s*", "", clean_s, flags=re.IGNORECASE).strip()
    clean_s = re.sub(r"/[-\s]*$", "", clean_s).strip()
    clean_s = re.sub(r"\s*\(.*?\)", "", clean_s).strip()

    # Contextual O/0 and I/1 normalization within numbers
    clean_s = re.sub(r"(?<=\d)[Oo](?=\d|\.|$)", "0", clean_s)
    clean_s = re.sub(r"(?<=\.)[Oo](?=\d)", "0", clean_s)
    clean_s = re.sub(r"^[Oo](?=\d)", "0", clean_s)
    clean_s = re.sub(r"(?<=\d)[Il|](?=\d|\.|$)", "1", clean_s)
    clean_s = re.sub(r"(?<=\.)[Il|](?=\d)", "1", clean_s)
    clean_s = re.sub(r"^[Il|](?=\d)", "1", clean_s)

    match = re.search(r"\b([\d\.,]+)\b", clean_s)
    if match:
        val = match.group(1).strip(" ,.-")
        val = val.replace(",", "")
        if re.match(r"^\d+(?:\.\d{1,2})?$", val):
            return val
    return None


def _extract_mrp(text: str) -> Optional[str]:
    """Extract Maximum Retail Price (MRP)."""
    return _extract_labeled_block(
        text,
        role_prefixes=MRP_PREFIXES,
        role_boundaries=MRP_BOUNDARIES,
        max_continuation_lines=1,
        line_validator=_match_mrp_in_str,
    )


BATCH_PREFIXES = [
    r"\b(?:batch\s*(?:number|num|no\.?)?|lot\s*(?:number|num|no\.?)?)\b\s*[:\.-]?",
]

BATCH_BOUNDARIES = [
    b for b in SHARED_SEMANTIC_BOUNDARIES if not re.search(r"batch|lot", b, re.IGNORECASE)
]


def _match_batch_in_str(s: str) -> Optional[str]:
    """Helper to validate and extract a clean batch/lot number string."""
    if not s or not s.strip():
        return None
    if re.search(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4})\b", s):
        return None
    if re.search(r"\b(?:rs\.?|₹)\s*\d+|\b\d+\s*(?:g|kg|ml|l|ltr|gm)\b", s, re.IGNORECASE):
        return None
    if re.search(r"\b1800[-\s]?\d{3}[-\s]?\d{4}\b", s):
        return None

    match = re.search(r"\b([a-zA-Z0-9\/-]{3,20})\b", s)
    if match:
        val = match.group(1).strip(" ,.-")
        if len(val) >= 3 and val.lower() not in ("date", "mrp", "net", "pack", "code", "rs", "inr"):
            return val
    return None


def _extract_batch(text: str) -> Optional[str]:
    """Extract Batch / Lot Number."""
    return _extract_labeled_block(
        text,
        role_prefixes=BATCH_PREFIXES,
        role_boundaries=BATCH_BOUNDARIES,
        max_continuation_lines=1,
        line_validator=_match_batch_in_str,
    )


INGREDIENTS_PREFIXES = [
    r"(?:ingredients|contains)\s*[:\.-]?",
]

INGREDIENTS_BOUNDARIES = [
    r"^\s*(?:mrp|max\s*retail\s*price|net\s*wt|net\s*qty|net\s*quantity|net\s*vol|mfg\s*date|mfd|exp|expiry|best\s*before|use\s*by|batch|lot|fssai|lic\s*no|manufactured\s*by|packed\s*by|marketed\s*by|customer\s*care|consumer\s*care|country\s*of\s*origin|made\s*in)\s*[:\.-]?",
]


def _extract_ingredients(text: str) -> Optional[str]:
    """Extract Ingredients declaration."""
    return _extract_labeled_block(
        text,
        role_prefixes=INGREDIENTS_PREFIXES,
        role_boundaries=INGREDIENTS_BOUNDARIES,
        max_continuation_lines=4,
    )


def _extract_veg_non_veg(text: str) -> Optional[str]:
    """Extract Vegetarian / Non-Vegetarian declaration symbol text (checking non-veg first)."""
    if not text:
        return None
    if re.search(r"\b(?:non[-\s]*vegetarian|non[-\s]*veg|contains\s*egg|contains\s*meat|contains\s*fish|brown\s*dot|red\s*dot)\b", text, re.IGNORECASE):
        return "NON_VEGETARIAN"
    if re.search(r"\b(?:100%\s*vegetarian|100%\s*veg|vegetarian|pure\s*veg|veg\s*logo|green\s*dot)\b", text, re.IGNORECASE):
        return "VEGETARIAN"
    return None


def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Apply trained entity recognition patterns to OCR extracted text.
    Extracts all physical packaging declarations into a structured dictionary.

    Args:
        text: Raw or normalized OCR extracted text string.

    Returns:
        Structured entity dictionary containing detected packaging declarations.
    """
    model_data = _load_model_weights()
    patterns = model_data.get("patterns", {})

    extracted = {
        "product_name": None,
        "brand": None,
        "category": None,
        "net_quantity": None,
        "mrp": None,
        "unit_sale_price": None,
        "mfg_date": None,
        "expiry_date": None,
        "batch_no": None,
        "manufacturer_name_address": None,
        "packer_name_address": None,
        "importer_name_address": None,
        "country_of_origin": None,
        "consumer_care": None,
        "fssai_lic": None,
        "ingredients": None,
        "veg_non_veg": None,
    }

    if not text or not text.strip():
        return extracted

    # 1. Product Name
    extracted["product_name"] = _extract_product_name(text)

    # 2. Brand Name
    extracted["brand"] = _extract_brand(text, extracted["product_name"])

    # 3. Product Category
    extracted["category"] = _extract_category(text, extracted["product_name"])

    # 4. Net Quantity
    extracted["net_quantity"] = _extract_net_quantity(text)

    # 5. Manufacturing Date
    extracted["mfg_date"] = _extract_mfg_date(text)

    # 6. Expiry Date (Direct + Best Before calculation)
    exp_val, _ = _extract_expiry_date(text, extracted["mfg_date"])
    extracted["expiry_date"] = exp_val

    # 7. Manufacturer Name & Address
    extracted["manufacturer_name_address"] = _extract_manufacturer_name_address(text)

    # 8. Packer Name & Address
    extracted["packer_name_address"] = _extract_packer_name_address(text)

    # 9. Importer Name & Address
    extracted["importer_name_address"] = _extract_importer_name_address(text)

    # 10. Consumer Care Details
    extracted["consumer_care"] = _extract_consumer_care(text)

    # 11. Country of Origin
    extracted["country_of_origin"] = _extract_country_of_origin(text)

    # 12. FSSAI License Number
    extracted["fssai_lic"] = _extract_fssai_lic(text)

    # 13. MRP
    extracted["mrp"] = _extract_mrp(text)

    # 14. Batch Number
    extracted["batch_no"] = _extract_batch(text)

    # 15. Ingredients
    extracted["ingredients"] = _extract_ingredients(text)

    # 16. Vegetarian / Non-Vegetarian
    extracted["veg_non_veg"] = _extract_veg_non_veg(text)

    # 17. Unit Sale Price (USP)
    default_patterns = {
        "unit_sale_price": [r"(?:unit\s*sale\s*price|unit\s*price)\s*[:\.-]?\s*([^\n,]+)"],
    }
    active_patterns = patterns if patterns else default_patterns

    for entity_key, regex_list in active_patterns.items():
        if extracted.get(entity_key) is not None:
            continue
        for pattern in regex_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                extracted[entity_key] = val.strip()
                break

    return extracted


def extract_entities_with_evidence(raw_text: str, normalized_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured entities with complete evidence tracing:
    - value
    - source ("IMAGE" / "BARCODE_CATALOG" / "INFERENCE" / "not_detected")
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
