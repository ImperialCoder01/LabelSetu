"""
Image preprocessing pipeline for packaging OCR.
Performs safe, conservative operations:
- Bytes decoding to NumPy array
- EXIF orientation correction
- Proportional resizing if max dimension > 2000px to prevent memory exhaustion
- Returns standard BGR array expected by PaddleOCR/OpenCV
- Preserves barcode and small print fidelity without distortion.
"""
import io
import logging
from typing import Tuple, Dict, Any
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

MAX_DIMENSION_DEFAULT = 960


def decode_and_preprocess_image(
    image_bytes: bytes,
    max_dimension: int = MAX_DIMENSION_DEFAULT
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Decodes raw image bytes and performs conservative preprocessing.

    Returns:
        np_image: BGR uint8 numpy array ready for PaddleOCR inference
        meta: dictionary with original and processed dimensions, scale factor
    """
    if not image_bytes or len(image_bytes) == 0:
        raise ValueError("Empty image bytes provided.")

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        pil_image.load()
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")

    # Correct orientation based on EXIF tag (e.g. smartphone packaging photos)
    try:
        pil_image = ImageOps.exif_transpose(pil_image)
    except Exception as e:
        logger.debug(f"EXIF transpose skipped: {e}")

    # Convert to RGB mode
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    orig_w, orig_h = pil_image.size
    if orig_w == 0 or orig_h == 0:
        raise ValueError("Decoded image has 0 dimension.")

    # Check dimension constraints
    scale_factor = 1.0
    new_w, new_h = orig_w, orig_h

    if max(orig_w, orig_h) > max_dimension:
        scale_factor = max_dimension / float(max(orig_w, orig_h))
        new_w = max(1, int(round(orig_w * scale_factor)))
        new_h = max(1, int(round(orig_h * scale_factor)))
        pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        logger.info(f"Image resized from ({orig_w}x{orig_h}) to ({new_w}x{new_h}) [scale: {scale_factor:.3f}]")

    # Convert RGB PIL Image to BGR NumPy array (standard OpenCV/PaddleOCR input format)
    rgb_arr = np.array(pil_image, dtype=np.uint8)
    bgr_arr = rgb_arr[:, :, ::-1].copy()

    meta = {
        "original_dimensions": {"width": orig_w, "height": orig_h},
        "processed_dimensions": {"width": new_w, "height": new_h},
        "scale_factor": round(scale_factor, 4),
        "channels": 3
    }

    return bgr_arr, meta
