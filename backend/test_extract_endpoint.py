"""
Test POST /api/extract endpoint end-to-end.
Spins up FastAPI, uploads a test image, and prints the JSON response.
"""
import os
import sys
import io
import json
import threading
import time

os.environ["PYTHONIOENCODING"] = "utf-8"
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from PIL import Image, ImageDraw, ImageFont


def create_test_image() -> bytes:
    """Create a product label test image."""
    img = Image.new("RGB", (500, 350), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    lines = [
        "Tata Salt",
        "Iodised Salt",
        "Net Wt: 1 kg",
        "MRP: Rs 28.00",
        "Expiry: 12/2026",
        "Batch: TS202601",
        "Mfg by: Tata Consumer Products",
    ]
    y = 30
    for line in lines:
        draw.text((30, y), line, fill="black", font=font)
        y += 42

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_test():
    """Start server and test /api/extract."""
    import uvicorn
    from fastapi.testclient import TestClient

    # Use TestClient (no actual server needed)
    from main import app

    client = TestClient(app)

    print("[1] Creating test image...")
    image_bytes = create_test_image()
    print(f"    Image: {len(image_bytes)} bytes")

    print("[2] POST /api/extract ...")
    response = client.post(
        "/api/extract",
        files={"file": ("label.png", image_bytes, "image/png")},
    )

    print(f"[3] Status: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("=" * 60)
        print("RESPONSE JSON:")
        print("=" * 60)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("=" * 60)
        print(f"\nProvider:            {data['provider']}")
        print(f"Full text:           {data['full_text']}")
        print(f"Detections:          {len(data['detections'])}")
        print(f"Average confidence:  {data['average_confidence']}")
        print("\n[OK] Endpoint working!")
    else:
        print(f"[FAIL] {response.json()}")
        sys.exit(1)


if __name__ == "__main__":
    sys.path.insert(0, ".")
    run_test()
