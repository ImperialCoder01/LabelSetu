"""
Executive Reports Router — investigation cases, evidence builders,
and enforcement action recommendations managed by Executive Officers (Regulators) for Admin review.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from auth.dependencies import require_role
from models.product_models import ExecutiveReportCreate, ExecutiveReportAdminDecision
from services import executive_report_service as ers

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_executive_report(
    body: ExecutiveReportCreate,
    regulator: dict = Depends(require_role("regulator", "admin")),
):
    """
    Executive Officer creates and submits an enforcement investigation case report.
    """
    try:
        case_report = ers.create_case_report(regulator_id=regulator["sub"], data=body)
        return case_report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
async def list_executive_reports(
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    status_filter: Optional[str] = Query(None, alias="status", description="SUBMITTED | APPROVED | REJECTED | etc."),
    report_type: Optional[str] = Query(None, description="VIOLATION | SUSPECTED_COUNTERFEIT | etc."),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("regulator", "admin")),
):
    """
    List executive investigation reports with severity and status filters.
    """
    return ers.list_case_reports(
        user=user,
        severity=severity,
        status=status_filter,
        report_type=report_type,
        limit=limit,
    )


@router.get("/{report_id}")
async def get_executive_report(
    report_id: str,
    user: dict = Depends(require_role("regulator", "admin")),
):
    """Get single executive report with evidence attachments."""
    report = ers.get_case_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Executive report not found")
    return report


@router.post("/{report_id}/decision")
async def review_executive_report(
    report_id: str,
    body: ExecutiveReportAdminDecision,
    admin: dict = Depends(require_role("admin")),
):
    """
    Admin reviews and approves/rejects an executive officer case recommendation.
    Generates immutable audit log entry and notifies the submitting officer.
    """
    try:
        updated = ers.admin_review_case(
            report_id=report_id,
            admin_id=admin["sub"],
            decision_data=body,
        )
        return {"success": True, "report": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{report_id}/timeline")
async def get_executive_report_timeline(
    report_id: str,
    user: dict = Depends(require_role("regulator", "admin")),
):
    """
    Reconstruct the full case timeline across product registration, barcode verification,
    OCR scans, consumer complaints, officer investigation, and admin decisions.
    """
    timeline_data = ers.get_case_timeline(report_id)
    if not timeline_data:
        raise HTTPException(status_code=404, detail="Executive report not found")
    return timeline_data
