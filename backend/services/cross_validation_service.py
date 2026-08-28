"""
Cross-Validation Service — compares physical package OCR detections against
Level 1 manufacturer-verified registered product specifications.

Implements a normalized comparison layer that outputs explicit statuses:
  - MATCH
  - MISMATCH
  - NOT_DETECTED
  - UNREADABLE
  - REQUIRES_REVIEW

IMPORTANT:
- Formatting differences (e.g. ₹28 vs Rs 28 vs Rs. 28.00; 1 kg vs 1KG vs 1000g) are normalized.
- Genuine discrepancies (e.g. ₹28 vs ₹35; 1 kg vs 500g) are flagged as MISMATCH.
- Missing OCR detections are marked as NOT_DETECTED and NEVER conflated with MISMATCH or counterfeit.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_price(val: Any) -> Optional[float]:
    """Extract numeric price value handling currency symbols and punctuation."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # Remove currency symbols and common labels
    cleaned = re.sub(r"(?i)(?:mrp|rs\.?|\u20b9|inr|incl\.?|of\s+all\s+taxes|/-)", "", s)
    cleaned = cleaned.replace(",", "").strip()
    match = re.search(r"(?:\b|^)(\d+(?:\.\d{1,2})?)(?:\b|$)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def normalize_quantity(val: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Normalize net quantity into a standard base metric:
      - Mass in grams ('g')
      - Volume in milliliters ('ml')
      - Units in pieces ('pcs')
    Returns: (standard_magnitude, standard_unit)
    """
    if not val:
        return None, None
    s = str(val).lower().strip()
    s = re.sub(r"\s+", " ", s)

    # Kilograms -> Grams
    kg_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilogram|k\.g|kgs)\b", s)
    if kg_match:
        try:
            return float(kg_match.group(1)) * 1000.0, "g"
        except ValueError:
            pass

    # Grams
    g_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|gm|gms|gram|grams)\b", s)
    if g_match:
        try:
            return float(g_match.group(1)), "g"
        except ValueError:
            pass

    # Litres -> Millilitres
    l_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:l|ltr|litre|litres|liter)\b", s)
    if l_match:
        try:
            return float(l_match.group(1)) * 1000.0, "ml"
        except ValueError:
            pass

    # Millilitres
    ml_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ml|m\.l|millilitre|milliliter)\b", s)
    if ml_match:
        try:
            return float(ml_match.group(1)), "ml"
        except ValueError:
            pass

    # Generic piece count
    unit_match = re.search(r"(\d+)\s*(?:u|units|pcs|pieces|n|count)\b", s)
    if unit_match:
        try:
            return float(unit_match.group(1)), "units"
        except ValueError:
            pass

    return None, s


def cross_validate_physical_package(
    barcode: str,
    ocr_text: str,
    extracted_entities: Dict[str, Any],
    registered_product: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cross-validate physical OCR extractions against Level 1 manufacturer registered data.
    """
    if not registered_product:
        return {
            "match_status": "NOT_REGISTERED",
            "confidence_score": 0.0,
            "field_comparisons": {},
            "discrepancies": [],
            "level_1_verified_data": None,
            "level_2_physical_data": extracted_entities,
            "summary": "Product barcode is not registered in the authoritative database.",
            "recommendation": "Verify physical declarations according to standard Legal Metrology rules.",
        }

    field_comparisons: Dict[str, Dict[str, Any]] = {}
    discrepancies: List[Dict[str, Any]] = []

    level_1 = {
        "product_name": registered_product.get("product_name"),
        "brand_name": registered_product.get("brand_name"),
        "category": registered_product.get("category"),
        "barcode": registered_product.get("barcode"),
        "mrp": registered_product.get("mrp"),
        "net_quantity": registered_product.get("net_quantity"),
        "unit_sale_price": registered_product.get("unit_sale_price"),
        "manufacturer": registered_product.get("manufacturer_name_address") or registered_product.get("brand_name"),
        "packer": registered_product.get("packer_name_address"),
        "importer": registered_product.get("importer_name_address"),
        "country_of_origin": registered_product.get("country_of_origin"),
        "consumer_care": registered_product.get("consumer_care"),
        "fssai_lic": registered_product.get("fssai_lic"),
        "status": registered_product.get("status"),
    }

    # 1. Product Status Check
    status = (registered_product.get("status") or "").lower()
    if status == "suspended":
        discrepancies.append({
            "field": "status",
            "registered_value": "SUSPENDED",
            "physical_ocr_value": "In Circulation",
            "discrepancy_type": "SUSPENDED_PRODUCT_IN_MARKET",
            "severity": "CRITICAL",
            "message": "This product registration has been SUSPENDED by regulatory administration.",
        })
    elif status != "approved":
        discrepancies.append({
            "field": "status",
            "registered_value": status.upper(),
            "physical_ocr_value": "In Circulation",
            "discrepancy_type": "UNAPPROVED_PRODUCT_IN_MARKET",
            "severity": "HIGH",
            "message": f"Product is in '{status.upper()}' status and has not completed final admin approval.",
        })

    # 2. Maximum Retail Price (MRP) Comparison
    reg_mrp_num = normalize_price(registered_product.get("mrp"))
    ocr_mrp_raw = extracted_entities.get("mrp")
    ocr_mrp_num = normalize_price(ocr_mrp_raw)

    if reg_mrp_num is not None and ocr_mrp_num is not None:
        if abs(reg_mrp_num - ocr_mrp_num) <= 0.05:
            field_comparisons["mrp"] = {
                "status": "MATCH",
                "registered": f"₹{reg_mrp_num:.2f}",
                "physical": f"₹{ocr_mrp_num:.2f}",
            }
        else:
            diff = ocr_mrp_num - reg_mrp_num
            severity = "HIGH" if diff > 0 else "MEDIUM"
            msg = f"Package printed MRP (₹{ocr_mrp_num:.2f}) is higher than registered MRP (₹{reg_mrp_num:.2f}) — potential price overcharging." if diff > 0 else f"Package printed MRP (₹{ocr_mrp_num:.2f}) differs from registered MRP (₹{reg_mrp_num:.2f})."
            field_comparisons["mrp"] = {
                "status": "MISMATCH",
                "registered": f"₹{reg_mrp_num:.2f}",
                "physical": f"₹{ocr_mrp_num:.2f}",
            }
            discrepancies.append({
                "field": "mrp",
                "registered_value": f"₹{reg_mrp_num:.2f}",
                "physical_ocr_value": f"₹{ocr_mrp_num:.2f}",
                "discrepancy_type": "MRP_MISMATCH",
                "severity": severity,
                "message": msg,
            })
    elif reg_mrp_num is not None and ocr_mrp_raw:
        field_comparisons["mrp"] = {"status": "REQUIRES_REVIEW", "registered": str(registered_product.get("mrp")), "physical": str(ocr_mrp_raw)}
    else:
        field_comparisons["mrp"] = {"status": "NOT_DETECTED", "registered": str(registered_product.get("mrp") or "N/A"), "physical": "Not Detected"}

    # 3. Brand Name Comparison
    reg_brand = (registered_product.get("brand_name") or "").strip()
    ocr_brand = (extracted_entities.get("brand") or "").strip()
    ocr_text_lower = (ocr_text or "").lower()

    if reg_brand:
        reg_brand_lower = reg_brand.lower()
        if reg_brand_lower in ocr_text_lower or (ocr_brand and reg_brand_lower in ocr_brand.lower()):
            field_comparisons["brand_name"] = {"status": "MATCH", "registered": reg_brand, "physical": ocr_brand or reg_brand}
        elif ocr_brand:
            field_comparisons["brand_name"] = {"status": "MISMATCH", "registered": reg_brand, "physical": ocr_brand}
            discrepancies.append({
                "field": "brand_name",
                "registered_value": reg_brand,
                "physical_ocr_value": ocr_brand,
                "discrepancy_type": "BRAND_MISMATCH",
                "severity": "HIGH",
                "message": f"Registered brand '{reg_brand}' differs from detected brand '{ocr_brand}'.",
            })
        else:
            field_comparisons["brand_name"] = {"status": "NOT_DETECTED", "registered": reg_brand, "physical": "Not Detected"}

    # 4. Net Quantity Comparison
    reg_qty_val, reg_qty_unit = normalize_quantity(registered_product.get("net_quantity"))
    ocr_qty_raw = extracted_entities.get("net_quantity")
    ocr_qty_val, ocr_qty_unit = normalize_quantity(ocr_qty_raw)

    if reg_qty_val is not None and ocr_qty_val is not None:
        if reg_qty_unit == ocr_qty_unit and abs(reg_qty_val - ocr_qty_val) <= 0.01:
            field_comparisons["net_quantity"] = {"status": "MATCH", "registered": registered_product.get("net_quantity"), "physical": ocr_qty_raw}
        else:
            field_comparisons["net_quantity"] = {"status": "MISMATCH", "registered": registered_product.get("net_quantity"), "physical": ocr_qty_raw}
            discrepancies.append({
                "field": "net_quantity",
                "registered_value": str(registered_product.get("net_quantity")),
                "physical_ocr_value": str(ocr_qty_raw),
                "discrepancy_type": "NET_QUANTITY_MISMATCH",
                "severity": "MEDIUM",
                "message": f"Registered quantity ({registered_product.get('net_quantity')}) differs from physical label ({ocr_qty_raw}).",
            })
    elif registered_product.get("net_quantity") and ocr_qty_raw:
        # Fallback string comparison
        reg_clean = re.sub(r"\s+", "", str(registered_product.get("net_quantity")).lower())
        ocr_clean = re.sub(r"\s+", "", str(ocr_qty_raw).lower())
        if reg_clean == ocr_clean:
            field_comparisons["net_quantity"] = {"status": "MATCH", "registered": registered_product.get("net_quantity"), "physical": ocr_qty_raw}
        else:
            field_comparisons["net_quantity"] = {"status": "MISMATCH", "registered": registered_product.get("net_quantity"), "physical": ocr_qty_raw}
            discrepancies.append({
                "field": "net_quantity",
                "registered_value": str(registered_product.get("net_quantity")),
                "physical_ocr_value": str(ocr_qty_raw),
                "discrepancy_type": "NET_QUANTITY_MISMATCH",
                "severity": "MEDIUM",
                "message": f"Registered quantity ({registered_product.get('net_quantity')}) differs from physical label ({ocr_qty_raw}).",
            })
    else:
        field_comparisons["net_quantity"] = {"status": "NOT_DETECTED" if not ocr_qty_raw else "MATCH", "registered": str(registered_product.get("net_quantity") or "N/A"), "physical": ocr_qty_raw or "Not Detected"}

    # 5. FSSAI License Comparison
    reg_fssai = re.sub(r"\D", "", str(registered_product.get("fssai_lic") or ""))
    ocr_fssai = re.sub(r"\D", "", str(extracted_entities.get("fssai_lic") or ""))
    if len(reg_fssai) == 14 and len(ocr_fssai) == 14:
        if reg_fssai == ocr_fssai:
            field_comparisons["fssai_lic"] = {"status": "MATCH", "registered": reg_fssai, "physical": ocr_fssai}
        else:
            field_comparisons["fssai_lic"] = {"status": "MISMATCH", "registered": reg_fssai, "physical": ocr_fssai}
            discrepancies.append({
                "field": "fssai_lic",
                "registered_value": reg_fssai,
                "physical_ocr_value": ocr_fssai,
                "discrepancy_type": "FSSAI_LICENSE_MISMATCH",
                "severity": "HIGH",
                "message": f"Registered FSSAI Lic ({reg_fssai}) does not match packaging Lic ({ocr_fssai}).",
            })
    elif len(reg_fssai) == 14 and not ocr_fssai:
        field_comparisons["fssai_lic"] = {"status": "NOT_DETECTED", "registered": reg_fssai, "physical": "Not Detected"}

    # 6. Country of Origin Comparison
    reg_origin = (registered_product.get("country_of_origin") or "India").strip().lower()
    ocr_origin = (extracted_entities.get("country_of_origin") or "").strip().lower()
    if reg_origin and ocr_origin:
        if reg_origin in ocr_origin or ocr_origin in reg_origin:
            field_comparisons["country_of_origin"] = {"status": "MATCH", "registered": registered_product.get("country_of_origin"), "physical": extracted_entities.get("country_of_origin")}
        else:
            field_comparisons["country_of_origin"] = {"status": "MISMATCH", "registered": registered_product.get("country_of_origin"), "physical": extracted_entities.get("country_of_origin")}
            discrepancies.append({
                "field": "country_of_origin",
                "registered_value": str(registered_product.get("country_of_origin")),
                "physical_ocr_value": str(extracted_entities.get("country_of_origin")),
                "discrepancy_type": "ORIGIN_MISMATCH",
                "severity": "HIGH",
                "message": f"Registered origin ({registered_product.get('country_of_origin')}) differs from physical label ({extracted_entities.get('country_of_origin')}).",
            })

    # Final Match Status Determination
    critical_count = len([d for d in discrepancies if d.get("severity") in ("CRITICAL", "HIGH")])
    if critical_count > 0:
        match_status = "DISCREPANCY_DETECTED"
        confidence_score = 0.40
        summary = f"Detected {len(discrepancies)} discrepancy(ies) between physical packaging and registered manufacturer specifications."
    elif len(discrepancies) > 0:
        match_status = "REQUIRES_REVIEW"
        confidence_score = 0.75
        summary = f"Minor variations noted in {len(discrepancies)} field(s)."
    else:
        match_status = "MATCH"
        confidence_score = 0.98
        summary = "Physical package declarations match Level 1 registered manufacturer specifications."

    return {
        "match_status": match_status,
        "confidence_score": confidence_score,
        "field_comparisons": field_comparisons,
        "discrepancies": discrepancies,
        "level_1_verified_data": level_1,
        "level_2_physical_data": extracted_entities,
        "summary": summary,
        "recommendation": "Review discrepancy with manufacturer or report issue to regulatory officer." if critical_count > 0 else "Product declarations verified against authoritative registry.",
    }
