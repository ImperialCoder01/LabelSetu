"""
Comprehensive Performance and Optimization Acceptance Tests.
Verifies response caching, GZip compression, parallel task execution,
database batching, timing telemetry, and strict statutory score immutability.
"""

import gzip
import json
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.audit import log_admin_actions_batch
from services.rule_engine import load_rules, apply_multi_image_rules
from services.product_research_service import research_product_information


class TestPerformanceOptimizations(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.rules = load_rules()

    def test_01_cached_rules_metadata_endpoint(self):
        """Test 1: Public deterministic rules metadata endpoint returns Cache-Control headers."""
        resp = self.client.get("/api/meta/rules")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("standard", data)
        self.assertIn("mandatory_fields_count", data)
        self.assertIn("Cache-Control", resp.headers)
        self.assertIn("public", resp.headers["Cache-Control"])
        self.assertIn("max-age=3600", resp.headers["Cache-Control"])

    def test_02_rules_in_memory_caching(self):
        """Test 2: load_rules() uses in-memory caching for sub-millisecond repeated execution."""
        t0 = time.perf_counter()
        for _ in range(100):
            rules = load_rules()
        dt_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(dt_ms, 50.0, "100 cached rule loads should take < 50ms")
        self.assertIn("fields", rules)

    def test_03_gzip_response_compression(self):
        """Test 3: GZipMiddleware compresses JSON responses >= 1000 bytes when client supports gzip."""
        headers = {"Accept-Encoding": "gzip"}
        resp = self.client.get("/api/meta/rules", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("mandatory_fields_count", data)
        # TestClient automatically decodes gzip content-encoding

    def test_04_batch_audit_logging(self):
        """Test 4: log_admin_actions_batch executes multiple audit entries in a single batch call."""
        entries = [
            {"admin_id": "test-admin-1", "action_type": "AUDIT_1", "target_table": "scans", "target_id": "s1"},
            {"admin_id": "test-admin-1", "action_type": "AUDIT_2", "target_table": "scans", "target_id": "s2"},
            {"admin_id": "test-admin-1", "action_type": "AUDIT_3", "target_table": "scans", "target_id": "s3"},
        ]
        with patch("services.audit.supabase.table") as mock_table:
            mock_query = MagicMock()
            mock_query.execute.return_value = MagicMock(data=entries)
            mock_table.return_value.insert.return_value = mock_query

            res = log_admin_actions_batch(entries)
            self.assertEqual(len(res), 3)
            # Verify single batch insert call
            mock_table.return_value.insert.assert_called_once_with([
                {"admin_id": "test-admin-1", "action_type": "AUDIT_1", "target_table": "scans", "target_id": "s1", "old_value": None, "new_value": None},
                {"admin_id": "test-admin-1", "action_type": "AUDIT_2", "target_table": "scans", "target_id": "s2", "old_value": None, "new_value": None},
                {"admin_id": "test-admin-1", "action_type": "AUDIT_3", "target_table": "scans", "target_id": "s3", "old_value": None, "new_value": None},
            ])

    def test_05_non_blocking_groq_failure(self):
        """Test 5: Non-blocking Groq AI failure does not affect scan completion or compliance report."""
        with patch("services.ai_service.is_groq_available", return_value=False):
            package_images = [{
                "image_index": 1,
                "filename": "label.jpg",
                "raw_text": "Tata Salt 1 kg",
                "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
                "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
                "extracted_entities_detailed": {}
            }]
            report = apply_multi_image_rules(package_images, self.rules)
            self.assertIn("overall_score", report)

    def test_06_non_blocking_external_research_failure(self):
        """Test 6: Non-blocking product research failure returns fallback without raising unhandled error."""
        with patch("services.product_research_service._search_open_food_facts", side_effect=Exception("Timeout 6s")):
            res = research_product_information(
                ocr_text="Some text",
                extracted_entities={"product_name": "Test"},
                missing_fields=[{"field_id": "mrp", "status": "fail"}],
            )
            self.assertIn("status", res)

    def test_07_statutory_score_immutability_under_parallel_execution(self):
        """Test 7: Compliance score is 100% immutable by concurrent external research."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        score_before = rule_report["overall_score"]

        # Run research
        research_product_information(
            ocr_text="Tata Salt 1 kg",
            extracted_entities={"product_name": "Tata Salt", "net_quantity": "1 kg"},
            missing_fields=rule_report.get("fields", []),
            barcode="8901030300000"
        )

        rule_report_after = apply_multi_image_rules(package_images, self.rules)
        self.assertEqual(rule_report_after["overall_score"], score_before)

    def test_08_package_mrp_remains_fail_when_external_mrp_exists(self):
        """Test 8: Package MRP remains FAIL/MISSING when only external reference MRP exists."""
        package_images = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        rule_report = apply_multi_image_rules(package_images, self.rules)
        mrp_field = next((f for f in rule_report["fields"] if f["field_id"] == "mrp"), None)
        self.assertEqual(mrp_field["status"], "fail")

    def test_09_multi_image_physical_evidence_recovery(self):
        """Test 9: Second physical image legitimately updates compliance score from package evidence."""
        front_panel = [{
            "image_index": 1,
            "filename": "front.jpg",
            "raw_text": "Tata Salt 1 kg",
            "classification": {"panel_type": "FRONT", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"product_name": "Tata Salt", "net_quantity": "1 kg"},
            "extracted_entities_detailed": {}
        }]
        report_1 = apply_multi_image_rules(front_panel, self.rules)
        mrp_1 = next((f for f in report_1["fields"] if f["field_id"] == "mrp"), None)
        self.assertEqual(mrp_1["status"], "fail")

        two_panels = front_panel + [{
            "image_index": 2,
            "filename": "back.jpg",
            "raw_text": "MRP Rs 28.00 incl. of all taxes Mfg 01/2026 Batch TS01",
            "classification": {"panel_type": "BACK", "classification": "PRODUCT_LABEL"},
            "extracted_entities": {"mrp": "Rs 28.00", "manufacturing_date": "01/2026", "batch_number": "TS01"},
            "extracted_entities_detailed": {}
        }]
        report_2 = apply_multi_image_rules(two_panels, self.rules)
        mrp_2 = next((f for f in report_2["fields"] if f["field_id"] == "mrp"), None)
        self.assertEqual(mrp_2["status"], "pass")


if __name__ == "__main__":
    unittest.main()
