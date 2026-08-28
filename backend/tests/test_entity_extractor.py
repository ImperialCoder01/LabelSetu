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

    def test_textual_mfg_date_formats(self):
        """Test textual month abbreviations and full month names for manufacturing date."""
        cases = [
            ("Mfg: DEC 2026", "DEC 2026"),
            ("Mfg: DEC-2026", "DEC 2026"),
            ("Packed: AUG 2026", "AUG 2026"),
            ("Packed on: AUG-2026", "AUG 2026"),
            ("Manufactured: DECEMBER 2026", "DECEMBER 2026"),
            ("Pkd: 15/08/2026", "15/08/2026"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                res = extract_entities_from_text(text)
                self.assertEqual(res["mfg_date"], expected)

    def test_best_before_expiry_calculation(self):
        """Test explicit Best Before X Months calculation from manufacturing date."""
        # DEC 2026 + 12 months = DEC 2027
        t1 = "Mfg: DEC 2026\nBest Before 12 Months"
        r1 = extract_entities_from_text(t1)
        self.assertEqual(r1["mfg_date"], "DEC 2026")
        self.assertEqual(r1["expiry_date"], "DEC 2027")

        # AUG 2026 + 6 months = FEB 2027 (Year boundary)
        t2 = "Mfg: AUG 2026\nBest Before 6 Months"
        r2 = extract_entities_from_text(t2)
        self.assertEqual(r2["mfg_date"], "AUG 2026")
        self.assertEqual(r2["expiry_date"], "FEB 2027")

    def test_multiline_manufacturer_address_extraction(self):
        """Test multi-line manufacturer and address extraction."""
        t1 = """Manufactured by:
ABC Foods Pvt. Ltd.
Plot 14, Industrial Area
New Delhi - 110020"""
        r1 = extract_entities_from_text(t1)
        self.assertEqual(r1["manufacturer_name_address"], "ABC Foods Pvt. Ltd., Plot 14, Industrial Area, New Delhi - 110020")

        t2 = """Manufactured & Packed by:
ABC Consumer Products Pvt. Ltd.
Noida, Uttar Pradesh"""
        r2 = extract_entities_from_text(t2)
        self.assertEqual(r2["manufacturer_name_address"], "ABC Consumer Products Pvt. Ltd., Noida, Uttar Pradesh")

    def test_manufacturer_boundary_protections(self):
        """Verify manufacturer extraction stops at semantic boundaries (Marketed by, Customer Care, MRP, etc.)."""
        # Stop at Marketed by
        t1 = """Manufactured by:
ABC Foods Pvt. Ltd.
Delhi

Marketed by:
XYZ Consumer Ltd.
Mumbai"""
        r1 = extract_entities_from_text(t1)
        self.assertEqual(r1["manufacturer_name_address"], "ABC Foods Pvt. Ltd., Delhi")
        self.assertNotIn("XYZ Consumer", r1["manufacturer_name_address"])

        # Stop at Customer Care
        t2 = """Manufactured by:
ABC Foods Pvt. Ltd.
Plot 14, Industrial Area

Customer Care:
1800-123-456"""
        r2 = extract_entities_from_text(t2)
        self.assertEqual(r2["manufacturer_name_address"], "ABC Foods Pvt. Ltd., Plot 14, Industrial Area")
        self.assertNotIn("1800-123-456", r2["manufacturer_name_address"])

        # Stop at MRP & Net Qty
        t3 = """Manufactured by:
ABC Foods Pvt. Ltd.
Delhi

MRP ₹200
Net Wt 400g"""
        r3 = extract_entities_from_text(t3)
        self.assertEqual(r3["manufacturer_name_address"], "ABC Foods Pvt. Ltd., Delhi")
        self.assertNotIn("MRP", r3["manufacturer_name_address"])
        self.assertNotIn("400g", r3["manufacturer_name_address"])

    def test_multiline_consumer_care_extraction(self):
        """Test multi-line consumer care extraction and boundary termination."""
        # Example A: Complete consumer care block
        t_a = """Customer Care:
Consumer Care Executive
1800-123-4567
care@abcfoods.com
www.abcfoods.com"""
        r_a = extract_entities_from_text(t_a)
        self.assertIn("1800-123-4567", r_a["consumer_care"])
        self.assertIn("care@abcfoods.com", r_a["consumer_care"])

        # Example B: Manufacturer followed by Customer Care (Clean Separation)
        t_b = """Manufactured by:
ABC Foods Pvt. Ltd.
Plot 14, Industrial Area
New Delhi - 110020
Customer Care:
1800-123-4567
care@abcfoods.com"""
        r_b = extract_entities_from_text(t_b)
        self.assertEqual(r_b["manufacturer_name_address"], "ABC Foods Pvt. Ltd., Plot 14, Industrial Area, New Delhi - 110020")
        self.assertNotIn("1800-123-4567", r_b["manufacturer_name_address"])
        self.assertIn("1800-123-4567", r_b["consumer_care"])

        # Example C: Imported by followed by Consumer Care (Clean Separation)
        t_c = """Imported by:
XYZ Imports Pvt. Ltd.
Mumbai
Consumer Care:
1800-123-4567
support@xyz.com"""
        r_c = extract_entities_from_text(t_c)
        self.assertNotIn("1800-123-4567", r_c.get("manufacturer_name_address", "") or "")
        self.assertIn("1800-123-4567", r_c["consumer_care"])

        # Example D: Marketed by followed by Consumer Care followed by MRP (Termination at MRP)
        t_d = """Marketed by:
ABC Consumer Products Ltd.
Mumbai
Customer Care:
1800-123-4567
care@example.com
MRP ₹200"""
        r_d = extract_entities_from_text(t_d)
        self.assertIn("1800-123-4567", r_d["consumer_care"])
        self.assertNotIn("MRP", r_d["consumer_care"])
        self.assertNotIn("200", r_d["consumer_care"])
        self.assertEqual(r_d["mrp"], "200")

    def test_country_of_origin_multi_word_and_boundaries(self):
        """Test single-word and multi-word Country of Origin extraction with strict boundary termination."""
        # A. Single-word country
        t_a = "Country of Origin: India"
        self.assertEqual(extract_entities_from_text(t_a)["country_of_origin"], "India")

        # B. Multi-word country
        t_b = "Country of Origin: Republic of India"
        self.assertEqual(extract_entities_from_text(t_b)["country_of_origin"], "Republic of India")

        # C. USA
        t_c = "Made in United States of America"
        self.assertEqual(extract_entities_from_text(t_c)["country_of_origin"], "United States of America")

        # D. United Kingdom
        t_d = "Product of United Kingdom"
        self.assertEqual(extract_entities_from_text(t_d)["country_of_origin"], "United Kingdom")

        # E. Boundary protection (Stop before Manufactured by)
        t_e = """Country of Origin: Republic of India
Manufactured by: ABC Foods Pvt. Ltd.
MRP: ₹200"""
        r_e = extract_entities_from_text(t_e)
        self.assertEqual(r_e["country_of_origin"], "Republic of India")
        self.assertNotIn("Manufactured", r_e["country_of_origin"])

        # F. Manufacturer separation (Indian address must NOT create fake origin)
        t_f = """Manufactured by:
ABC Foods Pvt. Ltd.
New Delhi - 110020"""
        self.assertIsNone(extract_entities_from_text(t_f)["country_of_origin"])

        # G. Arbitrary number protection
        t_g = "MRP ₹200\nNet Qty 400g\nBatch 123456"
        self.assertIsNone(extract_entities_from_text(t_g)["country_of_origin"])

        # J. OCR case/spacing variations
        t_j1 = "COUNTRY OF ORIGIN : INDIA"
        self.assertEqual(extract_entities_from_text(t_j1)["country_of_origin"], "INDIA")

        t_j2 = "Country   of   Origin - India"
        self.assertEqual(extract_entities_from_text(t_j2)["country_of_origin"], "India")

    def test_multipack_net_quantity_safety_rules(self):
        """Test explicit multi-pack printed total, pack count isolation, and ambiguous non-inference rules."""
        # A. Explicit total (grams)
        t_a = "Net Qty: 2 N x 100 g = 200 g"
        self.assertEqual(extract_entities_from_text(t_a)["net_quantity"], "200 g")

        # B. Explicit total (ml)
        t_b = "Net Content: 2 x 100 ml = 200 ml"
        self.assertEqual(extract_entities_from_text(t_b)["net_quantity"], "200 ml")

        # C. Pack count isolation (2 N should not become 2 g or 2 ml)
        t_c = "Net Qty: 2 N"
        self.assertEqual(extract_entities_from_text(t_c)["net_quantity"], "2 N")

        # D. Ambiguous pack declaration (3 Packs of 50 ml does NOT become 150 ml)
        t_d = "3 Packs of 50 ml"
        res_d = extract_entities_from_text(t_d)["net_quantity"]
        self.assertEqual(res_d, "50 ml")
        self.assertNotEqual(res_d, "150 ml")

        # F. Arbitrary number & USP protection
        t_f = "Batch 123456\nMRP ₹ 200\nUSP ₹ 2.60/ml\nDate 15/08/2026\nPhone 1800-123-4567"
        self.assertIsNone(extract_entities_from_text(t_f)["net_quantity"])

    def test_multiline_mfg_date_and_boundary_protection(self):
        """Test multi-line manufacturing date extraction and strict boundary protection."""
        # Multi-line formats
        t_m1 = "Mfg Date:\n15/08/2026"
        self.assertEqual(extract_entities_from_text(t_m1)["mfg_date"], "15/08/2026")

        t_m2 = "Packed on:\nAUG 2026"
        self.assertEqual(extract_entities_from_text(t_m2)["mfg_date"], "AUG 2026")

        t_m3 = "Manufactured:\nDEC 2026"
        self.assertEqual(extract_entities_from_text(t_m3)["mfg_date"], "DEC 2026")

        t_m4 = "Manufactured:\nDECEMBER 2026"
        self.assertEqual(extract_entities_from_text(t_m4)["mfg_date"], "DECEMBER 2026")

        # Same-line regression protection
        t_s1 = "Mfg Date: 15/08/2026"
        self.assertEqual(extract_entities_from_text(t_s1)["mfg_date"], "15/08/2026")

        t_s2 = "Packed on: AUG 2026"
        self.assertEqual(extract_entities_from_text(t_s2)["mfg_date"], "AUG 2026")

        # Boundary protection against arbitrary text/numbers on next line
        t_b1 = "Mfg Date:\nBatch 123456"
        self.assertIsNone(extract_entities_from_text(t_b1)["mfg_date"])

        t_b2 = "Mfg Date:\nMRP ₹200"
        self.assertIsNone(extract_entities_from_text(t_b2)["mfg_date"])

        t_b3 = "Mfg Date:\nNet Qty 400g"
        self.assertIsNone(extract_entities_from_text(t_b3)["mfg_date"])

        t_b4 = "Mfg Date:\nUSP ₹2.60/ml"
        self.assertIsNone(extract_entities_from_text(t_b4)["mfg_date"])


if __name__ == "__main__":
    unittest.main()
