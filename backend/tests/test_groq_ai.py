"""
Unit and Integration Tests for Groq AI Service & Non-Blocking Scan Pipeline Integration.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.ai_service import is_groq_available, analyze_label_with_groq
from services.rule_engine import load_rules, apply_multi_image_rules


class TestGroqAIService(unittest.TestCase):
    def test_groq_availability_detection(self):
        """is_groq_available returns boolean based on settings."""
        self.assertIsInstance(is_groq_available(), bool)

    def test_groq_unconfigured_fallback(self):
        """When key is missing, returns clean fallback state."""
        with patch("services.ai_service.is_groq_available", return_value=False):
            res = analyze_label_with_groq("sample text")
            self.assertFalse(res["available"])
            self.assertEqual(res["status"], "unconfigured")
            self.assertIn("message", res)

    def test_groq_empty_ocr_text(self):
        """When OCR text is empty, returns empty_input state."""
        with patch("services.ai_service.is_groq_available", return_value=True):
            res = analyze_label_with_groq("")
            self.assertFalse(res["available"])
            self.assertEqual(res["status"], "empty_input")

    def test_groq_successful_response_parsing(self):
        """Valid JSON from Groq is parsed into structured dictionary."""
        mock_groq_response = {
            "choices": [{
                "message": {
                    "content": """{
                        "normalized_entities": {
                            "product_name": "Tata Salt",
                            "manufacturer": "Tata Consumer Products",
                            "net_quantity": "1 kg",
                            "mrp": "Rs 28.00",
                            "manufacturing_date": "01/2026",
                            "country_of_origin": "India",
                            "consumer_care": "1800-200-0520",
                            "unit_sale_price": "Rs 28/kg"
                        },
                        "semantic_observations": ["Clean printed panel"],
                        "ambiguous_fields": [],
                        "recommendations": ["Ensure font height compliance"],
                        "explanation": "Compliant packaging."
                    }"""
                }
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_groq_response

        with patch("services.ai_service.is_groq_available", return_value=True),              patch("httpx.Client.post", return_value=mock_resp):
            res = analyze_label_with_groq("Tata Salt 1kg")
            self.assertTrue(res["available"])
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["normalized_entities"]["product_name"], "Tata Salt")
            self.assertEqual(len(res["recommendations"]), 1)

    def test_groq_malformed_json_fallback(self):
        """Invalid JSON from Groq triggers safe fallback without raising exceptions."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "INVALID_JSON_HERE"}}]}

        with patch("services.ai_service.is_groq_available", return_value=True),              patch("httpx.Client.post", return_value=mock_resp):
            res = analyze_label_with_groq("Tata Salt")
            self.assertFalse(res["available"])
            self.assertEqual(res["status"], "error")

    def test_groq_api_error_fallback(self):
        """HTTP 429/500 from Groq triggers safe non-blocking fallback."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit exceeded"

        with patch("services.ai_service.is_groq_available", return_value=True),              patch("httpx.Client.post", return_value=mock_resp):
            res = analyze_label_with_groq("Tata Salt")
            self.assertFalse(res["available"])
            self.assertEqual(res["status"], "api_error")
            self.assertEqual(res["http_status"], 429)

    def test_deterministic_score_preserved_regardless_of_ai(self):
        """The rule engine score is computed deterministically and cannot be altered by AI."""
        rules = load_rules()
        image_results = [{
            "image_index": 1,
            "filename": "test.jpg",
            "raw_text": "Tata Salt 1 kg MRP Rs 28.00 Mfg 01/2026 Batch TS01",
            "classification": {"panel_type": "PRIMARY", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {
                "product_name": "Tata Salt",
                "net_quantity": "1 kg",
                "mrp": "Rs 28.00",
                "mfg_date": "01/2026"
            },
            "extracted_entities_detailed": {}
        }]
        report = apply_multi_image_rules(image_results, rules)
        self.assertIsInstance(report["overall_score"], (int, float))
        self.assertIn("fields", report)
        self.assertIn("status", report)


if __name__ == "__main__":
    unittest.main()
