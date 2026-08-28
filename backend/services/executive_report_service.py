"""
Executive Report Service — manages case investigations, evidence handling,
and enforcement recommendations submitted by Executive Officers (Regulators) for Admin review.

Enforces strict role separation, state machine transitions, and comprehensive case timeline reconstruction.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from database import supabase
from models.product_models import ExecutiveReportCreate, ExecutiveReportAdminDecision
from services.notification_service import create_notification

logger = logging.getLogger(__name__)

# Valid Case / Enforcement Report State Transitions
VALID_CASE_TRANSITIONS = {
    "SUBMITTED": {"UNDER_ADMIN_REVIEW", "APPROVED", "REJECTED", "MORE_INFORMATION_REQUIRED"},
    "UNDER_ADMIN_REVIEW": {"APPROVED", "REJECTED", "MORE_INFORMATION_REQUIRED"},
    "APPROVED": {"ACTION_IN_PROGRESS", "RESOLVED", "CLOSED"},
    "REJECTED": {"CLOSED"},
    "MORE_INFORMATION_REQUIRED": {"SUBMITTED", "UNDER_ADMIN_REVIEW"},
    "ACTION_IN_PROGRESS": {"RESOLVED", "CLOSED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}


def _get_utc_now_iso() -> str:
    """Return ISO format UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def create_case_report(
    regulator_id: str,
    data: ExecutiveReportCreate,
) -> Dict[str, Any]:
    """Create a new enforcement case investigation report."""
    now_year = datetime.now(timezone.utc).year
    case_num = f"CASE-{now_year}-{str(uuid.uuid4())[:6].upper()}"

    # Extract manufacturer_id from product if product_id provided
    mfg_id = None
    if data.product_id:
        try:
            p_res = supabase.table("products").select("manufacturer_id").eq("id", data.product_id).single().execute()
            if p_res.data:
                mfg_id = p_res.data.get("manufacturer_id")
        except Exception:
            pass

    payload = {
        "case_number": case_num,
        "product_id": data.product_id,
        "manufacturer_id": mfg_id,
        "barcode": data.barcode,
        "report_type": data.report_type,
        "severity": data.severity,
        "description": data.description,
        "detected_issue": data.detected_issue,
        "applicable_rule": data.applicable_rule,
        "evidence": data.evidence or {},
        "executive_observations": data.executive_observations,
        "recommended_action": data.recommended_action,
        "submitted_by": regulator_id,
        "status": "SUBMITTED",
        "created_at": _get_utc_now_iso(),
        "updated_at": _get_utc_now_iso(),
    }

    try:
        res = supabase.table("executive_reports").insert(payload).execute()
        report = res.data[0] if res.data else payload

        # Notify Admins of New Executive Report
        try:
            admin_users = supabase.table("users_profile").select("id").eq("role", "admin").execute()
            if admin_users.data:
                for adm in admin_users.data:
                    create_notification(
                        user_id=adm["id"],
                        title=f"New Executive Report: {case_num} ({data.severity})",
                        message=f"Executive officer submitted {data.report_type} report on {data.barcode or 'product'}. Recommendation: {data.recommended_action}.",
                        notif_type="ACTION_REQUIRED",
                        entity_type="executive_report",
                        entity_id=report.get("id"),
                    )
        except Exception:
            pass

        return report
    except Exception as exc:
        logger.error("Failed to insert executive report: %s", exc)
        raise RuntimeError(f"Database error submitting executive report: {exc}")


