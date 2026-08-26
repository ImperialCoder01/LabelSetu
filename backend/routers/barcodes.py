"""
Barcodes Router

POST /api/barcodes/lookup   — look up a barcode on Open Food Facts
"""

import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.dependencies import get_current_user
from services.barcode_service import lookup_barcode

router = APIRouter()

# Barcode format: 8 or 13 digits (EAN-8, EAN-13, UPC-A, UPC-E)
BARCODE_RE = re.compile(r"^\d{8,13}$")


class BarcodeLookupRequest(BaseModel):
    barcode: str


class BarcodeLookupResponse(BaseModel):
    barcode: str
    found: bool
    product_name: str = ""
    brand: str = ""
    brand_tags: list[str] = []
    manufacturing_places: str = ""
    origins: str = ""
    categories: str = ""
    countries: str = ""
    ingredients_text: str = ""
    labels: str = ""
    quantity: str = ""


@router.post("/lookup", response_model=BarcodeLookupResponse)
async def barcode_lookup(
    body: BarcodeLookupRequest,
    user: dict = Depends(get_current_user),
):
    """
    Look up a product barcode on Open Food Facts and return
    registered product/manufacturer details.

    The barcode must be 8-13 digits (EAN-8, EAN-13, UPC-A, UPC-E).
    """
    barcode = body.barcode.strip()

    if not BARCODE_RE.match(barcode):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid barcode format: '{barcode}'. Expected 8-13 digits.",
        )

    result = lookup_barcode(barcode)

    if result is None:
        return BarcodeLookupResponse(barcode=barcode, found=False)

    return BarcodeLookupResponse(
        barcode=result["barcode"],
        found=True,
        product_name=result["product_name"],
        brand=result["brand"],
        brand_tags=result["brand_tags"],
        manufacturing_places=result["manufacturing_places"],
        origins=result["origins"],
        categories=result["categories"],
        countries=result["countries"],
        ingredients_text=result["ingredients_text"],
        labels=result["labels"],
        quantity=result["quantity"],
    )
