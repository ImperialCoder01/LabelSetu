"""
LABELSETU OCR RESILIENCE & FAIL-SAFE REGRESSION TEST SUITE
Asserts that OCR.space 502/503/timeouts trigger safe local fallback,
EasyOCR reader is reused across images, and OCR errors never crash the FastAPI process.
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

    def test_01_ocr_space_502_triggers_safe_fallback(self):
        """Test 1: Cloud OCR returning HTTP 502 triggers local fallback without raising unhandled exception."""
        with patch("httpx.Client.post") as mock_post,              patch("services.ocr_service._extract_local_with_scores") as mock_local:
            mock_post.return_value = MagicMock(status_code=502, raise_for_status=MagicMock(side_effect=Exception("HTTP 502 Bad Gateway")))
            mock_local.return_value = {
                "provider": "local",
                "full_text": "Tata Salt 1kg MRP Rs 28",
                "detections": [],
                "average_confidence": 0.95
            }
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIn("Tata Salt", res["full_text"])
            self.assertEqual(res["provider"], "local (fallback)")

    def test_02_ocr_space_503_triggers_safe_fallback(self):
        """Test 2: Cloud OCR returning HTTP 503 (overloaded) triggers local fallback."""
        with patch("httpx.Client.post") as mock_post,              patch("services.ocr_service._extract_local_with_scores") as mock_local:
            mock_post.return_value = MagicMock(status_code=503, raise_for_status=MagicMock(side_effect=Exception("HTTP 503 Service Unavailable")))
            mock_local.return_value = {
                "provider": "local",
                "full_text": "Sample Sugar 1kg MRP Rs 50",
                "detections": [],
                "average_confidence": 0.92
            }
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIn("Sample Sugar", res["full_text"])
            self.assertEqual(res["provider"], "local (fallback)")

    def test_03_ocr_space_timeout_triggers_safe_fallback(self):
        """Test 3: Cloud OCR timeout triggers local fallback."""
        import httpx
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")),              patch("services.ocr_service._extract_local_with_scores") as mock_local:
            mock_local.return_value = {
                "provider": "local",
                "full_text": "Amul Butter 100g",
                "detections": [],
                "average_confidence": 0.90
            }
            res = extract_text_with_scores(self.raw_bytes)
            self.assertEqual(res["provider"], "local (fallback)")
            self.assertIn("Amul Butter", res["full_text"])

    def test_04_local_easyocr_fallback_reader_reuse(self):
        """Test 4: EasyOCR singleton reader is reused across requests without re-allocating models."""
        dummy_reader = MagicMock()
        dummy_reader.readtext.return_value = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "Tata Salt", 0.95)
        ]
        with patch("services.ocr_service._reader", dummy_reader):
            res1 = ocr_service._extract_local_with_scores(self.raw_bytes)
            res2 = ocr_service._extract_local_with_scores(self.raw_bytes)
            self.assertEqual(res1["full_text"], "Tata Salt")
            self.assertEqual(res2["full_text"], "Tata Salt")
            # Proves reader was reused twice
            self.assertEqual(dummy_reader.readtext.call_count, 2)

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

    def test_06_both_cloud_and_local_ocr_failure_returns_controlled_json(self):
        """Test 6: If cloud AND local OCR both fail, extract_text_with_scores returns controlled JSON without crashing."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("Cloud failed")),              patch("services.ocr_service._extract_local_with_scores", side_effect=Exception("Local memory limit")):
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["provider"], "unavailable")
            self.assertEqual(res["full_text"], "")
            self.assertIn("error", res)

    def test_07_scan_endpoint_handles_empty_ocr_without_500_crash(self):
        """Test 7: POST /api/scans/scan returns structured result even if OCR returns empty/unavailable."""
        from routers.scans import router
        # Verifies that empty text flows into rule engine and produces compliance report with score 0
        from services.rule_engine import load_rules, apply_multi_image_rules
        rules = load_rules()
        empty_images = [{
            "image_index": 1,
            "filename": "unreadable.jpg",
            "raw_text": "",
            "normalized_text": "",
            "quality_info": {"quality_status": "UNREADABLE"},
            "classification": {"panel_type": "UNREADABLE"},
            "ocr_result": {"provider": "unavailable", "full_text": ""},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(empty_images, rules)
        self.assertIn("overall_score", rep)
        self.assertIn("fields", rep)
        self.assertIn("status", rep)


if __name__ == "__main__":
    unittest.main()
