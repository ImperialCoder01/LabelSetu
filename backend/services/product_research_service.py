"""
AI-Assisted Product Information Recovery & Supplementary Research Service.

Safely queries authoritative public product databases (Local FMCG Catalog, Open Food Facts,
Brand Registries) when package declarations are missing or incomplete on user-uploaded images.

CRITICAL LEGAL SAFEGUARDS:
1. All recovered fields are flagged with `package_verified = False` and `source_type = 'external_reference'`.
2. Package-specific statutory declarations (MRP, Batch No, Mfg Date, Expiry Date) are strictly
   classified as reference-only and `verification_status = 'REQUIRES_PACKAGE_VERIFICATION'`.
3. NEVER alters the deterministic rule engine's legal compliance score or pass/fail verdict.
4. If external data conflicts with package data, records an identity conflict warning only (no score deduction).
5. Generates actionable recommendations for additional packaging photos (e.g. Back Panel, Side Panel).
"""

import json
import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx

from services.barcode_service import lookup_barcode, _get_local_catalog

logger = logging.getLogger(__name__)

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
PACKAGE_SPECIFIC_FIELDS = {
    "mrp",
    "batch_number",
    "batch_no",
    "manufacturing_date",
    "mfg_date",
    "expiry_date",
    "best_before",
    "lot_no",
    "unit_sale_price",
}

PANEL_ACTION_MAP = {
    "mrp": {
        "panel": "Back Panel or Price Stamp Area",
        "rec": "Upload a clear Back Panel or Price Stamp area showing the printed MRP and Unit Sale Price.",
    },
    "manufacturing_date": {
        "panel": "Date-Code / Flap Area",
        "rec": "Upload a clear photo of the printed manufacturing date, packaging date, or batch code.",
    },
    "batch_number": {
        "panel": "Date-Code / Flap Area",
        "rec": "Upload the packaging flap or bottom panel showing the embossed/printed batch code.",
    },
    "manufacturer_name_address": {
        "panel": "Side or Back Panel",
        "rec": "Upload the side/back panel containing the full Manufacturer / Packer Name and Physical Address.",
    },
    "consumer_care_contact": {
        "panel": "Customer Care Box / Flap",
        "rec": "Upload the Consumer Care / Grievance Helpline panel containing customer care phone, email, and postal address.",
    },
    "country_of_origin": {
        "panel": "Principal Display or Side Panel",
        "rec": "Upload the panel containing the Country of Origin declaration (e.g., Made in India).",
    },
    "net_quantity": {
        "panel": "Principal Display Panel (PDP)",
        "rec": "Capture the front Principal Display Panel showing the Net Quantity declaration.",
    },
    "unit_sale_price": {
        "panel": "Price Declaration Box",
        "rec": "Upload the panel showing the Unit Sale Price (USP) printed adjacent to the MRP.",
    },
}


def _generate_panel_recommendations(missing_fields: List[str]) -> List[str]:
    """Generate recommendations for specific physical package panels to photograph."""
    recs = []
    for fid in missing_fields:
        if fid in PANEL_ACTION_MAP:
            recs.append(PANEL_ACTION_MAP[fid]["rec"])
    return recs


def _normalize_tokens(text: str) -> set[str]:
    """Normalize text into comparable word tokens, splitting unit concatenations like 1kg -> 1 kg."""
    s = text.lower()
    s = re.sub(r"(\d+)\s*([a-z]+)", r"\1 \2", s)
    tokens = re.findall(r"[a-z0-9]+", s)
    return set(tokens)


def _calculate_match_confidence(
    query_text: str,
    matched_name: str,
    matched_brand: str,
    has_barcode_match: bool = False,
) -> tuple[float, str]:
    """Calculate match confidence score and status between query context and retrieved record."""
    if has_barcode_match:
        return 0.96, "high_confidence"

    q_tokens = _normalize_tokens(query_text)
    target_tokens = _normalize_tokens(f"{matched_brand} {matched_name}")

    if not q_tokens or not target_tokens:
        return 0.0, "no_match"

    overlap = q_tokens.intersection(target_tokens)
    if not overlap:
        return 0.0, "no_match"

    score = len(overlap) / max(len(q_tokens), 1)
    score = min(round(score, 2), 0.92)

    if score >= 0.50:
        return score, "high_confidence"
    elif score >= 0.30:
        return score, "medium_confidence"
    elif score >= 0.15:
        return score, "low_confidence"
    return 0.0, "no_match"


