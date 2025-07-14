# src/processors/region/region_detector.py
"""
Region and language detection from document content
"""

import re
from typing import Dict, List, Tuple


def detect_region(text: str) -> str:
    """
    Detect document region from content

    Args:
        text: Document text content

    Returns:
        Two-letter region code (US, DE, FR, etc.)
    """
    detection_result = detect_region_with_confidence(text)
    return detection_result["region"]


def detect_region_with_confidence(text: str) -> Dict[str, any]:
    """
    Detect document region with confidence scores

    Args:
        text: Document text content

    Returns:
        Dict with region, confidence, and details
    """
    text_upper = text.upper()

    # Language/Region indicators with scoring
    region_indicators = {
        "US": {
            "indicators": ["USA", "UNITED STATES", "ZIP CODE", "STATE", "LLC", "INC", "CORP", "DOLLAR", "USD"],
            "patterns": [r'\b\d{5}(-\d{4})?\b', r'\b[A-Z]{2}\s+\d{5}\b'],  # ZIP codes
            "weight": 1.0
        },
        "CA": {
            "indicators": ["CANADA", "PROVINCE", "POSTAL CODE", "GST", "HST", "PST", "CANADIAN", "CAD"],
            "patterns": [r'\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b'],  # Canadian postal codes
            "weight": 1.0
        },
        "MX": {
            "indicators": ["MEXICO", "MÉXICO", "RFC", "FACTURA", "PESO", "MEXICAN", "MXN"],
            "patterns": [r'\bRFC\s*[A-Z0-9]{12,13}\b'],
            "weight": 1.0
        },
        "GB": {
            "indicators": ["UNITED KINGDOM", "UK", "VAT REG", "POSTCODE", "LTD", "BRITISH", "GBP", "POUND"],
            "patterns": [r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b'],  # UK postcodes
            "weight": 1.0
        },
        "DE": {
            "indicators": ["DEUTSCHLAND", "GERMANY", "MWST", "GMBH", "UG", "GERMAN", "EUR"],
            "patterns": [r'\b\d{5}\s+[A-Z][a-z]+\b'],  # German postal codes
            "weight": 1.0
        },
        "FR": {
            "indicators": ["FRANCE", "SIRET", "TVA", "SARL", "SAS", "FRENCH", "EUR"],
            "patterns": [r'\b\d{5}\s+[A-Z][a-z]+\b'],  # French postal codes
            "weight": 1.0
        },
        "IT": {
            "indicators": ["ITALY", "ITALIA", "IVA", "SRL", "SPA", "ITALIAN", "EUR"],
            "patterns": [r'\b\d{5}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "ES": {
            "indicators": ["SPAIN", "ESPAÑA", "IVA", "SL", "SA", "SPANISH", "EUR"],
            "patterns": [r'\b\d{5}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "IN": {
            "indicators": ["INDIA", "GST", "PAN", "RUPEE", "₹", "INDIAN", "INR"],
            "patterns": [r'\bGST\s*[A-Z0-9]{15}\b', r'\bPAN\s*[A-Z]{5}\d{4}[A-Z]\b'],
            "weight": 1.0
        },
        "AE": {
            "indicators": ["UAE", "EMIRATES", "DUBAI", "ABU DHABI", "DIRHAM", "AED"],
            "patterns": [r'\bTRN\s*[0-9]{15}\b'],
            "weight": 1.0
        },
        "SA": {
            "indicators": ["SAUDI", "ARABIA", "RIYAL", "VAT NO", "SAR"],
            "patterns": [r'\bVAT\s*[0-9]{15}\b'],
            "weight": 1.0
        },
        "AU": {
            "indicators": ["AUSTRALIA", "ABN", "ACN", "GST", "A$", "AUD", "AUSTRALIAN"],
            "patterns": [r'\bABN\s*\d{2}\s*\d{3}\s*\d{3}\s*\d{3}\b'],
            "weight": 1.0
        },
        "SG": {
            "indicators": ["SINGAPORE", "GST REG", "UEN", "S$", "SGD"],
            "patterns": [r'\bUEN\s*[0-9]{8,10}[A-Z]\b'],
            "weight": 1.0
        },
        "HK": {
            "indicators": ["HONG KONG", "HK$", "COMPANY REG", "HKD"],
            "patterns": [r'\bCR\s*NO\s*[0-9]+\b'],
            "weight": 1.0
        },
        "JP": {
            "indicators": ["JAPAN", "YEN", "¥", "株式会社", "JAPANESE", "JPY"],
            "patterns": [r'株式会社', r'\b〒\d{3}-\d{4}\b'],
            "weight": 1.0
        },
        "CN": {
            "indicators": ["CHINA", "YUAN", "人民币", "¥", "CHINESE", "CNY"],
            "patterns": [r'[0-9]{6}'],  # Simple pattern for Chinese postal codes
            "weight": 1.0
        },
        "BR": {
            "indicators": ["BRAZIL", "BRASIL", "CNPJ", "CPF", "REAL", "BRL"],
            "patterns": [r'\bCNPJ\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'],
            "weight": 1.0
        },
        "ZA": {
            "indicators": ["SOUTH AFRICA", "VAT NO", "RAND", "PTY", "ZAR"],
            "patterns": [r'\bVAT\s*[0-9]{10}\b'],
            "weight": 1.0
        },
        "CH": {
            "indicators": ["SWITZERLAND", "SCHWEIZ", "SUISSE", "CHF", "SWISS"],
            "patterns": [r'\bCH-\d{4}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "SE": {
            "indicators": ["SWEDEN", "SVERIGE", "KRONA", "ORG NR", "SEK"],
            "patterns": [r'\b\d{3}\s*\d{2}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "NO": {
            "indicators": ["NORWAY", "NORGE", "KRONER", "ORG NR", "NOK"],
            "patterns": [r'\b\d{4}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "DK": {
            "indicators": ["DENMARK", "DANMARK", "KRONER", "CVR", "DKK"],
            "patterns": [r'\b\d{4}\s+[A-Z][a-z]+\b'],
            "weight": 1.0
        },
        "TR": {
            "indicators": ["TURKEY", "TÜRKİYE", "LIRA", "VKN", "TRY"],
            "patterns": [r'\bVKN\s*[0-9]{10}\b'],
            "weight": 1.0
        },
        "RU": {
            "indicators": ["RUSSIA", "РОССИЯ", "РУБЛЬ", "ИНН", "RUB"],
            "patterns": [r'\bИНН\s*[0-9]{10,12}\b'],
            "weight": 1.0
        },
        "IL": {
            "indicators": ["ISRAEL", "SHEKEL", "₪", "מס׳", "ILS"],
            "patterns": [r'\bמס׳\s*[0-9]+\b'],
            "weight": 1.0
        },
        "EG": {
            "indicators": ["EGYPT", "POUND", "TAX REG", "EGP"],
            "patterns": [r'\bTAX\s*REG\s*[0-9]+\b'],
            "weight": 1.0
        },
        "QA": {
            "indicators": ["QATAR", "RIYAL", "TAX NO", "QAR"],
            "patterns": [r'\bTAX\s*NO\s*[0-9]+\b'],
            "weight": 1.0
        },
        "KW": {
            "indicators": ["KUWAIT", "DINAR", "TAX REG", "KWD"],
            "patterns": [r'\bTAX\s*REG\s*[0-9]+\b'],
            "weight": 1.0
        },
        "BH": {
            "indicators": ["BAHRAIN", "DINAR", "CR NO", "BHD"],
            "patterns": [r'\bCR\s*NO\s*[0-9]+\b'],
            "weight": 1.0
        },
        "OM": {
            "indicators": ["OMAN", "RIAL", "TAX REG", "OMR"],
            "patterns": [r'\bTAX\s*REG\s*[0-9]+\b'],
            "weight": 1.0
        },
        "TH": {
            "indicators": ["THAILAND", "BAHT", "฿", "VAT", "THB"],
            "patterns": [r'\bVAT\s*[0-9]{13}\b'],
            "weight": 1.0
        },
        "MY": {
            "indicators": ["MALAYSIA", "RINGGIT", "RM", "GST", "MYR"],
            "patterns": [r'\bGST\s*[0-9]{12}\b'],
            "weight": 1.0
        },
        "ID": {
            "indicators": ["INDONESIA", "RUPIAH", "RP", "NPWP", "IDR"],
            "patterns": [r'\bNPWP\s*[0-9]{15}\b'],
            "weight": 1.0
        },
        "PH": {
            "indicators": ["PHILIPPINES", "PESO", "₱", "TIN", "PHP"],
            "patterns": [r'\bTIN\s*[0-9]{9,12}\b'],
            "weight": 1.0
        },
        "VN": {
            "indicators": ["VIETNAM", "DONG", "₫", "VAT", "VND"],
            "patterns": [r'\bVAT\s*[0-9]{10,13}\b'],
            "weight": 1.0
        },
        "KR": {
            "indicators": ["KOREA", "WON", "₩", "BRN", "KRW"],
            "patterns": [r'\bBRN\s*[0-9]{10}\b'],
            "weight": 1.0
        }
    }

    region_scores = {}

    # Calculate scores for each region
    for region, config in region_indicators.items():
        score = 0
        matches_found = []

        # Check text indicators
        for indicator in config["indicators"]:
            if indicator in text_upper:
                score += 10 * config["weight"]
                matches_found.append(f"indicator:{indicator}")

        # Check regex patterns
        for pattern in config["patterns"]:
            try:
                if re.search(pattern, text):
                    score += 15 * config["weight"]
                    matches_found.append(f"pattern:{pattern}")
            except re.error:
                continue

        if score > 0:
            region_scores[region] = {
                "score": score,
                "matches": matches_found
            }

    # Determine best region
    if region_scores:
        best_region = max(region_scores.keys(), key=lambda r: region_scores[r]["score"])
        best_score = region_scores[best_region]["score"]
        confidence = min(best_score / 50.0, 1.0)  # Normalize to 0-1

        return {
            "region": best_region,
            "confidence": confidence,
            "score": best_score,
            "matches": region_scores[best_region]["matches"],
            "all_scores": region_scores
        }

    # Default to US if no clear indicators
    return {
        "region": "US",
        "confidence": 0.1,
        "score": 0,
        "matches": [],
        "all_scores": {}
    }


def detect_language(text: str) -> str:
    """
    Detect document language from content

    Args:
        text: Document text content

    Returns:
        Two-letter language code (en, de, fr, etc.)
    """
    language_result = detect_language_with_confidence(text)
    return language_result["language"]


def detect_language_with_confidence(text: str) -> Dict[str, any]:
    """
    Detect document language with confidence scores

    Args:
        text: Document text content

    Returns:
        Dict with language, confidence, and details
    """
    text_upper = text.upper()

    language_patterns = {
        "en": {
            "keywords": ["INVOICE", "TOTAL", "AMOUNT", "DUE", "DATE", "COMPANY", "PAYMENT", "CUSTOMER"],
            "patterns": [r'\bTHE\b', r'\bAND\b', r'\bOR\b', r'\bTO\b', r'\bFOR\b'],
            "weight": 1.0
        },
        "de": {
            "keywords": ["RECHNUNG", "BETRAG", "DATUM", "GMBH", "MWST", "GESELLSCHAFT", "ZAHLUNG"],
            "patterns": [r'\bUND\b', r'\bODER\b', r'\bDER\b', r'\bDIE\b', r'\bDAS\b'],
            "weight": 1.0
        },
        "fr": {
            "keywords": ["FACTURE", "MONTANT", "DATE", "SOCIETE", "TVA", "PAIEMENT", "CLIENT"],
            "patterns": [r'\bET\b', r'\bOU\b', r'\bLE\b', r'\bLA\b', r'\bLES\b'],
            "weight": 1.0
        },
        "es": {
            "keywords": ["FACTURA", "IMPORTE", "FECHA", "SOCIEDAD", "IVA", "PAGO", "CLIENTE"],
            "patterns": [r'\bY\b', r'\bO\b', r'\bEL\b', r'\bLA\b', r'\bLOS\b'],
            "weight": 1.0
        },
        "it": {
            "keywords": ["FATTURA", "IMPORTO", "DATA", "SOCIETA", "IVA", "PAGAMENTO", "CLIENTE"],
            "patterns": [r'\bE\b', r'\bO\b', r'\bIL\b', r'\bLA\b', r'\bI\b'],
            "weight": 1.0
        },
        "pt": {
            "keywords": ["FATURA", "VALOR", "DATA", "SOCIEDADE", "IVA", "PAGAMENTO", "CLIENTE"],
            "patterns": [r'\bE\b', r'\bOU\b', r'\bO\b', r'\bA\b', r'\bOS\b'],
            "weight": 1.0
        },
        "nl": {
            "keywords": ["FACTUUR", "BEDRAG", "DATUM", "MAATSCHAPPIJ", "BTW", "BETALING", "KLANT"],
            "patterns": [r'\bEN\b', r'\bOF\b', r'\bDE\b', r'\bHET\b', r'\bVAN\b'],
            "weight": 1.0
        },
        "zh": {
            "keywords": ["发票", "金额", "日期", "公司", "税", "付款", "客户"],
            "patterns": [r'[一-龯]+'],  # Chinese characters
            "weight": 1.0
        },
        "ja": {
            "keywords": ["請求書", "金額", "日付", "会社", "税", "支払", "顧客"],
            "patterns": [r'[ひ-ゖ]+', r'[ア-ヶ]+', r'[一-龯]+'],  # Japanese characters
            "weight": 1.0
        },
        "ar": {
            "keywords": ["فاتورة", "المبلغ", "التاريخ", "شركة", "ضريبة", "دفع", "عميل"],
            "patterns": [r'[\u0600-\u06FF]+'],  # Arabic characters
            "weight": 1.0
        },
        "ru": {
            "keywords": ["СЧЕТ", "СУММА", "ДАТА", "КОМПАНИЯ", "НДС", "ПЛАТЕЖ", "КЛИЕНТ"],
            "patterns": [r'[А-Я]+'],  # Cyrillic characters
            "weight": 1.0
        }
    }

    language_scores = {}

    # Calculate scores for each language
    for language, config in language_patterns.items():
        score = 0
        matches_found = []

        # Check keywords
        for keyword in config["keywords"]:
            if keyword in text_upper:
                score += 10 * config["weight"]
                matches_found.append(f"keyword:{keyword}")

        # Check patterns
        for pattern in config["patterns"]:
            try:
                matches = len(re.findall(pattern, text_upper))
                if matches > 0:
                    score += min(matches * 2, 20) * config["weight"]  # Cap pattern scoring
                    matches_found.append(f"pattern:{pattern}:{matches}")
            except re.error:
                continue

        if score > 0:
            language_scores[language] = {
                "score": score,
                "matches": matches_found
            }

    # Determine best language
    if language_scores:
        best_language = max(language_scores.keys(), key=lambda l: language_scores[l]["score"])
        best_score = language_scores[best_language]["score"]
        confidence = min(best_score / 50.0, 1.0)  # Normalize to 0-1

        return {
            "language": best_language,
            "confidence": confidence,
            "score": best_score,
            "matches": language_scores[best_language]["matches"],
            "all_scores": language_scores
        }

    # Default to English if no clear indicators
    return {
        "language": "en",
        "confidence": 0.1,
        "score": 0,
        "matches": [],
        "all_scores": {}
    }


def get_region_currency_mapping() -> Dict[str, str]:
    """
    Get mapping of regions to their default currencies

    Returns:
        Dict mapping region codes to currency codes
    """
    return {
        "US": "USD", "CA": "CAD", "MX": "MXN",
        "GB": "GBP", "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR",
        "IN": "INR", "AE": "AED", "SA": "SAR", "JP": "JPY", "CN": "CNY",
        "AU": "AUD", "CH": "CHF", "SE": "SEK", "NO": "NOK", "DK": "DKK",
        "BR": "BRL", "ZA": "ZAR", "SG": "SGD", "HK": "HKD", "RU": "RUB",
        "TR": "TRY", "IL": "ILS", "EG": "EGP", "QA": "QAR", "KW": "KWD",
        "BH": "BHD", "OM": "OMR", "TH": "THB", "MY": "MYR", "ID": "IDR",
        "PH": "PHP", "VN": "VND", "KR": "KRW"
    }


def get_region_info(region_code: str) -> Dict[str, str]:
    """
    Get comprehensive information about a region

    Args:
        region_code: Two-letter region code

    Returns:
        Dict with region information
    """
    region_info = {
        "US": {"name": "United States", "language": "en", "currency": "USD"},
        "CA": {"name": "Canada", "language": "en", "currency": "CAD"},
        "MX": {"name": "Mexico", "language": "es", "currency": "MXN"},
        "GB": {"name": "United Kingdom", "language": "en", "currency": "GBP"},
        "DE": {"name": "Germany", "language": "de", "currency": "EUR"},
        "FR": {"name": "France", "language": "fr", "currency": "EUR"},
        "IT": {"name": "Italy", "language": "it", "currency": "EUR"},
        "ES": {"name": "Spain", "language": "es", "currency": "EUR"},
        "IN": {"name": "India", "language": "en", "currency": "INR"},
        "AE": {"name": "United Arab Emirates", "language": "ar", "currency": "AED"},
        "SA": {"name": "Saudi Arabia", "language": "ar", "currency": "SAR"},
        "JP": {"name": "Japan", "language": "ja", "currency": "JPY"},
        "CN": {"name": "China", "language": "zh", "currency": "CNY"},
        "AU": {"name": "Australia", "language": "en", "currency": "AUD"},
        "CH": {"name": "Switzerland", "language": "de", "currency": "CHF"},
        "SE": {"name": "Sweden", "language": "sv", "currency": "SEK"},
        "NO": {"name": "Norway", "language": "no", "currency": "NOK"},
        "DK": {"name": "Denmark", "language": "da", "currency": "DKK"},
        "BR": {"name": "Brazil", "language": "pt", "currency": "BRL"},
        "ZA": {"name": "South Africa", "language": "en", "currency": "ZAR"},
        "SG": {"name": "Singapore", "language": "en", "currency": "SGD"},
        "HK": {"name": "Hong Kong", "language": "en", "currency": "HKD"},
        "RU": {"name": "Russia", "language": "ru", "currency": "RUB"},
        "TR": {"name": "Turkey", "language": "tr", "currency": "TRY"},
        "IL": {"name": "Israel", "language": "he", "currency": "ILS"},
        "EG": {"name": "Egypt", "language": "ar", "currency": "EGP"},
        "QA": {"name": "Qatar", "language": "ar", "currency": "QAR"},
        "KW": {"name": "Kuwait", "language": "ar", "currency": "KWD"},
        "BH": {"name": "Bahrain", "language": "ar", "currency": "BHD"},
        "OM": {"name": "Oman", "language": "ar", "currency": "OMR"},
        "TH": {"name": "Thailand", "language": "th", "currency": "THB"},
        "MY": {"name": "Malaysia", "language": "ms", "currency": "MYR"},
        "ID": {"name": "Indonesia", "language": "id", "currency": "IDR"},
        "PH": {"name": "Philippines", "language": "en", "currency": "PHP"},
        "VN": {"name": "Vietnam", "language": "vi", "currency": "VND"},
        "KR": {"name": "South Korea", "language": "ko", "currency": "KRW"}
    }

    return region_info.get(region_code.upper(), {
        "name": "Unknown",
        "language": "en",
        "currency": "USD"
    })