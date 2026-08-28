"""
Scans Router — POST /api/scans/scan, GET /api/scans/, GET /api/scans/{id}

Handles multi-image label uploads, barcode cross-referencing,
deterministic Legal Metrology rule engine evaluation, parallelized
Groq AI analysis and external product research, and persistence to Supabase.
"""

import asyncio
import json
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from auth.dependencies import get_current_user, require_role
from database import supabase
from services.ai_service import analyze_label_with_groq
from services.barcode_service import lookup_barcode, detect_manufacturer_mismatch
from services.entity_extractor import extract_entities_with_evidence
from services.image_processor import analyze_image_quality, classify_image_content
from services.ocr_service import extract_text_with_scores
from services.product_research_service import research_product_information
from services.rule_engine import load_rules, apply_multi_image_rules

router = APIRouter()

# Magic bytes for common image formats
_IMAGE_SIGNATURES = [
    bytes([0x89, 0x50, 0x4E, 0x47]),  # PNG
    bytes([0xFF, 0xD8, 0xFF]),        # JPEG
    b"GIF87a",        # GIF87a
    b"GIF89a",        # GIF89a
    b"RIFF",          # WebP (RIFF container)
    b"BM",            # BMP
]

# Cached in-memory rules reference
_RULES_CACHE = None


def _get_rules():
    global _RULES_CACHE
    if _RULES_CACHE is None:
        _RULES_CACHE = load_rules()
    return _RULES_CACHE


def _is_valid_image(data: bytes) -> bool:
    """Check file magic bytes to confirm it is an image."""
    if len(data) < 12:
        return False
    for sig in _IMAGE_SIGNATURES:
        if data[: len(sig)] == sig:
            return True
    return False


# ---------------------------------------------------------------------------
# POST /scan — Multi-image label upload + Barcode + Compliance check + Groq + Research
# ---------------------------------------------------------------------------
@router.post("/scan")
async def scan(
    files: Optional[List[UploadFile]] = File(None, description="1 to 5 product label images"),
    file: Optional[UploadFile] = File(None, description="Single product label image (legacy single-file support)"),
    barcode: Optional[str] = Form(None, description="Barcode/GTIN number if scanned"),
    user: dict = Depends(require_role("consumer", "brand")),
):
    """
    Multi-image scan pipeline with parallelized AI & external research execution.
    """
    t_start = time.perf_counter()
    upload_list = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    barcode_clean = barcode.strip() if barcode else None

    if len(upload_list) == 0 and not barcode_clean:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one product label image or a barcode number.",
        )

    if len(upload_list) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 images allowed per scan.",
        )

    # ---- Image Processing & OCR ----
    t_ocr_start = time.perf_counter()
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
            norm_txt = ocr_res.get("normalized_full_text", raw_txt)
            classification = classify_image_content(b_bytes, raw_txt, quality_info)
            detailed_entities = extract_entities_with_evidence(raw_txt, norm_txt)

            if raw_txt.strip():
                combined_texts.append(raw_txt)

            image_results.append({
                "image_index": idx,
                "filename": f.filename,
                "raw_text": raw_txt,
                "normalized_text": norm_txt,
                "quality_info": quality_info,
                "classification": classification,
                "ocr_result": ocr_res,
                "extracted_entities": ocr_res.get("extracted_entities", {}),
                "extracted_entities_detailed": detailed_entities,
            })

    t_ocr_ms = round((time.perf_counter() - t_ocr_start) * 1000, 2)

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

        image_results.append({
            "image_index": len(image_results) + 1,
            "filename": "Open Food Facts Barcode Catalog",
            "raw_text": synthetic_text,
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BARCODE_CATALOG", "classification": "BARCODE"},
            "extracted_entities": {},
            "extracted_entities_detailed": {},
        })

    # ---- Authoritative Deterministic Compliance Evaluation ----
    t_rules_start = time.perf_counter()
    compliance_report = apply_multi_image_rules(image_results, _get_rules())
    t_rules_ms = round((time.perf_counter() - t_rules_start) * 1000, 2)

    if barcode_data and any(img["classification"].get("panel_type") != "BARCODE_CATALOG" for img in image_results):
        manufacturer_mismatch = detect_manufacturer_mismatch(full_text, barcode_data)
        # CRITICAL SAFETY: External barcode/catalog mismatches generate warning flags ONLY.
        # They do NOT alter the deterministic statutory compliance score.

    # ---- Parallel Execution: Supplementary Groq AI + External Product Research ----
    t_parallel_start = time.perf_counter()
    loop = asyncio.get_running_loop()

    async def _run_ai_analysis():
        if not full_text.strip():
            return {
                "available": False,
                "status": "no_text",
                "provider": "groq",
                "message": "No OCR text detected for AI analysis.",
            }
        try:
            return await loop.run_in_executor(
                None,
                lambda: analyze_label_with_groq(
                    ocr_text=full_text,
                    extracted_entities=image_results[0].get("extracted_entities") if image_results else {},
                    rules_summary=compliance_report,
                )
            )
        except Exception as exc:
            return {
                "available": False,
                "status": "error",
                "provider": "groq",
                "message": f"AI analysis temporarily unavailable ({exc}).",
            }

    async def _run_product_research():
        try:
            return await loop.run_in_executor(
                None,
                lambda: research_product_information(
                    ocr_text=full_text,
                    extracted_entities=image_results[0].get("extracted_entities") if image_results else {},
                    missing_fields=compliance_report.get("fields", []),
                    barcode=barcode_clean,
                )
            )
        except Exception as exc:
            return {
                "status": "unavailable",
                "message": "External product research temporarily unavailable.",
                "product_match": {"status": "unavailable", "confidence": 0.0},
                "sources": [],
                "fields": [],
                "recommended_photos": [],
                "warnings": ["External product lookup could not be completed."],
            }

    ai_analysis, external_research = await asyncio.gather(_run_ai_analysis(), _run_product_research())
    t_parallel_ms = round((time.perf_counter() - t_parallel_start) * 1000, 2)

    # ---- Save to Supabase Database ----
    t_db_start = time.perf_counter()
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

    t_db_ms = round((time.perf_counter() - t_db_start) * 1000, 2)
    t_total_ms = round((time.perf_counter() - t_start) * 1000, 2)

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
        "ai_analysis": ai_analysis,
        "external_research": external_research,
        "saved": saved,
        "_performance": {
            "total_ms": t_total_ms,
            "ocr_ms": t_ocr_ms,
            "rules_ms": t_rules_ms,
            "parallel_tasks_ms": t_parallel_ms,
            "db_ms": t_db_ms,
            "concurrent_tasks": ["groq_ai", "product_research"],
        },
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

    user_role = user.get("profile", {}).get("role")
    if user_role not in ("admin", "regulator") and result.data["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return result.data