def _search_open_food_facts(search_term: str) -> Optional[Dict[str, Any]]:
    """Search Open Food Facts public API for product metadata."""
    if not search_term or len(search_term.strip()) < 3:
        return None

    params = {
        "search_terms": search_term,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": "3",
    }
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(OFF_SEARCH_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("products", [])
                if products:
                    p = products[0]
                    return {
                        "product_name": p.get("product_name") or p.get("generic_name") or "",
                        "brand": p.get("brands") or "",
                        "manufacturer": p.get("manufacturing_places") or p.get("creator") or "",
                        "country_of_origin": p.get("origins") or p.get("countries") or "India",
                        "net_quantity": p.get("quantity") or "",
                        "consumer_care": p.get("customer_service") or p.get("contact") or "",
                        "source_name": "Open Food Facts Public Product Catalog",
                        "source_url": f"https://world.openfoodfacts.org/product/{p.get('code', '')}" if p.get("code") else "https://world.openfoodfacts.org",
                        "source_type": "public_database",
                        "matched_by": "open_food_facts_search",
                    }
    except Exception as exc:
        logger.debug("Open Food Facts search error: %s", exc)
    return None


def _search_local_catalog_by_name(query_term: str) -> Optional[Dict[str, Any]]:
    """Search in-memory FMCG catalog for close product name/brand match."""
    catalog = _get_local_catalog()
    q_words = _normalize_tokens(query_term)

    best_match = None
    best_score = 0

    for barcode, item in catalog.items():
        name = item.get("product_name", "")
        brand = item.get("brand", "")
        item_words = _normalize_tokens(f"{brand} {name}")
        overlap = len(q_words.intersection(item_words))
        if overlap > best_score and overlap >= 2:
            best_score = overlap
            best_match = {
                "product_name": item.get("product_name", ""),
                "brand": item.get("brand", ""),
                "manufacturer": item.get("manufacturer", ""),
                "country_of_origin": item.get("country_of_origin", "India"),
                "net_quantity": item.get("net_quantity", ""),
                "consumer_care": item.get("consumer_care", ""),
                "mrp_reference": item.get("standard_mrp", ""),
                "source_name": "National FMCG Packaging Standard Catalog",
                "source_url": f"https://legalmetrology.gov.in/catalog/{barcode}",
                "source_type": "official_catalog",
                "matched_by": "local_fmcg_catalog",
            }

    return best_match


STOPWORDS = {"company", "pvt", "ltd", "limited", "inc", "corp", "corporation", "india", "global", "llc", "products", "foods", "industries"}


def detect_identity_conflicts(
    package_entities: Dict[str, Any],
    matched_record: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Detect semantic conflicts between package evidence and external catalog data.
    CRITICAL: Generates warning alerts only; NEVER modifies the compliance score.
    """
    conflicts = []
    pkg_mfg = (package_entities.get("manufacturer") or package_entities.get("brand") or "").strip()
    ext_mfg = (matched_record.get("manufacturer") or matched_record.get("brand") or "").strip()

    if pkg_mfg and ext_mfg:
        pkg_tokens = {t for t in _normalize_tokens(pkg_mfg) if t not in STOPWORDS}
        ext_tokens = {t for t in _normalize_tokens(ext_mfg) if t not in STOPWORDS}
        if pkg_tokens and ext_tokens and not pkg_tokens.intersection(ext_tokens):
            conflicts.append({
                "field": "manufacturer",
                "package_value": pkg_mfg,
                "external_value": ext_mfg,
                "warning": "Product identity conflict detected — external catalog manufacturer differs from package evidence.",
                "recommendation": "Manual package verification required. Statutory compliance score remains evaluated on physical package evidence only.",
            })

    return conflicts


def research_product_information(
    ocr_text: str,
    extracted_entities: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[Dict[str, Any]]] = None,
    barcode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform safe external product recovery for missing label declarations.

    CRITICAL RULES:
    - Never mutates rule engine results or compliance scores.
    - All recovered fields are flagged package_verified = False.
    - Package-specific declarations (MRP, dates) marked as reference only.
    """
    extracted_entities = extracted_entities or {}
    missing_fields = missing_fields or []
    missing_field_ids = [f.get("field_id") for f in missing_fields if f.get("status") == "fail"]

    disclaimer_text = (
        "External information is reference data only and does not verify declarations printed on the scanned package. "
        "Statutory compliance is calculated exclusively from uploaded package image evidence."
    )

    # If no declarations are missing, skip unnecessary external search
    if not missing_field_ids and not barcode:
        return {
            "status": "skipped",
            "message": "All mandatory Legal Metrology declarations verified on package. External research not required.",
            "product_match": {"status": "package_complete", "confidence": 1.0, "confidence_score": 1.0, "matched_by": "package_evidence"},
            "sources": [],
            "external_reference_fields": [],
            "package_verification_required": [],
            "identity_conflicts": [],
            "recommended_photos": [],
            "disclaimer": disclaimer_text,
        }

    # 1. Attempt Barcode-Based Retrieval First (Highest Accuracy)
    matched_record = None
    has_barcode = False
    matched_method = "name_and_brand"

    if barcode and barcode.strip():
        try:
            bc_res = lookup_barcode(barcode.strip())
            if bc_res and bc_res.get("found"):
                matched_record = {
                    "product_name": bc_res.get("product_name", ""),
                    "brand": bc_res.get("brand", ""),
                    "manufacturer": bc_res.get("manufacturing_places", ""),
                    "country_of_origin": bc_res.get("origins") or bc_res.get("countries") or "India",
                    "net_quantity": bc_res.get("quantity", ""),
                    "consumer_care": "",
                    "source_name": "Open Food Facts GTIN Database",
                    "source_url": f"https://world.openfoodfacts.org/product/{barcode}",
                    "source_type": "official_database",
                    "matched_by": "gtin",
                }
                has_barcode = True
                matched_method = "gtin"
        except Exception as exc:
            logger.debug("Barcode lookup in research service skipped: %s", exc)

    # 2. Name / Brand-Based Retrieval Fallback
    query_term = ""
    p_name = extracted_entities.get("product_name") or ""
    p_brand = extracted_entities.get("manufacturer") or extracted_entities.get("brand") or ""

    if not matched_record:
        if p_name or p_brand:
            query_term = f"{p_brand} {p_name}".strip()
        else:
            first_lines = [l.strip() for l in ocr_text.splitlines() if l.strip()][:2]
            query_term = " ".join(first_lines)

        if query_term:
            try:
                matched_record = _search_local_catalog_by_name(query_term)
                if matched_record:
                    matched_method = "local_catalog"
            except Exception as exc:
                logger.debug("Local catalog search error: %s", exc)

            if not matched_record:
                try:
                    matched_record = _search_open_food_facts(query_term)
                    if matched_record:
                        matched_method = "open_food_facts"
                except Exception as exc:
                    logger.debug("Open Food Facts search error: %s", exc)

    # 3. Assess Match Confidence
    if not matched_record:
        # Build package verification required entries
        pkg_req = []
        for fid in missing_field_ids:
            info = PANEL_ACTION_MAP.get(fid, {"panel": "Relevant Panel", "rec": f"Upload image showing {fid}."})
            pkg_req.append({
                "field_id": fid,
                "field_name": fid.replace("_", " ").title(),
                "reason": "Not visible in uploaded images",
                "recommended_panel": info["panel"],
                "recommendation": info["rec"],
            })

        return {
            "status": "no_match",
            "message": "No sufficiently reliable external product match found for missing declarations.",
            "product_match": {
                "name": None,
                "brand": None,
                "status": "no_match",
                "confidence": "no_match",
                "confidence_score": 0.0,
                "matched_by": None,
            },
            "sources": [],
            "external_reference_fields": [],
            "package_verification_required": pkg_req,
            "identity_conflicts": [],
            "recommended_photos": [r["recommendation"] for r in pkg_req],
            "disclaimer": disclaimer_text,
        }

    conf_score, conf_status = _calculate_match_confidence(
        query_text=query_term or barcode or "",
        matched_name=matched_record.get("product_name", ""),
        matched_brand=matched_record.get("brand", ""),
        has_barcode_match=has_barcode,
    )

    if conf_status == "no_match":
        pkg_req = []
        for fid in missing_field_ids:
            info = PANEL_ACTION_MAP.get(fid, {"panel": "Relevant Panel", "rec": f"Upload image showing {fid}."})
            pkg_req.append({
                "field_id": fid,
                "field_name": fid.replace("_", " ").title(),
                "reason": "Not visible in uploaded images",
                "recommended_panel": info["panel"],
                "recommendation": info["rec"],
            })

        return {
            "status": "low_confidence_rejected",
            "message": "External search results did not meet confidence threshold for this packaging.",
            "product_match": {
                "name": matched_record.get("product_name"),
                "brand": matched_record.get("brand"),
                "status": "low_confidence",
                "confidence": "low_confidence",
                "confidence_score": conf_score,
                "matched_by": matched_method,
            },
            "sources": [],
            "external_reference_fields": [],
            "package_verification_required": pkg_req,
            "identity_conflicts": [],
            "recommended_photos": [r["recommendation"] for r in pkg_req],
            "disclaimer": disclaimer_text,
        }

    # 4. Map Missing Declarations to External Reference Values
    field_mapping = {
        "manufacturer_name_address": ("manufacturer", "Manufacturer Name & Address"),
        "country_of_origin": ("country_of_origin", "Country of Origin"),
        "consumer_care_contact": ("consumer_care", "Consumer Care Contact"),
        "net_quantity": ("net_quantity", "Net Quantity"),
        "mrp": ("mrp_reference", "Maximum Retail Price (Reference MRP)"),
        "unit_sale_price": ("unit_sale_price_reference", "Unit Sale Price (Reference USP)"),
    }

    recovered_fields = []
    sources = [{
        "name": matched_record.get("source_name", "Public Product Catalog"),
        "url": matched_record.get("source_url", "https://world.openfoodfacts.org"),
        "source_type": matched_record.get("source_type", "public_database"),
    }]

    for m_field in missing_fields:
        fid = m_field.get("field_id")
        fname = m_field.get("field_name")
        if fid in field_mapping:
            record_key, friendly_name = field_mapping[fid]
            val = matched_record.get(record_key)
            if val and str(val).strip():
                is_pkg_specific = fid in PACKAGE_SPECIFIC_FIELDS
                recovered_fields.append({
                    "field_id": fid,
                    "field_name": friendly_name or fname,
                    "value": str(val).strip(),
                    "source_type": "external_reference",
                    "source_name": matched_record.get("source_name", "Public Product Catalog"),
                    "source_url": matched_record.get("source_url", ""),
                    "package_verified": False,
                    "verification_status": "REQUIRES_PACKAGE_VERIFICATION",
                    "is_package_specific": is_pkg_specific,
                    "explanation": (
                        "Reference value found online. This declaration varies by packaging batch and MUST be physically verified from the printed package label."
                        if is_pkg_specific else
                        "Manufacturer standard catalog value found online. Requires package photo confirmation under Legal Metrology Rules."
                    ),
                })

    # Build package verification required items
    package_verification_req = []
    for fid in missing_field_ids:
        info = PANEL_ACTION_MAP.get(fid, {"panel": "Relevant Panel", "rec": f"Upload image showing {fid}."})
        package_verification_req.append({
            "field_id": fid,
            "field_name": fid.replace("_", " ").title(),
            "reason": "Not visible in uploaded images",
            "recommended_panel": info["panel"],
            "recommendation": info["rec"],
        })

    # Detect conflicts (warning flags only, no score deduction)
    conflicts = detect_identity_conflicts(extracted_entities, matched_record)

    return {
        "status": "success",
        "product_match": {
            "name": matched_record.get("product_name"),
            "brand": matched_record.get("brand"),
            "confidence": conf_status,
            "confidence_score": conf_score,
            "matched_by": matched_method,
        },
        "sources": sources,
        "external_reference_fields": recovered_fields,
        "package_verification_required": package_verification_req,
        "identity_conflicts": conflicts,
        "recommended_photos": [r["recommendation"] for r in package_verification_req],
        "disclaimer": disclaimer_text,
    }
