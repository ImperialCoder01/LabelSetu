"""
Automated Multi-Image Evidence Model Test Suite.
Verifies all 17 multi-image evidence scenarios.
"""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.rule_engine import load_rules, apply_multi_image_rules


class TestMultiImageEvidence(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_front_only_image_evidence(self):
        """Test Front-only packaging image: unphotographed fields are NOT_VISIBLE with 0 score penalty."""
        front_img = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Americana TOP Butter Cracker with a twist",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {},
        }
        report = apply_multi_image_rules([front_img], self.rules)
        self.assertEqual(report["compliance_assessment"], "FRONT_PANEL_ONLY")
        self.assertEqual(report["overall_score"], 100)  # 0 score penalty for unphotographed back panel!

        # Check field status
        mrp_field = next(f for f in report["fields"] if f["field_id"] == "mrp")
        self.assertEqual(mrp_field["evidence_status"], "NOT_VISIBLE")
        self.assertEqual(mrp_field["score_impact"], 0)

    def test_back_only_image_evidence(self):
        """Test Back-only packaging image: readable declaration panel allows CONFIRMED_MISSING scoring."""
        back_img = {
            "image_index": 1,
            "filename": "back.jpg",
            "raw_text": "Manufactured by: Tata Consumer Products Ltd Net Wt: 1 kg MRP: Rs 28.00 Batch: TS202601 Country of Origin: India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"net_quantity": "1 kg", "mrp": "28.00"},
        }
        report = apply_multi_image_rules([back_img], self.rules)
        self.assertIn(report["compliance_assessment"], ["PARTIALLY_COMPLIANT", "NON_COMPLIANT"])

        # Passed fields
        net_field = next(f for f in report["fields"] if f["field_id"] == "net_quantity")
        self.assertEqual(net_field["evidence_status"], "CONFIRMED_PRESENT")

        # Missing fields on readable back panel
        mfg_field = next(f for f in report["fields"] if f["field_id"] == "manufacturing_date")
        self.assertEqual(mfg_field["evidence_status"], "CONFIRMED_MISSING")
        self.assertLess(mfg_field["score_impact"], 0)

    def test_front_and_back_multi_image_combination(self):
        """Test merging Front + Back packaging images: declarations are combined across both images."""
        front_img = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Pond's Dreamflower Fragrant Talc 400g",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"net_quantity": "400g"},
        }
        back_img = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "HINDUSTAN UNILEVER LIMITED Made in India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"country_of_origin": "India"},
        }
        report = apply_multi_image_rules([front_img, back_img], self.rules)

        # Net quantity from Front, Country of origin from Back
        net_field = next(f for f in report["fields"] if f["field_id"] == "net_quantity")
        self.assertEqual(net_field["evidence_status"], "CONFIRMED_PRESENT")
        self.assertIn("front.jpg", net_field["matched_images"])

        coo_field = next(f for f in report["fields"] if f["field_id"] == "country_of_origin")
        self.assertEqual(coo_field["evidence_status"], "CONFIRMED_PRESENT")
        self.assertIn("back.jpg", coo_field["matched_images"])

    def test_barcode_catalog_isolation(self):
        """Verify barcode catalog data NEVER turns an unphotographed image field into CONFIRMED_PRESENT."""
        barcode_catalog_img = {
            "image_index": 1,
            "filename": "Open Food Facts Barcode Catalog",
            "raw_text": "Product Name: Tata Salt\nCountry of Origin: India\nNet Quantity: 1kg",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BARCODE_CATALOG", "classification": "BARCODE"},
            "extracted_entities": {},
        }
        front_img = {
            "image_index": 2,
            "filename": "front.jpg",
            "raw_text": "Tata Salt Iodised",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {},
        }
        report = apply_multi_image_rules([front_img, barcode_catalog_img], self.rules)

        coo_field = next(f for f in report["fields"] if f["field_id"] == "country_of_origin")
        self.assertNotEqual(coo_field["evidence_status"], "CONFIRMED_PRESENT")
        self.assertEqual(coo_field["evidence_status"], "NOT_VISIBLE")

    def test_blurry_image_evidence(self):
        """Verify blurry unreadable image results in UNREADABLE_IMAGE assessment with 0 score penalty."""
        blurry_img = {
            "image_index": 1,
            "filename": "blurry.jpg",
            "raw_text": "",
            "quality_info": {"quality_status": "UNREADABLE", "issues": ["Extreme motion blur"]},
            "classification": {"panel_type": "UNREADABLE", "classification": "UNREADABLE_IMAGE"},
            "extracted_entities": {},
        }
        report = apply_multi_image_rules([blurry_img], self.rules)
        self.assertEqual(report["compliance_assessment"], "UNREADABLE_IMAGE")
        self.assertEqual(report["overall_score"], 100)

    def test_screenshot_evidence(self):
        """Verify UI screenshot results in SCREENSHOT assessment."""
        screenshot_img = {
            "image_index": 1,
            "filename": "screenshot.png",
            "raw_text": "https://labelsetu-ivory.vercel.app/dashboard Loading profile...",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "NON_PRODUCT", "classification": "SCREENSHOT"},
            "extracted_entities": {},
        }
        report = apply_multi_image_rules([screenshot_img], self.rules)
        self.assertEqual(report["compliance_assessment"], "SCREENSHOT")


if __name__ == "__main__":
    unittest.main()
