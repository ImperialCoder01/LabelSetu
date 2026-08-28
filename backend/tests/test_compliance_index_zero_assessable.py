"""
LABELSETU COMPLIANCE INDEX ZERO-ASSESSABLE REGRESSION TEST SUITE
Tests the 5 critical compliance index behaviors:
1. 0/8 assessable -> overall_score is None / N/A (NEVER 100)
2. 8/8 assessable & compliant -> overall_score is 100/100
3. Partially assessable -> existing scoring behavior unchanged
4. Non-compliant assessable -> existing non-compliant scoring unchanged
5. Empty violations list with assessable_count == 0 does NOT produce 100
"""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.rule_engine import load_rules, apply_multi_image_rules, apply_rules


class TestComplianceIndexZeroAssessable(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_01_zero_of_eight_assessable_returns_none_never_100(self):
        """TEST 1: 0/8 assessable declarations returns status=INSUFFICIENT_EVIDENCE and overall_score=None (never 100)."""
        front_only_no_declarations = [{
            "image_index": 1,
            "filename": "front_artwork.jpg",
            "raw_text": "Americana Butter Crisps",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(front_only_no_declarations, self.rules)

        self.assertIsNone(rep["overall_score"], "Score must be None (N/A) when 0/8 declarations are assessable")
        self.assertNotEqual(rep["overall_score"], 100, "Score must NEVER be 100 when 0/8 declarations are assessable")
        self.assertEqual(rep["evidence_coverage"], "0/8 declarations assessable")
        self.assertIn(rep["verification_completeness"], ["INSUFFICIENT_EVIDENCE", "UNREADABLE"])

    def test_02_eight_of_eight_assessable_and_compliant_remains_100(self):
        """TEST 2: 8/8 assessable and compliant remains 100/100."""
        text_fully_compliant = (
            "Amul Butter\n"
            "Brand: Amul\n"
            "Manufactured by: Gujarat Cooperative Milk Marketing Federation Ltd\n"
            "Net Quantity: 100g\n"
            "Manufacturing Date: 15/08/2026\n"
            "MRP: Rs 56.00 (incl. of all taxes)\n"
            "Unit Sale Price: Rs 560 per kg\n"
            "Consumer Care: 1800-200-0520\n"
            "Country of Origin: India"
        )
        rep = apply_rules(text_fully_compliant, self.rules)

        self.assertEqual(rep["overall_score"], 100)
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["compliance_assessment"], "COMPLIANT")
        self.assertEqual(rep["verification_completeness"], "FULLY_VERIFIED")
        self.assertEqual(rep["passed"], 8)
        self.assertEqual(rep["evidence_coverage"], "8/8 declarations assessable")

    def test_03_partially_assessable_scan_scoring_unchanged(self):
        """TEST 3: Partially assessable scan (5 pass, 3 missing on readable back panel) scores 75/100."""
        text_partial = (
            "Tata Salt\n"
            "Iodised Salt\n"
            "Manufactured by: Tata Consumer Products India Ltd\n"
            "Net Wt: 1 kg\n"
            "MRP: Rs 28.00\n"
            "Batch: TS202601\n"
            "Country of Origin: India"
        )
        rep = apply_rules(text_partial, self.rules)

        self.assertEqual(rep["overall_score"], 75)
        self.assertEqual(rep["status"], "partial")
        self.assertEqual(rep["compliance_assessment"], "PARTIALLY_COMPLIANT")
        self.assertEqual(rep["passed"], 5)
        self.assertEqual(rep["evidence_coverage"], "8/8 declarations assessable")

    def test_04_non_compliant_assessable_scoring_unchanged(self):
        """TEST 4: Non-compliant assessable declarations (readable panel with 0 matches) produces status=fail."""
        # Mixed/Back panel photographed and readable, but 0 mandatory declarations present
        empty_on_readable_back = [{
            "image_index": 1,
            "filename": "back_blank.jpg",
            "raw_text": "Some random text without mandatory declarations",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(empty_on_readable_back, self.rules)

        self.assertEqual(rep["status"], "fail")
        self.assertEqual(rep["compliance_assessment"], "NON_COMPLIANT")
        self.assertEqual(rep["verification_completeness"], "CONFIRMED_NON_COMPLIANCE")
        self.assertEqual(rep["evidence_coverage"], "8/8 declarations assessable")
        self.assertLessEqual(rep["overall_score"], 10)

    def test_05_empty_violations_list_does_not_produce_100_when_zero_assessable(self):
        """TEST 5: Ensure an empty violations list does NOT automatically produce 100 when assessable_count == 0."""
        unreadable_image = [{
            "image_index": 1,
            "filename": "blurry.jpg",
            "raw_text": "",
            "quality_info": {"quality_status": "UNREADABLE"},
            "classification": {"panel_type": "UNREADABLE", "classification": "UNREADABLE_IMAGE"},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(unreadable_image, self.rules)

        # Confirm critical_failures and minor_failures are both empty
        self.assertEqual(len(rep["critical_failures"]), 0)
        self.assertEqual(len(rep["minor_failures"]), 0)
        # Confirm that despite 0 violations, score is None / N/A, NOT 100
        self.assertIsNone(rep["overall_score"])
        self.assertEqual(rep["evidence_coverage"], "0/8 declarations assessable")


if __name__ == "__main__":
    unittest.main()
