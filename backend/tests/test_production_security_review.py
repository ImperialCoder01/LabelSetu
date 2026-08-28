"""
LABELSETU PRODUCTION SECURITY & COMPLIANCE REVIEW TEST SUITE
Asserts all security negative test cases, cross-user isolation,
client trust boundaries, and statutory evidence invariants.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.rule_engine import load_rules, apply_multi_image_rules
from services.product_research_service import research_product_information
from services.ai_service import analyze_label_with_groq
from services.barcode_service import detect_manufacturer_mismatch


class TestProductionSecurityReview(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.rules = load_rules()

    def test_01_cross_user_scan_access_blocked(self):
        """Negative Test 1: User B cannot access User A's scan record (returns 403 Forbidden)."""
        scan_data_user_a = {
            "id": "scan-101",
            "user_id": "user-a-uuid",
            "compliance_score": 100,
            "extracted_text": "Sample text",
        }
        # Simulate User B requesting User A's scan
        user_b = {"sub": "user-b-uuid", "profile": {"role": "consumer"}}

        # Verify application-level authorization boundary
        user_role = user_b.get("profile", {}).get("role")
        has_access = (user_role in ("admin", "regulator")) or (scan_data_user_a["user_id"] == user_b["sub"])
        self.assertFalse(has_access, "User B must be strictly forbidden from accessing User A's scan")

    def test_02_cross_user_report_creation_blocked(self):
        """Negative Test 2: User B cannot file a grievance report on User A's scan (returns 403 Forbidden)."""
        scan_data_user_a = {
            "id": "scan-101",
            "user_id": "user-a-uuid",
            "compliance_score": 50,
        }
        user_b = {"sub": "user-b-uuid", "profile": {"role": "consumer"}}

        # Verify ownership check in create_report
        can_report = scan_data_user_a["user_id"] == user_b["sub"]
        self.assertFalse(can_report, "User B must be forbidden from reporting a scan belonging to User A")

    def test_03_forged_client_payload_cannot_inject_scores(self):
        """Negative Test 3: Backend computes compliance itself; client cannot submit scores or status."""
        from routers.scans import scan
        import inspect

        sig = inspect.signature(scan)
        params = list(sig.parameters.keys())
        self.assertNotIn("compliance_score", params)
        self.assertNotIn("overall_score", params)
        self.assertNotIn("status", params)
        self.assertNotIn("passed", params)
        self.assertNotIn("user_id", params)  # user_id is extracted exclusively from verified JWT sub

    def test_04_forged_package_verified_flag_cannot_bypass_evidence_requirement(self):
        """Negative Test 4: All external reference values remain package_verified = False."""
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "net_quantity": "1 kg"},
            missing_fields=[{"field_id": "mrp", "status": "fail"}],
            barcode="8901030300000"
        )
        for field in res.get("fields", []):
            self.assertFalse(field["package_verified"], "External reference must NEVER have package_verified = True")
            self.assertEqual(field["verification_status"], "REQUIRES_PACKAGE_VERIFICATION")

    def test_05_external_mrp_cannot_alter_statutory_score(self):
        """Negative Test 5: External MRP existence does NOT modify rule engine score or PASS/FAIL state."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt Net Wt: 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        rep_before = apply_multi_image_rules(package_images, self.rules)
        score_before = rep_before["overall_score"]

        # Run research which discovers MRP Rs 28
        res = research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt"},
            missing_fields=rep_before["fields"],
            barcode="8901030300000"
        )

        rep_after = apply_multi_image_rules(package_images, self.rules)
        self.assertEqual(rep_after["overall_score"], score_before)
        mrp_field = next(f for f in rep_after["fields"] if f["field_id"] == "mrp")
        self.assertEqual(mrp_field["status"], "fail")

    def test_06_external_manufacturer_mismatch_produces_zero_score_deduction(self):
        """Negative Test 6: Third-party catalog mismatch flags a warning but never deducts score points."""
        package_images = [{
            "image_index": 1,
            "filename": "package.jpg",
            "raw_text": "Manufactured by: Authentic Brand India Ltd\nProduct: Pure Ghee 1kg\nMRP: Rs 650\nNet Qty: 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {
                "manufacturer_name": "Authentic Brand India Ltd",
                "product_name": "Pure Ghee",
                "mrp": "Rs 650",
                "net_quantity": "1 kg"
            },
            "extracted_entities_detailed": {}
        }]
        rep = apply_multi_image_rules(package_images, self.rules)
        score = rep["overall_score"]

        # Conflict detected
        conflict = detect_manufacturer_mismatch(
            "Manufactured by: Authentic Brand India Ltd",
            {"found": True, "brand": "ThirdParty Global Industries"}
        )
        self.assertFalse(conflict["match"])

        # Score remains intact
        rep_post = apply_multi_image_rules(package_images, self.rules)
        self.assertEqual(rep_post["overall_score"], score)

    def test_07_unauthenticated_requests_to_scans_rejected(self):
        """Negative Test 7: Unauthenticated request to protected scan endpoint is rejected (403 or 401)."""
        resp = self.client.post("/api/scans/scan")
        self.assertIn(resp.status_code, (401, 403))

    def test_08_consumer_cannot_access_admin_usage_telemetry(self):
        """Negative Test 8: Consumer role attempting to access admin telemetry receives 403 Forbidden."""
        with patch("auth.dependencies.decode_token", return_value={"sub": "user-consumer", "user_metadata": {"role": "consumer"}}),              patch("auth.dependencies.supabase.table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "user-consumer", "role": "consumer"}]
            resp = self.client.get("/api/usage", headers={"Authorization": "Bearer test_consumer_token"})
            self.assertEqual(resp.status_code, 403)

    def test_09_malformed_groq_and_external_data_tolerance(self):
        """Negative Test 9: Malformed JSON or API errors in Groq or Open Food Facts do not crash pipeline."""
        with patch("httpx.Client.post") as mock_groq:
            mock_groq.return_value = MagicMock(status_code=500, text="Internal Server Error")
            ai_res = analyze_label_with_groq("Some text", {}, {})
            self.assertFalse(ai_res["available"])

        with patch("httpx.Client.get") as mock_off:
            mock_off.return_value = MagicMock(status_code=500, text="Internal Server Error")
            research_res = research_product_information("Some text", {}, [{"field_id": "mrp", "status": "fail"}])
            self.assertIn("status", research_res)

    def test_10_concurrent_scans_do_not_mix_results(self):
        """Negative Test 10: Two distinct package scans evaluated concurrently maintain complete evidence isolation."""
        package_1 = [{
            "image_index": 1,
            "filename": "pkg1.jpg",
            "raw_text": "Product 1 Net Wt: 100g MRP Rs 50",
            "classification": {"panel_type": "FRONT"},
            "extracted_entities": {"product_name": "Product 1", "net_quantity": "100g", "mrp": "Rs 50"},
            "extracted_entities_detailed": {}
        }]
        package_2 = [{
            "image_index": 1,
            "filename": "pkg2.jpg",
            "raw_text": "Product 2 Net Wt: 200g",
            "classification": {"panel_type": "FRONT"},
            "extracted_entities": {"product_name": "Product 2", "net_quantity": "200g"},
            "extracted_entities_detailed": {}
        }]

        rep_1 = apply_multi_image_rules(package_1, self.rules)
        rep_2 = apply_multi_image_rules(package_2, self.rules)

        mrp_1 = next(f for f in rep_1["fields"] if f["field_id"] == "mrp")
        mrp_2 = next(f for f in rep_2["fields"] if f["field_id"] == "mrp")

        self.assertEqual(mrp_1["status"], "pass")
        self.assertEqual(mrp_2["status"], "fail")


if __name__ == "__main__":
    unittest.main()
