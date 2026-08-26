"""
Compliance service — thin wrapper around the rule engine.

Keeps backward compatibility with existing routers that call
check_compliance(extracted_text) while the rule engine does the
heavy lifting.
"""

from services.rule_engine import load_rules, apply_rules


# Load rules once at module level
_rules = None


def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


def check_compliance(extracted_text: str) -> dict:
    """
    Check extracted text against Legal Metrology compliance rules.

    Backward-compatible wrapper — returns the same shape the rest
    of the app already expects:

        {
          "score": int,            # 0–100
          "found_fields": [...],   # list of field_ids that passed
          "missing_fields": [...], # list of field_ids that failed
          "total_required": int,
          "report": { ... }        # full structured report from rule_engine
        }
    """
    report = apply_rules(extracted_text, _get_rules())

    found = [f["field_id"] for f in report["fields"] if f["status"] == "pass"]
    missing = [f["field_id"] for f in report["fields"] if f["status"] == "fail"]

    return {
        "score": report["overall_score"],
        "found_fields": found,
        "missing_fields": missing,
        "total_required": report["total_fields"],
        "report": report,
    }
