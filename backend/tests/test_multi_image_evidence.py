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
        self.assertIsNone(report["overall_score"])  # 0 declarations assessable -> score is None (N/A)

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
        self.assertIsNone(report["overall_score"])

    def test_package_mismatch(self):
        """Test package mismatch detection when photos of different products are uploaded together."""
        img1 = {
            "image_index": 1,
            "filename": "tata_salt.jpg",
            "raw_text": "Tata Salt Iodised 1kg",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {},
        }
        img2 = {
            "image_index": 2,
            "filename": "amul_butter.jpg",
            "raw_text": "Amul Butter Pasteurised 100g",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {},
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        self.assertEqual(report["compliance_assessment"], "PACKAGE_MISMATCH")
        self.assertFalse(report["package_identity"]["match"])

    def test_duplicate_images_deduplicated(self):
        """Verify identical duplicate image uploads are deduplicated safely."""
        img1 = {
            "image_index": 1,
            "filename": "back_1.jpg",
            "raw_text": "Manufactured by: Tata Consumer Products Ltd Net Wt: 1 kg MRP: Rs 28.00 Batch: TS202601 Country of Origin: India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"net_quantity": "1 kg"},
        }
        img2 = {
            "image_index": 2,
            "filename": "back_2_duplicate.jpg",
            "raw_text": "Manufactured by: Tata Consumer Products Ltd Net Wt: 1 kg MRP: Rs 28.00 Batch: TS202601 Country of Origin: India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"net_quantity": "1 kg"},
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        self.assertEqual(report["duplicate_count"], 1)

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

    def test_conflicting_mrp_evidence(self):
        """Verify contradictory MRP values produce CONFLICTING_EVIDENCE status."""
        img1 = {
            "image_index": 1,
            "filename": "label1.jpg",
            "raw_text": "Manufactured by: Tata Ltd Net Wt: 1kg MRP: Rs 520.00",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"mrp": "520.00"},
        }
        img2 = {
            "image_index": 2,
            "filename": "label2.jpg",
            "raw_text": "Manufactured by: Tata Ltd Net Wt: 1kg MRP: Rs 550.00",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"mrp": "550.00"},
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        mrp_field = next(f for f in report["fields"] if f["field_id"] == "mrp")
        self.assertEqual(mrp_field["evidence_status"], "CONFLICTING_EVIDENCE")
        self.assertEqual(mrp_field["score_impact"], 0)

    def test_mop_to_mrp_normalization(self):
        """Verify MOP OCR typo normalization is performed safely."""
        from services.ocr_service import normalize_ocr_text_contextual
        raw = "MOP Rs 520.00 Mktd by Tata Consumer Products"
        normalized = normalize_ocr_text_contextual(raw)
        self.assertIn("MRP Rs 520.00", normalized)
        self.assertIn("Marketed by", normalized)

    def test_net_quantity_usp_isolation(self):
        """Verify Net Quantity is never corrupted by USP price per unit."""
        from services.entity_extractor import extract_entities_from_text
        text = "USP ₹ 2.60/ml\nNet Content (when packed): 200ml (202.2g)"
        extracted = extract_entities_from_text(text)
        self.assertEqual(extracted["net_quantity"], "200ml (202.2g)")
        self.assertNotEqual(extracted["net_quantity"], "2.601ml")

    def test_verification_completeness_states(self):
        """Verify verification_completeness state separation (NO_CONFIRMED_VIOLATION vs FULLY_VERIFIED)."""
        front_img = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Americana TOP Butter Cracker 60g",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"net_quantity": "60g"},
        }
        report = apply_multi_image_rules([front_img], self.rules)
        self.assertEqual(report["verification_completeness"], "NO_CONFIRMED_VIOLATION")
        self.assertEqual(report["overall_score"], 100)
        self.assertEqual(report["structured_coverage"]["manufacturing_date"], "NOT_VISIBLE")

    def test_whitespace_and_currency_formatting_not_conflicting(self):
        """Verify '400g' vs '400 g' or 'Rs 28.00' vs '28.00' is recognized as matching evidence, not CONFLICTING_EVIDENCE."""
        img1 = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Pond's Dreamflower 400g MRP Rs 28.00",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"net_quantity": "400g", "mrp": "Rs 28.00"},
        }
        img2 = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "Net Wt.: 400 g MRP 28.00 Made in India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"net_quantity": "400 g", "mrp": "28.00"},
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        net_field = next(f for f in report["fields"] if f["field_id"] == "net_quantity")
        self.assertEqual(net_field["evidence_status"], "CONFIRMED_PRESENT")

        mrp_field = next(f for f in report["fields"] if f["field_id"] == "mrp")
        self.assertEqual(mrp_field["evidence_status"], "CONFIRMED_PRESENT")

    def test_equivalent_date_formatting_not_conflicting(self):
        """Verify 'Mfg: DEC 2026' vs 'Mfg: 12/2026' is recognized as matching date evidence, not CONFLICTING_EVIDENCE."""
        img1 = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt Iodised Mfg: DEC 2026",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"mfg_date": "DEC 2026"},
        }
        img2 = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "Manufactured by: Tata Ltd Mfg: 12/2026",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"mfg_date": "12/2026"},
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        mfg_field = next(f for f in report["fields"] if f["field_id"] == "manufacturing_date")
        self.assertEqual(mfg_field["evidence_status"], "CONFIRMED_PRESENT")

    def test_multi_image_origin_non_conflict_and_genuine_conflict(self):
        """Verify 'Republic of India' vs 'Made in Republic of India' match as CONFIRMED_PRESENT, while 'India' vs 'China' is CONFLICTING_EVIDENCE."""
        # Non-conflict equivalent origin
        img1 = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Country of Origin: Republic of India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"country_of_origin": "Republic of India"},
        }
        img2 = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "Made in Republic of India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"country_of_origin": "Made in Republic of India"},
        }
        report1 = apply_multi_image_rules([img1, img2], self.rules)
        coo_field1 = next(f for f in report1["fields"] if f["field_id"] == "country_of_origin")
        self.assertEqual(coo_field1["evidence_status"], "CONFIRMED_PRESENT")

        # Genuine conflict (India vs China)
        img3 = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "Country of Origin: China",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"country_of_origin": "China"},
        }
        report2 = apply_multi_image_rules([img1, img3], self.rules)
        coo_field2 = next(f for f in report2["fields"] if f["field_id"] == "country_of_origin")
        self.assertEqual(coo_field2["evidence_status"], "CONFLICTING_EVIDENCE")

    def test_three_panel_complementary_evidence(self):
        """Test merging Front + Back + Side panels: all evidence survives without false violations."""
        front = {
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Amul Butter 100g",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL", "classification": "FRONT_PANEL"},
            "extracted_entities": {"net_quantity": "100g"},
        }
        back = {
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "Manufactured by Gujarat Milk Federation. MRP Rs 56.00 Batch B102",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL", "classification": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"manufacturer_name_address": "Gujarat Milk Federation", "mrp": "56.00", "batch_no": "B102"},
        }
        side = {
            "image_index": 3,
            "filename": "side.jpg",
            "raw_text": "Customer Care: 1800-200-0520 Country of Origin: India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "SIDE_PANEL", "classification": "SIDE_PANEL"},
            "extracted_entities": {"consumer_care": "1800-200-0520", "country_of_origin": "India"},
        }
        report = apply_multi_image_rules([front, back, side], self.rules)
        self.assertIn("front.jpg", next(f for f in report["fields"] if f["field_id"] == "net_quantity")["matched_images"])
        self.assertIn("back.jpg", next(f for f in report["fields"] if f["field_id"] == "mrp")["matched_images"])
        self.assertIn("side.jpg", next(f for f in report["fields"] if f["field_id"] == "country_of_origin")["matched_images"])


if __name__ == "__main__":
    unittest.main()
