"""
Test POST /api/scans/scan — full pipeline.
"""
import os
import sys
import io
import json

os.environ["PYTHONIOENCODING"] = "utf-8"
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")


def create_test_image(text_lines: list[str], width=500, height=400) -> bytes:
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    y = 20
    for line in text_lines:
        draw.text((20, y), line, fill="black", font=font)
        y += 38
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_test():
    from fastapi.testclient import TestClient
    from main import app
    from database import supabase

    client = TestClient(app)

    # ---- Create confirmed test user via admin API ----
    import httpx
    from config import settings

    test_email = "test_scan_labelsetu@test.com"
    test_pass = "TestPass123!"
    base = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    # Create confirmed user via admin API
    httpx.post(
        f"{base}/auth/v1/admin/users",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        json={"email": test_email, "email_confirm": True, "password": test_pass},
    )

    # Get user ID from auth.users
    user_resp = httpx.get(
        f"{base}/auth/v1/admin/users",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={"page": 1, "per_page": 1000},
    )
    users = user_resp.json().get("users", [])
    matched = [u for u in users if u["email"] == test_email]
    assert matched, f"User {test_email} not found after creation"
    user_id = matched[0]["id"]

    # Upsert profile (ignore if exists)
    supabase.table("users_profile").upsert(
        {"id": user_id, "full_name": "Test User", "role": "consumer"}
    ).execute()

    # Sign in to get JWT
    session = supabase.auth.sign_in_with_password({"email": test_email, "password": test_pass})
    token = session.session.access_token
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Auth: signed in as {test_email}\n")

    # ---- Test 1: Partially compliant label ----
    print("=" * 60)
    print("TEST 1: POST /api/scans/scan (partially compliant)")
    print("=" * 60)

    img1 = create_test_image([
        "Tata Salt",
        "Iodised Salt",
        "Manufactured by: Tata Consumer Products Ltd",
        "Net Wt: 1 kg",
        "MRP: Rs 28.00",
        "Country of Origin: India",
    ])
    print(f"Image: {len(img1)} bytes\n")

    resp = client.post(
        "/api/scans/scan",
        files={"file": ("label.png", img1, "image/png")},
        headers=headers,
    )

    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"Scan ID:   {data['scan_id']}")
        print(f"Saved:     {data['saved']}")
        print(f"Provider:  {data['ocr']['provider']}")
        print(f"Text:      {data['ocr']['full_text'][:80]}...")
        print(f"Detections: {len(data['ocr']['detections'])}")
        print(f"Avg conf:  {data['ocr']['average_confidence']}")
        print()
        c = data["compliance"]
        print(f"Score:     {c['overall_score']}/100")
        print(f"Status:    {c['status']}")
        print(f"Passed:    {c['passed']}/{c['total_fields']}")
        print(f"Failed:    {c['failed']}/{c['total_fields']}")
        print()
        for f in c["fields"]:
            icon = "PASS" if f["status"] == "pass" else "FAIL"
            print(f"  [{icon}] [{f['severity']:>8}] {f['field_name']}")
        print()

        assert data["scan_id"] is not None, "scan_id should not be None"
        assert data["saved"] is True, "saved should be True"
        assert c["overall_score"] < 100, "partial label should score < 100"
        assert c["status"] == "partial"
        assert len(c["critical_failures"]) > 0 or len(c["minor_failures"]) > 0
        print("[OK] TEST 1 PASSED\n")
    else:
        print(f"[FAIL] {resp.json()}")
        sys.exit(1)

    # ---- Test 2: Fully compliant label ----
    print("=" * 60)
    print("TEST 2: POST /api/scans/scan (fully compliant)")
    print("=" * 60)

    img2 = create_test_image([
        "Amul Butter",
        "Brand: Amul",
        "Manufactured by: Gujarat Cooperative Milk Marketing Federation",
        "Net Quantity: 100g",
        "Manufacturing Date: 15/08/2026",
        "MRP: Rs 56.00",
        "Unit Sale Price: Rs 560 per kg",
        "Consumer Care: 1800-200-0520",
        "Country of Origin: India",
    ], height=500)

    resp2 = client.post(
        "/api/scans/scan",
        files={"file": ("butter.png", img2, "image/png")},
        headers=headers,
    )

    print(f"Status: {resp2.status_code}")

    if resp2.status_code == 200:
        data2 = resp2.json()
        c2 = data2["compliance"]
        print(f"Scan ID:   {data2['scan_id']}")
        print(f"Score:     {c2['overall_score']}/100")
        print(f"Status:    {c2['status']}")
        print(f"Passed:    {c2['passed']}/{c2['total_fields']}")
        print()

        assert data2["saved"] is True
        assert c2["overall_score"] == 100, f"Expected 100, got {c2['overall_score']}"
        assert c2["status"] == "pass"
        print("[OK] TEST 2 PASSED\n")
    else:
        print(f"[FAIL] {resp2.json()}")
        sys.exit(1)

    # ---- Test 3: Bad file type ----
    print("=" * 60)
    print("TEST 3: POST /api/scans/scan (bad file type)")
    print("=" * 60)

    resp3 = client.post(
        "/api/scans/scan",
        files={"file": ("data.txt", b"not an image", "text/plain")},
    )
    print(f"Status: {resp3.status_code}")
    assert resp3.status_code == 400
    print("[OK] TEST 3 PASSED\n")

    # ---- Summary ----
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
