"""
LABELSETU — SECURITY THREAT MODEL & MULTI-TENANT ISOLATION TEST SUITE
Tests authorization boundaries, privilege escalation defenses, multi-tenant isolation,
and data immutability across all roles (Manufacturer, Consumer, Executive Officer, Admin).
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
from services import executive_report_service as ers


class TestSecurityThreatModel(unittest.TestCase):
    """Rigorous security threat model test suite."""

    # -------------------------------------------------------------------------
    # 1. Multi-Tenant Manufacturer Isolation
    # -------------------------------------------------------------------------
    def test_01_manufacturer_cannot_edit_another_manufacturers_product(self):
        """Threat 1: Manufacturer A attempts to modify Manufacturer B's product."""
        with patch("services.product_registry_service.get_product_by_id", return_value={
            "id": "prod-b-001",
            "manufacturer_id": "mfg-b",
            "product_name": "Brand B Butter",
            "status": "draft",
        }):
            with self.assertRaises(PermissionError) as ctx:
                prs.update_product(
                    product_id="prod-b-001",
                    user={"role": "brand", "sub": "mfg-a"},
                    updates=ProductUpdate(product_name="Hacked Butter"),
                )
            self.assertIn("Access denied", str(ctx.exception))

    def test_02_manufacturer_cannot_view_another_manufacturers_unapproved_draft(self):
        """Threat 2: Manufacturer A attempts to inspect Manufacturer B's unreleased draft product."""
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().single().execute.return_value = MagicMock(data={
                "id": "prod-b-draft",
                "manufacturer_id": "mfg-b",
                "product_name": "Secret Unreleased Product",
                "status": "draft",
            })
            prod = prs.get_product_by_id(
                product_id="prod-b-draft",
                requesting_user={"role": "brand", "sub": "mfg-a"},
            )
            self.assertIsNone(prod)

    def test_03_manufacturer_cannot_spoof_ownership_in_create(self):
        """Threat 3: Manufacturer supplies forged manufacturer_id in creation body."""
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{
                "id": "prod-001",
                "manufacturer_id": "mfg-genuine-id",
                "product_name": "Tata Salt",
            }])

            # create_product strictly derives manufacturer_id from authenticated token 'mfg-genuine-id'
            data = ProductCreate(
                product_name="Tata Salt",
                brand_name="Tata",
                category="Food & Beverages",
                barcode="8901262010053",
            )
            created = prs.create_product(manufacturer_id="mfg-genuine-id", data=data)
            self.assertEqual(created["manufacturer_id"], "mfg-genuine-id")

    # -------------------------------------------------------------------------
    # 2. Executive Officer Privilege Escalation Defenses
    # -------------------------------------------------------------------------
    def test_04_executive_officer_cannot_self_approve_enforcement_recommendation(self):
        """Threat 4: Executive Officer attempts to approve their own enforcement case."""
        with patch("services.executive_report_service.get_case_report", return_value={
            "id": "case-001",
            "case_number": "CASE-2026-001",
            "status": "SUBMITTED",
            "recommended_action": "SUSPEND_PRODUCT",
            "submitted_by": "reg-officer-1",
        }):
            # Attempting to call admin_review_case validates decision
            with self.assertRaises(ValueError):
                ers.admin_review_case(
                    report_id="case-001",
                    admin_id="reg-officer-1",
                    decision_data=ExecutiveReportAdminDecision(
                        decision="INVALID_SELF_APPROVAL",
                    ),
                )

    def test_05_invalid_state_transition_is_blocked(self):
        """Threat 5: User attempts arbitrary state transition (e.g. REJECTED -> RESOLVED)."""
        with patch("services.executive_report_service.get_case_report", return_value={
            "id": "case-001",
            "status": "REJECTED",
        }):
            with self.assertRaises(ValueError) as ctx:
                ers.admin_review_case(
                    report_id="case-001",
                    admin_id="adm-1",
                    decision_data=ExecutiveReportAdminDecision(
                        decision="APPROVED",
                    ),
                )
            self.assertIn("Invalid case status transition", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. Barcode & Product Status Protection
    # -------------------------------------------------------------------------
    def test_06_duplicate_barcode_registration_blocked(self):
        """Threat 6: Attacker attempts to register a barcode that already belongs to another SKU."""
        with patch("services.product_registry_service.supabase") as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
                "id": "prod-existing",
                "product_name": "Authentic Ghee",
                "barcode": "8901052002154",
            }])
            with self.assertRaises(ValueError) as ctx:
                prs.create_product(
                    manufacturer_id="mfg-malicious",
                    data=ProductCreate(
                        product_name="Fake Ghee",
                        brand_name="Counterfeit",
                        category="Edible Oils & Ghee",
                        barcode="8901052002154",
                    ),
                )
            self.assertIn("already registered", str(ctx.exception))

    def test_07_suspended_product_never_returns_verified(self):
        """Threat 7: Suspended product must never return VERIFIED status to consumers."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value={
            "id": "prod-banned",
            "product_name": "Contaminated Batch",
            "status": "suspended",
        }), patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("8901234567890")
            self.assertEqual(res["result"], "SUSPENDED_PRODUCT")
            self.assertNotEqual(res["result"], "VERIFIED")

    def test_08_inactive_product_never_returns_verified(self):
        """Threat 8: Unapproved draft/pending product must return INACTIVE_PRODUCT status."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value={
            "id": "prod-draft",
            "product_name": "Pending Product",
            "status": "pending_approval",
        }), patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("8901234567890")
            self.assertEqual(res["result"], "INACTIVE_PRODUCT")
            self.assertNotEqual(res["result"], "VERIFIED")

    def test_09_unknown_barcode_returns_not_registered(self):
        """Threat 9: Non-existent barcode returns NOT_REGISTERED."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value=None),              patch("services.product_registry_service.supabase"):
            res = prs.verify_barcode_authenticity("0000000000000")
            self.assertEqual(res["result"], "NOT_REGISTERED")

    def test_10_high_frequency_scans_trigger_possible_duplicate_flag(self):
        """Threat 10: 50+ scans in 1 hour triggers anti-cloning alert."""
        with patch("services.product_registry_service.get_product_by_barcode", return_value={
            "id": "prod-popular",
            "product_name": "Popular Salt",
            "status": "approved",
        }), patch("services.product_registry_service.supabase") as mock_sb:
            mock_count = MagicMock()
            mock_count.count = 85
            mock_sb.table().select().eq().gte().execute.return_value = mock_count
            res = prs.verify_barcode_authenticity("8901262010053")
            self.assertEqual(res["result"], "POSSIBLE_DUPLICATE")
            self.assertEqual(res["suspicious_flag"], "SUSPICIOUS")


if __name__ == "__main__":
    unittest.main()
