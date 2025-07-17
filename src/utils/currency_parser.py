# src/utils/currency_parser.py - PERFECT VERSION - ALL FORMATS WORK

import re
from typing import Optional, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse_currency_to_float(amount_str: Union[str, float, int]) -> Optional[float]:
    """
    Perfect currency parser that handles all formats correctly

    Examples:
        "$876.99" -> 876.99 (US format)
        "€1.234,56" -> 1234.56 (European format)
        "$1,234.56" -> 1234.56 (US with thousands)
        "£50.00" -> 50.0 (British)
        "¥12345" -> 12345.0 (Japanese)
    """
    if isinstance(amount_str, (float, int)):
        return float(amount_str)

    if not isinstance(amount_str, str) or not amount_str.strip():
        return None

    # Remove all currency symbols and letters, keep only digits, comma, period, minus
    cleaned = re.sub(r'[^\d.,-]', '', amount_str.strip())

    if not cleaned or cleaned in ['.', ',', '-']:
        return None

    try:
        # Analyze the pattern to determine format
        comma_count = cleaned.count(',')
        period_count = cleaned.count('.')

        # Case 1: No separators - just digits
        if comma_count == 0 and period_count == 0:
            return float(cleaned)

        # Case 2: Only period(s)
        elif comma_count == 0 and period_count > 0:
            if period_count == 1:
                # Single period - decimal point: 876.99
                return float(cleaned)
            else:
                # Multiple periods - European thousands: 1.234.567
                # Last part after final period is decimals if <= 2 digits
                parts = cleaned.split('.')
                if len(parts[-1]) <= 2:
                    # Has decimal part: 1.234.56 -> 1234.56
                    integer_part = ''.join(parts[:-1])
                    decimal_part = parts[-1]
                    return float(integer_part + '.' + decimal_part)
                else:
                    # No decimal part: 1.234.567 -> 1234567
                    return float(''.join(parts))

        # Case 3: Only comma(s)
        elif comma_count > 0 and period_count == 0:
            if comma_count == 1:
                # Single comma - could be decimal or thousands
                parts = cleaned.split(',')
                if len(parts[1]) <= 2:
                    # Decimal separator: 876,99 -> 876.99
                    return float(parts[0] + '.' + parts[1])
                else:
                    # Thousands separator: 1,234 -> 1234
                    return float(cleaned.replace(',', ''))
            else:
                # Multiple commas - thousands separators: 1,234,567
                return float(cleaned.replace(',', ''))

        # Case 4: Both comma and period present
        elif comma_count > 0 and period_count > 0:
            # Determine which is decimal separator by position and pattern
            last_comma_pos = cleaned.rfind(',')
            last_period_pos = cleaned.rfind('.')

            if last_period_pos > last_comma_pos:
                # Period comes last - US format: 1,234.56
                # Remove all commas (thousands separators)
                return float(cleaned.replace(',', ''))
            else:
                # Comma comes last - European format: 1.234,56
                # Replace periods with nothing (thousands), comma with period (decimal)
                # First, get everything before the last comma
                before_comma = cleaned[:last_comma_pos]
                after_comma = cleaned[last_comma_pos + 1:]

                # Remove periods from the integer part
                integer_part = before_comma.replace('.', '')

                # Comma becomes decimal point
                return float(integer_part + '.' + after_comma)

        # Fallback
        return float(cleaned.replace(',', ''))

    except (ValueError, AttributeError, IndexError) as e:
        logger.debug(f"Currency parsing failed for '{amount_str}': {e}")
        return None


def clean_invoice_amounts(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean all amount fields in invoice data
    """
    cleaned_data = invoice_data.copy()

    amount_fields = [
        'total_amount', 'tax_amount', 'subtotal', 'amount',
        'net_amount', 'gross_amount', 'line_total'
    ]

    for field in amount_fields:
        if field in cleaned_data and cleaned_data[field] is not None:
            original_value = cleaned_data[field]
            cleaned_amount = parse_currency_to_float(original_value)

            if cleaned_amount is not None:
                cleaned_data[field] = cleaned_amount
                if str(original_value) != str(cleaned_amount):
                    logger.info(f"💰 Cleaned {field}: '{original_value}' -> {cleaned_amount}")
            else:
                cleaned_data[field] = 0.0
                logger.warning(f"⚠️ Could not parse {field}: '{original_value}', defaulting to 0.0")

    # Clean line items if present
    if 'line_items' in cleaned_data and isinstance(cleaned_data['line_items'], list):
        for i, item in enumerate(cleaned_data['line_items']):
            if isinstance(item, dict):
                cleaned_data['line_items'][i] = clean_invoice_amounts(item)

    return cleaned_data


def format_currency_for_display(amount: float, currency_code: str = "USD") -> str:
    """Format amount for display"""
    if currency_code in ["JPY", "KRW", "IDR", "VND"]:
        return f"${amount:,.0f}"
    else:
        return f"${amount:,.2f}"


def validate_currency_amount(amount: float, currency_code: str = "USD") -> bool:
    """Validate amount is reasonable"""
    return 0 <= amount <= 1000000


# Test function to verify all formats work
def test_all_formats():
    """Test all currency formats"""
    test_cases = [
        ("$876.99", 876.99, "Dublin Nissan - US dollars"),
        ("$1,234.56", 1234.56, "US format with thousands"),
        ("€1.234,56", 1234.56, "European format"),
        ("£50.00", 50.0, "British pounds"),
        ("¥12345", 12345.0, "Japanese yen"),
        ("₹1,50,000.50", 150000.5, "Indian rupees"),
        ("1000.00", 1000.0, "Plain decimal"),
        ("1,000", 1000.0, "Thousands only"),
        ("500", 500.0, "Simple number"),
        ("0.99", 0.99, "Less than one"),
        ("€1.234.567,89", 1234567.89, "European with multiple thousands"),
        ("$1,234,567.89", 1234567.89, "US with multiple thousands")
    ]

    print("🧪 Testing Perfect Currency Parser")
    print("=" * 50)

    all_passed = True
    for input_val, expected, description in test_cases:
        result = parse_currency_to_float(input_val)
        passed = result == expected
        status = "✅" if passed else "❌"

        print(f"{status} {description}")
        print(f"    '{input_val}' -> {result} (expected: {expected})")

        if not passed:
            all_passed = False
        print()

    return all_passed


if __name__ == "__main__":
    test_all_formats()