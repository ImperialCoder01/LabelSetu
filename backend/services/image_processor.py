"""
Image Preprocessing Engine — OpenCV enhancement pipeline for package label photos.

Applies contrast equalization (CLAHE), adaptive thresholding, edge sharpening,
and auto-deskew to clean real-world noisy packaging photos before OCR extraction.
"""

import cv2
import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def auto_deskew(image: np.ndarray) -> np.ndarray:
    """Detect text line angle and auto-rotate image to straighten skewed text."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        # Invert colors so text is white on black background
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Find coordinates of all non-zero pixels
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Only rotate if skew is noticeable (> 0.5 degrees and < 45 degrees)
        if abs(angle) > 0.5 and abs(angle) < 45:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
    except Exception as exc:
        logger.warning("Deskew failed, returning original image: %s", exc)
    
    return image


def enhance_image_for_ocr(image_bytes: bytes) -> Tuple[bytes, bool]:
    """
    Enhance raw package photo bytes for maximum OCR text detection accuracy.

    Pipeline:
    1. Decode raw bytes to BGR image matrix
    2. Auto-deskew orientation
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Unsharp Masking / Laplacian sharpening for small fonts (MRP, Mfg Date)
    5. Encode back to PNG bytes

    Returns:
        Tuple of (enhanced_image_bytes, was_enhanced_boolean)
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, False

        # Step 1: Auto Deskew
        img = auto_deskew(img)

        # Step 2: Convert to LAB color space and apply CLAHE to L channel
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # Step 3: Unsharp mask sharpening to sharpen small package fonts
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3.0)
        sharpened = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)

        # Step 4: Encode to PNG bytes
        success, encoded_img = cv2.imencode(".png", sharpened)
        if success:
            return encoded_img.tobytes(), True

    except Exception as exc:
        logger.error("Image preprocessing error: %s", exc)

    return image_bytes, False
