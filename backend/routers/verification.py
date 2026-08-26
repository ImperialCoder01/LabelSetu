"""
Verification Router — public endpoints for certificate verification.

GET /api/verify/{scan_id} — returns scan details as JSON (no auth required)
GET /api/verify/{scan_id}/html — returns an HTML verification page
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from database import supabase
from services.rule_engine import load_rules, apply_rules

router = APIRouter()

_rules = None

def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


@router.get("/{scan_id}")
async def verify_scan(scan_id: str):
    """
    Public endpoint — returns scan verification details as JSON.
    No authentication required.
    """
    result = (
        supabase.table("scans")
        .select("id, user_id, extracted_text, compliance_score, missing_fields, created_at")
        .eq("id", scan_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = result.data

    # Get brand name from user profile
    profile_result = (
        supabase.table("users_profile")
        .select("full_name, role")
        .eq("id", scan["user_id"])
        .single()
        .execute()
    )
    brand_name = profile_result.data.get("full_name", "Unknown") if profile_result.data else "Unknown"

    # Rebuild compliance report
    extracted_text = scan.get("extracted_text", "")
    compliance_report = apply_rules(extracted_text, _get_rules()) if extracted_text else None

    return {
        "verified": True,
        "scan_id": scan["id"],
        "brand": brand_name,
        "compliance_score": scan["compliance_score"],
        "missing_fields": scan.get("missing_fields", []),
        "created_at": scan["created_at"],
        "compliance_report": compliance_report,
    }


@router.get("/{scan_id}/html", response_class=HTMLResponse)
async def verify_scan_html(scan_id: str):
    """
    Public endpoint — returns a styled HTML verification page.
    No authentication required.
    """
    result = (
        supabase.table("scans")
        .select("id, user_id, extracted_text, compliance_score, missing_fields, created_at")
        .eq("id", scan_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTMLResponse(
            content="<html><body><h1>Scan Not Found</h1><p>This certificate ID is not valid.</p></body></html>",
            status_code=404,
        )

    scan = result.data
    profile_result = (
        supabase.table("users_profile")
        .select("full_name")
        .eq("id", scan["user_id"])
        .single()
        .execute()
    )
    brand_name = profile_result.data.get("full_name", "Unknown") if profile_result.data else "Unknown"

    score = scan.get("compliance_score", 0)
    if score >= 80:
        status_text = "COMPLIANT"
        status_color = "#16a34a"
        bg_color = "#f0fdf4"
    elif score >= 50:
        status_text = "PARTIALLY COMPLIANT"
        status_color = "#d97706"
        bg_color = "#fffbeb"
    else:
        status_text = "NON-COMPLIANT"
        status_color = "#dc2626"
        bg_color = "#fef2f2"

    extracted_text = scan.get("extracted_text", "")
    product_name = extracted_text.split("\n")[0][:60] if extracted_text else "Product"
    created = scan.get("created_at", "")[:10]
    missing_count = len(scan.get("missing_fields") or [])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LabelSetu Certificate Verification</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 480px; width: 100%; overflow: hidden; }}
        .header {{ background: #1e3a8a; color: white; padding: 24px; text-align: center; }}
        .header h1 {{ font-size: 20px; margin-bottom: 4px; }}
        .header p {{ font-size: 13px; opacity: 0.8; }}
        .body {{ padding: 24px; }}
        .badge {{ display: inline-block; padding: 6px 16px; border-radius: 9999px; font-weight: 700; font-size: 14px; color: {status_color}; background: {bg_color}; }}
        .score {{ font-size: 48px; font-weight: 800; color: {status_color}; text-align: center; margin: 16px 0; }}
        .score span {{ font-size: 16px; color: #9ca3af; }}
        .detail {{ padding: 12px 0; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; font-size: 14px; }}
        .detail:last-child {{ border-bottom: none; }}
        .detail .label {{ color: #6b7280; }}
        .detail .value {{ font-weight: 500; color: #111827; text-align: right; }}
        .footer {{ padding: 16px 24px; background: #f9fafb; text-align: center; font-size: 12px; color: #9ca3af; }}
        .checkmark {{ text-align: center; font-size: 48px; margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>LabelSetu</h1>
            <p>Product Label Compliance Verification</p>
        </div>
        <div class="body">
            <div class="checkmark">{"&#10004;" if score >= 80 else "&#10006;" if score < 50 else "&#9888;"}</div>
            <div style="text-align:center"><span class="badge">{status_text}</span></div>
            <div class="score">{score}<span>/100</span></div>
            <div class="detail"><span class="label">Brand</span><span class="value">{brand_name}</span></div>
            <div class="detail"><span class="label">Product</span><span class="value" style="max-width:260px;text-align:right">{product_name}</span></div>
            <div class="detail"><span class="label">Score</span><span class="value">{score} / 100</span></div>
            <div class="detail"><span class="label">Issue Date</span><span class="value">{created}</span></div>
            <div class="detail"><span class="label">Certificate ID</span><span class="value" style="font-family:monospace;font-size:11px">{scan_id[:16]}…</span></div>
            <div class="detail"><span class="label">Missing Fields</span><span class="value">{missing_count} field{'s' if missing_count != 1 else ''}</span></div>
        </div>
        <div class="footer">
            This verification page was generated by LabelSetu.<br>
            Certificate ID: {scan_id}
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html)
