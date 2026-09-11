"""
LabelSetu Local PaddleOCR Service - Standalone Test & Validation Client.
Executes:
1. GET /health check
2. GET /ready probe
3. Sample packaging OCR:
   - English packaging text (Net weight, MRP, FSSAI, Batch, Mfg)
   - Hindi packaging text (Devanagari declarations)
   - Mixed packaging text (Bilingual packaging)
4. Latency benchmarking:
   - First request latency
   - Warm subsequent requests (3 iterations)
5. Validation of error/failure cases:
   - Empty file upload (HTTP 400)
   - Non-image corrupted file upload (HTTP 400)
   - Optional API key authentication rejection
6. Exports JSON responses to test_outputs/ directory.
"""
import os
import sys
import time
import json
from pathlib import Path
import requests

# Reconfigure console output to UTF-8
sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = os.environ.get("LOCAL_OCR_URL", "http://127.0.0.1:8001")
API_KEY = os.environ.get("LOCAL_OCR_API_KEY", "")
SCRIPT_DIR = Path(__file__).parent
TEST_IMAGES_DIR = SCRIPT_DIR / "test_images"
OUTPUT_DIR = SCRIPT_DIR / "test_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {}
if API_KEY:
    HEADERS["X-Local-OCR-Key"] = API_KEY


def print_banner(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_health():
    print_banner("1. Testing GET /health")
    url = f"{BASE_URL}/health"
    resp = requests.get(url, timeout=10)
    print(f"HTTP Status: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2))
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert data.get("status") == "ok"
    assert data.get("engine_ready") is True
    (OUTPUT_DIR / "health_response.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✓ Health check PASSED")
    return data


def test_ready():
    print_banner("2. Testing GET /ready")
    url = f"{BASE_URL}/ready"
    resp = requests.get(url, timeout=10)
    print(f"HTTP Status: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2))
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert data.get("ready") is True
    (OUTPUT_DIR / "ready_response.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✓ Readiness check PASSED")
    return data


def test_ocr_file(image_path: Path, test_name: str):
    print_banner(f"3. Testing POST /ocr: {test_name} ({image_path.name})")
    url = f"{BASE_URL}/ocr"
    assert image_path.exists(), f"Image file not found: {image_path}"

    with open(image_path, "rb") as f:
        files = {"file": (image_path.name, f, "image/png")}
        start_time = time.perf_counter()
        resp = requests.post(url, files=files, headers=HEADERS, timeout=60)
        wall_time_ms = int(round((time.perf_counter() - start_time) * 1000))

    print(f"HTTP Status: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    out_file = OUTPUT_DIR / f"{test_name}_response.json"
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Processing time (server): {data.get('processing_time_ms')} ms")
    print(f"Wall-clock request time: {wall_time_ms} ms")
    print(f"Detected Languages: {data.get('languages_detected')}")
    print(f"Total Lines: {len(data.get('lines', []))}")
    print("--- Extracted Text ---")
    print(data.get("raw_text"))
    print("----------------------")
    print(f"Saved response to {out_file.name}")
    print(f"✓ {test_name} PASSED")
    return data, wall_time_ms


def test_latency_benchmark(image_path: Path, iterations: int = 3):
    print_banner(f"4. Latency Benchmark ({iterations} consecutive runs)")
    url = f"{BASE_URL}/ocr"
    latencies = []

    for i in range(1, iterations + 1):
        with open(image_path, "rb") as f:
            files = {"file": (image_path.name, f, "image/png")}
            t0 = time.perf_counter()
            resp = requests.post(url, files=files, headers=HEADERS, timeout=60)
            t1 = time.perf_counter()
            wall_ms = int(round((t1 - t0) * 1000))
            server_ms = resp.json().get("processing_time_ms")
            latencies.append((wall_ms, server_ms))
            print(f"  Run #{i}: Wall time = {wall_ms} ms | Server OCR time = {server_ms} ms")

    avg_wall = sum(x[0] for x in latencies) / len(latencies)
    avg_server = sum(x[1] for x in latencies) / len(latencies)
    print(f"\nAverage Warm Wall-clock Latency: {avg_wall:.1f} ms")
    print(f"Average Warm Server OCR Latency: {avg_server:.1f} ms")
    print("✓ Latency Benchmark PASSED")
    return latencies


def test_error_cases():
    print_banner("5. Testing Error and Edge Cases")
    url = f"{BASE_URL}/ocr"

    # Test 5.1: Empty file upload
    print("\n-- Subtest 5.1: Empty file upload --")
    files = {"file": ("empty.png", b"", "image/png")}
    resp = requests.post(url, files=files, headers=HEADERS, timeout=10)
    print(f"Status: {resp.status_code}, Response: {resp.text}")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("✓ Empty file rejection PASSED")

    # Test 5.2: Corrupt / non-image file upload
    print("\n-- Subtest 5.2: Corrupted non-image file upload --")
    files = {"file": ("corrupt.png", b"This is plain text and not a valid PNG or JPEG image.", "image/png")}
    resp = requests.post(url, files=files, headers=HEADERS, timeout=10)
    print(f"Status: {resp.status_code}, Response: {resp.text}")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("✓ Corrupt file rejection PASSED")

    # Test 5.3: Authentication rejection (if auth enabled)
    print("\n-- Subtest 5.3: Auth rejection with invalid token --")
    health = requests.get(f"{BASE_URL}/health", timeout=5).json()
    if health.get("auth_enabled"):
        bad_headers = {"X-Local-OCR-Key": "invalid_wrong_token_12345"}
        with open(TEST_IMAGES_DIR / "test_en.png", "rb") as f:
            files = {"file": ("test_en.png", f, "image/png")}
            resp = requests.post(url, files=files, headers=bad_headers, timeout=10)
            print(f"Status with bad key: {resp.status_code}")
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
            print("✓ Auth rejection PASSED")
    else:
        print("Note: LOCAL_OCR_API_KEY is not configured (auth disabled by default). Verified open local access.")


def run_all_tests():
    print_banner("STARTING LABELSETU LOCAL PADDLEOCR VALIDATION SUITE")
    print(f"Target Server URL: {BASE_URL}")

    t_start = time.time()
    health_data = test_health()
    ready_data = test_ready()

    # Sample packaging tests
    en_img = TEST_IMAGES_DIR / "test_en.png"
    hi_img = TEST_IMAGES_DIR / "test_hi.png"
    mixed_img = TEST_IMAGES_DIR / "test_mixed.png"

    en_res, en_lat = test_ocr_file(en_img, "ocr_en")
    hi_res, hi_lat = test_ocr_file(hi_img, "ocr_hi")
    mixed_res, mixed_lat = test_ocr_file(mixed_img, "ocr_mixed")

    # Latency benchmark
    latencies = test_latency_benchmark(mixed_img, iterations=3)

    # Edge and error cases
    test_error_cases()

    total_time = time.time() - t_start
    print_banner("ALL STAGE 1 OCR VALIDATION TESTS COMPLETED SUCCESSFULLY")
    print(f"Total Test Suite Duration: {total_time:.2f} s")
    print(f"English lines detected: {len(en_res.get('lines', []))}")
    print(f"Hindi lines detected:   {len(hi_res.get('lines', []))}")
    print(f"Mixed lines detected:   {len(mixed_res.get('lines', []))}")
    print(f"JSON outputs saved in:  {OUTPUT_DIR}")


if __name__ == "__main__":
    run_all_tests()
