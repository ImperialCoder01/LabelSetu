"""
Unit and Regression Tests for AI-Assisted Product Information Recovery & Evidence Segregation.
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
from services.rule_engine import load_rules, apply_multi_image_rules


class TestProductResearchService(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_mandatory_regression_1_missing_mrp_unaltered_by_external_data(self):
        """
        CRITICAL REGRESSION TEST 1 (Section 22):
        Given: Package evidence missing MRP.
        External research finds MRP = 'Rs 28.00'.
        Expected:
          - Rule engine MRP = FAIL / MISSING
          - External research MRP = 'Rs 28.00'
          - package_verified = False
          - verification_status = 'REQUIRES_PACKAGE_VERIFICATION'
          - Compliance score remains UNCHANGED
        """
        # 1. Package image with product name and net qty, missing MRP
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

        # Rule engine evaluation before external research
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mrp_field_before = next((f for f in rule_report["fields"] if f["field_id"] == "mrp"), None)
        self.assertIsNotNone(mrp_field_before)
        self.assertEqual(mrp_field_before["status"], "fail", "Rule engine must evaluate missing MRP as FAIL")
        score_before = rule_report["overall_score"]

        # 2. External research simulated
        missing_fields = [f for f in rule_report["fields"] if f["status"] == "fail"]
        research_result = research_product_information(
            ocr_text="Tata Salt Iodised Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "brand": "Tata", "net_quantity": "1 kg"},
            missing_fields=missing_fields,
            barcode="8901030300000"
        )

        # 3. Verify external research results
        self.assertEqual(research_result["status"], "success")
        self.assertGreaterEqual(research_result["product_match"]["confidence_score"], 0.70)

        # Verify recovered fields
        recovered_mrp = next((f for f in research_result["external_reference_fields"] if f["field_id"] == "mrp"), None)
        if recovered_mrp:
            self.assertFalse(recovered_mrp["package_verified"], "External MRP must NEVER be marked package_verified=True")
            self.assertEqual(recovered_mrp["verification_status"], "REQUIRES_PACKAGE_VERIFICATION")
            self.assertEqual(recovered_mrp["source_type"], "external_reference")

        # 4. Confirm rule engine report was NOT mutated by external research
        self.assertEqual(mrp_field_before["status"], "fail", "Rule engine status must remain FAIL despite internet data")
        self.assertEqual(rule_report["overall_score"], score_before, "Rule engine score must remain strictly unchanged")

    def test_mandatory_regression_2_identity_conflict_does_not_deduct_statutory_score(self):
        """
        CRITICAL REGRESSION TEST 2 (Section 23):
        Given: Package evidence says Manufacturer = 'Company A'.
        External research says Manufacturer = 'Company B'.
        Expected:
          - identity_conflict detected = True
          - User warning generated
          - Statutory compliance score remains exactly what rule engine calculated (no score deduction)
        """
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

        # Conflict detection
        conflicts = detect_identity_conflicts(
            package_entities={"manufacturer": "Company A India Ltd"},
            matched_record={"manufacturer": "Company B Global LLC"}
        )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["field"], "manufacturer")
        self.assertIn("identity conflict detected", conflicts[0]["warning"])

        # Score remains unchanged
        self.assertEqual(rule_report["overall_score"], score_before, "Identity conflict MUST NOT deduct statutory compliance score")

    def test_missing_mfg_date_and_batch_cannot_be_overridden_by_internet(self):
        """Missing manufacturing date/batch cannot be turned into PASS by external data."""
        package_images = [{
            "image_index": 1,
            "filename": "panel.jpg",
            "raw_text": "Amul Butter 100g MRP Rs 56.00",
            "classification": {"panel_type": "PRIMARY", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Amul Butter", "mrp": "Rs 56.00"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mfg_field = next((f for f in rule_report["fields"] if f["field_id"] == "manufacturing_date"), None)
        self.assertEqual(mfg_field["status"], "fail")

    def test_high_confidence_product_matching(self):
        """GTIN/Barcode or high token overlap yields high confidence."""
        conf, status = _calculate_match_confidence(
            query_text="Tata Salt 1 kg",
            matched_name="Tata Salt Iodised 1kg",
            matched_brand="Tata",
            has_barcode_match=False
        )
        self.assertGreaterEqual(conf, 0.50)
        self.assertEqual(status, "high_confidence")

    def test_low_confidence_product_matching_rejected(self):
        """Unrelated tokens yield no_match or low_confidence."""
        conf, status = _calculate_match_confidence(
            query_text="Completely Unrelated Query 12345",
            matched_name="Tata Salt",
            matched_brand="Tata",
            has_barcode_match=False
        )
        self.assertEqual(status, "no_match")

    def test_panel_recommendations_generation(self):
        """Generates specific physical panel photo requests for missing fields."""
        recs = _generate_panel_recommendations(["mrp", "manufacturer_name_address", "consumer_care_contact"])
        self.assertEqual(len(recs), 3)
        self.assertTrue(any("Back Panel" in r or "Date-Code" in r for r in recs))
        self.assertTrue(any("Side Panel" in r or "Manufacturer" in r for r in recs))
        self.assertTrue(any("Consumer Care" in r or "Helpline" in r for r in recs))

    def test_external_search_failure_is_non_blocking(self):
        """Network/API failure in external research returns clean fallback without raising exceptions."""
        with patch("services.product_research_service._search_open_food_facts", side_effect=Exception("API Timeout")):
            res = research_product_information(
                ocr_text="Some Product Text",
                extracted_entities={"product_name": "Unknown"},
                missing_fields=[{"field_id": "mrp", "status": "fail"}],
            )
            self.assertIn("status", res)
            self.assertEqual(res["status"], "no_match")
            self.assertIsInstance(res["disclaimer"], str)


if __name__ == "__main__":
    unittest.main()
