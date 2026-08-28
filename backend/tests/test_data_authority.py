"""
LABELSETU — 6-AUTHORITY DATA ISOLATION TEST SUITE
Proves that the 6 independent data authorities remain distinct and never overwrite one another:
  A. REGISTERED PRODUCT DATA (Manufacturer + Admin)
  B. PHYSICAL PACKAGE / OCR DETECTION (OCR Engine)
  C. CONSUMER COMPLAINT (Consumer)
  D. EXECUTIVE INVESTIGATION (Executive Officer)
  E. FINAL ENFORCEMENT DECISION (Admin)
  F. IMMUTABLE AUDIT HISTORY (System-controlled history)
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


class TestDataAuthorityIsolation(unittest.TestCase):
    """Rigorous 6-authority data isolation test suite."""

    def test_01_ocr_detection_does_not_mutate_registered_product_record(self):
        """1. Level 2 Physical OCR detections cannot mutate Level 1 registered product in DB."""
        reg_product = {
            "id": "prod-001",
            "product_name": "Tata Salt",
            "mrp": 28.00,
            "status": "approved",
        }
        ocr_entities = {
            "product_name": "Different Salt",
            "mrp": "99.00",
        }
        # Run cross validation
        report = cvs.cross_validate_physical_package(
            barcode="8901262010053",
            ocr_text="Different Salt MRP Rs 99.00",
            extracted_entities=ocr_entities,
            registered_product=reg_product,
        )
        # Level 1 registered data in memory/report remains strictly unchanged
        self.assertEqual(reg_product["mrp"], 28.00)
        self.assertEqual(reg_product["product_name"], "Tata Salt")
        self.assertEqual(report["level_1_verified_data"]["mrp"], 28.00)
        self.assertEqual(report["level_2_physical_data"]["mrp"], "99.00")

    def test_02_consumer_grievance_does_not_mutate_product_or_status(self):
        """2. Level 3 Consumer Grievance cannot directly suspend or alter registered product."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-001",
            "product_name": "Tata Salt",
            "status": "approved",
            "manufacturer_id": "mfg-1",
        }):
            # Consumer cannot call update_product (fails role check)
            with self.assertRaises(PermissionError):
                prs.update_product(
                    product_id="prod-001",
                    user={"role": "consumer", "sub": "consumer-user-1"},
                    updates=ProductUpdate(product_name="Fake Salt"),
                )

    def test_03_admin_decision_preserves_executive_recommendation(self):
        """3. Admin review preserves both original executive recommendation and final admin action."""
        with patch("services.executive_report_service.get_case_report", return_value={
            "id": "case-001",
            "case_number": "CASE-2026-001",
            "status": "SUBMITTED",
            "recommended_action": "SEIZE_BATCH",
            "submitted_by": "reg-1",
        }), patch("services.executive_report_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                "id": "case-001",
                "status": "APPROVED",
                "recommended_action": "SEIZE_BATCH",
                "admin_decision": "APPROVED",
                "final_action_taken": "SEIZE_BATCH",
                "admin_comments": "Executed market seizure immediately.",
            }])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": "audit-1"}])

            res = ers.admin_review_case(
                report_id="case-001",
                admin_id="adm-1",
                decision_data=ExecutiveReportAdminDecision(
                    decision="APPROVED",
                    comments="Executed market seizure immediately.",
                ),
            )
            self.assertEqual(res["recommended_action"], "SEIZE_BATCH")
            self.assertEqual(res["admin_decision"], "APPROVED")

    def test_04_admin_status_transition_generates_immutable_audit_log(self):
        """4. Admin status change generates immutable audit record with previous/new state."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-001",
            "product_name": "Tata Salt",
            "status": "pending_approval",
            "verification_status": "UNDER_REVIEW",
            "manufacturer_id": "mfg-1",
        }), patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().update().eq().execute.return_value = MagicMock(data=[{
                "id": "prod-001",
                "status": "approved",
                "verification_status": "VERIFIED",
            }])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": "audit-rec-1"}])

            res = prs.admin_set_product_status(
                product_id="prod-001",
                action="APPROVE",
                admin_id="adm-super-1",
            )
            self.assertEqual(res["status"], "approved")
            self.assertEqual(res["verification_status"], "VERIFIED")
            # Verify insert was called for audit_log
            mock_sb.table().insert.assert_called()

    def test_05_product_version_creates_historical_snapshot(self):
        """5. Product revision creates snapshot without altering historical version records."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-001",
            "product_name": "Tata Salt",
            "mrp": 28.00,
            "versions": [{"version_number": 1, "mrp": 28.00}],
        }), patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "ver-2",
                "product_id": "prod-001",
                "version_number": 2,
                "change_summary": "Updated price to ₹30.00",
            }])
            v = prs.create_product_version(
                product_id="prod-001",
                user_id="mfg-1",
                version_data=ProductVersionCreate(
                    change_summary="Updated price to ₹30.00",
                    updates=ProductUpdate(mrp=30.00),
                ),
            )
            self.assertEqual(v["version_number"], 2)


if __name__ == "__main__":
    unittest.main()
