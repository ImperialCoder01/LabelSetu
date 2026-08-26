"""
Certificates Router

GET /api/scans/{scan_id}/certificate — download PDF compliance certificate
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from database import supabase
from auth.dependencies import get_current_user, require_role
from services.certificate_service import generate_certificate
from services.rule_engine import load_rules, apply_rules
from config import settings

router = APIRouter()

_rules = None

def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


@router.get("/{scan_id}/certificate")
async def download_certificate(
    scan_id: str,
    user: dict = Depends(require_role("brand", "admin")),
):
    """
    Generate and download a PDF compliance certificate for a scan.
    Only brand owners or admins can download certificates.
    """
    # Fetch scan
    result = (
        supabase.table("scans")
        .select("*")
        .eq("id", scan_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = result.data

    # Check ownership (unless admin)
    user_role = user.get("profile", {}).get("role")
    if user_role != "admin" and scan["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build compliance report from extracted text
    extracted_text = scan.get("extracted_text", "")
    compliance_report = apply_rules(extracted_text, _get_rules()) if extracted_text else {
        "overall_score": scan.get("compliance_score", 0),
        "status": "unknown",
        "total_fields": 0,
        "passed": 0,
        "failed": 0,
        "fields": [],
    }

    # Build user profile dict for the certificate
    user_profile = user.get("profile", {})

    # Generate verification URL — QR code links to the public HTML page
    verify_url = f"{settings.BACKEND_URL}/api/verify/{scan_id}/html"

    # Generate PDF
    pdf_bytes = generate_certificate(
        scan=scan,
        compliance_report=compliance_report,
        user_profile=user_profile,
        verify_url=verify_url,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificate-{scan_id[:8]}.pdf"',
        },
    )
