# src/processors/currency/currency_detector.py
"""
Currency and region detection from document content
"""

import re
from typing import Dict, List

from .currency_config import CURRENCY_CONFIG, REGION_CURRENCY_MAP


def detect_document_currency_and_region(text: str) -> Dict[str, str]:
    """
    Detect document currency and region from content

    Args:
        text: Document text content

    Returns:
        Dict with detected currency, region, and confidence scores
    """
    text_upper = text.upper()

    # Language/Region indicators
    region_indicators = {
        "US": ["USA", "UNITED STATES", "ZIP CODE", "STATE", "LLC", "INC", "CORP"],
        "CA": ["CANADA", "PROVINCE", "POSTAL CODE", "GST", "HST", "PST", "TORONTO", "VANCOUVER"],
        "MX": ["MEXICO", "MÉXICO", "RFC", "FACTURA", "PESO", "MEXICO CITY"],
        "GB": ["UNITED KINGDOM", "UK", "VAT REG", "POSTCODE", "LTD", "LONDON", "MANCHESTER"],
        "DE": ["DEUTSCHLAND", "GERMANY", "MWST", "GMBH", "UG", "BERLIN", "HAMBURG"],
        "FR": ["FRANCE", "SIRET", "TVA", "SARL", "SAS", "PARIS", "LYON"],
        "IT": ["ITALY", "ITALIA", "IVA", "SRL", "SPA", "ROME", "MILAN"],
        "ES": ["SPAIN", "ESPAÑA", "IVA", "SL", "SA", "MADRID", "BARCELONA"],
        "IN": ["INDIA", "GST", "PAN", "RUPEE", "₹", "MUMBAI", "DELHI", "BANGALORE"],
        "AE": ["UAE", "EMIRATES", "DUBAI", "ABU DHABI", "DIRHAM", "SHARJAH"],
        "SA": ["SAUDI", "ARABIA", "RIYAL", "VAT NO", "RIYADH", "JEDDAH"],
        "AU": ["AUSTRALIA", "ABN", "ACN", "GST", "A$", "SYDNEY", "MELBOURNE"],
        "SG": ["SINGAPORE", "GST REG", "UEN", "S$"],
        "HK": ["HONG KONG", "HK$", "COMPANY REG"],
        "JP": ["JAPAN", "YEN", "¥", "株式会社", "TOKYO", "OSAKA"],
        "CN": ["CHINA", "YUAN", "人民币", "¥", "BEIJING", "SHANGHAI"],
        "BR": ["BRAZIL", "BRASIL", "CNPJ", "CPF", "REAL", "SAO PAULO", "RIO"],
        "ZA": ["SOUTH AFRICA", "VAT NO", "RAND", "PTY", "CAPE TOWN", "JOHANNESBURG"],
        "CH": ["SWITZERLAND", "SCHWEIZ", "SUISSE", "CHF", "ZURICH", "GENEVA"],
        "SE": ["SWEDEN", "SVERIGE", "KRONA", "ORG NR", "STOCKHOLM"],
        "NO": ["NORWAY", "NORGE", "KRONER", "ORG NR", "OSLO"],
        "DK": ["DENMARK", "DANMARK", "KRONER", "CVR", "COPENHAGEN"],
        "TR": ["TURKEY", "TÜRKİYE", "LIRA", "VKN", "ISTANBUL", "ANKARA"],
        "RU": ["RUSSIA", "РОССИЯ", "РУБЛЬ", "ИНН", "MOSCOW", "ST PETERSBURG"],
        "IL": ["ISRAEL", "SHEKEL", "₪", "מס׳", "TEL AVIV", "JERUSALEM"],
        "EG": ["EGYPT", "POUND", "TAX REG", "CAIRO"],
        "QA": ["QATAR", "RIYAL", "TAX NO", "DOHA"],
        "KW": ["KUWAIT", "DINAR", "TAX REG", "KUWAIT CITY"],
        "BH": ["BAHRAIN", "DINAR", "CR NO", "MANAMA"],
        "OM": ["OMAN", "RIAL", "TAX REG", "MUSCAT"],
        "TH": ["THAILAND", "BAHT", "฿", "VAT", "BANGKOK"],
        "MY": ["MALAYSIA", "RINGGIT", "RM", "GST", "KUALA LUMPUR"],
        "ID": ["INDONESIA", "RUPIAH", "RP", "JAKARTA"],
        "PH": ["PHILIPPINES", "PESO", "₱", "VAT", "MANILA"],
        "VN": ["VIETNAM", "DONG", "₫", "VAT", "HO CHI MINH"],
        "KR": ["KOREA", "WON", "₩", "VAT", "SEOUL"]
    }

    detected_region = "US"  # Default
    region_confidence = 0

    for region, indicators in region_indicators.items():
        region_score = sum(1 for indicator in indicators if indicator in text_upper)
        if region_score > region_confidence:
            region_confidence = region_score
            detected_region = region

    # Currency detection with enhanced patterns
    currency_indicators = {
        "USD": ["$", "USD", "DOLLAR", "CENTS", "US DOLLAR"],
        "EUR": ["€", "EUR", "EURO", "EUROS"],
        "GBP": ["£", "GBP", "POUND", "PENCE", "STERLING"],
        "CAD": ["C$", "CAD", "CANADIAN", "CANADIAN DOLLAR"],
        "MXN": ["MX$", "MXN", "PESO", "MEXICAN PESO"],
        "INR": ["₹", "INR", "RUPEE", "PAISA", "INDIAN RUPEE"],
        "AED": ["د.إ", "AED", "DIRHAM", "FILS", "UAE DIRHAM"],
        "JPY": ["¥", "JPY", "YEN", "JAPANESE YEN"],
        "CNY": ["¥", "CNY", "YUAN", "RMB", "CHINESE YUAN"],
        "AUD": ["A$", "AUD", "AUSTRALIAN", "AUSTRALIAN DOLLAR"],
        "CHF": ["CHF", "FRANC", "SWISS FRANC"],
        "SEK": ["kr", "SEK", "KRONA", "SWEDISH KRONA"],
        "NOK": ["kr", "NOK", "KRONE", "NORWEGIAN KRONE"],
        "DKK": ["kr", "DKK", "KRONE", "DANISH KRONE"],
        "BRL": ["R$", "BRL", "REAL", "BRAZILIAN REAL"],
        "ZAR": ["R", "ZAR", "RAND", "SOUTH AFRICAN RAND"],
        "SGD": ["S$", "SGD", "SINGAPORE", "SINGAPORE DOLLAR"],
        "HKD": ["HK$", "HKD", "HONG KONG", "HONG KONG DOLLAR"],
        "RUB": ["₽", "RUB", "RUBLE", "RUSSIAN RUBLE"],
        "TRY": ["₺", "TRY", "LIRA", "TURKISH LIRA"],
        "ILS": ["₪", "ILS", "SHEKEL", "ISRAELI SHEKEL"],
        "THB": ["฿", "THB", "BAHT", "THAI BAHT"],
        "MYR": ["RM", "MYR", "RINGGIT", "MALAYSIAN RINGGIT"],
        "IDR": ["RP", "IDR", "RUPIAH", "INDONESIAN RUPIAH"],
        "PHP": ["₱", "PHP", "PESO", "PHILIPPINE PESO"],
        "VND": ["₫", "VND", "DONG", "VIETNAMESE DONG"],
        "SAR": ["﷼", "SAR", "RIYAL", "SAUDI RIYAL"],
        "QAR": ["﷼", "QAR", "RIYAL", "QATARI RIYAL"],
        "KWD": ["د.ك", "KWD", "DINAR", "KUWAITI DINAR"],
        "BHD": [".د.ب", "BHD", "DINAR", "BAHRAINI DINAR"],
        "OMR": ["﷼", "OMR", "RIAL", "OMANI RIAL"],
        "EGP": ["EGP", "EGYPTIAN", "EGYPTIAN POUND"],
        "KRW": ["₩", "KRW", "WON", "KOREAN WON"]
    }

    detected_currency = REGION_CURRENCY_MAP.get(detected_region, "USD")  # Default based on region
    currency_confidence = 0

    # Check for explicit currency indicators
    for currency, indicators in currency_indicators.items():
        currency_score = sum(1 for indicator in indicators if indicator in text_upper)
        if currency_score > currency_confidence:
            currency_confidence = currency_score
            detected_currency = currency

    # Special handling for currencies with same symbols
    if detected_currency in ["JPY", "CNY"] and "¥" in text_upper:
        # Distinguish between Japanese Yen and Chinese Yuan
        if any(indicator in text_upper for indicator in ["JAPAN", "YEN", "株式会社", "TOKYO"]):
            detected_currency = "JPY"
        elif any(indicator in text_upper for indicator in ["CHINA", "YUAN", "人民币", "BEIJING"]):
            detected_currency = "CNY"

    # Override with region-based currency if no explicit currency found
    if currency_confidence == 0:
        detected_currency = REGION_CURRENCY_MAP.get(detected_region, "USD")
        currency_confidence = region_confidence

    return {
        "region": detected_region,
        "currency": detected_currency,
        "region_confidence": region_confidence,
        "currency_confidence": currency_confidence
    }


