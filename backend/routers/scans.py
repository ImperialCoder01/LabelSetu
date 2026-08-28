"""
Scans Router — POST /api/scans/scan, GET /api/scans/, GET /api/scans/{id}

Handles multi-image label uploads, barcode cross-referencing,
deterministic Legal Metrology rule engine evaluation, parallelized
Groq AI analysis and external product research, and persistence to Supabase.
"""

import asyncio
import json
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

logger = logging.getLogger(__name__)
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
    user: dict = Depends(require_role("consumer", "brand", "regulator", "admin")),
):
    """
    Multi-image scan pipeline with parallelized AI & external research execution.
    """
    t_start = time.perf_counter()
    user_role = user.get("profile", {}).get("role", "consumer")
    logger.info("[SCAN] request started (user_id=%s, role=%s)", user.get("sub"), user_role)

    upload_list = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    logger.info("[SCAN] received %d images", len(upload_list))

    barcode_clean = barcode.strip() if barcode else None
    if barcode_clean and len(barcode_clean) > 64:
        raise HTTPException(
            status_code=400,
            detail="Barcode string is too long. Standard barcodes are 8 to 14 digits (max 64 characters).",
        )

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
                logger.error("[OCR] unexpected OCR extraction error for %s: %s", f.filename, exc)
                ocr_res = {"provider": "unavailable", "full_text": "", "detections": [], "average_confidence": 0.0}

            raw_txt = ocr_res.get("full_text", "")
            norm_txt = ocr_res.get("normalized_full_text", raw_txt)
            classification = classify_image_content(b_bytes, raw_txt, quality_info)
            detailed_entities = extract_entities_with_evidence(raw_txt, norm_txt)

            logger.info("[OCR] image %d completed (chars=%d, provider=%s)", idx, len(raw_txt), ocr_res.get("provider"))

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
            del b_bytes

    import gc
    gc.collect()

    t_ocr_ms = round((time.perf_counter() - t_ocr_start) * 1000, 2)
    logger.info("[SCAN] OCR completed (%sms, combined_length=%d)", t_ocr_ms, len(full_text) if 'full_text' in locals() else len(combined_texts))

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

    # Aggregate entities across all uploaded images without overwriting valid data with nulls
    aggregated_entities = {}
    aggregated_entities_detailed = {}
    for img in image_results:
        for k, v in img.get("extracted_entities", {}).items():
            if v is not None and not aggregated_entities.get(k):
                aggregated_entities[k] = v
        for k, v_dict in img.get("extracted_entities_detailed", {}).items():
            if v_dict and v_dict.get("value") is not None and not aggregated_entities_detailed.get(k, {}).get("value"):
                aggregated_entities_detailed[k] = v_dict

    detected_product_name = aggregated_entities.get("product_name")
    detected_brand = aggregated_entities.get("brand")

    # Propagate detected product_name and brand into classification dictionaries
    for img in image_results:
        if detected_product_name:
            img["classification"]["product_name"] = detected_product_name
        if detected_brand:
            img["classification"]["brand"] = detected_brand

    # Attach aggregated entities to primary_ocr
    if image_results and "ocr_result" in image_results[0]:
        primary_ocr = image_results[0]["ocr_result"]
        primary_ocr["extracted_entities"] = aggregated_entities
        primary_ocr["extracted_entities_detailed"] = aggregated_entities_detailed
    else:
        primary_ocr = {
            "provider": "open_food_facts",
            "enhanced": False,
            "full_text": full_text,
            "extracted_entities": aggregated_entities,
            "extracted_entities_detailed": aggregated_entities_detailed,
            "detections": [],
            "average_confidence": 0.0,
        }

    # ---- Save to Supabase Database ----
    t_db_start = time.perf_counter()
    missing_field_ids = [f["field_id"] for f in compliance_report["fields"] if f["status"] == "fail"]

    # Ensure user profile exists for foreign key constraint
    try:
        supabase.table("users_profile").upsert({
            "id": user["sub"],
            "role": user.get("profile", {}).get("role") or user.get("role", "consumer"),
            "status": "active"
        }, on_conflict="id").execute()
    except Exception as up_err:
        logger.debug("users_profile ensure check: %s", up_err)

    resolved_product_name = (
        detected_product_name
        or (barcode_data.get("product_name") if barcode_data else "")
        or "Product Packaging"
    )
    resolved_brand = (
        detected_brand
        or (barcode_data.get("brand") if barcode_data else "")
        or ""
    )
    resolved_barcode = barcode_clean or (barcode_data.get("barcode") if barcode_data else "") or ""

    scan_data = {
        "user_id": user["sub"],
        "image_url": "",
        "extracted_text": full_text[:5000],
        "compliance_score": compliance_report["overall_score"] if compliance_report["overall_score"] is not None else 0,
        "missing_fields": missing_field_ids,
        "product_name": resolved_product_name,
        "brand": resolved_brand,
        "barcode": resolved_barcode,
        "metadata": {
            "status": compliance_report.get("status", "unknown"),
            "passed_declarations": compliance_report.get("passed_declarations", 0),
            "failed_declarations": compliance_report.get("failed_declarations", 0),
            "found_fields": compliance_report.get("found_fields", []),
            "user_role": user_role,
            "image_count": len(image_results),
        }
    }

    try:
        db_result = supabase.table("scans").insert(scan_data).execute()
        scan_id = db_result.data[0]["id"] if db_result.data else None
        saved = True
        logger.info("[SCAN] Saved scan to DB with ID: %s", scan_id)
    except Exception as db_exc:
        logger.warning("[SCAN] Failed to save scan to database: %s", db_exc)
        # Fallback to basic columns if custom columns encounter any issue
        try:
            fallback_data = {
                "user_id": user["sub"],
                "image_url": "",
                "extracted_text": full_text[:5000],
                "compliance_score": compliance_report["overall_score"] if compliance_report["overall_score"] is not None else 0,
                "missing_fields": json.dumps(missing_field_ids),
            }
            db_result = supabase.table("scans").insert(fallback_data).execute()
            scan_id = db_result.data[0]["id"] if db_result.data else None
            saved = True
        except Exception:
            scan_id = None
            saved = False

    t_db_ms = round((time.perf_counter() - t_db_start) * 1000, 2)
    t_total_ms = round((time.perf_counter() - t_start) * 1000, 2)

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
# GET / — list scan history for current user or all scans for regulators/admins
# ---------------------------------------------------------------------------
@router.get("/")
async def list_my_scans(
    all: bool = False,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(get_current_user),
):
    """List scans for the current user or ecosystem scans for regulators/admins."""
    role = user.get("profile", {}).get("role") or user.get("role", "consumer")
    try:
        query = supabase.table("scans").select("*, users_profile!scans_user_id_fkey(full_name, role)")
        if not all or role not in ("admin", "regulator"):
            query = query.eq("user_id", user["sub"])

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []
    except Exception as exc:
        logger.error("Failed to list scans: %s", exc)
        # Fallback without join in case of relationship cache issues
        try:
            query = supabase.table("scans").select("*")
            if not all or role not in ("admin", "regulator"):
                query = query.eq("user_id", user["sub"])
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception:
            return []


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
