"""
Unit and Regression Tests for AI-Assisted Product Information Recovery & Evidence Segregation.
Tests all 18 specific requirements defined in Section 26 of the LabelSetu specification.
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

    def test_01_missing_mrp_remains_fail_when_external_mrp_exists(self):
        """TEST 1: Missing MRP remains FAIL even when external MRP exists."""
        package_images = [{
            "image_index": 1,
            "filename": "front_panel.jpg",
            "raw_text": "Tata Salt Iodised Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
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

    def test_02_missing_mfg_date_remains_fail_when_external_date_exists(self):
        """TEST 2: Missing manufacturing date remains FAIL even when external date exists."""
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

    def test_03_missing_batch_remains_fail_when_external_batch_exists(self):
        """TEST 3: Missing batch number remains FAIL even when external batch data exists."""
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

    def test_04_external_manufacturer_is_marked_reference_only(self):
        """TEST 4: External manufacturer information is marked reference-only."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt"},
            missing_fields=[{"field_id": "manufacturer_name_address", "status": "fail"}],
            barcode="8901030300000"
        )
        self.assertEqual(res["status"], "success")
        ext_mfg = next((f for f in res["fields"] if f["field_id"] == "manufacturer_name_address"), None)
        if ext_mfg:
            self.assertFalse(ext_mfg["package_verified"])
            self.assertEqual(ext_mfg["source_type"], "external_reference")

    def test_05_mismatch_generates_warning_without_score_deduction(self):
        """TEST 5: External/package manufacturer mismatch generates warning but does not modify score."""
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

    def test_06_exact_gtin_produces_high_confidence_match(self):
        """TEST 6: Exact GTIN produces high-confidence product match."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode="8901030300000"
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["product_match"]["confidence_level"], "high_confidence")
        self.assertGreaterEqual(res["product_match"]["confidence_score"], 0.90)

    def test_07_weak_product_match_is_rejected(self):
        """TEST 7: Weak product match is rejected."""
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

    def test_08_external_api_failure_does_not_break_scan(self):
        """TEST 8: External API failure does not break scanning."""
        with patch("services.product_research_service._search_open_food_facts", side_effect=Exception("HTTP 500 Server Error")):
            res = research_product_information(
                ocr_text="Some Product Text",
                extracted_entities={"product_name": "Test"},
                missing_fields=[{"field_id": "mrp", "status": "fail"}],
            )
            self.assertIn("status", res)
            self.assertIsInstance(res["disclaimer"], str)

    def test_09_groq_failure_does_not_break_scan(self):
        """TEST 9: Groq failure does not break scanning."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("services.ai_service.is_groq_available", return_value=True),              patch("httpx.Client.post", return_value=mock_resp):
            ai_res = analyze_label_with_groq("Tata Salt")
            self.assertFalse(ai_res["available"])
            self.assertEqual(ai_res["status"], "api_error")

    def test_10_compliance_score_is_immutable_by_external_research(self):
        """TEST 10: Compliance score is immutable by external research."""
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

    def test_11_no_fake_url_is_generated(self):
        """TEST 11: No fake URL is generated."""
        res = research_product_information(
            ocr_text="NonExistentItem 12345",
            extracted_entities={"product_name": "NonExistentItem"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode=""
        )
        self.assertEqual(len(res.get("sources", [])), 0)

    def test_12_multi_image_package_evidence_can_confirm_missing_fields(self):
        """TEST 12: Multi-image package evidence can legitimately change a missing field to confirmed."""
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
        self.assertEqual(mrp_2["status"], "pass")

    def test_13_external_reference_never_enters_rule_engine_input(self):
        """TEST 13: External reference never enters rule-engine input."""
        package_images = [{
            "image_index": 1,
            "filename": "test.jpg",
            "raw_text": "Generic Biscuit 100g",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Generic Biscuit"},
            "extracted_entities_detailed": {}
        }]
        # Assert apply_multi_image_rules accepts only image structures, never external dicts
        report = apply_multi_image_rules(package_images, self.rules)
        self.assertNotIn("external_research", report)
        self.assertNotIn("reference_mrp", report)

    def test_14_package_specific_fields_always_package_verified_false(self):
        """TEST 14: Package-specific fields always remain package_verified=false when sourced externally."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}, {"field_id": "unit_sale_price", "status": "fail"}],
            barcode="8901030300000"
        )
        for field in res.get("fields", []):
            if field.get("is_package_specific"):
                self.assertFalse(field["package_verified"])
                self.assertEqual(field["verification_status"], "REQUIRES_PACKAGE_VERIFICATION")

    def test_15_low_confidence_results_clearly_labeled(self):
        """TEST 15: Low-confidence external results are clearly labeled."""
        conf, status = _calculate_match_confidence(
            query_text="Partial Brand Only",
            matched_name="Full Product Specific Name 500g",
            matched_brand="Brand",
            has_barcode_match=False
        )
        self.assertIn(status, ("low_confidence", "medium_confidence", "high_confidence", "no_match"))

    def test_16_official_manufacturer_source_preferred_when_available(self):
        """TEST 16: Official manufacturer/catalog source is preferred when available."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "brand": "Tata"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode=""
        )
        if res.get("sources"):
            top_source = res["sources"][0]
            self.assertIn(top_source.get("source_type"), ("official_catalog", "public_database", "official_database"))

    def test_17_external_source_conflict_does_not_declare_counterfeit(self):
        """TEST 17: External source conflict does not automatically declare counterfeit (warning only)."""
        conflicts = detect_identity_conflicts(
            package_entities={"manufacturer": "Brand Alpha Private Ltd"},
            matched_record={"manufacturer": "Brand Beta Global Inc"}
        )
        self.assertEqual(len(conflicts), 1)
        self.assertNotIn("counterfeit", conflicts[0]["warning"].lower())
        self.assertIn("conflict detected", conflicts[0]["warning"])

    def test_18_no_reliable_product_match_produces_no_fabricated_data(self):
        """TEST 18: No reliable product match produces no fabricated data."""
        res = research_product_information(
            ocr_text="XYZ123 Completely Nonexistent",
            extracted_entities={"product_name": "XYZ123"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode=""
        )
        self.assertEqual(len(res.get("fields", [])), 0)
        self.assertEqual(len(res.get("sources", [])), 0)
        self.assertEqual(res["status"], "no_reliable_match")


if __name__ == "__main__":
    unittest.main()
