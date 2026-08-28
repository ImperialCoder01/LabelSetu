"""
Reports Router

POST   /api/reports             — consumer submits a product report
GET    /api/reports             — admin lists all reports (newest first)
PATCH  /api/reports/{id}/forward  — admin forwards report to regulator
PATCH  /api/reports/{id}/resolve  — admin marks report as resolved
PATCH  /api/reports/{id}/dismiss  — admin dismisses report as spam
GET    /api/reports/flagged     — regulator views forwarded reports
PATCH  /api/reports/{id}/review  — regulator marks forwarded report as reviewed
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_current_user, require_role
from database import supabase

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ReportCreate(BaseModel):
    scan_id: str
    reason: str = ""


# ---------------------------------------------------------------------------
# Consumer — submit a report
# ---------------------------------------------------------------------------
@router.post("", status_code=201)
async def create_report(body: ReportCreate, user: dict = Depends(require_role("consumer", "brand"))):
    """Submit a product report linked to a scan."""
    # Verify scan exists and belongs to user
    scan_result = (
        supabase.table("scans")
        .select("id, user_id")
        .eq("id", body.scan_id)
        .single()
        .execute()
    )
    if not scan_result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan_result.data.get("user_id") != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied: Cannot report a scan belonging to another user")

    # Check for duplicate pending report on same scan
    existing = (
        supabase.table("product_reports")
        .select("id")
        .eq("scan_id", body.scan_id)
        .eq("reporter_id", user["sub"])
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="You have already reported this product")

    report_data = {
        "scan_id": body.scan_id,
        "reporter_id": user["sub"],
        "reason": body.reason,
    }

    result = supabase.table("product_reports").insert(report_data).execute()
    return result.data[0] if result.data else {"success": True}


# ---------------------------------------------------------------------------
# Admin — list all reports
# ---------------------------------------------------------------------------
@router.get("")
async def list_reports(admin: dict = Depends(require_role("admin"))):
    """List all product reports (newest first)."""
    result = (
        supabase.table("product_reports")
        .select("*, scans!product_reports_scan_id_fkey(extracted_text, compliance_score, users_profile!scans_user_id_fkey(full_name)), users_profile!product_reports_reporter_id_fkey(full_name)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


# ---------------------------------------------------------------------------
# Admin — update report status
# ---------------------------------------------------------------------------
@router.patch("/{report_id}/forward")
async def forward_report(report_id: str, admin: dict = Depends(require_role("admin"))):
    """Forward a report to the regulator for review."""
    result = (
        supabase.table("product_reports")
        .update({"status": "forwarded", "resolved_by": admin["sub"], "updated_at": datetime.utcnow().isoformat()})
        .eq("id", report_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return result.data[0]


@router.patch("/{report_id}/resolve")
async def resolve_report(report_id: str, admin: dict = Depends(require_role("admin"))):
    """Mark a report as resolved."""
    result = (
        supabase.table("product_reports")
        .update({"status": "resolved", "resolved_by": admin["sub"], "updated_at": datetime.utcnow().isoformat()})
        .eq("id", report_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return result.data[0]


@router.patch("/{report_id}/dismiss")
async def dismiss_report(report_id: str, admin: dict = Depends(require_role("admin"))):
    """Dismiss a report as spam."""
    result = (
        supabase.table("product_reports")
        .update({"status": "spam", "resolved_by": admin["sub"], "updated_at": datetime.utcnow().isoformat()})
        .eq("id", report_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Regulator — view forwarded reports
# ---------------------------------------------------------------------------
@router.get("/flagged")
async def flagged_reports(regulator: dict = Depends(require_role("regulator"))):
    """List forwarded reports for regulator review."""
    result = (
        supabase.table("product_reports")
        .select("*, scans!product_reports_scan_id_fkey(extracted_text, compliance_score, users_profile!scans_user_id_fkey(full_name)), users_profile!product_reports_reporter_id_fkey(full_name)")
        .eq("status", "forwarded")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.patch("/{report_id}/review")
async def review_report(report_id: str, regulator: dict = Depends(require_role("regulator"))):
    """Regulator marks a forwarded report as reviewed (resolved)."""
    result = (
        supabase.table("product_reports")
        .update({"status": "resolved", "resolved_by": regulator["sub"], "updated_at": datetime.utcnow().isoformat()})
        .eq("id", report_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return result.data[0]
