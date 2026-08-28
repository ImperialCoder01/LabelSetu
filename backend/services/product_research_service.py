"""
AI-Assisted Product Information Recovery & Supplementary Research Service.

Safely queries authoritative public product databases (Local FMCG Catalog, Open Food Facts,
Brand Registries) when package declarations are missing or incomplete on user-uploaded images.

CRITICAL LEGAL SAFEGUARDS:
1. All recovered fields are flagged with `package_verified = False` and `source_type = 'internet'`.
2. Package-specific statutory declarations (MRP, Batch No, Mfg Date, Expiry Date) are strictly
   classified as reference-only and `verification_status = 'REQUIRES_PACKAGE_VERIFICATION'`.
3. NEVER alters the deterministic rule engine's legal compliance score or pass/fail verdict.
4. Generates actionable recommendations for additional packaging photos (e.g. Back Panel, Side Panel).
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
    "net_quantity",
}


def _normalize_tokens(text: str) -> set[str]:
    """Normalize text into comparable word tokens, splitting unit concatenations like 1kg -> 1 kg."""
    s = text.lower()
    s = re.sub(r"(\d+)\s*([a-z]+)", r" ", s)
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
        return 0.95, "high_confidence"

    q_tokens = _normalize_tokens(query_text)
    target_tokens = _normalize_tokens(f"{matched_brand} {matched_name}")

    if not q_tokens or not target_tokens:
        return 0.0, "no_match"

    overlap = q_tokens.intersection(target_tokens)
    if not overlap:
        return 0.0, "no_match"

    score = len(overlap) / max(len(q_tokens), 1)
    score = min(round(score, 2), 0.95)

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
            }

    return best_match


def _generate_panel_recommendations(missing_fields: List[str]) -> List[str]:
    """Generate recommendations for specific physical package panels to photograph."""
    recs = []
    missing_set = set(missing_fields)

    # 1. Back panel recommendations
    if any(f in missing_set for f in ("mrp", "manufacturing_date", "batch_number", "unit_sale_price")):
        recs.append("Please upload a clear, unglared photo of the Back Panel or Printed Date-Code Flap to verify statutory MRP, Mfg Date, and Batch declarations.")

    # 2. Manufacturer / Packer panel
    if "manufacturer_name_address" in missing_set:
        recs.append("Please upload the Side Panel or Lower Flap containing the full Manufacturer / Packer Name & Physical Address.")

    # 3. Consumer Care panel
    if "consumer_care_contact" in missing_set:
        recs.append("Please photograph the Consumer Care / Grievance Helpline panel (toll-free number, email, or physical postal address).")

    # 4. Net quantity / PDP
    if "net_quantity" in missing_set:
        recs.append("Please capture the Principal Display Panel (PDP) showing the Net Quantity declaration.")

    return recs


def research_product_information(
    ocr_text: str,
    extracted_entities: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[Dict[str, Any]]] = None,
    barcode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform safe external product recovery for missing label declarations.

    CRITICAL RULES:
    - Never mutates rule engine results.
    - All recovered fields are flagged package_verified = False.
    - Package-specific declarations (MRP, dates) marked as reference only.
    """
    extracted_entities = extracted_entities or {}
    missing_fields = missing_fields or []
    missing_field_ids = [f.get("field_id") for f in missing_fields if f.get("status") == "fail"]

    # If no declarations are missing, skip unnecessary external search
    if not missing_field_ids and not barcode:
        return {
            "status": "skipped",
            "message": "All mandatory Legal Metrology declarations verified on package. External research not required.",
            "product_match": {"status": "package_complete", "confidence": 1.0},
            "sources": [],
            "fields": [],
            "recommended_photos": [],
            "warnings": [],
        }

    # 1. Attempt Barcode-Based Retrieval First (Highest Accuracy)
    matched_record = None
    has_barcode = False

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
                }
                has_barcode = True
        except Exception as exc:
            logger.debug("Barcode lookup in research service skipped: %s", exc)

    # 2. Name / Brand-Based Retrieval Fallback
    query_term = ""
    p_name = extracted_entities.get("product_name") or ""
    p_brand = extracted_entities.get("manufacturer") or extracted_entities.get("brand") or ""

    if not matched_record:
        # Construct search query from extracted tokens or first OCR lines
        if p_name or p_brand:
            query_term = f"{p_brand} {p_name}".strip()
        else:
            first_lines = [l.strip() for l in ocr_text.splitlines() if l.strip()][:2]
            query_term = " ".join(first_lines)

        if query_term:
            try:
                matched_record = _search_local_catalog_by_name(query_term)
            except Exception as exc:
                logger.debug("Local catalog search error: %s", exc)

            if not matched_record:
                try:
                    matched_record = _search_open_food_facts(query_term)
                except Exception as exc:
                    logger.debug("Open Food Facts search error: %s", exc)

    # 3. Assess Match Confidence
    if not matched_record:
        return {
            "status": "no_match",
            "message": "No sufficiently reliable external product match found for missing declarations.",
            "product_match": {
                "status": "no_match",
                "confidence": 0.0,
                "matched_product": None,
                "matched_brand": None,
            },
            "sources": [],
            "fields": [],
            "recommended_photos": _generate_panel_recommendations(missing_field_ids),
            "warnings": [
                "External reference information could not be retrieved. Please upload additional package photos."
            ],
        }

    conf_score, conf_status = _calculate_match_confidence(
        query_text=query_term or barcode or "",
        matched_name=matched_record.get("product_name", ""),
        matched_brand=matched_record.get("brand", ""),
        has_barcode_match=has_barcode,
    )

    if conf_status == "no_match":
        return {
            "status": "low_confidence_rejected",
            "message": "External search results did not meet confidence threshold for this packaging.",
            "product_match": {"status": "low_confidence", "confidence": conf_score},
            "sources": [],
            "fields": [],
            "recommended_photos": _generate_panel_recommendations(missing_field_ids),
            "warnings": [],
        }

    # 4. Map Missing Declarations to External Reference Values
    field_mapping = {
        "manufacturer_name_address": ("manufacturer", "Manufacturer Name & Address"),
        "country_of_origin": ("country_of_origin", "Country of Origin"),
        "consumer_care_contact": ("consumer_care", "Consumer Care Contact"),
        "net_quantity": ("net_quantity", "Net Quantity"),
        "mrp": ("mrp_reference", "Maximum Retail Price (Reference MRP)"),
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
                    "field": fid,
                    "field_name": friendly_name or fname,
                    "value": str(val).strip(),
                    "source_type": "internet",
                    "source_name": matched_record.get("source_name", "Public Product Catalog"),
                    "source_url": matched_record.get("source_url", ""),
                    "package_verified": False,
                    "verification_status": "REQUIRES_PACKAGE_VERIFICATION",
                    "package_evidence_status": "NOT_DETECTED_ON_UPLOADED_PANEL",
                    "is_package_specific": is_pkg_specific,
                    "explanation": (
                        "Reference value found online. This declaration varies by packaging batch and MUST be physically verified from the printed package label."
                        if is_pkg_specific else
                        "Manufacturer standard catalog value found online. Requires package photo confirmation under Legal Metrology Rules."
                    ),
                })

    return {
        "status": "success",
        "product_match": {
            "status": conf_status,
            "confidence": conf_score,
            "matched_product": matched_record.get("product_name"),
            "matched_brand": matched_record.get("brand"),
        },
        "sources": sources,
        "fields": recovered_fields,
        "recommended_photos": _generate_panel_recommendations(missing_field_ids),
        "warnings": [
            "External reference information is supplementary and does NOT verify what is physically printed on the scanned package.",
            "Statutory Legal Metrology compliance is calculated exclusively from uploaded package image evidence.",
        ],
    }
