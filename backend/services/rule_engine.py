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
    text_lower = (extracted_text or "").lower()
    all_fields = rules.get("fields", [])

    # Only evaluate active fields
    active_fields = [f for f in all_fields if f.get("active", True)]

    scoring = rules.get("scoring", {"critical_weight": 15, "minor_weight": 5})
    critical_weight = scoring.get("critical_weight", 15)
    minor_weight = scoring.get("minor_weight", 5)

    field_results = []
    critical_failures = []
    minor_failures = []
    passed_count = 0

    class_type = classification.get("classification") if classification else "PRODUCT_LABEL"
    quality_status = quality_info.get("quality_status") if quality_info else "GOOD"

    for field in active_fields:
        result = _check_field(text_lower, field)

        # Enhance semantic status
        if result["status"] == "pass":
            result["semantic_status"] = "PASS"
        elif quality_status == "UNREADABLE":
            result["semantic_status"] = "UNREADABLE"
        elif class_type == "FRONT_PANEL":
            result["semantic_status"] = "NOT_DETECTED"
        else:
            result["semantic_status"] = "CONFIRMED_MISSING"

        field_results.append(result)

        if result["status"] == "pass":
            passed_count += 1
        else:
            if result["severity"] == "Critical":
                critical_failures.append(result)
            else:
                minor_failures.append(result)

    total = len(active_fields)
    failed_count = total - passed_count

    # Calculate score: start at 100, deduct per severity
    score = 100
    for f in critical_failures:
        score -= critical_weight
    for f in minor_failures:
        score -= minor_weight

    score = max(0, min(100, score))

    if failed_count == 0:
        status = "pass"
        assessment = "COMPLIANT"
    elif passed_count == 0:
        status = "fail"
        assessment = "NON_COMPLIANT" if class_type not in ("UNREADABLE_IMAGE", "SCREENSHOT") else class_type
    else:
        status = "partial"
        assessment = "PARTIALLY_COMPLIANT"

    if class_type == "FRONT_PANEL":
        assessment = "FRONT_PANEL_ONLY"

    return {
        "overall_score": score,
        "status": status,
        "compliance_assessment": assessment,
        "total_fields": total,
        "passed": passed_count,
        "failed": failed_count,
        "critical_failures": critical_failures,
        "minor_failures": minor_failures,
        "fields": field_results,
    }
