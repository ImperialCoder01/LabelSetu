"""
Rule Engine — Legal Metrology compliance checker.

Checks OCR-extracted text against the mandatory declaration fields
defined in docs/rules.json and returns a structured compliance report.

Fields with "active": false are skipped during evaluation.

Usage:
    from services.rule_engine import load_rules, apply_rules

    rules = load_rules()
    report = apply_rules(extracted_text, rules)
"""

import json
import re
from pathlib import Path
from typing import Any


# -----------------------------------------------------------------------
# Load rules
# -----------------------------------------------------------------------
def load_rules() -> dict:
    """Load compliance rules from backend/rules.json or docs/rules.json."""
    candidates = [
        Path(__file__).parent.parent / "rules.json",
        Path(__file__).parent.parent.parent / "docs" / "rules.json",
    ]
    for rules_path in candidates:
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError("Rules file not found in backend/rules.json or docs/rules.json")


# -----------------------------------------------------------------------
# Single-field check
# -----------------------------------------------------------------------
def _check_field(text_lower: str, field: dict) -> dict:
    """Check whether a single field's keywords appear in the text."""
    keywords = field.get("keywords", [])
    matched = None

    for kw in keywords:
        if kw.lower() in text_lower:
            matched = kw
            break

    return {
        "field_id": field["id"],
        "field_name": field["name"],
        "severity": field["severity"],
        "status": "pass" if matched else "fail",
        "matched_keyword": matched,
        "description": field.get("description", ""),
        "active": field.get("active", True),
    }


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
def apply_multi_image_rules(image_results: list, rules: dict) -> dict:
    """
    Multi-Image Evidence Aggregator & Legal Metrology Compliance Engine.

    Parameters:
      image_results: List of dicts per image, containing:
        - image_index (int)
        - filename (str)
        - raw_text (str)
        - quality_info (dict: status, issues, guidance)
        - classification (dict: panel_type, is_product_label, guidance)
        - extracted_entities (dict)
        - extracted_entities_detailed (dict)

    Multi-Image Rules:
      1. Merges visible declarations across all uploaded panels.
      2. Assigns exact evidence_status per field:
         - CONFIRMED_PRESENT: Supported by readable image/OCR text on any uploaded panel.
         - CONFIRMED_MISSING: Declaration panel was photographed & readable, but field is genuinely missing.
         - NOT_VISIBLE: Relevant declaration panel was not photographed (e.g. only Front Panel uploaded).
         - UNREADABLE: Panel captured, but image quality is unreadable.
         - CONFLICTING_EVIDENCE: Multiple images return conflicting extracted values.
      3. Evidence-aware scoring:
         - ONLY CONFIRMED_MISSING fields deduct score points.
         - NOT_VISIBLE, UNREADABLE, and NOT_DETECTED do NOT penalize the score.
      4. Calculates Evidence Coverage (e.g., "5/8 declarations assessable").
      5. Formulates actionable user guidance for missing panels.
    """
    all_fields = rules.get("fields", [])
    active_fields = [f for f in all_fields if f.get("active", True)]
    scoring = rules.get("scoring", {"critical_weight": 15, "minor_weight": 5})
    critical_weight = scoring.get("critical_weight", 15)
    minor_weight = scoring.get("minor_weight", 5)

    if not image_results:
        return apply_rules("", rules)

    captured_panels = set()
    has_readable_back_panel = False
    has_unreadable_image = False
    has_screenshot = False

    for img_res in image_results:
        panel = img_res.get("classification", {}).get("panel_type", "UNKNOWN")
        captured_panels.add(panel)

        q_status = img_res.get("quality_info", {}).get("quality_status", "GOOD")
        if q_status == "UNREADABLE":
            has_unreadable_image = True
        if panel in ("BACK_DECLARATION_PANEL", "MIXED_PANEL") and q_status in ("GOOD", "FAIR", "POOR"):
            has_readable_back_panel = True
        if img_res.get("classification", {}).get("classification") == "SCREENSHOT":
            has_screenshot = True

    field_results = []
    critical_failures = []
    minor_failures = []
    assessable_count = 0
    passed_count = 0

    for field in active_fields:
        field_id = field["id"]
        field_name = field["name"]
        keywords = field.get("keywords", [])

        matches = []
        conflicting_values = set()

        for img_res in image_results:
            panel = img_res.get("classification", {}).get("panel_type", "UNKNOWN")
            if panel == "BARCODE_CATALOG":
                continue

            text_lower = (img_res.get("raw_text") or "").lower()
            q_status = img_res.get("quality_info", {}).get("quality_status", "GOOD")
            img_idx = img_res.get("image_index", 1)

            matched_kw = None
            for kw in keywords:
                if kw.lower() in text_lower:
                    matched_kw = kw
                    break

            ent_val = img_res.get("extracted_entities", {}).get(field_id)
            if not matched_kw and ent_val:
                matched_kw = str(ent_val)

            if matched_kw:
                display_val = ent_val or matched_kw
                matches.append({
                    "image_index": img_idx,
                    "filename": img_res.get("filename", f"Image {img_idx}"),
                    "matched_keyword": matched_kw,
                    "extracted_value": display_val,
                    "panel_type": panel,
                    "quality_status": q_status
                })
                conflicting_values.add(str(display_val).strip().lower())

        if len(conflicting_values) > 1 and field_id in ("net_quantity", "mrp", "mfg_date"):
            evidence_status = "CONFLICTING_EVIDENCE"
            status = "fail"
            score_impact = 0
            reason = f"Conflicting values detected across images: {list(conflicting_values)}"
        elif len(matches) > 0:
            evidence_status = "CONFIRMED_PRESENT"
            status = "pass"
            score_impact = 0
            reason = f"Matched '{matches[0]['matched_keyword']}' in {matches[0]['filename']} ({matches[0]['panel_type']})"
            passed_count += 1
            assessable_count += 1
        elif has_readable_back_panel:
            evidence_status = "CONFIRMED_MISSING"
            status = "fail"
            score_impact = -critical_weight if field["severity"] == "Critical" else -minor_weight
            reason = "Back declaration panel was photographed and readable, but declaration is absent."
            assessable_count += 1
        elif has_unreadable_image and not has_readable_back_panel:
            evidence_status = "UNREADABLE"
            status = "fail"
            score_impact = 0
            reason = "Relevant area was photographed, but image quality is unreadable."
        elif "FRONT_PANEL" in captured_panels and not has_readable_back_panel:
            evidence_status = "NOT_VISIBLE"
            status = "fail"
            score_impact = 0
            reason = "Only front panel captured. Declaration panel is not visible."
        else:
            evidence_status = "NOT_DETECTED"
            status = "fail"
            score_impact = 0
            reason = "Declaration could not be detected from available images."

        field_res = {
            "field_id": field_id,
            "field_name": field_name,
            "severity": field["severity"],
            "status": status,
            "evidence_status": evidence_status,
            "matched_keyword": matches[0]["matched_keyword"] if matches else None,
            "extracted_value": matches[0]["extracted_value"] if matches else None,
            "matched_images": [m["filename"] for m in matches],
            "score_impact": score_impact,
            "description": field.get("description", ""),
            "reason": reason,
            "active": field.get("active", True),
        }

        field_results.append(field_res)

        if evidence_status == "CONFIRMED_MISSING":
            if field["severity"] == "Critical":
                critical_failures.append(field_res)
            else:
                minor_failures.append(field_res)

    total = len(active_fields)

    # Score calculation: only CONFIRMED_MISSING deducts score
    score = 100
    for f in critical_failures:
        score -= critical_weight
    for f in minor_failures:
        score -= minor_weight

    score = max(0, min(100, score))

    # Overall Compliance Assessment
    if has_screenshot:
        assessment = "SCREENSHOT"
        overall_status = "fail"
    elif has_unreadable_image and not has_readable_back_panel:
        assessment = "UNREADABLE_IMAGE"
        overall_status = "fail"
    elif "FRONT_PANEL" in captured_panels and not has_readable_back_panel and passed_count < total:
        assessment = "FRONT_PANEL_ONLY"
        overall_status = "partial"
    elif len(critical_failures) > 0 or len(minor_failures) > 0:
        assessment = "PARTIALLY_COMPLIANT" if passed_count > 0 else "NON_COMPLIANT"
        overall_status = "partial" if passed_count > 0 else "fail"
    elif passed_count == total:
        assessment = "COMPLIANT"
        overall_status = "pass"
    else:
        assessment = "INSUFFICIENT_EVIDENCE"
        overall_status = "partial"

    actions_required = []
    if not has_readable_back_panel and assessment != "SCREENSHOT":
        actions_required.append("Upload a clear photograph of the back/side declaration panel for full Legal Metrology verification.")
    if has_unreadable_image:
        actions_required.append("Retake blurry photos with steady lighting and camera focus.")

    return {
        "overall_score": score,
        "status": overall_status,
        "compliance_assessment": assessment,
        "evidence_coverage": f"{assessable_count}/{total} declarations assessable",
        "captured_panels": list(captured_panels),
        "total_fields": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "critical_failures": critical_failures,
        "minor_failures": minor_failures,
        "fields": field_results,
        "actions_required": actions_required,
    }


def apply_rules(
    extracted_text: str,
    rules: dict,
    classification: dict = None,
    quality_info: dict = None
) -> dict:
    """
    Check OCR-extracted text against the Legal Metrology rules.

    Fields with ``active: false`` are excluded from scoring and
    the total field count.

    Returns a structured compliance report dict.
    """
    img_res = {
        "image_index": 1,
        "filename": "Image 1",
        "raw_text": extracted_text or "",
        "quality_info": quality_info or {"quality_status": "GOOD"},
        "classification": classification or {"panel_type": "MIXED_PANEL", "classification": "PRODUCT_LABEL"},
        "extracted_entities": {},
    }
    return apply_multi_image_rules([img_res], rules)
