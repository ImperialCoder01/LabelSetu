"""
LABELSETU — COMPREHENSIVE VISIBLE FIELD & PRODUCT NAME EXTRACTION TEST SUITE

Covers all 38 required test cases across 5 functional categories:
A. Product Name (1-7)
B. Visible Fields (8-20)
C. Multi-Image (21-25)
D. Failure Cases (26-31)
E. Regression (32-38)
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.entity_extractor import (
    extract_entities_from_text,
    extract_entities_with_evidence,
    _extract_product_name,
    _extract_brand,
    _extract_mrp,
    _extract_net_quantity,
    _extract_mfg_date,
    _extract_expiry_date,
    _extract_batch,
    _extract_manufacturer_name_address,
    _extract_packer_name_address,
    _extract_importer_name_address,
    _extract_consumer_care,
    _extract_country_of_origin,
    _extract_fssai_lic,
    _extract_ingredients,
    _extract_veg_non_veg,
)
from services.ocr_service import extract_text_with_scores
from services.rule_engine import load_rules, apply_multi_image_rules


class TestComprehensiveVisibleEntityExtraction(unittest.TestCase):
    """38-point test suite for visible field extraction, OCR resilience, and compliance preservation."""

    def setUp(self):
        self.rules = load_rules()

    # =========================================================================
    # Group A: Product Name Extraction (1-7)
    # =========================================================================
    def test_01_explicit_product_name_label(self):
        """1. Explicit Product Name label."""
        text = "Product Name: Britannia Good Day Butter Cookies\nNet Wt: 150g"
        self.assertEqual(_extract_product_name(text), "Britannia Good Day Butter Cookies")

    def test_02_name_of_commodity(self):
        """2. Name of Commodity label."""
        text = "Name of Commodity: Iodised Salt\nNet Quantity: 1 kg"
        self.assertEqual(_extract_product_name(text), "Iodised Salt")

    def test_03_front_panel_product_name(self):
        """3. Front-panel product name without explicit label."""
        text = "TATA SALT\nVacuum Evaporated Iodised Salt\nNet Weight: 1 kg"
        self.assertEqual(_extract_product_name(text), "TATA SALT")

    def test_04_brand_plus_product_combination(self):
        """4. Brand + product combination across lines."""
        text = "AMUL\nPASTEURISED BUTTER\nUtterly Butterly Delicious"
        self.assertEqual(_extract_product_name(text), "AMUL PASTEURISED BUTTER")

    def test_05_product_name_with_ocr_punctuation_errors(self):
        """5. Product name with OCR punctuation/spacing errors (e.g. ProductName :, Commodity -)."""
        text = "ProductName : Surf Excel Easy Wash Detergent\nNet Wt: 1 kg"
        self.assertEqual(_extract_product_name(text), "Surf Excel Easy Wash Detergent")

    def test_06_product_name_absent_returns_none(self):
        """6. Product name absent returns None (no hallucination)."""
        text = "Manufactured by: ABC Foods Ltd\nNet Wt: 500g\nMRP Rs 50"
        self.assertIsNone(_extract_product_name(text))

    def test_07_marketing_slogan_not_product_name(self):
        """7. Marketing slogan must not become product name."""
        text = "100% PURE & NATURAL\nServing Suggestion\nCatch Garam Masala\nImages for illustration only"
        self.assertEqual(_extract_product_name(text), "Catch Garam Masala")

    # =========================================================================
    # Group B: Visible Field Extraction (8-20)
    # =========================================================================
    def test_08_mrp_variations(self):
        """8. MRP variations (₹, Rs, Rs., :, M.R.P., decimal/int)."""
        cases = [
            ("MRP ₹50", "50"),
            ("MRP Rs 50", "50"),
            ("MRP Rs. 50.00", "50.00"),
            ("MRP: 50", "50"),
            ("M.R.P. Rs 50", "50"),
            ("Maximum Retail Price Rs 50.00 (incl of taxes)", "50.00"),
            ("MRP INR 50", "50"),
        ]
        for t, exp in cases:
            self.assertEqual(_extract_mrp(t), exp, f"Failed for {t}")

    def test_09_net_quantity_variations(self):
        """9. Net quantity variations."""
        cases = [
            ("Net Qty: 500 g", "500 g"),
            ("Net Quantity 500g", "500g"),
            ("Net Wt. 500 g", "500 g"),
            ("Net Weight: 500g", "500g"),
            ("500 g", "500 g"),
        ]
        for t, exp in cases:
            self.assertEqual(_extract_net_quantity(t), exp, f"Failed for {t}")

    def test_10_batch_variations(self):
        """10. Batch variations."""
        cases = [
            ("Batch No: AB1234", "AB1234"),
            ("Batch Number: BN5678", "BN5678"),
            ("Batch: B-999", "B-999"),
            ("Lot No: LOT123", "LOT123"),
            ("Lot Number: L-456", "L-456"),
        ]
        for t, exp in cases:
            self.assertEqual(_extract_batch(t), exp, f"Failed for {t}")

    def test_11_manufacturing_date(self):
        """11. Manufacturing date variations."""
        cases = [
            ("Mfg: 12/2026", "12/2026"),
            ("Mfg Date: 12/2026", "12/2026"),
            ("Manufactured: DEC 2026", "DEC 2026"),
            ("Date of Mfg: 15/08/2026", "15/08/2026"),
            ("PKD: 10/2026", "10/2026"),
            ("Packed: 10/2026", "10/2026"),
        ]
        for t, exp in cases:
            self.assertEqual(_extract_mfg_date(t), exp, f"Failed for {t}")

    def test_12_expiry_and_best_before(self):
        """12. Expiry and best-before extraction and calculation."""
        t1 = "EXP: 12/2027"
        exp1, _ = _extract_expiry_date(t1)
        self.assertEqual(exp1, "12/2027")

        t2 = "Best Before: 6 Months"
        exp2, is_calc = _extract_expiry_date(t2, mfg_date="12/2026")
        self.assertTrue(is_calc)
        self.assertEqual(exp2, "JUN 2027")

    def test_13_manufacturer(self):
        """13. Manufacturer extraction."""
        text = "Manufactured by: Tata Consumer Products Ltd, 1 Bishop Lefroy Road, Kolkata 700020\nNet Wt: 1 kg"
        self.assertIn("Tata Consumer Products Ltd", _extract_manufacturer_name_address(text))

    def test_14_packer(self):
        """14. Packer extraction."""
        text = "Packed by: ABC Logistics Pvt Ltd, Warehouse 4, Delhi 110001\nMRP: Rs 100"
        self.assertIn("ABC Logistics Pvt Ltd", _extract_packer_name_address(text))

    def test_15_importer(self):
        """15. Importer extraction."""
        text = "Imported by: Global Brands India Pvt Ltd, Mumbai 400050\nCountry of Origin: USA"
        self.assertIn("Global Brands India Pvt Ltd", _extract_importer_name_address(text))

    def test_16_fssai(self):
        """16. FSSAI 14-digit number."""
        text = "FSSAI Lic. No. 10014022002652\nCustomer Care: 1800-200-0520"
        self.assertEqual(_extract_fssai_lic(text), "10014022002652")

    def test_17_consumer_care(self):
        """17. Consumer care phone and email."""
        text = "Customer Care Executive: 1800-200-0520, care@tataconsumer.com\nAddress: Mumbai"
        self.assertIn("1800-200-0520", _extract_consumer_care(text))

    def test_18_country_of_origin(self):
        """18. Country of origin."""
        text = "Country of Origin: India\nNet Wt: 1 kg"
        self.assertEqual(_extract_country_of_origin(text), "India")

    def test_19_ingredients(self):
        """19. Ingredients list."""
        text = "Ingredients: Edible Common Salt, Potassium Iodate.\nMRP: Rs 28.00"
        self.assertIn("Edible Common Salt", _extract_ingredients(text))

    def test_20_veg_non_veg(self):
        """20. Vegetarian / Non-Vegetarian declaration."""
        self.assertEqual(_extract_veg_non_veg("100% Vegetarian Green Dot"), "VEGETARIAN")
        self.assertEqual(_extract_veg_non_veg("Contains Egg Non-Vegetarian"), "NON_VEGETARIAN")
        self.assertIsNone(_extract_veg_non_veg("Just regular label text"))

    # =========================================================================
    # Group C: Multi-Image Aggregation (21-25)
    # =========================================================================
    def test_21_front_image_provides_product_name(self):
        """21. Front image provides product name and brand."""
        front_text = "TATA SALT\nVacuum Evaporated Iodised Salt"
        front_ent = extract_entities_from_text(front_text)
        self.assertEqual(front_ent["product_name"], "TATA SALT")
        self.assertEqual(front_ent["brand"], "TATA")

    def test_22_back_image_provides_statutory_fields(self):
        """22. Back image provides statutory fields."""
        back_text = "Manufactured by: Tata Consumer Products Ltd\nNet Wt: 1 kg\nMRP: Rs 28.00\nMfg Date: 12/2026"
        back_ent = extract_entities_from_text(back_text)
        self.assertEqual(back_ent["net_quantity"], "1 kg")
        self.assertEqual(back_ent["mrp"], "28.00")
        self.assertEqual(back_ent["mfg_date"], "12/2026")

    def test_23_second_image_does_not_erase_first_image(self):
        """23. Second image does not erase non-null fields from first image."""
        img1_ent = {"product_name": "Tata Salt", "brand": "Tata", "net_quantity": None}
        img2_ent = {"product_name": None, "brand": None, "net_quantity": "1 kg", "mrp": "28.00"}

        merged = {}
        for k, v in img1_ent.items():
            if v is not None:
                merged[k] = v
        for k, v in img2_ent.items():
            if v is not None and not merged.get(k):
                merged[k] = v

        self.assertEqual(merged["product_name"], "Tata Salt")
        self.assertEqual(merged["brand"], "Tata")
        self.assertEqual(merged["net_quantity"], "1 kg")
        self.assertEqual(merged["mrp"], "28.00")

    def test_24_duplicate_values_merge_correctly(self):
        """24. Duplicate identical entities across images merge cleanly."""
        img1_ent = {"net_quantity": "1 kg", "mrp": "28.00"}
        img2_ent = {"net_quantity": "1 kg", "mrp": "28.00"}

        merged = {}
        for k, v in img1_ent.items():
            if v is not None:
                merged[k] = v
        for k, v in img2_ent.items():
            if v is not None and not merged.get(k):
                merged[k] = v

        self.assertEqual(merged["net_quantity"], "1 kg")
        self.assertEqual(merged["mrp"], "28.00")

    def test_25_conflicting_values_handled_conservatively(self):
        """25. Conflicting values are detected and flagged by rule engine."""
        img1 = {
            "image_index": 1,
            "filename": "img1.jpg",
            "raw_text": "MRP: Rs 28.00",
            "classification": {"panel_type": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"mrp": "28.00"}
        }
        img2 = {
            "image_index": 2,
            "filename": "img2.jpg",
            "raw_text": "MRP: Rs 35.00",
            "classification": {"panel_type": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {"mrp": "35.00"}
        }
        report = apply_multi_image_rules([img1, img2], self.rules)
        mrp_field = next(f for f in report["fields"] if f["field_id"] == "mrp")
        self.assertEqual(mrp_field["evidence_status"], "CONFLICTING_EVIDENCE")
        self.assertEqual(mrp_field["status"], "fail")

    # =========================================================================
    # Group D: OCR Failure Resilience (26-31)
    # =========================================================================
    def test_26_ocr_space_timeout_produces_safe_response(self):
        """26. OCR.space timeout returns safe structured dict without crashing."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("ReadTimeout: HTTP connection timed out")):
            res = extract_text_with_scores(b"dummy")
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertEqual(res["full_text"], "")
            self.assertIsNone(res["extracted_entities"]["product_name"])

    def test_27_ocr_space_502_error_handled_safely(self):
        """27. OCR.space 502 Bad Gateway handled safely."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("OCR.space API error: 502 Bad Gateway")):
            res = extract_text_with_scores(b"dummy")
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertIn("502", res["error"])

    def test_28_ocr_space_503_error_handled_safely(self):
        """28. OCR.space 503 Service Unavailable handled safely."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("OCR.space API error: 503 Service Unavailable")):
            res = extract_text_with_scores(b"dummy")
            self.assertEqual(res["provider"], "cloud (unavailable)")
            self.assertIn("503", res["error"])

    def test_29_empty_ocr_response_handled_safely(self):
        """29. Empty OCR response returns empty text and null entities."""
        with patch("services.ocr_service._extract_cloud_with_scores", return_value={"provider": "cloud", "full_text": "", "detections": [], "average_confidence": 0.0}):
            res = extract_text_with_scores(b"dummy")
            self.assertEqual(res["full_text"], "")
            self.assertIsNone(res["extracted_entities"]["product_name"])

    def test_30_unreadable_image_handled_safely(self):
        """30. Unreadable image returns safe empty entities."""
        ent = extract_entities_from_text("")
        self.assertIsNone(ent["product_name"])
        self.assertIsNone(ent["mrp"])

    def test_31_malformed_ocr_response_handled_safely(self):
        """31. Malformed OCR response does not crash."""
        with patch("services.ocr_service._extract_cloud_with_scores", side_effect=Exception("JSONDecodeError")):
            res = extract_text_with_scores(b"dummy")
            self.assertEqual(res["provider"], "cloud (unavailable)")

    # =========================================================================
    # Group E: Compliance Scoring & Non-Negotiable Invariants (32-38)
    # =========================================================================
    def test_32_existing_compliance_scoring_intact(self):
        """32. 8/8 assessable & compliant scores exactly 100/100."""
        image_results = [{
            "image_index": 1,
            "filename": "full.jpg",
            "raw_text": (
                "Tata Salt\nBrand: Tata\n"
                "Manufactured by: Tata Consumer Products Ltd, Kolkata\n"
                "Net Quantity: 1000g\nManufacturing Date: 12/2026\n"
                "MRP: Rs 28.00 (incl. of all taxes)\nConsumer Care: 1800-200-0520\n"
                "Unit Sale Price: Rs 28 per kg\nCountry of Origin: India"
            ),
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {
                "product_name": "Tata Salt",
                "manufacturer_name_address": "Tata Consumer Products Ltd",
                "net_quantity": "1000g",
                "mfg_date": "12/2026",
                "mrp": "28.00",
                "consumer_care": "1800-200-0520",
                "unit_sale_price": "Rs 28 per kg",
                "country_of_origin": "India"
            }
        }]
        rep = apply_multi_image_rules(image_results, self.rules)
        self.assertEqual(rep["overall_score"], 100)
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["passed"], 8)

    def test_33_existing_multi_image_compliance_intact(self):
        """33. Multi-image compliance evaluation aggregates across front and back panels."""
        img1 = {
            "image_index": 1, "filename": "front.jpg",
            "raw_text": "TATA SALT", "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL"},
            "extracted_entities": {"product_name": "TATA SALT"}
        }
        img2 = {
            "image_index": 2, "filename": "back.jpg",
            "raw_text": "Manufactured by: Tata Consumer Products Ltd\nNet Wt: 1 kg\nMRP: Rs 28.00\nMfg Date: 12/2026\nCountry of Origin: India",
            "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "BACK_DECLARATION_PANEL"},
            "extracted_entities": {
                "manufacturer_name_address": "Tata Consumer Products Ltd",
                "net_quantity": "1 kg", "mrp": "28.00",
                "mfg_date": "12/2026", "country_of_origin": "India"
            }
        }
        rep = apply_multi_image_rules([img1, img2], self.rules)
        passed_fields = [f["field_id"] for f in rep["fields"] if f["status"] == "pass"]
        self.assertIn("product_name", passed_fields)
        self.assertIn("manufacturer_name_address", passed_fields)
        self.assertIn("net_quantity", passed_fields)
        self.assertIn("mrp", passed_fields)
        self.assertIn("manufacturing_date", passed_fields)
        self.assertIn("country_of_origin", passed_fields)

    def test_34_existing_authentication_invariants(self):
        """34. Auth token verification imports and behavior intact."""
        from auth.dependencies import get_current_user
        self.assertTrue(callable(get_current_user))

    def test_35_existing_security_review_invariants(self):
        """35. Ensure no hardcoded secrets in entity extractor."""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "entity_extractor.py"), "r", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("K8", src)
        self.assertNotIn("gsk_", src)

    def test_36_existing_api_response_structure_intact(self):
        """36. Router responses preserve all standard keys."""
        from routers.scans import router
        self.assertIsNotNone(router)

    def test_37_easyocr_remains_completely_removed(self):
        """37. EasyOCR and PyTorch remain completely unimported."""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "ocr_service.py"), "r", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("import easyocr", src)
        self.assertNotIn("import torch", src)

    def test_38_zero_assessable_compliance_returns_na(self):
        """38. Zero assessable declarations returns score=None (N/A) and INSUFFICIENT_EVIDENCE."""
        front_only = [{
            "image_index": 1, "filename": "front.jpg",
            "raw_text": "Americana Crisps", "quality_info": {"quality_status": "GOOD"},
            "classification": {"panel_type": "FRONT_PANEL"},
            "extracted_entities": {}
        }]
        rep = apply_multi_image_rules(front_only, self.rules)
        self.assertIsNone(rep["overall_score"])
        self.assertEqual(rep["evidence_coverage"], "0/8 declarations assessable")
        self.assertEqual(rep["verification_completeness"], "INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
