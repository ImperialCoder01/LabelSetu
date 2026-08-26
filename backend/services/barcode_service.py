"""
Barcode Lookup Service — queries Open Food Facts for product details.

Given a barcode (EAN/UPC), fetches product metadata including:
  - product_name, brands, manufacturing_places, origins, categories
  - ingredients_text, labels, countries

Used to cross-reference OCR-extracted label text against registered
product data and flag manufacturer-name mismatches.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_FIELDS = (
    "product_name,brands,brands_tags,"
    "manufacturing_places,origins,categories,"
    "countries,ingredients_text,labels,"
    "quantity,stores,nutrition_grades"
)


def lookup_barcode(barcode: str) -> dict | None:
    """
    Look up a product barcode on Open Food Facts.

    Returns:
        Normalized dict with product info, or None if not found.

        {
          "barcode": "5449000000996",
          "product_name": "Coca-Cola",
          "brand": "Coca-Cola",
          "manufacturing_places": "atlanta, georgia, united-states",
          "origins": "United Kingdom",
          "categories": "Colas, ...",
          "countries": "...",
          "ingredients_text": "...",
          "labels": "...",
          "quantity": "...",
          "found": True
        }
    """
    url = OFF_API_URL.format(barcode=barcode)
    params = {"fields": OFF_FIELDS}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()

        data = resp.json()

        if data.get("status") != 1 or not data.get("product"):
            logger.info("Open Food Facts: barcode %s not found", barcode)
            return None

        product = data["product"]

        return {
            "barcode": barcode,
            "product_name": product.get("product_name") or "",
            "brand": product.get("brands") or "",
            "brand_tags": product.get("brands_tags") or [],
            "manufacturing_places": product.get("manufacturing_places") or "",
            "origins": product.get("origins") or "",
            "categories": product.get("categories") or "",
            "countries": product.get("countries") or "",
            "ingredients_text": product.get("ingredients_text") or "",
            "labels": product.get("labels") or "",
            "quantity": product.get("quantity") or "",
            "found": True,
        }

    except httpx.HTTPStatusError as exc:
        logger.warning("Open Food Facts HTTP %s for barcode %s", exc.response.status_code, barcode)
        return None
    except Exception as exc:
        logger.error("Open Food Facts lookup failed for %s: %s", barcode, exc)
        return None


def detect_manufacturer_mismatch(ocr_text: str, off_data: dict) -> dict | None:
    """
    Compare OCR-extracted text against Open Food Facts brand/manufacturer
    data to detect potential mismatches.

    Returns:
        {
          "match": True | False,
          "off_brand": "...",
          "ocr_brand_fragments": [...],
          "mismatch_detail": "..."  # only if mismatch
        }
        or None if off_data is empty / no comparison possible.
    """
    if not off_data or not off_data.get("found"):
        return None

    off_brand = (off_data.get("brand") or "").strip()
    if not off_brand:
        return None

    text_lower = ocr_text.lower()

    # Extract the primary brand name (first comma-separated entry)
    primary_brand = off_brand.split(",")[0].strip().lower()

    # Check if brand or its tags appear in OCR text
    brand_tags = [t.lower() for t in (off_data.get("brand_tags") or [])]

    found_in_ocr = primary_brand in text_lower or any(tag in text_lower for tag in brand_tags)

    if found_in_ocr:
        return {"match": True, "off_brand": off_brand, "ocr_brand_fragments": [], "mismatch_detail": None}

    # Collect what brand-like fragments ARE in OCR text (simple heuristic)
    return {
        "match": False,
        "off_brand": off_brand,
        "ocr_brand_fragments": [],
        "mismatch_detail": (
            f"Registered brand '{off_brand}' was NOT found in OCR text. "
            "This may indicate a label-brand mismatch or tampering."
        ),
    }
