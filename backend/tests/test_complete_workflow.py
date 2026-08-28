"""
LABELSETU — COMPLETE WORKFLOW TEST SUITE
Tests the full Manufacturer → Product → Consumer → Executive → Admin lifecycle:
1. Product Registry & Category Declarations
2. Manufacturer Isolation & Authorization
3. Product Versioning & Snapshots
4. Barcode Authenticity & Anti-Cloning Telemetry
5. Physical OCR vs Level 1 Registered Data Cross-Validation
6. Executive Officer Investigation Cases
7. Admin Approval & Governance Queue
8. Notifications & Audit Trail
9. Compliance Engine & Invariant Inviolability
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product_models import (
    ProductCreate,
    ProductUpdate,
    ProductVersionCreate,
    ExecutiveReportCreate,
    ExecutiveReportAdminDecision,
)
from services import product_registry_service as prs
from services import cross_validation_service as cvs
from services import executive_report_service as ers
from services import notification_service as ns
from services.rule_engine import load_rules, apply_multi_image_rules


class TestCompleteWorkflow(unittest.TestCase):
    """Complete multi-role workflow test suite."""

    def setUp(self):
        self.rules = load_rules()
        self.sample_product_data = ProductCreate(
            product_name="Tata Salt Vacuum Evaporated",
            brand_name="Tata",
            category="Food & Beverages",
            barcode="8901262010053",
            mrp=28.00,
            net_quantity="1 kg",
            unit_sale_price="₹28.00 per kg",
            manufacturer_name_address="Tata Consumer Products Ltd, Kolkata",
            consumer_care="1800-200-0520",
            fssai_lic="10014022002652",
            country_of_origin="India",
            veg_non_veg="VEGETARIAN",
        )

    # -------------------------------------------------------------------------
    # 1. Product Registry Tests
    # -------------------------------------------------------------------------
    def test_01_create_product_success(self):
        """1. Manufacturer creates product with pending_approval status."""
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "prod-123",
                "product_name": self.sample_product_data.product_name,
                "status": "pending_approval",
                "verification_status": "UNDER_REVIEW",
                "barcode": self.sample_product_data.barcode,
            }])
            res = prs.create_product(manufacturer_id="mfg-1", data=self.sample_product_data)
            self.assertEqual(res["product_name"], "Tata Salt Vacuum Evaporated")
            self.assertEqual(res["status"], "pending_approval")

    def test_02_duplicate_barcode_rejected(self):
        """2. Duplicate barcode registration is rejected."""
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
                "id": "prod-existing",
                "product_name": "Existing Salt",
                "barcode": "8901262010053",
            }])
            with self.assertRaises(ValueError):
                prs.create_product(manufacturer_id="mfg-1", data=self.sample_product_data)

    def test_03_manufacturer_cannot_edit_other_brand_product(self):
        """3. Manufacturer isolation: cannot update another brand's product."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-123",
            "manufacturer_id": "mfg-other",
            "product_name": "Other Brand Salt",
        }):
            with self.assertRaises(PermissionError):
                prs.update_product(
                    product_id="prod-123",
                    user={"role": "brand", "sub": "mfg-me"},
                    updates=ProductUpdate(mrp=32.00),
                )

    # -------------------------------------------------------------------------
    # 2. Product Versioning & Historical Snapshots
    # -------------------------------------------------------------------------
    def test_04_create_product_version(self):
        """4. Creating a product revision records new version snapshot."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-123",
            "product_name": "Tata Salt",
            "mrp": 28.00,
            "versions": [{"version_number": 1}],
        }), patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "product_id": "prod-123",
                "version_number": 2,
                "change_summary": "Updated MRP to ₹30.00",
            }])
            v = prs.create_product_version(
                product_id="prod-123",
                user_id="mfg-1",
                version_data=ProductVersionCreate(
                    change_summary="Updated MRP to ₹30.00",
                    updates=ProductUpdate(mrp=30.00),
                ),
            )
            self.assertEqual(v["version_number"], 2)

    # -------------------------------------------------------------------------
    # 3. Barcode Authenticity & Anti-Cloning Telemetry
    # -------------------------------------------------------------------------
    def test_05_verify_barcode_registered_and_approved(self):
        """5. Approved registered barcode returns VERIFIED status."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value={
            "id": "prod-123",
            "product_name": "Tata Salt",
            "status": "approved",
            "mrp": 28.00,
        }), patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("8901262010053")
            self.assertEqual(res["result"], "VERIFIED")
            self.assertEqual(res["suspicious_flag"], "NORMAL")

    def test_06_verify_barcode_not_registered(self):
        """6. Unregistered barcode returns NOT_REGISTERED status."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value=None), patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("9999999999999")
            self.assertEqual(res["result"], "NOT_REGISTERED")

    def test_07_verify_barcode_suspended_product(self):
        """7. Suspended product returns SUSPENDED_PRODUCT status."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value={
            "id": "prod-123",
            "product_name": "Banned Substance",
            "status": "suspended",
        }), patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("8901234567890")
            self.assertEqual(res["result"], "SUSPENDED_PRODUCT")

    # -------------------------------------------------------------------------
    # 4. Physical OCR vs Level 1 Registered Data Cross-Validation
    # -------------------------------------------------------------------------
    def test_08_cross_validation_matching_declarations(self):
        """8. Matching physical OCR declarations returns MATCH."""
        reg = {
            "product_name": "Tata Salt",
            "brand_name": "Tata",
            "mrp": 28.00,
            "net_quantity": "1 kg",
            "status": "approved",
            "fssai_lic": "10014022002652",
        }
        ocr_entities = {
            "brand": "Tata",
            "mrp": "28.00",
            "net_quantity": "1 kg",
            "fssai_lic": "10014022002652",
        }
        report = cvs.cross_validate_physical_package(
            barcode="8901262010053",
            ocr_text="Tata Salt 1 kg MRP Rs 28.00",
            extracted_entities=ocr_entities,
            registered_product=reg,
        )
        self.assertEqual(report["match_status"], "MATCH")
        self.assertEqual(len(report["discrepancies"]), 0)

    def test_09_cross_validation_mrp_overcharge_discrepancy(self):
        """9. Physical printed MRP higher than registered MRP triggers MRP_MISMATCH."""
        reg = {
            "product_name": "Tata Salt",
            "brand_name": "Tata",
            "mrp": 28.00,
            "status": "approved",
        }
        ocr_entities = {
            "brand": "Tata",
            "mrp": "35.00",
        }
        report = cvs.cross_validate_physical_package(
            barcode="8901262010053",
            ocr_text="Tata Salt MRP Rs 35.00",
            extracted_entities=ocr_entities,
            registered_product=reg,
        )
        self.assertEqual(report["match_status"], "DISCREPANCY_DETECTED")
        mrp_disc = next(d for d in report["discrepancies"] if d["field"] == "mrp")
        self.assertEqual(mrp_disc["discrepancy_type"], "MRP_MISMATCH")
        self.assertEqual(mrp_disc["severity"], "HIGH")

    # -------------------------------------------------------------------------
    # 5. Executive Officer Case Investigations
    # -------------------------------------------------------------------------
    def test_10_executive_creates_case_report(self):
        """10. Executive Officer submits enforcement investigation case."""
        with patch("services.executive_report_service.supabase") as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "case-001",
                "case_number": "CASE-2026-ABC123",
                "report_type": "VIOLATION",
                "severity": "CRITICAL",
                "status": "SUBMITTED",
                "recommended_action": "SUSPEND_PRODUCT",
            }])
            case_data = ExecutiveReportCreate(
                barcode="8901262010053",
                report_type="VIOLATION",
                severity="CRITICAL",
                description="MRP overcharged on physical packaging (₹35 vs registered ₹28).",
                recommended_action="SUSPEND_PRODUCT",
            )
            res = ers.create_case_report(regulator_id="reg-1", data=case_data)
            self.assertEqual(res["status"], "SUBMITTED")
            self.assertEqual(res["recommended_action"], "SUSPEND_PRODUCT")

    # -------------------------------------------------------------------------
    # 6. Admin Approval & Governance Decisions
    # -------------------------------------------------------------------------
    def test_11_admin_approves_product_registration(self):
        """11. Admin approves pending product registration."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-123",
            "product_name": "Tata Salt",
            "status": "pending_approval",
            "manufacturer_id": "mfg-1",
        }), patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                "id": "prod-123",
                "status": "approved",
                "verification_status": "VERIFIED",
            }])
            res = prs.admin_set_product_status(product_id="prod-123", action="APPROVE", admin_id="adm-1")
            self.assertEqual(res["status"], "approved")
            self.assertEqual(res["verification_status"], "VERIFIED")

    def test_12_admin_reviews_executive_case_recommendation(self):
        """12. Admin reviews and approves executive officer recommendation."""
        with patch("services.executive_report_service.get_case_report", return_value={
            "id": "case-001",
            "case_number": "CASE-2026-ABC123",
            "status": "SUBMITTED",
            "recommended_action": "SUSPEND_PRODUCT",
            "submitted_by": "reg-1",
        }), patch("services.executive_report_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                "id": "case-001",
                "status": "APPROVED",
                "admin_decision": "APPROVED",
            }])
            res = ers.admin_review_case(
                report_id="case-001",
                admin_id="adm-1",
                decision_data=ExecutiveReportAdminDecision(
                    decision="APPROVED",
                    comments="Approved product suspension pending laboratory inspection.",
                ),
            )
            self.assertEqual(res["status"], "APPROVED")

    # -------------------------------------------------------------------------
    # 7. Notifications & Audit Trail
    # -------------------------------------------------------------------------
    def test_13_create_and_list_notifications(self):
        """13. In-app notification creation and list retrieval."""
        with patch("services.notification_service.supabase") as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "notif-1",
                "user_id": "user-1",
                "title": "Product Approved",
                "is_read": False,
            }])
            notif = ns.create_notification(
                user_id="user-1",
                title="Product Approved",
                message="Your product was approved.",
                notif_type="PRODUCT_APPROVAL",
            )
            self.assertEqual(notif["title"], "Product Approved")

    # -------------------------------------------------------------------------
    # 8. Compliance Scoring Invariance Check
    # -------------------------------------------------------------------------
    def test_14_existing_compliance_scoring_remains_intact(self):
        """14. 8/8 assessable & compliant scores exactly 100/100."""
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

    def test_15_zero_assessable_returns_none_never_100(self):
        """15. Zero assessable declarations returns overall_score=None (N/A)."""
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
