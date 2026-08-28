"""
LABELSETU — AUTHENTICITY MODEL & CONSERVATIVE VERIFICATION TEST SUITE
Tests the 8 core authenticity and evidence-based verification cases:
  CASE 1: Registered barcode + active product + matching package -> VERIFIED PRODUCT
  CASE 2: Unknown barcode -> NOT_REGISTERED
  CASE 3: Registered barcode + suspended product -> SUSPENDED_PRODUCT
  CASE 4: Registered barcode + MRP mismatch -> REGISTERED PRODUCT FOUND + MRP_MISMATCH
  CASE 5: Registered barcode + product name / brand mismatch -> BRAND_MISMATCH / REQUIRES_REVIEW
  CASE 6: High-frequency repeated scans -> POSSIBLE_DUPLICATE / SUSPICIOUS
  CASE 7: OCR unavailable -> barcode verification still works reliably
  CASE 8: Barcode copied onto package -> system avoids false certainty claims
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import product_registry_service as prs
from services import cross_validation_service as cvs


class TestAuthenticityModel(unittest.TestCase):
    """Authenticity and conservative verification test suite."""

    def test_case_1_registered_active_matching_package(self):
        """CASE 1: Registered barcode + active product + matching package -> VERIFIED PRODUCT."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt Vacuum Evaporated",
            "brand_name": "Tata",
            "barcode": "8901262010053",
            "mrp": 28.00,
            "net_quantity": "1 kg",
            "status": "approved",
        }
        with patch("services.product_registry_service.get_product_by_barcode", return_value=reg_prod),              patch("services.product_registry_service.supabase"):
            verif = prs.verify_barcode_authenticity("8901262010053")
            self.assertEqual(verif["result"], "VERIFIED")

            # OCR match
            cv_res = cvs.cross_validate_physical_package(
                barcode="8901262010053",
                ocr_text="Tata Salt Vacuum Evaporated 1 kg MRP Rs 28.00",
                extracted_entities={"brand": "Tata", "mrp": "28.00", "net_quantity": "1 kg"},
                registered_product=reg_prod,
            )
            self.assertEqual(cv_res["match_status"], "MATCH")
            self.assertEqual(len(cv_res["discrepancies"]), 0)

    def test_case_2_unknown_barcode(self):
        """CASE 2: Unknown barcode -> NOT_REGISTERED."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value=None),              patch("services.product_registry_service.supabase"):
            verif = prs.verify_barcode_authenticity("9999999999999")
            self.assertEqual(verif["result"], "NOT_REGISTERED")

    def test_case_3_suspended_product(self):
        """CASE 3: Registered barcode + suspended product -> SUSPENDED_PRODUCT."""
        suspended_prod = {
            "id": "prod-suspended",
            "product_name": "Contaminated Lot",
            "status": "suspended",
        }
        with patch("services.product_registry_service.get_product_by_barcode", return_value=suspended_prod),              patch("services.product_registry_service.supabase"):
            verif = prs.verify_barcode_authenticity("8901234567890")
            self.assertEqual(verif["result"], "SUSPENDED_PRODUCT")

    def test_case_4_mrp_mismatch_overcharge(self):
        """CASE 4: Registered barcode + MRP mismatch -> DISCREPANCY_DETECTED (MRP_MISMATCH)."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "brand_name": "Tata",
            "mrp": 28.00,
            "status": "approved",
        }
        cv_res = cvs.cross_validate_physical_package(
            barcode="8901262010053",
            ocr_text="Tata Salt MRP Rs 35.00",
            extracted_entities={"brand": "Tata", "mrp": "35.00"},
            registered_product=reg_prod,
        )
        self.assertEqual(cv_res["match_status"], "DISCREPANCY_DETECTED")
        mrp_disc = next(d for d in cv_res["discrepancies"] if d["field"] == "mrp")
        self.assertEqual(mrp_disc["discrepancy_type"], "MRP_MISMATCH")
        self.assertEqual(mrp_disc["severity"], "HIGH")

    def test_case_5_brand_mismatch(self):
        """CASE 5: Registered barcode + brand mismatch -> BRAND_MISMATCH."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "brand_name": "Tata",
            "status": "approved",
        }
        cv_res = cvs.cross_validate_physical_package(
            barcode="8901262010053",
            ocr_text="Generic Brand Salt",
            extracted_entities={"brand": "Generic Brand"},
            registered_product=reg_prod,
        )
        self.assertEqual(cv_res["match_status"], "DISCREPANCY_DETECTED")
        brand_disc = next(d for d in cv_res["discrepancies"] if d["field"] == "brand_name")
        self.assertEqual(brand_disc["discrepancy_type"], "BRAND_MISMATCH")

    def test_case_6_high_frequency_scan_velocity_alert(self):
        """CASE 6: High-frequency repeated scans -> POSSIBLE_DUPLICATE."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "status": "approved",
        }
        with patch("services.product_registry_service.get_product_by_barcode", return_value=reg_prod),              patch("services.product_registry_service.supabase") as mock_sb:
            mock_count = MagicMock()
            mock_count.count = 62
            mock_sb.table().select().eq().gte().execute.return_value = mock_count

            verif = prs.verify_barcode_authenticity("8901262010053")
            self.assertEqual(verif["result"], "POSSIBLE_DUPLICATE")
            self.assertEqual(verif["suspicious_flag"], "SUSPICIOUS")

    def test_case_7_ocr_unavailable_barcode_verification_still_works(self):
        """CASE 7: OCR unavailable -> barcode verification still works reliably."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "status": "approved",
        }
        with patch("services.product_registry_service.get_product_by_barcode", return_value=reg_prod),              patch("services.product_registry_service.supabase"):
            verif = prs.verify_barcode_authenticity("8901262010053")
            self.assertEqual(verif["result"], "VERIFIED")
            self.assertIsNotNone(verif["verified_product"])

    def test_case_8_copied_barcode_avoids_false_certainty_claim(self):
        """CASE 8: Copied barcode on package -> message specifies 'registered product found', not 100% genuine physical item."""
        reg_prod = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "status": "approved",
        }
        with patch("services.product_registry_service.get_product_by_barcode", return_value=reg_prod),              patch("services.product_registry_service.supabase"):
            verif = prs.verify_barcode_authenticity("8901262010053")
            self.assertNotIn("100% original", verif["message"].lower())
            self.assertNotIn("guaranteed genuine physical unit", verif["message"].lower())


if __name__ == "__main__":
    unittest.main()
