"""
Standalone Local PaddleOCR FastAPI Microservice.
Exposes:
- GET  /health: System and model status
- GET  /ready:  Readiness probe
- POST /ocr:    Extract text lines with coordinates and confidence
"""
import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Header, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np

from preprocessing import decode_and_preprocess_image
from ocr_engine import PaddleOCREngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("local_ocr_server")

# Environment Configuration
SERVER_START_TIME = time.time()
LOCAL_OCR_API_KEY = os.environ.get("LOCAL_OCR_API_KEY", "").strip()
OCR_LANG = os.environ.get("OCR_LANG", "hi").strip()
MAX_IMAGE_SIZE_MB = int(os.environ.get("MAX_IMAGE_SIZE_MB", 15))
MAX_IMAGE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
MAX_IMAGE_DIMENSION = int(os.environ.get("MAX_IMAGE_DIMENSION", 960))

ocr_engine_instance: Optional[PaddleOCREngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: loads and warms up OCR engine at server startup."""
    global ocr_engine_instance
    logger.info(f"Initializing PaddleOCR Engine at startup (lang='{OCR_LANG}')...")
    start_init = time.perf_counter()
    ocr_engine_instance = PaddleOCREngine.get_instance(lang=OCR_LANG)
    
    # Warm up model with small synthetic array to ensure weights are primed
    try:
        dummy_img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        ocr_engine_instance.extract_text(dummy_img)
        init_duration = time.perf_counter() - start_init
        logger.info(f"PaddleOCR Engine loaded and warmed up in {init_duration:.2f}s")
    except Exception as e:
        logger.warning(f"Engine warmup encountered a non-fatal warning: {e}")

    yield
    logger.info("Shutting down PaddleOCR Server.")


app = FastAPI(
    title="LabelSetu Local PaddleOCR Service",
    description="Standalone, local-only OCR microservice supporting packaging text in Hindi and English.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration: allow local frontend / backend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health status check returning engine readiness, device, versions, and uptime."""
    ready = ocr_engine_instance is not None and ocr_engine_instance.is_ready
    info = ocr_engine_instance.get_engine_info() if ready else {}
    return {
        "status": "ok",
        "service": "paddleocr_local",
        "engine_ready": ready,
        "device": info.get("device", "cpu"),
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "versions": {
            "paddleocr": info.get("paddleocr_version", "unknown"),
            "paddlepaddle": info.get("paddle_version", "unknown"),
        },
        "auth_enabled": bool(LOCAL_OCR_API_KEY)
    }


@app.get("/ready")
def readiness_check():
    """Readiness probe for orchestrators and health monitors."""
    if ocr_engine_instance is not None and ocr_engine_instance.is_ready:
        return {"ready": True, "message": "OCR engine initialized and warm."}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ready": False, "message": "OCR engine is not yet ready."}
    )


@app.post("/ocr")
def process_ocr(
    file: UploadFile = File(..., description="Package label image (PNG, JPEG, WEBP, BMP)"),
    lang: Optional[str] = Form(None, description="Optional OCR language override (defaults to server config)"),
    x_local_ocr_key: Optional[str] = Header(None, alias="X-Local-OCR-Key")
):
    """
    Accepts multipart/form-data image upload and returns structured, normalized OCR results.
    """
    # 1. Authentication Check (if LOCAL_OCR_API_KEY is configured)
    if LOCAL_OCR_API_KEY:
        if not x_local_ocr_key or x_local_ocr_key != LOCAL_OCR_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-Local-OCR-Key header"
            )

    # 2. Engine readiness check
    if ocr_engine_instance is None or not ocr_engine_instance.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR Engine is not ready"
        )

    # 3. Read and validate file content
    start_time = time.perf_counter()
    image_bytes = file.file.read()

    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size exceeds maximum limit of {MAX_IMAGE_SIZE_MB}MB"
        )

    # 4. Conservative preprocessing & decoding
    try:
        np_image, meta = decode_and_preprocess_image(
            image_bytes,
            max_dimension=MAX_IMAGE_DIMENSION
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Image preprocessing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}"
        )

    # 5. Inference
    try:
        ocr_result = ocr_engine_instance.extract_text(
            np_image,
            scale_factor=meta["scale_factor"],
            orig_dimensions=meta["original_dimensions"]
        )
    except Exception as e:
        logger.error(f"OCR Inference error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Inference failed: {str(e)}"
        )

    processing_time_ms = int(round((time.perf_counter() - start_time) * 1000))

    # 6. Structured LabelSetu Normalized Response
    response_payload = {
        "provider": "paddleocr_local",
        "success": True,
        "processing_time_ms": processing_time_ms,
        "raw_text": ocr_result["raw_text"],
        "lines": ocr_result["lines"],
        "languages_detected": ocr_result["languages_detected"],
        "metadata": {
            "engine_version": ocr_result["metadata"]["engine_version"],
            "model_name": ocr_result["metadata"]["model_name"],
            "device": ocr_result["metadata"]["device"],
            "image_dimensions": ocr_result["metadata"]["image_dimensions"],
            "total_lines": ocr_result["metadata"]["total_lines_detected"],
            "scale_factor_applied": meta["scale_factor"]
        }
    }

    return response_payload


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8001))
    logger.info(f"Starting Local PaddleOCR Server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
