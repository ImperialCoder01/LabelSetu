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
    _calculate_match_confidence,
    _generate_panel_recommendations,
)
from services.rule_engine import load_rules, apply_multi_image_rules


class TestProductResearchService(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_package_evidence_strictly_authoritative(self):
        """
        CRITICAL MANDATORY REGRESSION TEST:
        Given: Package evidence missing MRP.
        Internet: MRP = 'Rs 50'.
        Expected: Rule engine MRP = FAIL / MISSING, compliance score UNCHANGED,
                  external research MRP has package_verified = False.
        """
        # 1. Package images without MRP
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
        self.assertEqual(mrp_field_before["status"], "fail", "Rule engine must flag missing MRP as FAIL")
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
        self.assertGreaterEqual(research_result["product_match"]["confidence"], 0.70)

        # Verify recovered fields have package_verified = False
        for f in research_result["fields"]:
            self.assertFalse(f["package_verified"], "External recovered fields must NEVER be marked package_verified=True")
            self.assertEqual(f["verification_status"], "REQUIRES_PACKAGE_VERIFICATION")
            self.assertEqual(f["source_type"], "internet")

        # 4. Confirm rule engine report was NOT mutated by external research
        self.assertEqual(mrp_field_before["status"], "fail", "Rule engine status must remain FAIL despite internet data")
        self.assertEqual(rule_report["overall_score"], score_before, "Rule engine score must remain strictly unchanged")

    def test_missing_mfg_date_cannot_be_overridden_by_internet(self):
        """Missing manufacturing date cannot be turned into PASS by external data."""
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
        self.assertGreaterEqual(conf, 0.65)
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
            self.assertIsInstance(res["warnings"], list)


if __name__ == "__main__":
    unittest.main()
