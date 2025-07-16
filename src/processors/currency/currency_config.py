# src/processors/currency/currency_config.py
"""
Global currency configuration and definitions
Supports 30+ currencies worldwide
"""

from typing import Dict, List, Tuple

# Global Currency Configuration
CURRENCY_CONFIG = {
    # Major World Currencies
    "USD": {"symbol": "$", "code": "USD", "name": "US Dollar", "decimal_places": 2},
    "EUR": {"symbol": "€", "code": "EUR", "name": "Euro", "decimal_places": 2},
    "GBP": {"symbol": "£", "code": "GBP", "name": "British Pound", "decimal_places": 2},
    "CAD": {"symbol": "C$", "code": "CAD", "name": "Canadian Dollar", "decimal_places": 2},
    "MXN": {"symbol": "MX$", "code": "MXN", "name": "Mexican Peso", "decimal_places": 2},
    "INR": {"symbol": "₹", "code": "INR", "name": "Indian Rupee", "decimal_places": 2},
    "AED": {"symbol": "د.إ", "code": "AED", "name": "UAE Dirham", "decimal_places": 2},
    "SAR": {"symbol": "﷼", "code": "SAR", "name": "Saudi Riyal", "decimal_places": 2},
    "JPY": {"symbol": "¥", "code": "JPY", "name": "Japanese Yen", "decimal_places": 0},
    "CNY": {"symbol": "¥", "code": "CNY", "name": "Chinese Yuan", "decimal_places": 2},
    "KRW": {"symbol": "₩", "code": "KRW", "name": "South Korean Won", "decimal_places": 0},
    "AUD": {"symbol": "A$", "code": "AUD", "name": "Australian Dollar", "decimal_places": 2},
    "CHF": {"symbol": "CHF", "code": "CHF", "name": "Swiss Franc", "decimal_places": 2},
    "SEK": {"symbol": "kr", "code": "SEK", "name": "Swedish Krona", "decimal_places": 2},
    "NOK": {"symbol": "kr", "code": "NOK", "name": "Norwegian Krone", "decimal_places": 2},
    "DKK": {"symbol": "kr", "code": "DKK", "name": "Danish Krone", "decimal_places": 2},
    "RUB": {"symbol": "₽", "code": "RUB", "name": "Russian Ruble", "decimal_places": 2},
    "BRL": {"symbol": "R$", "code": "BRL", "name": "Brazilian Real", "decimal_places": 2},
    "ZAR": {"symbol": "R", "code": "ZAR", "name": "South African Rand", "decimal_places": 2},
    "SGD": {"symbol": "S$", "code": "SGD", "name": "Singapore Dollar", "decimal_places": 2},
    "HKD": {"symbol": "HK$", "code": "HKD", "name": "Hong Kong Dollar", "decimal_places": 2},
    "THB": {"symbol": "฿", "code": "THB", "name": "Thai Baht", "decimal_places": 2},
    "MYR": {"symbol": "RM", "code": "MYR", "name": "Malaysian Ringgit", "decimal_places": 2},
    "IDR": {"symbol": "Rp", "code": "IDR", "name": "Indonesian Rupiah", "decimal_places": 0},
    "PHP": {"symbol": "₱", "code": "PHP", "name": "Philippine Peso", "decimal_places": 2},
    "VND": {"symbol": "₫", "code": "VND", "name": "Vietnamese Dong", "decimal_places": 0},
    "TRY": {"symbol": "₺", "code": "TRY", "name": "Turkish Lira", "decimal_places": 2},
    "ILS": {"symbol": "₪", "code": "ILS", "name": "Israeli Shekel", "decimal_places": 2},
    "EGP": {"symbol": "£", "code": "EGP", "name": "Egyptian Pound", "decimal_places": 2},
    "QAR": {"symbol": "﷼", "code": "QAR", "name": "Qatari Riyal", "decimal_places": 2},
    "KWD": {"symbol": "د.ك", "code": "KWD", "name": "Kuwaiti Dinar", "decimal_places": 3},
    "BHD": {"symbol": ".د.ب", "code": "BHD", "name": "Bahraini Dinar", "decimal_places": 3},
    "OMR": {"symbol": "﷼", "code": "OMR", "name": "Omani Rial", "decimal_places": 3}
}

