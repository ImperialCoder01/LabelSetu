"""
Automated Regression Test Suite for Entity Extractor Net Quantity Fix.
"""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.entity_extractor import extract_entities_from_text


class TestEntityExtractorNetQuantity(unittest.TestCase):
    def test_nivea_usp_conflict(self):
        """Test real NIVEA label string where USP price precedes Net Content."""
        raw_text = "USP ₹ 2.60/ml Net Content (when packed): 200ml (202.2g)"
        extracted = extract_entities_from_text(raw_text)
        self.assertEqual(extracted["net_quantity"], "200ml (202.2g)")
        self.assertNotEqual(extracted["net_quantity"], "2.601ml")

    def test_americana_top_usp_conflict(self):
        """Test real Americana TOP label string where USP price precedes Net Weight."""
        raw_text = "USP ₹ 0.16 per g Net Weight 60 g"
        extracted = extract_entities_from_text(raw_text)
        self.assertEqual(extracted["net_quantity"], "60 g")
        self.assertNotEqual(extracted["net_quantity"], "0.16 per g")

    def test_ponds_net_wt(self):
        """Test Pond's talc Net Wt format."""
        raw_text = "Net Wt.: 400g"
        extracted = extract_entities_from_text(raw_text)
        self.assertEqual(extracted["net_quantity"], "400g")

    def test_common_net_quantity_formats(self):
        """Test standard Net Quantity format variations."""
        cases = [
            ("Net Quantity: 1 kg", "1 kg"),
            ("Net Qty: 500 g", "500 g"),
            ("Net Weight: 60 g", "60 g"),
            ("Net Content: 200ml", "200ml"),
            ("Net Volume: 1 L", "1 L"),
            ("200 ml", "200 ml"),
            ("500 g", "500 g"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                res = extract_entities_from_text(text)
                self.assertEqual(res["net_quantity"], expected)

    def test_other_entities_preserved(self):
        """Verify MRP, Mfg Date, Country of Origin, Consumer Care are preserved without regression."""
        text = """MRP ₹ 520.00
Mfg 09/25
Country of Origin: India
Consumer Care: care@nivea.com
USP ₹ 2.60/ml
Net Content: 200ml"""
        extracted = extract_entities_from_text(text)
        self.assertEqual(extracted["mrp"], "520.00")
        self.assertEqual(extracted["mfg_date"], "09/25")
        self.assertEqual(extracted["country_of_origin"], "India")
        self.assertEqual(extracted["consumer_care"], "care@nivea.com")
        self.assertEqual(extracted["net_quantity"], "200ml")


if __name__ == "__main__":
    unittest.main()
