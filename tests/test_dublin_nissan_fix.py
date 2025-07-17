# test_dublin_nissan_fix.py - Fixed version with proper imports

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))


def test_dublin_nissan_case():
    """Test the exact Dublin Nissan case that was failing"""

    try:
        # Import your new utilities
        from src.utils.currency_parser import parse_currency_to_float, clean_invoice_amounts
        print("✅ Successfully imported currency parser utilities")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("📝 Make sure you've created:")
        print("   - src/utils/__init__.py")
        print("   - src/utils/currency_parser.py")
        return False

    print("\n🧪 Testing Dublin Nissan Currency Fix")
    print("=" * 50)

    # Test the exact case from your logs
    dublin_amount = "$876.99"
    parsed = parse_currency_to_float(dublin_amount)

    print(f"Original amount: '{dublin_amount}'")
    print(f"Parsed amount:   {parsed}")
    print(f"Type:           {type(parsed)}")
    print(f"Database ready:  {isinstance(parsed, (int, float))}")

    # Test various currency formats that your system handles
    test_cases = [
        "$876.99",  # Dublin Nissan case
        "€1,234.56",  # European
        "£50.00",  # British
        "¥12,345",  # Japanese
        "₹1,000.50",  # Indian
        "1000.00",  # Plain number
        "",  # Empty
        None,  # None
        123.45  # Already float
    ]

    print(f"\n🧪 Testing Various Currency Formats")
    print("-" * 50)

    for test_case in test_cases:
        result = parse_currency_to_float(test_case)
        print(f"'{test_case}' -> {result}")

    # Test full invoice data like from your mobile processing
    test_invoice_data = {
        "vendor_name": "Dublin Nissan",
        "total_amount": "$876.99",  # This was causing the error
        "tax_amount": "$0.00",
        "currency": "USD",
        "invoice_number": None,
        "notes": "Processed via mobile app: NISSAN - 3.pdf"
    }

    print(f"\n🧪 Testing Full Invoice Data Cleaning")
    print("-" * 50)
    print(f"Before: {test_invoice_data}")

    cleaned = clean_invoice_amounts(test_invoice_data)
    print(f"After:  {cleaned}")

    # Verify database compatibility
    print(f"\n✅ Database Compatibility Check")
    print("-" * 50)

    total_amount = cleaned['total_amount']
    tax_amount = cleaned['tax_amount']

    print(f"total_amount: {total_amount} ({type(total_amount).__name__})")
    print(f"tax_amount:   {tax_amount} ({type(tax_amount).__name__})")

    # Check constraints from your Invoice model
    checks = {
        "total_amount is numeric": isinstance(total_amount, (int, float)),
        "total_amount >= 0": total_amount >= 0,
        "tax_amount is numeric": isinstance(tax_amount, (int, float)),
        "tax_amount >= 0": tax_amount >= 0,
        "currency is 3 chars": len(cleaned['currency']) == 3,
        "Dublin Nissan amount correct": total_amount == 876.99
    }

    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    all_passed = all(checks.values())
    print(f"\n{'🎉 ALL TESTS PASSED!' if all_passed else '❌ SOME TESTS FAILED'}")

    return all_passed


if __name__ == "__main__":
    test_dublin_nissan_case()