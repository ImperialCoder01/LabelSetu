"""
LABELSETU OCR RESILIENCE & FAIL-SAFE REGRESSION TEST SUITE
Asserts that OCR.space 502/503/timeouts return safe structured results,
EasyOCR is never imported or invoked, and OCR errors never crash the FastAPI process.
"""

import sys
import io
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
import services.ocr_service as ocr_service
from services.ocr_service import extract_text_with_scores


class TestOCRResilience(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Create a sample test image in memory
        img = np.full((300, 400, 3), 255, dtype=np.uint8)
        cv2.putText(img, "Tata Salt 1kg MRP Rs 28", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        _, self.img_bytes = cv2.imencode(".jpg", img)
        self.raw_bytes = self.img_bytes.tobytes()

    def test_01_ocr_space_502_returns_safe_structured_result(self):
        """Test 1: Cloud OCR returning HTTP 502 returns safe structured result without crashing or raising unhandled exception."""
        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=502, raise_for_status=MagicMock(side_effect=Exception("HTTP 502 Bad Gateway")))
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertEqual(res["full_text"], "")
            self.assertEqual(res["detections"], [])
            self.assertIn("error", res)

    def test_02_ocr_space_503_returns_safe_structured_result(self):
        """Test 2: Cloud OCR returning HTTP 503 (overloaded) returns safe structured result."""
        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=503, raise_for_status=MagicMock(side_effect=Exception("HTTP 503 Service Unavailable")))
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertEqual(res["full_text"], "")
            self.assertIn("error", res)

    def test_03_ocr_space_timeout_returns_safe_structured_result(self):
        """Test 3: Cloud OCR timeout returns safe structured result."""
        import httpx
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertEqual(res["full_text"], "")
            self.assertIn("error", res)

    def test_04_no_easyocr_or_torch_imports_in_ocr_service(self):
        """Test 4: Verify ocr_service does not import or contain easyocr or torch."""
        import inspect
        src = inspect.getsource(ocr_service)
        self.assertNotIn("import easyocr", src, "ocr_service must not import easyocr")
        self.assertNotIn("import torch", src, "ocr_service must not import torch")
        self.assertNotIn("_reader", src, "ocr_service must not contain _reader")

    def test_05_multiple_images_handled_sequentially_without_leakage(self):
        """Test 5: Multiple images in multi-image scan loop process cleanly."""
        with patch("services.ocr_service._extract_cloud_with_scores") as mock_cloud:
            mock_cloud.side_effect = [
                {"provider": "cloud", "full_text": "Tata Salt Net Wt: 1 kg", "detections": [], "average_confidence": 0.95},
                {"provider": "cloud", "full_text": "MRP Rs 28.00 Mfg 12/2026 Batch TS01", "detections": [], "average_confidence": 0.95}
            ]
            res1 = extract_text_with_scores(self.raw_bytes)
            res2 = extract_text_with_scores(self.raw_bytes)
            self.assertIn("Tata Salt", res1["full_text"])
            self.assertIn("MRP Rs 28.00", res2["full_text"])

    def test_06_cloud_ocr_failure_returns_controlled_json(self):
        """Test 6: If cloud OCR fails, extract_text_with_scores returns controlled JSON without crashing."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("OCR.space network timeout")):
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertEqual(res["full_text"], "")
            self.assertIn("error", res)

    def test_07_scan_endpoint_handles_empty_ocr_without_500_crash(self):
        """Test 7: Multi-image rule engine handles empty/unavailable OCR gracefully."""
        from services.rule_engine import load_rules, apply_multi_image_rules
        rules = load_rules()
        empty_images = [{
            "image_index": 1,
            "filename": "unreadable.jpg",
            "raw_text": "",
            "normalized_text": "",
            "quality_info": {"quality_status": "UNREADABLE"},
            "classification": {"panel_type": "UNREADABLE"},
            "ocr_result": {"provider": "cloud (unavailable)", "full_text": ""},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(empty_images, rules)
        self.assertIn("overall_score", rep)
        self.assertIn("fields", rep)
        self.assertIn("status", rep)


if __name__ == "__main__":
    unittest.main()
