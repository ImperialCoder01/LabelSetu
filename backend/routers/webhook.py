"""
Webhook Router — marketplace integration stub.

POST /api/webhook/marketplace-check — accept a product listing JSON
     and return a compliance score based on Legal Metrology rules.

This endpoint is designed for marketplace platforms (e.g. Amazon, Flipkart,
Meesho) to verify product label compliance before listing approval.

Authentication:
    In production this endpoint should be protected by a shared API key
    (X-Webhook-Secret header). For now the endpoint is open for
    prototyping — guard it before going to production.
"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.rule_engine import load_rules, apply_rules

router = APIRouter()

_rules = None


def _get_rules() -> dict:
    global _rules
    if _rules is None:
        _rules = load_rules()
    return _rules


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ProductListing(BaseModel):
    """
    A product listing submitted by a marketplace partner.

    All text fields are optional — the more you provide, the more
    accurately the compliance engine can evaluate the label.
    """
    product_name: str = Field(
        "",
        description="Product / commodity name as it appears on the label",
        examples=["Tata Salt Iodised Salt"],
    )
    manufacturer_name: str = Field(
        "",
        description="Manufacturer, packer, or importer name",
        examples=["Tata Chemicals Ltd"],
    )
    manufacturer_address: str = Field(
        "",
        description="Manufacturer address",
        examples=["Mumbai, Maharashtra, India"],
    )
    net_quantity: str = Field(
        "",
        description="Net quantity with unit (e.g. '500 g', '1 L')",
        examples=["500 g"],
    )
    manufacturing_date: str = Field(
        "",
        description="Date of manufacturing (any human-readable format)",
        examples=["2025-06-15", "15/06/2025", "Jun 2025"],
    )
    mrp: str = Field(
        "",
        description="Maximum retail price inclusive of taxes",
        examples=["₹45.00", "Rs. 45"],
    )
    consumer_care_contact: str = Field(
        "",
        description="Consumer care phone/email/helpline",
        examples=["1800-123-4567", "care@tata.com"],
    )
    unit_sale_price: str = Field(
        "",
        description="Price per unit (per kg, litre, etc.)",
        examples=["₹90/kg"],
    )
    country_of_origin: str = Field(
        "",
        description="Country of origin",
        examples=["India"],
    )
    extra_text: str = Field(
        "",
        description=(
            "Any additional label text to include in evaluation. "
            "Useful when the listing contains a full OCR dump."
        ),
        examples=["Manufactured by: Tata Chemicals Ltd, Mumbai"],
    )


class FieldResult(BaseModel):
    field_id: str
    field_name: str
    status: str
    severity: str
    description: str
    matched_keyword: str | None = None


class MarketplaceCheckResponse(BaseModel):
    """
    Compliance check result for a marketplace product listing.
    """
    marketplace_id: str = Field(
        description="Unique ID for this check (for audit trail)",
        examples=["chk_a1b2c3d4"],
    )
    overall_score: int = Field(
        ge=0,
        le=100,
        description="Weighted compliance score (0-100). "
                    "Scores >= 80 are considered compliant.",
        examples=[85],
    )
    status: str = Field(
        description="Human-readable status: compliant, partial, or non_compliant",
        examples=["compliant"],
    )
    passed_fields: int = Field(description="Number of fields that passed")
    failed_fields: int = Field(description="Number of fields that failed")
    total_fields: int = Field(description="Total fields evaluated")
    field_results: list[FieldResult] = Field(
        description="Per-field pass/fail details"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking warnings (e.g. minor field missing)",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Blocking errors (e.g. critical field missing)",
    )
    listing_approved: bool = Field(
        description="Recommendation: true if score >= 80, false otherwise",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _listing_to_text(listing: ProductListing) -> str:
    """Flatten product listing fields into a single text blob for the rule engine."""
    parts = []
    for field in [
        "product_name",
        "manufacturer_name",
        "manufacturer_address",
        "net_quantity",
        "manufacturing_date",
        "mrp",
        "consumer_care_contact",
        "unit_sale_price",
        "country_of_origin",
    ]:
        val = getattr(listing, field, "").strip()
        if val:
            parts.append(val)
    if listing.extra_text.strip():
        parts.append(listing.extra_text.strip())
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post(
    "/marketplace-check",
    response_model=MarketplaceCheckResponse,
    summary="Marketplace product compliance check",
    description=(
        "Submit a product listing and receive a compliance score "
        "against India's Legal Metrology (Packaged Commodities) Rules.\n\n"
        "**Use case**: Marketplace platforms call this endpoint before "
        "approving a product listing to ensure the label meets mandatory "
        "declaration requirements.\n\n"
        "**Scoring**:\n"
        "- Base score: 100\n"
        "- Each missing **Critical** field: −15 points\n"
        "- Each missing **Minor** field: −5 points\n"
        "- Score >= 80 → compliant (listing approved)\n"
        "- Score 50–79 → partial (review needed)\n"
        "- Score < 50 → non-compliant (listing rejected)"
    ),
    tags=["Webhook"],
)
async def marketplace_check(listing: ProductListing):
    """
    Evaluate a product listing against Legal Metrology compliance rules.

    **Example request**:
    ```json
    {
      "product_name": "Tata Salt Iodised Salt",
      "manufacturer_name": "Tata Chemicals Ltd",
      "manufacturer_address": "Mumbai, Maharashtra",
      "net_quantity": "1 kg",
      "manufacturing_date": "2025-06-15",
      "mrp": "₹28.00",
      "consumer_care_contact": "1800-200-2222",
      "country_of_origin": "India"
    }
    ```

    **Example response**:
    ```json
    {
      "marketplace_id": "chk_a1b2c3d4",
      "overall_score": 95,
      "status": "compliant",
      "passed_fields": 7,
      "failed_fields": 1,
      "total_fields": 8,
      "listing_approved": true
    }
    ```
    """
    # Build text for rule engine
    text = _listing_to_text(listing)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="At least one product field must be provided",
        )

    # Run compliance rules
    report = apply_rules(text, _get_rules())

    # Classify errors / warnings
    errors = []
    warnings = []
    for f in report.get("fields", []):
        msg = f"{f['field_name']}: {f['description']}"
        if f["status"] == "fail" and f.get("severity") == "Critical":
            errors.append(msg)
        elif f["status"] == "fail":
            warnings.append(msg)

    score = report["overall_score"]
    if score >= 80:
        status = "compliant"
    elif score >= 50:
        status = "partial"
    else:
        status = "non_compliant"

    return MarketplaceCheckResponse(
        marketplace_id=f"chk_{uuid.uuid4().hex[:12]}",
        overall_score=score,
        status=status,
        passed_fields=report["passed"],
        failed_fields=report["failed"],
        total_fields=report["total_fields"],
        field_results=[
            FieldResult(
                field_id=f["field_id"],
                field_name=f["field_name"],
                status=f["status"],
                severity=f.get("severity", ""),
                description=f.get("description", ""),
                matched_keyword=f.get("matched_keyword"),
            )
            for f in report.get("fields", [])
        ],
        warnings=warnings,
        errors=errors,
        listing_approved=score >= 80,
    )
