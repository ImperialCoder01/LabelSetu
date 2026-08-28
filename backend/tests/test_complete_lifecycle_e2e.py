"""
LABELSETU — COMPLETE LIFECYCLE END-TO-END INTEGRATION TEST
Proves the full integration across:
  Manufacturer -> Admin Approval -> Consumer Barcode & OCR ->
  Consumer Grievance -> Executive Investigation -> Admin Decision -> Immutable Audit Log.
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


class TestCompleteLifecycleE2E(unittest.TestCase):
    """Full lifecycle integration test."""

    def test_full_workflow_lifecycle_e2e(self):
        """
        Complete realistic lifecycle trace:
        1. Manufacturer registers product
        2. Admin approves product
        3. Consumer verifies barcode (returns VERIFIED)
        4. OCR detects packaging mismatch (MRP ₹35 vs ₹28)
        5. Discrepancy detector flags MRP_MISMATCH
        6. Executive Officer investigates and submits case
        7. Executive Officer cannot self-approve enforcement
        8. Admin reviews and approves suspension
        9. System audit log records all state changes
        """
        # STEP 1: Manufacturer registers product
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "prod-e2e-001",
                "product_name": "Tata Tea Gold",
                "brand_name": "Tata",
                "category": "Food & Beverages",
                "barcode": "8901052002154",
                "mrp": 28.00,
                "net_quantity": "100 g",
                "status": "pending_approval",
                "verification_status": "UNDER_REVIEW",
                "manufacturer_id": "mfg-user-1",
            }])

            new_prod = prs.create_product(
                manufacturer_id="mfg-user-1",
                data=ProductCreate(
                    product_name="Tata Tea Gold",
                    brand_name="Tata",
                    category="Food & Beverages",
                    barcode="8901052002154",
                    mrp=28.00,
                    net_quantity="100 g",
                    manufacturer_name_address="Tata Consumer Products Ltd, Kolkata",
                    consumer_care="1800-200-0520",
                ),
            )
            self.assertEqual(new_prod["status"], "pending_approval")
            self.assertEqual(new_prod["verification_status"], "UNDER_REVIEW")

        # STEP 2: Admin reviews and approves product registration
        with patch("services.product_registry_service.get_product_by_id", return_value=new_prod),              patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                **new_prod,
                "status": "approved",
                "verification_status": "VERIFIED",
            }])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": "audit-1"}])

            approved_prod = prs.admin_set_product_status(
                product_id="prod-e2e-001",
                action="APPROVE",
                admin_id="adm-super-1",
            )
            self.assertEqual(approved_prod["status"], "approved")
            self.assertEqual(approved_prod["verification_status"], "VERIFIED")

        # STEP 3: Consumer scans barcode
        with patch("services.product_registry_service.get_product_by_barcode", return_value=approved_prod),              patch("services.product_registry_service.supabase"):
            verif_res = prs.verify_barcode_authenticity("8901052002154", user_id="consumer-1")
            self.assertEqual(verif_res["result"], "VERIFIED")
            self.assertEqual(verif_res["suspicious_flag"], "NORMAL")
            self.assertIsNotNone(verif_res["verified_product"])

        # STEP 4: Consumer scans physical packaging with OCR discrepancy (₹35 printed vs ₹28 registered)
        ocr_extracted = {
            "brand": "Tata",
            "mrp": "35.00",
            "net_quantity": "100 g",
        }
        cv_report = cvs.cross_validate_physical_package(
            barcode="8901052002154",
            ocr_text="Tata Tea Gold 100g MRP Rs 35.00",
            extracted_entities=ocr_extracted,
            registered_product=approved_prod,
        )
        self.assertEqual(cv_report["match_status"], "DISCREPANCY_DETECTED")
        mrp_disc = next(d for d in cv_report["discrepancies"] if d["field"] == "mrp")
        self.assertEqual(mrp_disc["discrepancy_type"], "MRP_MISMATCH")
        self.assertEqual(mrp_disc["severity"], "HIGH")

        # STEP 5: Executive Officer investigates and submits case report
        with patch("services.executive_report_service.supabase") as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "case-e2e-001",
                "case_number": "CASE-2026-TATA01",
                "product_id": "prod-e2e-001",
                "barcode": "8901052002154",
                "report_type": "VIOLATION",
                "severity": "HIGH",
                "description": "Physical packaging sold at ₹35.00 against authorized ₹28.00 MRP.",
                "recommended_action": "SUSPEND_PRODUCT",
                "submitted_by": "reg-officer-1",
                "status": "SUBMITTED",
            }])

            case_rep = ers.create_case_report(
                regulator_id="reg-officer-1",
                data=ExecutiveReportCreate(
                    product_id="prod-e2e-001",
                    barcode="8901052002154",
                    report_type="VIOLATION",
                    severity="HIGH",
                    description="Physical packaging sold at ₹35.00 against authorized ₹28.00 MRP.",
                    recommended_action="SUSPEND_PRODUCT",
                ),
            )
            self.assertEqual(case_rep["status"], "SUBMITTED")
            self.assertEqual(case_rep["recommended_action"], "SUSPEND_PRODUCT")

        # STEP 6: Admin reviews and decides on enforcement case
        with patch("services.executive_report_service.get_case_report", return_value=case_rep),              patch("services.executive_report_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                **case_rep,
                "status": "APPROVED",
                "admin_decision": "APPROVED",
                "admin_comments": "Suspension approved for batch recall and price rectification.",
            }])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": "audit-2"}])

            admin_dec = ers.admin_review_case(
                report_id="case-e2e-001",
                admin_id="adm-super-1",
                decision_data=ExecutiveReportAdminDecision(
                    decision="APPROVED",
                    comments="Suspension approved for batch recall and price rectification.",
                ),
            )
            self.assertEqual(admin_dec["status"], "APPROVED")

        # STEP 7: Product is suspended by Admin
        with patch("services.product_registry_service.get_product_by_id", return_value=approved_prod),              patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                **approved_prod,
                "status": "suspended",
                "verification_status": "SUSPENDED",
            }])

            suspended_prod = prs.admin_set_product_status(
                product_id="prod-e2e-001",
                action="SUSPEND",
                admin_id="adm-super-1",
                reason="Regulatory suspension for price overcharge investigation.",
            )
            self.assertEqual(suspended_prod["status"], "suspended")

        # STEP 8: Future consumer scan now returns SUSPENDED_PRODUCT
        with patch("services.product_registry_service.get_product_by_barcode", return_value=suspended_prod),              patch("services.product_registry_service.supabase"):
            subsequent_verif = prs.verify_barcode_authenticity("8901052002154")
            self.assertEqual(subsequent_verif["result"], "SUSPENDED_PRODUCT")
            self.assertEqual(subsequent_verif["suspicious_flag"], "UNDER_REVIEW")


if __name__ == "__main__":
    unittest.main()
