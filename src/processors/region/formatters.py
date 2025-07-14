# src/processors/region/formatters.py
"""
Regional number formatting and normalization utilities
FIXED: Syntax error in line 163
"""

import re
from typing import Optional, Dict


def normalize_amount_text(amount_text: str, region: str = "US") -> str:
    """
    Normalize amount text based on regional formatting

    Args:
        amount_text: Raw amount text from document
        region: Region code (US, DE, FR, etc.)

    Returns:
        Normalized amount string ready for float conversion
    """
    if not amount_text:
        return ""

    # Remove extra whitespace
    amount_text = amount_text.strip()

    # European formatting (1.234,56) vs US formatting (1,234.56)
    european_regions = ["DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "DK", "NO", "SE", "FI"]

    if region in european_regions:
        # European format: 1.234,56 -> 1234.56
        if ',' in amount_text and '.' in amount_text:
            # Format like 1.234,56
            if amount_text.rfind(',') > amount_text.rfind('.'):
                amount_text = amount_text.replace('.', '').replace(',', '.')
            else:
                # Unusual case: 1,234.56 in European document
                amount_text = amount_text.replace(',', '')
        elif ',' in amount_text and amount_text.count(',') == 1:
            # Check if comma is decimal separator (has 2 digits after)
            parts = amount_text.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2 and parts[1].isdigit():
                # Format like 1234,56 -> 1234.56
                amount_text = amount_text.replace(',', '.')
            else:
                # Format like 1,234 (thousands separator)
                amount_text = amount_text.replace(',', '')
    else:
        # US/International format: 1,234.56
        if ',' in amount_text and '.' in amount_text:
            # Format like 1,234.56 -> remove thousands separators
            amount_text = amount_text.replace(',', '')
        elif ',' in amount_text:
            # Could be thousands separator or decimal (rare)
            # If more than 3 digits after comma, likely thousands separator
            parts = amount_text.split(',')
            if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
                # Format like 1,234 (thousands separator)
                amount_text = amount_text.replace(',', '')
            # Otherwise keep comma as is (unusual case)

    return amount_text


def format_amount_by_region(amount: float, currency_code: str, region: str = "US") -> str:
    """
    Format amount according to regional conventions

    Args:
        amount: Numeric amount
        currency_code: Currency code (USD, EUR, etc.)
        region: Region code for formatting rules

    Returns:
        Formatted amount string
    """
    from ..currency.currency_config import get_currency_info

    currency_info = get_currency_info(currency_code)
    symbol = currency_info["symbol"]
    decimal_places = currency_info["decimal_places"]

    # European formatting
    european_regions = ["DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "DK", "NO", "SE", "FI"]

    if region in european_regions:
        # European style: 1.234,56 €
        if decimal_places == 0:
            # No decimals (JPY, KRW, etc.)
            amount_str = f"{amount:,.0f}".replace(',', '.')
        else:
            # With decimals
            amount_str = f"{amount:,.{decimal_places}f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Symbol placement varies by region
        if region in ["DE", "AT"]:
            return f"{amount_str} {symbol}"  # German style: 1.234,56 €
        else:
            return f"{symbol}{amount_str}"  # Most European: €1.234,56

    # US/International formatting
    else:
        if decimal_places == 0:
            return f"{symbol}{amount:,.0f}"
        else:
            return f"{symbol}{amount:,.{decimal_places}f}"


def clean_amount_string(text: str) -> Optional[str]:
    """
    Clean and standardize amount text for extraction

    Args:
        text: Raw text containing amount

    Returns:
        Cleaned amount string or None if not valid
    """
    if not text:
        return None

    # Remove extra whitespace
    text = text.strip()

    # Extract amount using comprehensive regex
    amount_patterns = [
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # Various formats
        r'(\d+(?:[.,]\d{2})?)',  # Simple formats
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            amount = match.group(1)
            try:
                # Basic validation - should contain digits
                if sum(c.isdigit() for c in amount) > 0:
                    return amount
            except:
                continue

    return None


def detect_decimal_separator(text: str) -> str:
    """
    Detect decimal separator used in document (. or ,)

    Args:
        text: Document text

    Returns:
        Decimal separator: '.' or ','
    """
    # Look for patterns that clearly indicate decimal separators
    comma_decimal_patterns = [
        r'\d+,\d{2}\s*€',  # 123,45 €
        r'\d+,\d{2}\s*EUR',  # 123,45 EUR
        r'€\s*\d+,\d{2}',  # € 123,45
    ]

    dot_decimal_patterns = [
        r'\d+\.\d{2}\s*\$',  # 123.45 $
        r'\d+\.\d{2}\s*USD',  # 123.45 USD
        r'\$\s*\d+\.\d{2}',  # $ 123.45
    ]

    comma_score = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in comma_decimal_patterns)
    dot_score = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in dot_decimal_patterns)

    return ',' if comma_score > dot_score else '.'


def detect_thousands_separator(text: str) -> str:
    """
    Detect thousands separator used in document (, or .)

    Args:
        text: Document text

    Returns:
        Thousands separator: ',' or '.'
    """
    # Look for clear thousands separator patterns
    comma_thousands_patterns = [
        r'\d{1,3}(?:,\d{3})+\.\d{2}',  # 1,234.56
        r'\$\d{1,3}(?:,\d{3})+',  # $1,234
    ]

    dot_thousands_patterns = [
        r'\d{1,3}(?:\.\d{3})+,\d{2}',  # 1.234,56
        r'€\d{1,3}(?:\.\d{3})+',  # €1.234
    ]

    comma_score = sum(len(re.findall(pattern, text)) for pattern in comma_thousands_patterns)
    dot_score = sum(len(re.findall(pattern, text)) for pattern in dot_thousands_patterns)

    return ',' if comma_score > dot_score else '.'


def standardize_number_format(amount_str: str, decimal_sep: str = '.', thousands_sep: str = ',') -> str:
    """
    Standardize number format to US style (1,234.56)

    Args:
        amount_str: Amount string to standardize
        decimal_sep: Current decimal separator
        thousands_sep: Current thousands separator

    Returns:
        Standardized amount string
    """
    if not amount_str:
        return ""

    # If already in standard format, return as is
    if decimal_sep == '.' and thousands_sep == ',':
        return amount_str

    # Convert European format (1.234,56) to US format (1234.56)
    if decimal_sep == ',' and thousands_sep == '.':
        # Replace thousands separators first, then decimal separator
        standardized = amount_str.replace('.', '').replace(',', '.')
        return standardized

    # Handle other combinations
    if decimal_sep == ',':
        # Replace decimal separator
        amount_str = amount_str.replace(',', '.')

    if thousands_sep == '.' and decimal_sep != '.':
        # Remove thousands separators
        parts = amount_str.split('.')
        if len(parts) > 1:
            # Keep only the last part as decimal, join others
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]

    return amount_str


