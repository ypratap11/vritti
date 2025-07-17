# comprehensive_test.py - Test the fixed currency parser

import sys
import os

sys.path.append('.')

from src.utils.currency_parser import parse_currency_to_float, clean_invoice_amounts


def test_currency_parsing():
    """Test various currency formats"""

    test_cases = [
        # (input, expected_output, description)
        ("$876.99", 876.99, "Dublin Nissan case - US dollars"),
        ("$1,234.56", 1234.56, "US format with thousands separator"),
        ("€1.234,56", 1234.56, "European format"),
        ("£50.00", 50.00, "British pounds"),
        ("¥12345", 12345.0, "Japanese yen (no decimals)"),
        ("₹1,50,000.50", 150000.50, "Indian rupees with lakh format"),
        ("1000.00", 1000.00, "Plain number with decimals"),
        ("1,000", 1000.0, "Thousands separator only"),
        ("500", 500.0, "Simple number"),
        ("0.99", 0.99, "Less than one"),
        ("", None, "Empty string"),
        (None, None, "None value"),
        (123.45, 123.45, "Already a float"),
    ]

    print("🧪 Testing Currency Parsing (Fixed Version)")
    print("=" * 60)

    all_passed = True

    for input_val, expected, description in test_cases:
        result = parse_currency_to_float(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{status} {description}")
        print(f"    Input: {repr(input_val)} -> Output: {result} (Expected: {expected})")

        if not passed:
            all_passed = False
        print()

    # Test Dublin Nissan specifically
    print("🎯 Dublin Nissan Specific Test")
    print("-" * 40)

    dublin_test = parse_currency_to_float("$876.99")
    dublin_correct = dublin_test == 876.99

    print(f"Input: '$876.99'")
    print(f"Output: {dublin_test}")
    print(f"Correct: {'✅' if dublin_correct else '❌'} (should be 876.99)")

    # Test full invoice data
    print(f"\n📄 Full Invoice Data Test")
    print("-" * 40)

    test_invoice = {
        "vendor_name": "Dublin Nissan",
        "total_amount": "$876.99",
        "tax_amount": "$76.99",
        "currency": "USD",
        "notes": "Test invoice"
    }

    print(f"Before: {test_invoice}")
    cleaned = clean_invoice_amounts(test_invoice)
    print(f"After:  {cleaned}")

    # Validation
    validations = [
        ("Total amount correct", cleaned['total_amount'] == 876.99),
        ("Tax amount correct", cleaned['tax_amount'] == 76.99),
        ("Total is float", isinstance(cleaned['total_amount'], float)),
        ("Tax is float", isinstance(cleaned['tax_amount'], float)),
        ("Currency unchanged", cleaned['currency'] == "USD"),
        ("Vendor name unchanged", cleaned['vendor_name'] == "Dublin Nissan")
    ]

    print(f"\n✅ Validation Results:")
    invoice_passed = True
    for check, result in validations:
        status = "✅" if result else "❌"
        print(f"    {status} {check}")
        if not result:
            invoice_passed = False

    overall_success = all_passed and dublin_correct and invoice_passed

    print(f"\n{'🎉 ALL TESTS PASSED!' if overall_success else '❌ SOME TESTS FAILED'}")
    print(f"Ready for database: {overall_success}")

    return overall_success


if __name__ == "__main__":
    test_currency_parsing()