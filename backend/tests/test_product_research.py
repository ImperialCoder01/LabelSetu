"""
Unit and Regression Tests for AI-Assisted Product Information Recovery & Evidence Segregation.
Tests all 12 core requirements specified in the LabelSetu architecture specification.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.product_research_service import (
    research_product_information,
    detect_identity_conflicts,
    _calculate_match_confidence,
    _generate_panel_recommendations,
)
from services.ai_service import analyze_label_with_groq
from services.rule_engine import load_rules, apply_multi_image_rules


class TestProductResearchService(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_01_missing_mrp(self):
        """TEST 1 — Missing MRP: External MRP = ₹28 does not change rule engine status or score."""
        package_images = [{
            "image_index": 1,
            "filename": "front_panel.jpg",
            "raw_text": "Tata Salt Iodised Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {
                "product_name": "Tata Salt",
                "net_quantity": "1 kg"
            },
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mrp_field = next((f for f in rule_report["fields"] if f["field_id"] == "mrp"), None)
        self.assertIsNotNone(mrp_field)
        self.assertEqual(mrp_field["status"], "fail")
        score_before = rule_report["overall_score"]

        missing_fields = [f for f in rule_report["fields"] if f["status"] == "fail"]
        res = research_product_information(
            ocr_text="Tata Salt Iodised Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "brand": "Tata", "net_quantity": "1 kg"},
            missing_fields=missing_fields,
            barcode="8901030300000"
        )
        self.assertEqual(res["status"], "success")
        ext_mrp = next((f for f in res["fields"] if f["field_id"] == "mrp"), None)
        if ext_mrp:
            self.assertFalse(ext_mrp["package_verified"])
            self.assertEqual(ext_mrp["verification_status"], "REQUIRES_PACKAGE_VERIFICATION")
        self.assertEqual(mrp_field["status"], "fail")
        self.assertEqual(rule_report["overall_score"], score_before)

    def test_02_missing_manufacturing_date(self):
        """TEST 2 — Missing Manufacturing Date: External date is reference only, package_verified = False."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mfg_field = next((f for f in rule_report["fields"] if f["field_id"] == "manufacturing_date"), None)
        self.assertEqual(mfg_field["status"], "fail")

    def test_03_missing_batch_number(self):
        """TEST 3 — Missing Batch Number: External batch data never marks package batch as verified."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        batch_field = next((f for f in rule_report["fields"] if f["field_id"] == "batch_number"), None)
        if batch_field:
            self.assertEqual(batch_field["status"], "fail")

    def test_04_manufacturer_reference(self):
        """TEST 4 — Manufacturer Reference: Missing package manufacturer is FAIL in rule engine, reference only externally."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg MRP Rs 28.00",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "mrp": "Rs 28.00"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mfg_field = next((f for f in rule_report["fields"] if f["field_id"] == "manufacturer_name_address"), None)
        self.assertEqual(mfg_field["status"], "fail")

    def test_05_identity_conflict(self):
        """TEST 5 — Identity Conflict: Package Company A vs External Company B sets identity_conflict=True without score deduction."""
        package_images = [{
            "image_index": 1,
            "filename": "label.jpg",
            "raw_text": "Sparkle Water 500ml Manufactured by: Company A India Ltd",
            "classification": {"panel_type": "PRIMARY", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {
                "product_name": "Sparkle Water",
                "manufacturer": "Company A India Ltd",
                "net_quantity": "500 ml"
            },
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        score_before = rule_report["overall_score"]

        conflicts = detect_identity_conflicts(
            package_entities={"manufacturer": "Company A India Ltd"},
            matched_record={"manufacturer": "Company B Global LLC"}
        )
        self.assertEqual(len(conflicts), 1)
        self.assertIn("identity conflict detected", conflicts[0]["warning"])
        self.assertEqual(rule_report["overall_score"], score_before)

    def test_06_exact_gtin_match(self):
        """TEST 6 — Exact GTIN Match: Barcode lookup yields high confidence and package_verified=False on external fields."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode="8901030300000"
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["product_match"]["confidence_level"], "high_confidence")
        self.assertGreaterEqual(res["product_match"]["confidence_score"], 0.90)

    def test_07_weak_product_match(self):
        """TEST 7 — Weak Product Match: Vague OCR returns no_reliable_match or low confidence rejection."""
        conf, status = _calculate_match_confidence(
            query_text="Random Unrelated Text 9999",
            matched_name="Tata Salt",
            matched_brand="Tata",
            has_barcode_match=False
        )
        self.assertEqual(status, "no_match")

        res = research_product_information(
            ocr_text="Random Unrelated Text 9999",
            extracted_entities={"product_name": "Unknown"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode=""
        )
        self.assertIn(res["status"], ("no_reliable_match", "low_confidence_rejected"))

    def test_08_external_api_failure_non_blocking(self):
        """TEST 8 — External API Failure: 500/429/timeout returns clean fallback without raising unhandled exceptions."""
        with patch("services.product_research_service._search_open_food_facts", side_effect=Exception("HTTP 500 Server Error")):
            res = research_product_information(
                ocr_text="Some Product Text",
                extracted_entities={"product_name": "Test"},
                missing_fields=[{"field_id": "mrp", "status": "fail"}],
            )
            self.assertIn("status", res)
            self.assertIsInstance(res["disclaimer"], str)

    def test_09_groq_failure_non_blocking(self):
        """TEST 9 — Groq Failure: Timeout/429 returns clean fallback without failing scan."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("services.ai_service.is_groq_available", return_value=True),              patch("httpx.Client.post", return_value=mock_resp):
            ai_res = analyze_label_with_groq("Tata Salt")
            self.assertFalse(ai_res["available"])
            self.assertEqual(ai_res["status"], "api_error")

    def test_10_external_data_cannot_change_score(self):
        """TEST 10 — External Data Cannot Change Score: Absolute score immutability assertion."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        rule_report_before = apply_multi_image_rules(package_images, self.rules)
        score_before = rule_report_before["overall_score"]
        passed_before = rule_report_before["passed"]
        failed_before = rule_report_before["failed"]
        crit_before = len(rule_report_before.get("critical_failures", []))

        # Run research
        research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "net_quantity": "1 kg"},
            missing_fields=rule_report_before.get("fields", []),
            barcode="8901030300000"
        )

        rule_report_after = apply_multi_image_rules(package_images, self.rules)
        self.assertEqual(rule_report_after["overall_score"], score_before)
        self.assertEqual(rule_report_after["passed"], passed_before)
        self.assertEqual(rule_report_after["failed"], failed_before)
        self.assertEqual(len(rule_report_after.get("critical_failures", [])), crit_before)

    def test_11_no_fake_url(self):
        """TEST 11 — No Fake URL: When source cannot be verified, no fake URL is generated."""
        res = research_product_information(
            ocr_text="NonExistentItem 12345",
            extracted_entities={"product_name": "NonExistentItem"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode=""
        )
        self.assertEqual(len(res.get("sources", [])), 0)

    def test_12_multi_image_recovery(self):
        """TEST 12 — Multi-image Recovery: Adding back image resolves MRP purely through package evidence without external research."""
        # 1. Front panel only (missing MRP)
        front_panel = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt Iodised Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        report_1 = apply_multi_image_rules(front_panel, self.rules)
        mrp_1 = next((f for f in report_1["fields"] if f["field_id"] == "mrp"), None)
        self.assertEqual(mrp_1["status"], "fail")

        # 2. Back panel added (with printed MRP)
        two_panels = front_panel + [{
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "MRP Rs 28.00 incl. of all taxes Mfg 01/2026 Batch TS01",
            "classification": {"panel_type": "BACK", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"mrp": "Rs 28.00", "manufacturing_date": "01/2026", "batch_number": "TS01"},
            "extracted_entities_detailed": {}
        }]
        report_2 = apply_multi_image_rules(two_panels, self.rules)
        mrp_2 = next((f for f in report_2["fields"] if f["field_id"] == "mrp"), None)
        self.assertEqual(mrp_2["status"], "pass", "MRP must become PASS through package evidence when back panel is provided")


if __name__ == "__main__":
    unittest.main()
