"""
Scans Router

POST  /api/scans/scan      — full pipeline: image → OCR → rules → score → save → report
                             optionally accepts barcode for Open Food Facts cross-reference
GET   /api/scans/          — list current user's scan history
GET   /api/scans/{id}      — get a single scan by ID
"""

import io
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database import supabase
from auth.dependencies import get_current_user, require_role
from services.ocr_service import extract_text_with_scores
from services.rule_engine import load_rules, apply_rules, apply_multi_image_rules
from services.barcode_service import lookup_barcode, detect_manufacturer_mismatch
from services.image_processor import analyze_image_quality, classify_image_content
from services.entity_extractor import extract_entities_with_evidence

router = APIRouter()

# Load rules once at module level
_rules = None


def _is_valid_image(data: bytes) -> bool:
    """Check file magic bytes to confirm it is an image."""
    if len(data) < 12:
        return False
    _IMAGE_SIGNATURES = [
        b"\x89PNG",            # PNG
        b"\xff\xd8\xff",      # JPEG
        b"GIF87a",             # GIF87a
        b"GIF89a",             # GIF89a
        b"RIFF",               # WebP (RIFF container)
        b"BM",                 # BMP
    ]
    for sig in _IMAGE_SIGNATURES:
        if data[: len(sig)] == sig:
            return True
    return False


def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


@router.post("/scan")
async def scan(
    file: Optional[UploadFile] = File(None, description="Single product label image"),
    files: Optional[List[UploadFile]] = File(None, description="Multiple product packaging images of the same product"),
    barcode: str = Form(default="", description="Optional barcode for Open Food Facts lookup"),
    user: dict = Depends(require_role("consumer", "brand")),
):
    """
    Upload one or multiple packaging label images (e.g. Front + Back panels)
    and/or scan a barcode to run multi-image OCR evidence aggregation, apply
    Legal Metrology rules, compute a score, save to Supabase, and return report.
    """
    barcode_clean = (barcode or "").strip()
    upload_list = []

    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)

    image_results = []
    combined_texts = []

    for idx, f in enumerate(upload_list, 1):
        if not f or not f.filename:
            continue
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {f.filename} must be an image (got {f.content_type})")

        b_bytes = await f.read()
        if len(b_bytes) > 0:
            if not _is_valid_image(b_bytes):
                raise HTTPException(status_code=400, detail=f"File {f.filename} is not a valid image format")
            if len(b_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"File {f.filename} is too large. Max 10 MB per image.")

            quality_info = analyze_image_quality(b_bytes)
            try:
                ocr_res = extract_text_with_scores(b_bytes)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"OCR failed for image {f.filename}: {exc}")

            raw_txt = ocr_res.get("full_text", "")
            classification = classify_image_content(b_bytes, raw_txt, quality_info)
            detailed_entities = extract_entities_with_evidence(raw_txt)

            if raw_txt.strip():
                combined_texts.append(raw_txt)

            image_results.append({
                "image_index": idx,
                "filename": f.filename,
                "raw_text": raw_txt,
                "quality_info": quality_info,
                "classification": classification,
                "ocr_result": ocr_res,
                "extracted_entities": ocr_res.get("extracted_entities", {}),
                "extracted_entities_detailed": detailed_entities,
            })

    if len(image_results) == 0 and not barcode_clean:
        raise HTTPException(status_code=400, detail="Please upload at least one label image or scan a barcode.")

    barcode_data = None
    manufacturer_mismatch = None

    if barcode_clean:
        barcode_data = lookup_barcode(barcode_clean)

    full_text = "\n\n".join(combined_texts)

    if not full_text and barcode_data and barcode_data.get("found"):
        b_lines = [
            f"Product Name: {barcode_data.get('product_name', '')}",
            f"Brand / Manufacturer: {barcode_data.get('brand', '')}",
            f"Manufacturing Place: {barcode_data.get('manufacturing_places', '')}",
            f"Country of Origin: {barcode_data.get('origins', '') or barcode_data.get('countries', '')}",
            f"Net Quantity: {barcode_data.get('quantity', '')}",
        ]
        synthetic_text = "\n".join(l for l in b_lines if l.strip())
        full_text = synthetic_text

        # Synthetic image result for Open Food Facts barcode
        image_results.append({
            "image_index": len(image_results) + 1,
            "filename": "Open Food Facts Barcode Catalog",
            "raw_text": synthetic_text,
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BARCODE_CATALOG", "classification": "BARCODE"},
            "extracted_entities": {},
            "extracted_entities_detailed": {},
        })

    # ---- Multi-Image Compliance Evaluation ----
    compliance_report = apply_multi_image_rules(image_results, _get_rules())

    if barcode_data and any(img["classification"].get("panel_type") != "BARCODE_CATALOG" for img in image_results):
        manufacturer_mismatch = detect_manufacturer_mismatch(full_text, barcode_data)
        if manufacturer_mismatch and not manufacturer_mismatch["match"]:
            mismatch_field = {
                "field_id": "barcode_brand_match",
                "field_name": "Barcode-Brand Cross-Check",
                "severity": "Critical",
                "status": "fail",
                "evidence_status": "CONFIRMED_MISSING",
                "matched_keyword": None,
                "description": manufacturer_mismatch["mismatch_detail"],
                "reason": "Registered barcode manufacturer does not match packaging text.",
                "score_impact": -15
            }
            compliance_report["fields"].append(mismatch_field)
            compliance_report["critical_failures"].append(mismatch_field)
            compliance_report["failed"] += 1
            compliance_report["overall_score"] = max(0, compliance_report["overall_score"] - 15)

    # Save to Supabase
    missing_field_ids = [f["field_id"] for f in compliance_report["fields"] if f["status"] == "fail"]
    scan_data = {
        "user_id": user["sub"],
        "image_url": "",
        "extracted_text": full_text[:5000],
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

    # First image or aggregated primary metadata
    primary_ocr = image_results[0]["ocr_result"] if image_results and "ocr_result" in image_results[0] else {
        "provider": "open_food_facts",
        "enhanced": False,
        "full_text": full_text,
        "extracted_entities": {},
        "extracted_entities_detailed": {},
        "detections": [],
        "average_confidence": 0.0,
    }

    response = {
        "scan_id": scan_id,
        "image_count": len(image_results),
        "ocr": primary_ocr,
        "image_details": [
            {
                "image_index": img["image_index"],
                "filename": img["filename"],
                "quality_info": img["quality_info"],
                "classification": img["classification"],
                "raw_text": img["raw_text"],
                "extracted_entities": img["extracted_entities"],
            }
            for img in image_results
        ],
        "quality_info": image_results[0]["quality_info"] if image_results else {"quality_status": "GOOD"},
        "classification": image_results[0]["classification"] if image_results else {"classification": "PRODUCT_LABEL"},
        "compliance": compliance_report,
        "saved": saved,
    }

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
