"""
Quick test to verify EasyOCR works end-to-end in local mode.
Creates a test image with text and runs OCR on it.
"""
import os
import sys
import io

# Force UTF-8 stdout BEFORE any EasyOCR import (fixes Windows cp1252 crash)
os.environ["PYTHONIOENCODING"] = "utf-8"
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from PIL import Image, ImageDraw, ImageFont


def create_test_image(text: str = "Tata Salt\nIodised Salt\nNet Wt: 1 kg\nMRP: Rs 28.00\nExpiry: 12/2026") -> bytes:
    """Create a simple test image with text."""
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)

    # Use default font (no external font needed)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()

    # Draw text line by line
    y = 30
    for line in text.split("\n"):
        draw.text((30, y), line, fill="black", font=font)
        y += 35

    # Save to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_easyocr():
    """Test EasyOCR with the generated image."""
    print("[1/3] Creating test image with product label text...")
    image_bytes = create_test_image()
    print(f"      Image size: {len(image_bytes)} bytes")

    print("[2/3] Importing and loading EasyOCR (en + hi)...")
    from services.ocr_service import extract_text, preload_model

    # Preload the model (same as startup)
    preload_model()

    print("[3/3] Running OCR on test image...")
    result = extract_text(image_bytes)

    print(f"\n{'='*50}")
    print(f"EXTRACTED TEXT:")
    print(f"{'='*50}")
    print(result)
    print(f"{'='*50}")
    print(f"Characters extracted: {len(result)}")

    if result.strip():
        print("\n[OK] EasyOCR is working correctly!")
        return True
    else:
        print("\n[WARN] No text extracted. Check font rendering.")
        return False


if __name__ == "__main__":
    # Add backend dir to path so imports work
    sys.path.insert(0, ".")

    success = test_easyocr()
    sys.exit(0 if success else 1)
