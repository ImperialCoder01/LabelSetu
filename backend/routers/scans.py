"""
Scans Router

POST  /api/scans/scan      — full pipeline: image → OCR → rules → score → save → report
                             optionally accepts barcode for Open Food Facts cross-reference
GET   /api/scans/          — list current user's scan history
GET   /api/scans/{id}      — get a single scan by ID
"""

import io
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database import supabase
from auth.dependencies import get_current_user, require_role
from services.ocr_service import extract_text_with_scores
from services.rule_engine import load_rules, apply_rules
from services.barcode_service import lookup_barcode, detect_manufacturer_mismatch

router = APIRouter()

# Load rules once at module level
_rules = None

# Magic bytes for common image formats
_IMAGE_SIGNATURES = [
    b"\x89PNG",            # PNG
    b"\xff\xd8\xff",      # JPEG
    b"GIF87a",             # GIF87a
    b"GIF89a",             # GIF89a
    b"RIFF",               # WebP (RIFF container)
    b"BM",                 # BMP
]


def _is_valid_image(data: bytes) -> bool:
    """Check file magic bytes to confirm it is an image."""
    if len(data) < 12:
        return False
    for sig in _IMAGE_SIGNATURES:
        if data[: len(sig)] == sig:
            return True
    return False


def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


# ---------------------------------------------------------------------------
# POST /scan — combined OCR + rule engine + Supabase save
# ---------------------------------------------------------------------------
from typing import Optional

@router.post("/scan")
async def scan(
    file: Optional[UploadFile] = File(None, description="Optional product label image (PNG / JPEG, max 10 MB)"),
    barcode: str = Form(default="", description="Optional barcode for Open Food Facts lookup"),
    user: dict = Depends(require_role("consumer", "brand")),
):
    """
    Upload a product label image and/or scan a barcode to run OCR, apply
    Legal Metrology rules, compute a compliance score, save to Supabase,
    and return the full report.

    Supports image-only, barcode-only, or combined image + barcode.
    """
    barcode_clean = (barcode or "").strip()
    image_bytes = b""

    if file and file.filename:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File must be an image (got {file.content_type})")
        image_bytes = await file.read()
        if len(image_bytes) > 0:
            if not _is_valid_image(image_bytes):
                raise HTTPException(status_code=400, detail="File is not a valid image")
            if len(image_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File too large. Max 10 MB.")

    if len(image_bytes) == 0 and not barcode_clean:
        raise HTTPException(status_code=400, detail="Please upload a label image or scan a barcode.")

    # ---- Handle OCR or Barcode-only text generation ----
    ocr_result = {
        "provider": "none",
        "enhanced": False,
        "full_text": "",
        "extracted_entities": {},
        "detections": [],
        "average_confidence": 0.0,
    }

    if len(image_bytes) > 0:
        try:
            ocr_result = extract_text_with_scores(image_bytes)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=f"OCR provider error: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    barcode_data = None
    manufacturer_mismatch = None

    if barcode_clean:
        barcode_data = lookup_barcode(barcode_clean)

    # Build full text for compliance evaluation
    full_text = ocr_result.get("full_text", "")

    if not full_text and barcode_data and barcode_data.get("found"):
        # Construct synthetic text representation from registered Open Food Facts data
        b_lines = [
            f"Product Name: {barcode_data.get('product_name', '')}",
            f"Brand / Manufacturer: {barcode_data.get('brand', '')}",
            f"Manufacturing Place: {barcode_data.get('manufacturing_places', '')}",
            f"Country of Origin: {barcode_data.get('origins', '') or barcode_data.get('countries', '')}",
            f"Net Quantity: {barcode_data.get('quantity', '')}",
        ]
        full_text = "\n".join(l for l in b_lines if l.strip())
        ocr_result["full_text"] = full_text
        ocr_result["provider"] = "open_food_facts"

    if not full_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from image or barcode lookup.")

    # ---- Compliance Evaluation ----
    compliance_report = apply_rules(full_text, _get_rules())

    if barcode_data and ocr_result.get("provider") != "open_food_facts":
        manufacturer_mismatch = detect_manufacturer_mismatch(full_text, barcode_data)
        if manufacturer_mismatch and not manufacturer_mismatch["match"]:
            mismatch_field = {
                "field_id": "barcode_brand_match",
                "field_name": "Barcode-Brand Cross-Check",
                "severity": "Critical",
                "status": "fail",
                "matched_keyword": None,
                "description": manufacturer_mismatch["mismatch_detail"],
            }
            compliance_report["fields"].append(mismatch_field)
            compliance_report["critical_failures"].append(mismatch_field)
            compliance_report["failed"] += 1
            compliance_report["overall_score"] = max(0, compliance_report["overall_score"] - 15)

    # ---- Save to Supabase ----
    missing_field_ids = [f["field_id"] for f in compliance_report["fields"] if f["status"] == "fail"]

    scan_data = {
        "user_id": user["sub"],
        "image_url": "",  # TODO: upload to Supabase Storage
        "extracted_text": full_text,
        "compliance_score": compliance_report["overall_score"],
        "missing_fields": json.dumps(missing_field_ids),
    }

    try:
        db_result = supabase.table("scans").insert(scan_data).execute()
        scan_id = db_result.data[0]["id"] if db_result.data else None
        saved = True
    except Exception:
        scan_id = None
        saved = False

    # ---- Response ----
    response = {
        "scan_id": scan_id,
        "ocr": {
            "provider": ocr_result["provider"],
            "enhanced": ocr_result.get("enhanced", False),
            "full_text": full_text,
            "extracted_entities": ocr_result.get("extracted_entities", {}),
            "detections": ocr_result["detections"],
            "average_confidence": ocr_result["average_confidence"],
        },
        "compliance": compliance_report,
        "saved": saved,
    }

    # Include barcode data if available
    if barcode_data:
        response["barcode_lookup"] = barcode_data
    if manufacturer_mismatch:
        response["manufacturer_mismatch"] = manufacturer_mismatch

    return response


# ---------------------------------------------------------------------------
# GET / — list current user's scan history
# ---------------------------------------------------------------------------
@router.get("/")
async def list_my_scans(user: dict = Depends(get_current_user)):
    """List scans for the current user."""
    result = (
        supabase.table("scans")
        .select("*")
        .eq("user_id", user["sub"])
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


# ---------------------------------------------------------------------------
# GET /{scan_id} — get a single scan by ID
# ---------------------------------------------------------------------------
@router.get("/{scan_id}")
async def get_scan(scan_id: str, user: dict = Depends(get_current_user)):
    """Get a specific scan by ID."""
    result = (
        supabase.table("scans")
        .select("*")
        .eq("id", scan_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Check ownership (unless admin/regulator)
    user_role = user.get("profile", {}).get("role")
    if user_role not in ("admin", "regulator") and result.data["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return result.data
