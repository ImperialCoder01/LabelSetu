"""
OCR Router — POST /extract, GET /usage

Accepts an image upload, runs it through the configured OCR provider
(OCR.space cloud engine), and returns the raw extracted text
along with per-detection confidence scores.

When OCR_PROVIDER=cloud, every successful /extract call increments
the api_usage_log table for the current month.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from auth.dependencies import get_current_user, require_role
from config import settings
from database import supabase
from services.ocr_service import extract_text_with_scores

router = APIRouter()

OCR_QUOTA_LIMIT = 25_000  # OCR.space free-tier monthly limit

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


class Detection(BaseModel):
    text: str
    confidence: float
    bbox: list | None = None


class ExtractResponse(BaseModel):
    provider: str
    full_text: str
    detections: list[Detection]
    average_confidence: float


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    file: UploadFile = File(..., description="Image file (PNG / JPEG) to OCR"),
    user: dict = Depends(get_current_user),
):
    """
    Upload an image and get back the raw OCR text plus per-detection
    confidence scores and bounding boxes.

    **Request**: multipart/form-data with a single `file` field.

    **Response**:
    ```json
    {
      "provider": "local",
      "full_text": "Tata Salt Iodised Salt Net Wt 1 kg",
      "detections": [
        {"text": "Tata", "confidence": 0.9876, "bbox": [[12, 14], [60, 14], [60, 36], [12, 36]]},
        ...
      ],
      "average_confidence": 0.9521
    }
    ```
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image (got {file.content_type})",
        )

    # Read file bytes
    image_bytes = await file.read()

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Magic-byte validation
    if not _is_valid_image(image_bytes):
        raise HTTPException(status_code=400, detail="File is not a valid image")

    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10 MB.",
        )

    # Run OCR
    try:
        result = extract_text_with_scores(image_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    # Increment API usage when using cloud provider
    if settings.OCR_PROVIDER.lower() == "cloud":
        _increment_api_usage(result["provider"])

    # Return structured response
    return ExtractResponse(
        provider=result["provider"],
        full_text=result["full_text"],
        detections=[Detection(**d) for d in result["detections"]],
        average_confidence=result["average_confidence"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_month() -> str:
    """Return the current month in YYYY-MM format."""
    return datetime.utcnow().strftime("%Y-%m")


def _increment_api_usage(provider: str) -> None:
    """Increment the request_count for the current month (upsert)."""
    month = _current_month()
    try:
        # Try to fetch existing row
        existing = (
            supabase.table("api_usage_log")
            .select("id, request_count")
            .eq("provider", provider)
            .eq("month", month)
            .limit(1)
            .execute()
        )
        if existing.data:
            row = existing.data[0]
            supabase.table("api_usage_log").update(
                {"request_count": row["request_count"] + 1}
            ).eq("id", row["id"]).execute()
        else:
            supabase.table("api_usage_log").insert(
                {"provider": provider, "month": month, "request_count": 1}
            ).execute()
    except Exception:
        pass  # best-effort — don't fail the OCR response if the log write fails


# ---------------------------------------------------------------------------
# Usage endpoint
# ---------------------------------------------------------------------------
from services.ai_service import is_groq_available, GROQ_MODEL


class UsageResponse(BaseModel):
    provider: str
    month: str
    request_count: int
    quota_limit: int
    usage_percent: float
    warning: bool
    groq_available: bool = True
    groq_model: str = "openai/gpt-oss-20b"
    external_research_enabled: bool = True


@router.get("/usage", response_model=UsageResponse)
async def get_usage(admin: dict = Depends(require_role("admin"))):
    """
    Return the current month's OCR API usage stats.

    - **provider**: the active OCR provider (local or cloud)
    - **month**: YYYY-MM string
    - **request_count**: requests logged this month (0 if none)
    - **quota_limit**: 25 000 (OCR.space free tier)
    - **usage_percent**: request_count / quota_limit × 100
    - **warning**: true when usage exceeds 80 %
    """
    provider = settings.OCR_PROVIDER.lower()
    month = _current_month()
    request_count = 0

    if provider == "cloud":
        try:
            result = (
                supabase.table("api_usage_log")
                .select("request_count")
                .eq("provider", "cloud")
                .eq("month", month)
                .limit(1)
                .execute()
            )
            if result.data:
                request_count = result.data[0]["request_count"] or 0
        except Exception:
            pass

    usage_percent = round((request_count / OCR_QUOTA_LIMIT) * 100, 2) if OCR_QUOTA_LIMIT else 0

    groq_active = is_groq_available()
    return UsageResponse(
        provider=provider,
        month=month,
        request_count=request_count,
        quota_limit=OCR_QUOTA_LIMIT,
        usage_percent=usage_percent,
        warning=usage_percent > 80,
        groq_available=groq_active,
        groq_model=GROQ_MODEL if groq_active else "None",
        external_research_enabled=True,
    )
