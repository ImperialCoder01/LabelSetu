"""
LABELSETU EASYOCR COMPLETE REMOVAL REGRESSION TEST SUITE

Verifies all 9 requirements from Section 13:
1. EasyOCR is not imported.
2. EasyOCR is not initialized.
3. OCR.space is called.
4. OCR.space success continues normally.
5. OCR.space failure does NOT attempt EasyOCR.
6. OCR failure returns a safe structured result.
7. The FastAPI process does not crash.
8. Multi-image scanning still works.
9. Existing response structure remains compatible.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import services.ocr_service as ocr_service
from services.ocr_service import extract_text, extract_text_with_scores
from services.rule_engine import load_rules, apply_multi_image_rules


class TestEasyOCRCompleteRemoval(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()
        img = np.full((300, 400, 3), 255, dtype=np.uint8)
        cv2.putText(img, "Tata Salt 1kg MRP Rs 28", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        _, img_bytes = cv2.imencode(".jpg", img)
        self.raw_bytes = img_bytes.tobytes()

    def test_01_easyocr_is_not_imported_in_service(self):
        """1. EasyOCR is not imported in services/ocr_service.py."""
        import inspect
        src = inspect.getsource(ocr_service)
        self.assertNotIn("easyocr", src.lower())
        self.assertNotIn("import easyocr", src)

    def test_02_easyocr_is_not_initialized_or_present(self):
        """2. EasyOCR reader singleton is not initialized or present."""
        self.assertFalse(hasattr(ocr_service, "_reader"))
        self.assertFalse(hasattr(ocr_service, "_get_reader"))
        self.assertFalse(hasattr(ocr_service, "_extract_local"))

    def test_03_ocr_space_is_called(self):
        """3. OCR.space cloud API is called for image extraction."""
        with patch("services.ocr_service._extract_cloud_with_scores") as mock_cloud:
            mock_cloud.return_value = {
                "provider": "cloud",
                "full_text": "Amul Butter 100g MRP Rs 56",
                "detections": [{"text": "Amul", "confidence": 0.98, "bbox": None}],
                "average_confidence": 0.98,
            }
            res = extract_text_with_scores(self.raw_bytes)
            mock_cloud.assert_called_once()
            self.assertEqual(res["provider"], "cloud")

    def test_04_ocr_space_success_continues_normally(self):
        """4. OCR.space success extracts text and entities correctly."""
        with patch("services.ocr_service._extract_cloud_with_scores") as mock_cloud:
            mock_cloud.return_value = {
                "provider": "cloud",
                "full_text": "Tata Salt Net Quantity: 1 kg MRP: Rs 28.00 Mfg: 01/2026 Batch: TS01",
                "detections": [],
                "average_confidence": 0.96,
            }
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIn("Tata Salt", res["full_text"])
            self.assertIn("extracted_entities", res)
            self.assertEqual(res["extracted_entities"].get("net_quantity"), "1 kg")
            self.assertIn("28.00", res["extracted_entities"].get("mrp", ""))

    def test_05_ocr_space_failure_does_not_attempt_easyocr(self):
        """5. OCR.space failure does NOT attempt EasyOCR or any local fallback."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("HTTP 502 Bad Gateway")):
            # Verify no fallback functions exist to be called
            self.assertFalse(hasattr(ocr_service, "_extract_local_with_scores"))
            res = extract_text_with_scores(self.raw_bytes)
            # Result provider is cloud (unavailable), never local
            self.assertNotIn("local", res.get("provider", "").lower())
            self.assertEqual(res["provider"], "cloud (unavailable)")

    def test_06_ocr_failure_returns_safe_structured_result(self):
        """6. OCR failure returns a safe structured result with expected keys."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("API limit exceeded")):
            res = extract_text_with_scores(self.raw_bytes)
            self.assertIsInstance(res, dict)
            self.assertIn("provider", res)
            self.assertIn("full_text", res)
            self.assertIn("normalized_full_text", res)
            self.assertIn("detections", res)
            self.assertIn("average_confidence", res)
            self.assertIn("extracted_entities", res)
            self.assertIn("enhanced", res)
            self.assertIn("error", res)
            self.assertEqual(res["full_text"], "")
            self.assertEqual(res["detections"], [])

    def test_07_fastapi_process_does_not_crash_on_ocr_failure(self):
        """7. The process does not crash and extract_text returns empty string on error."""
        with patch("services.ocr_service._extract_cloud", side_effect=Exception("Network drop")):
            text = extract_text(self.raw_bytes)
            self.assertEqual(text, "")

    def test_08_multi_image_scanning_works(self):
        """8. Multi-image scanning pipeline works seamlessly with cloud OCR."""
        with patch("services.ocr_service._extract_cloud_with_scores") as mock_cloud:
            mock_cloud.side_effect = [
                {
                    "provider": "cloud",
                    "full_text": "Tata Salt Iodised Salt 1 kg",
                    "detections": [],
                    "average_confidence": 0.95,
                },
                {
                    "provider": "cloud",
                    "full_text": "MRP Rs 28.00 Mfg 01/2026 Batch TS01 Tata Consumer Products Ltd",
                    "detections": [],
                    "average_confidence": 0.95,
                },
            ]
            img1_res = extract_text_with_scores(self.raw_bytes)
            img2_res = extract_text_with_scores(self.raw_bytes)

            image_results = [
                {
                    "image_index": 1,
                    "filename": "front.jpg",
                    "raw_text": img1_res["full_text"],
                    "quality_info": {"quality_status": "GOOD"},
                    "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
                    "extracted_entities": img1_res["extracted_entities"],
                },
                {
                    "image_index": 2,
                    "filename": "back.jpg",
                    "raw_text": img2_res["full_text"],
                    "quality_info": {"quality_status": "GOOD"},
                    "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
                    "extracted_entities": img2_res["extracted_entities"],
                },
            ]
            rep = apply_multi_image_rules(image_results, self.rules)
            self.assertIn(rep["status"], ["pass", "partial"])
            self.assertGreater(rep["passed"], 0)

    def test_09_existing_response_structure_remains_compatible(self):
        """9. Response schema conforms exactly to frontend expectations."""
        with patch("services.ocr_service._extract_cloud_with_scores") as mock_cloud:
            mock_cloud.return_value = {
                "provider": "cloud",
                "full_text": "Britannia Good Day 50g",
                "detections": [{"text": "Britannia", "confidence": 0.92, "bbox": None}],
                "average_confidence": 0.92,
            }
            res = extract_text_with_scores(self.raw_bytes)
            # Essential frontend keys
            for key in ["provider", "full_text", "normalized_full_text", "detections", "average_confidence", "extracted_entities", "enhanced"]:
                self.assertIn(key, res, f"Key '{key}' must be present in OCR response")


if __name__ == "__main__":
    unittest.main()