def detect_number_format(text: str, region: str) -> str:
    """
    Detect number formatting style (US vs European)

    Args:
        text: Document text
        region: Detected region

    Returns:
        Format style: 'us' or 'european'
    """
    # European regions typically use comma as decimal separator
    european_regions = ["DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT", "DK", "NO", "SE"]

    if region in european_regions:
        return 'european'

    # Check for explicit formatting patterns in text
    us_patterns = [
        r'\d{1,3}(?:,\d{3})+\.\d{2}',  # 1,234.56
        r'\$\d+\.\d{2}',  # $123.45
    ]

    european_patterns = [
        r'\d{1,3}(?:\.\d{3})+,\d{2}',  # 1.234,56
        r'€\d+,\d{2}',  # €123,45
    ]

    us_matches = sum(len(re.findall(pattern, text)) for pattern in us_patterns)
    european_matches = sum(len(re.findall(pattern, text)) for pattern in european_patterns)

    if european_matches > us_matches:
        return 'european'
    else:
        return 'us'


def get_language_indicators(text: str) -> List[str]:
    """
    Get language indicators from text

    Args:
        text: Document text

    Returns:
        List of detected languages
    """
    language_patterns = {
        "en": ["INVOICE", "TOTAL", "AMOUNT", "DUE", "DATE", "COMPANY"],
        "de": ["RECHNUNG", "BETRAG", "DATUM", "GMBH", "MWST"],
        "fr": ["FACTURE", "MONTANT", "DATE", "SOCIETE", "TVA"],
        "es": ["FACTURA", "IMPORTE", "FECHA", "SOCIEDAD", "IVA"],
        "it": ["FATTURA", "IMPORTO", "DATA", "SOCIETA", "IVA"],
        "pt": ["FATURA", "VALOR", "DATA", "SOCIEDADE", "IVA"],
        "nl": ["FACTUUR", "BEDRAG", "DATUM", "MAATSCHAPPIJ", "BTW"],
        "zh": ["发票", "金额", "日期", "公司", "税"],
        "ja": ["請求書", "金額", "日付", "会社", "税"],
        "ar": ["فاتورة", "المبلغ", "التاريخ", "شركة", "ضريبة"],
        "ru": ["СЧЕТ", "СУММА", "ДАТА", "КОМПАНИЯ", "НДС"]
    }

    detected_languages = []
    text_upper = text.upper()

    for lang, indicators in language_patterns.items():
        matches = sum(1 for indicator in indicators if indicator in text_upper)
        if matches >= 2:  # At least 2 indicators
            detected_languages.append(lang)

    return detected_languages if detected_languages else ["en"]  # Default to English