def validate_amount_format(amount_str: str) -> bool:
    """
    Validate if amount string is in valid format

    Args:
        amount_str: Amount string to validate

    Returns:
        True if valid format, False otherwise
    """
    if not amount_str:
        return False

    # Valid amount patterns
    valid_patterns = [
        r'^\d+$',  # 1234
        r'^\d+\.\d{1,3}$',  # 1234.56
        r'^\d{1,3}(?:,\d{3})*$',  # 1,234
        r'^\d{1,3}(?:,\d{3})*\.\d{1,3}$',  # 1,234.56
        r'^\d{1,3}(?:\.\d{3})*$',  # 1.234 (European thousands)
        r'^\d{1,3}(?:\.\d{3})*,\d{1,3}$',  # 1.234,56 (European)
    ]

    return any(re.match(pattern, amount_str) for pattern in valid_patterns)


def get_regional_formatting_rules(region: str) -> Dict[str, str]:
    """
    Get formatting rules for specific region

    Args:
        region: Region code (US, DE, FR, etc.)

    Returns:
        Dict with formatting rules
    """
    regional_rules = {
        # North America
        "US": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "CA": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "MX": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},

        # Europe - Germanic
        "DE": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "after"},
        "AT": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "after"},
        "CH": {"decimal_sep": ".", "thousands_sep": "'", "symbol_position": "before"},

        # Europe - Romance
        "FR": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},
        "IT": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "after"},
        "ES": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "after"},
        "PT": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},

        # Europe - Nordic
        "SE": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},
        "NO": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},
        "DK": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "after"},
        "FI": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},

        # Europe - Other
        "GB": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "NL": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},
        "BE": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},

        # Asia
        "IN": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "JP": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "CN": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "KR": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "SG": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "HK": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "TH": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "MY": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "ID": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},
        "PH": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "VN": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},

        # Middle East
        "AE": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "SA": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "QA": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "KW": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "BH": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "OM": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "IL": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "TR": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},

        # Other
        "AU": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "NZ": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
        "ZA": {"decimal_sep": ".", "thousands_sep": " ", "symbol_position": "before"},
        "BR": {"decimal_sep": ",", "thousands_sep": ".", "symbol_position": "before"},
        "RU": {"decimal_sep": ",", "thousands_sep": " ", "symbol_position": "after"},
        "EG": {"decimal_sep": ".", "thousands_sep": ",", "symbol_position": "before"},
    }

    # Default to US formatting
    return regional_rules.get(region, regional_rules["US"])