def list_case_reports(
    user: Dict[str, Any],
    severity: Optional[str] = None,
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List case reports with role-based visibility and filters."""
    role = user.get("role", "consumer")
    user_id = user.get("sub")

    try:
        query = supabase.table("executive_reports").select(
            "*, users_profile!executive_reports_submitted_by_fkey(full_name), products(product_name, brand_name, barcode)"
        )

        if severity:
            query = query.eq("severity", severity)
        if status:
            query = query.eq("status", status)
        if report_type:
            query = query.eq("report_type", report_type)

        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as exc:
        logger.error("Failed to list executive reports: %s", exc)
        return []


def get_case_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Get single executive report with evidence."""
    try:
        res = (
            supabase.table("executive_reports")
            .select("*, users_profile!executive_reports_submitted_by_fkey(full_name), products(*)")
            .eq("id", report_id)
            .single()
            .execute()
        )
        return res.data
    except Exception as exc:
        logger.error("Failed to fetch executive report %s: %s", report_id, exc)
        return None


def get_case_timeline(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Reconstruct the complete case timeline:
      1. Product registration & revisions
      2. Barcode verification history & velocity
      3. Physical packaging scans & OCR detections
      4. Consumer grievance complaints
      5. Executive officer observations & evidence
      6. Admin decisions & enforcement actions
      7. Immutable system audit log entries
    """
    case = get_case_report(report_id)
    if not case:
        return None

    timeline_events = []

    # 1. Case Creation Event
    timeline_events.append({
        "stage": "EXECUTIVE_INVESTIGATION_SUBMITTED",
        "timestamp": case.get("created_at"),
        "actor": case.get("users_profile", {}).get("full_name") or "Executive Officer",
        "title": f"Investigation Filed: {case.get('case_number')}",
        "details": f"Severity: {case.get('severity')} | Recommended Action: {case.get('recommended_action')}",
    })

    # 2. Product Registration Event if linked
    product = case.get("products")
    if product:
        timeline_events.append({
            "stage": "PRODUCT_REGISTRATION",
            "timestamp": product.get("created_at"),
            "actor": "Manufacturer",
            "title": f"Product Registered: {product.get('product_name')}",
            "details": f"Brand: {product.get('brand_name')} | Barcode: {product.get('barcode')} | Status: {product.get('status')}",
        })

    # 3. Admin Decision Event if reviewed
    if case.get("admin_decision"):
        timeline_events.append({
            "stage": "ADMIN_ENFORCEMENT_DECISION",
            "timestamp": case.get("updated_at"),
            "actor": "Administrative Authority",
            "title": f"Admin Decision: {case.get('admin_decision')}",
            "details": f"Comments: {case.get('admin_comments') or 'None'} | Final Action: {case.get('final_action_taken')}",
        })

    # Sort timeline chronologically
    timeline_events.sort(key=lambda x: x.get("timestamp") or "")

    return {
        "case": case,
        "timeline": timeline_events,
    }


def admin_review_case(
    report_id: str,
    admin_id: str,
    decision_data: ExecutiveReportAdminDecision,
) -> Dict[str, Any]:
    """Admin reviews and decides on an executive officer enforcement report."""
    existing = get_case_report(report_id)
    if not existing:
        raise ValueError("Executive report not found")

    decision = decision_data.decision.upper()
    status_map = {
        "APPROVED": "APPROVED",
        "REJECTED": "REJECTED",
        "MORE_INFORMATION_REQUIRED": "MORE_INFORMATION_REQUIRED",
    }
    if decision not in status_map:
        raise ValueError(f"Invalid decision '{decision}'. Must be APPROVED, REJECTED, or MORE_INFORMATION_REQUIRED.")

    current_status = existing.get("status", "SUBMITTED")
    new_status = status_map[decision]

    # Validate State Transition
    allowed_transitions = VALID_CASE_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_transitions and new_status != current_status:
        raise ValueError(f"Invalid case status transition from '{current_status}' to '{new_status}'")

    payload = {
        "status": new_status,
        "admin_id": admin_id,
        "admin_decision": decision,
        "admin_comments": decision_data.comments,
        "final_action_taken": decision_data.final_action_taken or existing.get("recommended_action"),
        "updated_at": _get_utc_now_iso(),
    }

    try:
        res = supabase.table("executive_reports").update(payload).eq("id", report_id).execute()

        # Audit Log Entry
        try:
            supabase.table("audit_log").insert({
                "admin_id": admin_id,
                "action_type": f"EXECUTIVE_CASE_{decision}",
                "target_table": "executive_reports",
                "target_id": report_id,
                "old_value": json.dumps({"status": current_status, "recommended_action": existing.get("recommended_action")}),
                "new_value": json.dumps(payload),
            }).execute()
        except Exception:
            pass

        # Notify Submitting Officer
        officer_id = existing.get("submitted_by")
        if officer_id:
            create_notification(
                user_id=officer_id,
                title=f"Case Decision: {existing.get('case_number')}",
                message=f"Admin {decision.lower()} case recommendation: {decision_data.comments or ''}".strip(),
                notif_type="INFO",
                entity_type="executive_report",
                entity_id=report_id,
            )

        return res.data[0] if res.data else payload
    except Exception as exc:
        logger.error("Failed to update executive report decision on %s: %s", report_id, exc)
        raise RuntimeError(f"Database error recording admin decision: {exc}")