# Currency-specific reasonable ranges (min, max)
CURRENCY_RANGES = {
    "USD": (1, 100000),
    "EUR": (1, 100000),
    "GBP": (1, 100000),
    "CAD": (1, 130000),
    "MXN": (20, 2000000),
    "INR": (50, 7500000),
    "AED": (5, 367000),
    "JPY": (100, 11000000),
    "CNY": (10, 700000),
    "AUD": (1, 150000),
    "CHF": (1, 100000),
    "SEK": (10, 1000000),
    "BRL": (5, 500000),
    "ZAR": (15, 1500000),
    "SGD": (1, 140000),
    "HKD": (8, 780000),
    "THB": (30, 3200000),
    "MYR": (4, 420000),
    "IDR": (15000, 1500000000),
    "PHP": (50, 5000000),
    "VND": (23000, 2300000000),
    "TRY": (8, 800000),
    "ILS": (3, 350000),
    "EGP": (16, 1600000),
    "QAR": (4, 360000),
    "KWD": (0.3, 30000),
    "BHD": (0.4, 38000),
    "OMR": (0.4, 38000),
    "SAR": (4, 375000),
    "RUB": (75, 7500000),
    "KRW": (1200, 120000000)
}

# Region to currency mapping
REGION_CURRENCY_MAP = {
    "US": "USD",
    "CA": "CAD",
    "MX": "MXN",
    "GB": "GBP",
    "DE": "EUR",
    "FR": "EUR",
    "IT": "EUR",
    "ES": "EUR",
    "NL": "EUR",
    "AT": "EUR",
    "BE": "EUR",
    "PT": "EUR",
    "IN": "INR",
    "AE": "AED",
    "SA": "SAR",
    "JP": "JPY",
    "CN": "CNY",
    "KR": "KRW",
    "AU": "AUD",
    "CH": "CHF",
    "SE": "SEK",
    "NO": "NOK",
    "DK": "DKK",
    "BR": "BRL",
    "ZA": "ZAR",
    "SG": "SGD",
    "HK": "HKD",
    "TH": "THB",
    "MY": "MYR",
    "ID": "IDR",
    "PH": "PHP",
    "VN": "VND",
    "TR": "TRY",
    "IL": "ILS",
    "EG": "EGP",
    "QA": "QAR",
    "KW": "KWD",
    "BH": "BHD",
    "OM": "OMR",
    "RU": "RUB"
}


def get_currency_info(currency_code: str) -> Dict:
    """Get currency information by code"""
    return CURRENCY_CONFIG.get(currency_code.upper(), CURRENCY_CONFIG["USD"])


def get_currency_range(currency_code: str) -> Tuple[float, float]:
    """Get reasonable amount range for currency"""
    return CURRENCY_RANGES.get(currency_code.upper(), CURRENCY_RANGES["USD"])


def get_all_currency_symbols() -> List[str]:
    """Get all currency symbols for pattern matching"""
    return [info["symbol"] for info in CURRENCY_CONFIG.values()]


def get_all_currency_codes() -> List[str]:
    """Get all currency codes"""
    return list(CURRENCY_CONFIG.keys())


def get_currency_by_region(region_code: str) -> str:
    """Get default currency for a region"""
    return REGION_CURRENCY_MAP.get(region_code.upper(), "USD")


def format_amount(amount: float, currency_code: str) -> str:
    """Format amount with proper currency symbol and decimal places"""
    currency_info = get_currency_info(currency_code)
    decimal_places = currency_info["decimal_places"]
    symbol = currency_info["symbol"]

    if decimal_places == 0:
        return f"{symbol}{amount:.0f}"
    else:
        return f"{symbol}{amount:.{decimal_places}f}"


def is_valid_currency(currency_code: str) -> bool:
    """Check if currency code is supported"""
    return currency_code.upper() in CURRENCY_CONFIG


def get_currencies_by_symbol(symbol: str) -> List[str]:
    """Get currency codes that use a specific symbol"""
    return [code for code, info in CURRENCY_CONFIG.items() if info["symbol"] == symbol]