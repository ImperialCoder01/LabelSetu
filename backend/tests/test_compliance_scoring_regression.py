"""
LABELSETU COMPREHENSIVE COMPLIANCE SCORING AND HINDI RULE REGRESSION TESTS

Verifies:
1. English label compliance matching and scoring
2. Pure Hindi label compliance matching and scoring (never 0 due to Devanagari)
3. Bilingual label compliance matching
4. Independent recomputation of score from rule result list matching overall_score
5. Intermediate scores (30, 45, 60, 75) remain accurate intermediate values
6. Front-panel-only image never becomes 100 merely because 1 declaration is found
7. Front-panel-only image never becomes 0 merely because back declarations are unavailable
8. Metadata mapping (passed_declarations, failed_declarations, found_fields) matches rule report
"""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.rule_engine import load_rules, apply_rules, apply_multi_image_rules


class TestComplianceScoringRegression(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_01_english_label_scoring(self):
        """Test 1: English label evaluates correctly with intermediate scores."""
        en_text = (
            "Product Name: NutriChoice High-Fiber Digestive Biscuits\n"
            "Net Weight: 250 g\n"
            "MRP: Rs 45.00\n"
            "Country of Origin: India\n"
        )
        report = apply_rules(en_text, self.rules)
        self.assertEqual(report['overall_score'], 60)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['compliance_assessment'], 'PARTIALLY_COMPLIANT')
        self.assertEqual(report['passed'], 4)
        self.assertEqual(report['failed'], 4)

    def test_02_pure_hindi_label_full_compliance(self):
        """Test 2: Pure Hindi label containing all 8 declarations must be recognized and score 100."""
        hi_full_text = (
            "आनंद शाही गरम मसाला\n"
            "उत्पाद का नाम: गरम मसाला\n"
            "ब्रांड: आनंद\n"
            "निर्माता: आनंद फूड्स प्राइवेट लिमिटेड, जयपुर, राजस्थान\n"
            "शुद्ध मात्रा: 200 ग्राम\n"
            "निर्माण तिथि: 01/2026\n"
            "अधिकतम खुदरा मूल्य: ₹120.00 (सभी करों सहित)\n"
            "प्रति इकाई विक्रय मूल्य: ₹0.60 प्रति ग्राम\n"
            "उपभोक्ता सेवा: 1800-123-4567\n"
            "उत्पत्ति का देश: भारत में निर्मित"
        )
        report = apply_rules(hi_full_text, self.rules)
        self.assertEqual(report['overall_score'], 100, f"Hindi label with all declarations must score 100, got {report['overall_score']}")
        self.assertEqual(report['passed'], 8)
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['compliance_assessment'], 'COMPLIANT')

    def test_03_pure_hindi_label_partial_compliance(self):
        """Test 3: Pure Hindi label with 3 declarations must not produce 0; scores intermediate value."""
        hi_partial_text = (
            "निर्माता: पतंजलि आयुर्वेद लिमिटेड, हरिद्वार\n"
            "शुद्ध मात्रा: 500 ग्राम\n"
            "अधिकतम खुदरा मूल्य: ₹245.00\n"
        )
        report = apply_rules(hi_partial_text, self.rules)
        self.assertEqual(report['overall_score'], 45)
        self.assertEqual(report['passed'], 3)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['compliance_assessment'], 'PARTIALLY_COMPLIANT')

    def test_04_bilingual_label_matching(self):
        """Test 4: Bilingual (Hindi + English) label matches declarations across languages."""
        mixed_text = (
            "Product Name / उत्पाद का नाम: पतंजलि च्यवनप्राश (Patanjali Special Chyawanprash)\n"
            "शुद्ध मात्रा / Net Quantity: 1 kg\n"
            "MRP / अधिकतम खुदरा मूल्य: Rs 375.00\n"
            "Manufactured by: Patanjali Ayurved Ltd, Haridwar\n"
            "Country of Origin: India\n"
        )
        report = apply_rules(mixed_text, self.rules)
        self.assertEqual(report['overall_score'], 75)
        self.assertEqual(report['passed'], 5)
        self.assertEqual(report['status'], 'partial')

    def test_05_independent_recomputation_of_score_from_rule_results(self):
        """Test 5: Independently recompute score from returned field list and verify match."""
        test_text = (
            "Brand: Britannia Good Day Biscuits\n"
            "Net Weight: 100g\n"
            "MRP: Rs 20.00\n"
        )
        report = apply_rules(test_text, self.rules)

        scoring = self.rules.get('scoring', {'critical_weight': 15, 'minor_weight': 5})
        crit_w = scoring.get('critical_weight', 15)
        min_w = scoring.get('minor_weight', 5)

        computed_score = 100
        for f in report['fields']:
            if f.get('evidence_status') == 'CONFIRMED_MISSING':
                if f.get('severity') == 'Critical':
                    computed_score -= crit_w
                else:
                    computed_score -= min_w
        computed_score = max(0, min(100, computed_score))

        self.assertEqual(report['overall_score'], computed_score)
        self.assertEqual(report['overall_score'], 45)

    def test_06_front_panel_only_with_one_declaration_is_none_never_100_or_0(self):
        """Test 6: Front-panel-only with 1 or 2 declarations returns overall_score=None (never 100, never 0)."""
        front_panel_img = [{
            "image_index": 1,
            "filename": "front_pouch.jpg",
            "raw_text": "Pond's Dreamflower Talc Net Wt: 400g",
            "quality_info": {'quality_status': 'GOOD'},
            "classification": {'panel_type': 'FRONT_PANEL', 'classification': 'FRONT_PANEL'},
            "extracted_entities": {'net_quantity': '400g'},
            "extracted_entities_detailed": {}
        }]
        report = apply_multi_image_rules(front_panel_img, self.rules)

        self.assertIsNone(report['overall_score'], 'Front panel only must have overall_score=None (never 100)')
        self.assertNotEqual(report['overall_score'], 100, 'Front panel only must NEVER be 100')
        self.assertNotEqual(report['overall_score'], 0, 'Front panel only must NEVER be 0')
        self.assertEqual(report['compliance_assessment'], 'FRONT_PANEL_ONLY')
        self.assertEqual(report['verification_completeness'], 'FRONT_PANEL_ONLY')
        self.assertEqual(report['status'], 'partial')
        self.assertGreater(report['passed'], 0, 'Passed declarations on front panel must still be recorded')

    def test_07_front_panel_only_with_zero_declarations_is_none_never_0(self):
        """Test 7: Front-panel-only with 0 declarations returns overall_score=None (never 0)."""
        front_panel_empty_decl = [{
            "image_index": 1,
            "filename": "front_graphic.jpg",
            "raw_text": "Delicious Crunchy Snacks",
            "quality_info": {'quality_status': 'GOOD'},
            "classification": {'panel_type': 'FRONT_PANEL', 'classification': 'FRONT_PANEL'},
            "extracted_entities": {},
            "extracted_entities_detailed": {}
        }]
        report = apply_multi_image_rules(front_panel_empty_decl, self.rules)

        self.assertIsNone(report['overall_score'], 'Zero declarations on front panel must return None, not 0')
        self.assertEqual(report['compliance_assessment'], 'FRONT_PANEL_ONLY')
        self.assertEqual(report['verification_completeness'], 'INSUFFICIENT_EVIDENCE')

    def test_08_metadata_mapping_contract(self):
        """Test 8: Verify report provides passed_declarations, failed_declarations, found_fields."""
        text = "Brand: Amul Butter\nNet Weight: 100g\nMRP: Rs 56.00"
        report = apply_rules(text, self.rules)

        self.assertIn('passed_declarations', report)
        self.assertIn('failed_declarations', report)
        self.assertIn('found_fields', report)
        self.assertEqual(report['passed_declarations'], report['passed'])
        self.assertEqual(report['failed_declarations'], report['failed'])
        self.assertIsInstance(report['found_fields'], list)
        self.assertIn('product_name', report['found_fields'])
        self.assertIn('net_quantity', report['found_fields'])
        self.assertIn('mrp', report['found_fields'])


if __name__ == '__main__':
    unittest.main()
