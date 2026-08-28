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


def _downscale_if_large(image: np.ndarray, max_dim: int = 1600) -> np.ndarray:
    """Downscale large phone photos to max_dim to cap OpenCV memory while preserving OCR clarity."""
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image


def enhance_image_for_ocr(image_bytes: bytes) -> Tuple[bytes, bool]:
    """
    Enhance raw package photo bytes for maximum OCR text detection accuracy.

    Pipeline:
    1. Decode raw bytes to BGR image matrix & downscale if oversized
    2. Auto-deskew orientation
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Unsharp Masking / Laplacian sharpening for small fonts (MRP, Mfg Date)
    5. Encode back to optimized bytes

    Returns:
        Tuple of (enhanced_image_bytes, was_enhanced_boolean)
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, False

        # Step 0: Downscale if image exceeds max dimension to avoid memory spike
        img = _downscale_if_large(img, max_dim=1600)

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


# Configurable Quality Thresholds
QUALITY_SETTINGS = {
    "MIN_WIDTH": 100,
    "MIN_HEIGHT": 100,
    "MAX_WIDTH": 8000,
    "MAX_HEIGHT": 8000,
    "BLUR_THRESHOLD_UNREADABLE": 35.0,
    "BLUR_THRESHOLD_FAIR": 80.0,
    "BRIGHTNESS_MIN_DARK": 35.0,
    "BRIGHTNESS_MAX_OVEREXPOSED": 225.0,
    "CONTRAST_MIN_LOW": 20.0,
}


def analyze_image_quality(image_bytes: bytes) -> dict:
    """
    Calculate measurable OpenCV image quality metrics:
    - Blur score (Variance of Laplacian)
    - Mean Brightness
    - Contrast (Std Dev of grayscale pixels)
    - Image Dimensions & Aspect Ratio
    - Quality Status: GOOD, FAIR, POOR, UNREADABLE
    """
    result = {
        "width": 0,
        "height": 0,
        "blur_score": 0.0,
        "brightness": 0.0,
        "contrast": 0.0,
        "quality_status": "GOOD",
        "issues": [],
        "user_guidance": None,
    }

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            result["quality_status"] = "UNREADABLE"
            result["issues"].append("Corrupt or unreadable image format")
            result["user_guidance"] = "The uploaded file could not be decoded as a valid image. Please select a valid photo."
            return result

        h, w = img.shape[:2]
        result["width"] = w
        result["height"] = h

        # Grayscale for analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Blur Detection using Variance of Laplacian
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        result["blur_score"] = round(blur_score, 2)

        # 2. Brightness & Contrast
        mean_brightness = float(np.mean(gray))
        std_contrast = float(np.std(gray))
        result["brightness"] = round(mean_brightness, 2)
        result["contrast"] = round(std_contrast, 2)

        # Evaluate Issues
        issues = []
        if w < QUALITY_SETTINGS["MIN_WIDTH"] or h < QUALITY_SETTINGS["MIN_HEIGHT"]:
            issues.append(f"Image resolution too low ({w}x{h})")

        if blur_score < QUALITY_SETTINGS["BLUR_THRESHOLD_UNREADABLE"]:
            issues.append("Extreme motion blur detected")
        elif blur_score < QUALITY_SETTINGS["BLUR_THRESHOLD_FAIR"]:
            issues.append("Slight image blur detected")

        if mean_brightness < QUALITY_SETTINGS["BRIGHTNESS_MIN_DARK"]:
            issues.append("Image is too dark")
        elif mean_brightness > QUALITY_SETTINGS["BRIGHTNESS_MAX_OVEREXPOSED"]:
            issues.append("Image is overexposed")

        if std_contrast < QUALITY_SETTINGS["CONTRAST_MIN_LOW"]:
            issues.append("Low contrast")

        result["issues"] = issues

        # Determine overall Quality Status
        if blur_score < QUALITY_SETTINGS["BLUR_THRESHOLD_UNREADABLE"] or w < QUALITY_SETTINGS["MIN_WIDTH"] or h < QUALITY_SETTINGS["MIN_HEIGHT"]:
            result["quality_status"] = "UNREADABLE"
            result["user_guidance"] = "Image is too blurry or low-resolution to reliably read package text. Retake photo with steady lighting and clear focus."
        elif issues:
            if len(issues) >= 2 or blur_score < QUALITY_SETTINGS["BLUR_THRESHOLD_FAIR"]:
                result["quality_status"] = "POOR"
                result["user_guidance"] = "Image quality is sub-optimal (" + ", ".join(issues) + "). OCR results may have minor inaccuracies."
            else:
                result["quality_status"] = "FAIR"
                result["user_guidance"] = "Photo is acceptable, but improving lighting and camera focus will give better results."
        else:
            result["quality_status"] = "GOOD"
            result["user_guidance"] = "High quality image detected."

    except Exception as exc:
        logger.error("Quality analysis exception: %s", exc)
        result["quality_status"] = "FAIR"

    return result


def classify_image_content(image_bytes: bytes, raw_text: str, quality_info: dict) -> dict:
    """
    Lightweight classification for product packaging images:
    - SCREENSHOT / NON_PRODUCT_IMAGE
    - UNREADABLE_IMAGE
    - FRONT_PANEL
    - BACK_DECLARATION_PANEL
    - PRODUCT_LABEL
    """
    text_lower = (raw_text or "").lower()

    # 1. Screenshot / UI Detection
    screenshot_keywords = [
        "vercel.app", "dashboard", "loading profile", "localhost:", "http://", "https://",
        "chrome", "firefox", "browser", "window", "tab", "user_uploaded", "select file"
    ]
    if any(kw in text_lower for kw in screenshot_keywords):
        return {
            "classification": "SCREENSHOT",
            "is_product_label": False,
            "panel_type": "NON_PRODUCT",
            "confidence": 0.98,
            "description": "Uploaded image appears to be a web UI screenshot or non-product graphic.",
            "user_guidance": "Please upload a real photograph of a physical product package label."
        }

    # 2. Unreadable Detection
    if quality_info.get("quality_status") == "UNREADABLE" or (not text_lower.strip() and quality_info.get("blur_score", 100) < 35.0):
        return {
            "classification": "UNREADABLE_IMAGE",
            "is_product_label": True,
            "panel_type": "UNREADABLE",
            "confidence": 0.95,
            "description": "Image is unreadable due to severe blur or poor lighting.",
            "user_guidance": quality_info.get("user_guidance", "Retake photo with clear focus.")
        }

    # 3. Legal Metrology Back Declaration Panel Check
    back_panel_keywords = [
        "manufactured by", "manufactured at", "mfg by", "mfd by", "marketed by", "mktd by",
        "packed by", "pkd by", "imported by", "mrp", "max retail price", "net qty",
        "net quantity", "net wt", "net weight", "net content", "consumer care",
        "customer care", "unit sale price", "country of origin", "batch no", "mfg date"
    ]
    back_matches = [kw for kw in back_panel_keywords if kw in text_lower]

    if len(back_matches) >= 2:
        return {
            "classification": "BACK_DECLARATION_PANEL",
            "is_product_label": True,
            "panel_type": "BACK_DECLARATION_PANEL",
            "confidence": 0.95,
            "matched_declarations_count": len(back_matches),
            "description": "Back/Side packaging panel containing mandatory Legal Metrology declarations detected.",
            "user_guidance": "Complete declaration panel detected."
        }

    # 4. Front Panel Detection
    if len(text_lower.strip()) > 0 and len(back_matches) < 2:
        return {
            "classification": "FRONT_PANEL",
            "is_product_label": True,
            "panel_type": "FRONT_PANEL",
            "confidence": 0.85,
            "description": "Front branding panel detected. Full Legal Metrology declarations are usually printed on the back or side panel.",
            "user_guidance": "Front panel detected. Upload the back or side declaration panel for full Legal Metrology compliance verification."
        }

    return {
        "classification": "PRODUCT_LABEL",
        "is_product_label": True,
        "panel_type": "MIXED_PANEL",
        "confidence": 0.80,
        "description": "Product packaging photo detected.",
        "user_guidance": "Product label detected."
    }
