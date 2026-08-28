"""
Product Verification Router — Consumer authenticity verification, anti-cloning telemetry,
and Physical OCR vs Level 1 Manufacturer Registered Data cross-validation.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, require_role
from models.product_models import BarcodeVerifyRequest, CrossValidateRequest
from services import product_registry_service as prs
from services import cross_validation_service as cvs
from database import supabase

router = APIRouter()


@router.post("/verify-barcode")
async def verify_barcode(
    body: BarcodeVerifyRequest,
    user: Optional[dict] = Depends(get_current_user),
):
    """
    Instant Barcode Authenticity Verification.
    Looks up authoritative registry, evaluates anti-cloning frequency,
    and logs verification event.
    """
    user_id = user.get("sub") if user else None
    result = prs.verify_barcode_authenticity(
        barcode=body.barcode,
        user_id=user_id,
        source=body.verification_source or "barcode_scan",
        metadata=body.metadata or {},
    )
    return result


@router.post("/cross-validate")
async def cross_validate_package(
    body: CrossValidateRequest,
    user: Optional[dict] = Depends(get_current_user),
):
    """
    Cross-validate Physical Package OCR detections against Level 1 Manufacturer Registered Data.
    Detects price mismatches, brand variations, and declaration discrepancies.
    """
    registered = prs.get_product_by_barcode(body.barcode)
    report = cvs.cross_validate_physical_package(
        barcode=body.barcode,
        ocr_text=body.ocr_text or "",
        extracted_entities=body.extracted_entities or {},
        registered_product=registered,
    )
    return report


@router.get("/analytics")
async def get_verification_analytics(
    barcode: Optional[str] = None,
    user: dict = Depends(require_role("brand", "admin", "regulator")),
):
    """
    Get verification volume, status distributions, and suspicious activity telemetry.
    """
    role = user.get("role", "consumer")
    user_id = user.get("sub")

    try:
        query = supabase.table("product_verifications").select("*")
        if barcode:
            query = query.eq("barcode", barcode)
        elif role == "brand":
            # Filter to brand's own products
            p_res = supabase.table("products").select("id").eq("manufacturer_id", user_id).execute()
            p_ids = [p["id"] for p in p_res.data] if p_res.data else []
            if p_ids:
                query = query.in_("product_id", p_ids)
            else:
                return {"total_scans": 0, "verified": 0, "suspicious": 0, "recent_events": []}

        res = query.order("created_at", desc=True).limit(100).execute()
        events = res.data or []

        total = len(events)
        verified_count = len([e for e in events if e.get("result") == "VERIFIED"])
        suspicious_count = len([e for e in events if e.get("suspicious_flag") in ("SUSPICIOUS", "UNDER_REVIEW")])

        return {
            "total_scans": total,
            "verified": verified_count,
            "suspicious": suspicious_count,
            "recent_events": events[:20],
        }
    except Exception as exc:
        return {"total_scans": 0, "verified": 0, "suspicious": 0, "recent_events": [], "error": str(exc)}
