"""
Test the rule engine with realistic product label text.
"""
import os
import sys
import json

os.environ["PYTHONIOENCODING"] = "utf-8"
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, ".")


def test_rule_engine():
    from services.rule_engine import load_rules, apply_rules
    from services.compliance import check_compliance

    rules = load_rules()
    print(f"Loaded {len(rules['fields'])} fields from rules.json\n")

    # ---- Test 1: Partially compliant label ----
    text_1 = (
        "Tata Salt\n"
        "Iodised Salt\n"
        "Manufactured by: Tata Consumer Products India Ltd\n"
        "Net Wt: 1 kg\n"
        "MRP: Rs 28.00\n"
        "Batch: TS202601\n"
        "Country of Origin: India"
    )

    print("=" * 60)
    print("TEST 1: Partially compliant label")
    print("=" * 60)
    print(f"Input text:\n{text_1}\n")

    report = apply_rules(text_1, rules)
    print(f"Overall Score: {report['overall_score']}/100")
    print(f"Status:        {report['status']}")
    print(f"Passed:        {report['passed']}/{report['total_fields']}")
    print(f"Failed:        {report['failed']}/{report['total_fields']}")
    print()

    for f in report["fields"]:
        icon = "PASS" if f["status"] == "pass" else "FAIL"
        kw = f" (matched: '{f['matched_keyword']}')" if f["matched_keyword"] else ""
        print(f"  [{icon}] [{f['severity']:>8}] {f['field_name']}{kw}")

    print()

    # ---- Test 2: Fully compliant label ----
    text_2 = (
        "Amul Butter\n"
        "Brand: Amul\n"
        "Manufactured by: Gujarat Cooperative Milk Marketing Federation Ltd\n"
        "Net Quantity: 100g\n"
        "Manufacturing Date: 15/08/2026\n"
        "MRP: Rs 56.00 (incl. of all taxes)\n"
        "Unit Sale Price: Rs 560 per kg\n"
        "Consumer Care: 1800-200-0520\n"
        "Country of Origin: India"
    )

    print("=" * 60)
    print("TEST 2: Fully compliant label")
    print("=" * 60)
    print(f"Input text:\n{text_2}\n")

    report2 = apply_rules(text_2, rules)
    print(f"Overall Score: {report2['overall_score']}/100")
    print(f"Status:        {report2['status']}")
    print(f"Passed:        {report2['passed']}/{report2['total_fields']}")
    print()

    for f in report2["fields"]:
        icon = "PASS" if f["status"] == "pass" else "FAIL"
        print(f"  [{icon}] [{f['severity']:>8}] {f['field_name']}")

    print()

    # ---- Test 3: Backward-compatible check_compliance() ----
    print("=" * 60)
    print("TEST 3: check_compliance() backward compatibility")
    print("=" * 60)
    compat = check_compliance(text_1)
    print(f"Score:             {compat['score']}")
    print(f"Found fields:      {compat['found_fields']}")
    print(f"Missing fields:    {compat['missing_fields']}")
    print(f"Total required:    {compat['total_required']}")
    print(f"Report present:    {'report' in compat}")
    print()

    # ---- Test 4: Empty text ----
    print("=" * 60)
    print("TEST 4: Empty text (all should fail)")
    print("=" * 60)
    report4 = apply_rules("", rules)
    print(f"Overall Score: {report4['overall_score']}/100")
    print(f"Status:        {report4['status']}")
    print(f"Failed:        {report4['failed']}/{report4['total_fields']}")
    print()

    # ---- Summary ----
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    assert report["status"] == "partial", f"Expected 'partial', got '{report['status']}'"
    assert report2["status"] == "pass", f"Expected 'pass', got '{report2['status']}'"
    assert report2["overall_score"] == 100, f"Expected 100, got {report2['overall_score']}"
    assert report4["status"] == "fail", f"Expected 'fail', got '{report4['status']}'"
    assert compat["score"] == report["overall_score"]
    assert "report" in compat
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    test_rule_engine()
