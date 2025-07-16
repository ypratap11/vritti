# src/processors/vendor/business_indicators.py
"""
Business entity indicators by region/country
"""

from typing import List, Dict

# Global business entity indicators by region
BUSINESS_INDICATORS = {
    # North America
    "US": ["LLC", "INC", "CORP", "COMPANY", "CO.", "LTD", "CORPORATION", "ENTERPRISES", "GROUP"],
    "CA": ["LTD", "CORP", "INC", "COMPANY", "LTÉE", "CORPORÉE", "ENTERPRISES"],
    "MX": ["SA DE CV", "SC", "AC", "SOCIEDAD", "EMPRESA", "COMPAÑÍA"],

    # Europe - Germanic
    "DE": ["GMBH", "AG", "KG", "OHG", "GMBH & CO", "UG", "GESELLSCHAFT"],
    "AT": ["GMBH", "AG", "KG", "OHG", "GESELLSCHAFT"],
    "CH": ["AG", "GMBH", "SARL", "SA", "GESELLSCHAFT"],

    # Europe - Romance
    "FR": ["SARL", "SAS", "SA", "EURL", "SNC", "SOCIETE", "SOCIÉTÉ"],
    "IT": ["SRL", "SPA", "SNCA", "SOCIETA", "SOCIETÀ"],
    "ES": ["SL", "SA", "SLU", "SOCIEDAD", "EMPRESA"],
    "PT": ["LDA", "SA", "SOCIEDADE", "EMPRESA"],

    # Europe - Nordic
    "SE": ["AB", "AKTIEBOLAG", "HB", "KB", "FÖRETAG"],
    "NO": ["AS", "ASA", "BA", "DA", "SELSKAP"],
    "DK": ["A/S", "APS", "I/S", "K/S", "SELSKAB"],
    "FI": ["OY", "OYJ", "KY", "YHTIÖ"],

    # Europe - Other
    "GB": ["LTD", "LIMITED", "PLC", "COMPANY", "CORP"],
    "NL": ["BV", "NV", "VOF", "CV", "MAATSCHAPPIJ"],
    "BE": ["BVBA", "SA", "NV", "SPRL", "MAATSCHAPPIJ"],
    "IE": ["LTD", "LIMITED", "PLC", "TEORANTA"],

    # Asia
    "IN": ["PVT LTD", "LIMITED", "LLP", "PRIVATE LIMITED", "COMPANY"],
    "JP": ["株式会社", "KK", "CO LTD", "CORPORATION", "KABUSHIKI KAISHA"],
    "CN": ["有限公司", "CO LTD", "LIMITED", "CORPORATION", "COMPANY"],
    "KR": ["주식회사", "CO LTD", "CORPORATION", "COMPANY"],
    "SG": ["PTE LTD", "LIMITED", "COMPANY", "CORP"],
    "HK": ["LIMITED", "LTD", "COMPANY", "CORP"],
    "TH": ["CO LTD", "LIMITED", "COMPANY", "CORPORATION"],
    "MY": ["SDN BHD", "BHD", "COMPANY", "CORPORATION"],
    "ID": ["PT", "CV", "FIRMA", "PERUSAHAAN"],
    "PH": ["CORP", "INC", "COMPANY", "CORPORATION"],
    "VN": ["CO LTD", "JSC", "COMPANY", "CORPORATION"],
    "TW": ["CO LTD", "LIMITED", "COMPANY", "CORPORATION"],

    # Middle East
    "AE": ["LLC", "FZCO", "FZE", "COMPANY", "ESTABLISHMENT"],
    "SA": ["LLC", "CO", "COMPANY", "ESTABLISHMENT", "CORPORATION"],
    "QA": ["LLC", "WLL", "COMPANY", "ESTABLISHMENT"],
    "KW": ["WLL", "KSC", "COMPANY", "ESTABLISHMENT"],
    "BH": ["WLL", "BSC", "COMPANY", "ESTABLISHMENT"],
    "OM": ["LLC", "SAOG", "COMPANY", "ESTABLISHMENT"],
    "IL": ["LTD", "LIMITED", "COMPANY", "CORP"],
    "TR": ["AS", "LTD STI", "COMPANY", "ŞIRKET"],

    # Africa
    "ZA": ["PTY LTD", "LIMITED", "COMPANY", "CC", "CORPORATION"],
    "EG": ["SAE", "LLC", "COMPANY", "CORPORATION"],
    "NG": ["LTD", "LIMITED", "COMPANY", "CORP"],
    "KE": ["LTD", "LIMITED", "COMPANY", "CORP"],

    # Oceania
    "AU": ["PTY LTD", "LIMITED", "COMPANY", "CORP"],
    "NZ": ["LIMITED", "LTD", "COMPANY", "CORP"],

    # South America
    "BR": ["LTDA", "SA", "EIRELI", "SOCIEDADE", "EMPRESA"],
    "AR": ["SA", "SRL", "SOCIEDAD", "EMPRESA"],
    "CL": ["SA", "LTDA", "SOCIEDAD", "EMPRESA"],
    "CO": ["SA", "LTDA", "SOCIEDAD", "EMPRESA"],
    "PE": ["SA", "SAC", "SOCIEDAD", "EMPRESA"],

    # Eastern Europe
    "RU": ["ООО", "ОАО", "ЗАО", "ИП", "ОБЩЕСТВО"],
    "PL": ["SP Z OO", "SA", "SPÓŁKA", "FIRMA"],
    "CZ": ["SRO", "AS", "SPOLEČNOST", "FIRMA"],
    "HU": ["KFT", "RT", "BT", "TÁRSASÁG"],
    "UA": ["ТОВ", "ПАТ", "ТОВАРИСТВО", "КОМПАНІЯ"],
}

# Professional service indicators
PROFESSIONAL_SERVICES = [
    "CONSULTING", "CONSULTANCY", "ADVISORS", "ADVISORY", "PARTNERS",
    "SERVICES", "SOLUTIONS", "SYSTEMS", "TECHNOLOGIES", "TECH",
    "LAW FIRM", "ATTORNEYS", "LAWYERS", "LEGAL",
    "ACCOUNTING", "AUDITING", "TAX", "FINANCIAL",
    "ENGINEERING", "ARCHITECTS", "DESIGN",
    "MEDICAL", "HEALTHCARE", "CLINIC", "HOSPITAL"
]

# Industry-specific indicators
INDUSTRY_INDICATORS = {
    "TECHNOLOGY": ["SOFTWARE", "TECH", "DIGITAL", "IT", "SYSTEMS", "DATA"],
    "MANUFACTURING": ["MANUFACTURING", "FACTORY", "INDUSTRIAL", "PRODUCTION"],
    "RETAIL": ["RETAIL", "STORE", "SHOP", "MARKET", "TRADING"],
    "CONSTRUCTION": ["CONSTRUCTION", "BUILDING", "CONTRACTORS", "BUILDERS"],
    "AUTOMOTIVE": ["AUTOMOTIVE", "AUTO", "MOTORS", "VEHICLES", "GARAGE"],
    "REAL_ESTATE": ["REAL ESTATE", "PROPERTY", "REALTY", "PROPERTIES"],
    "FINANCE": ["BANK", "BANKING", "FINANCIAL", "INVESTMENT", "CAPITAL"],
    "HEALTHCARE": ["MEDICAL", "HEALTHCARE", "HOSPITAL", "CLINIC", "HEALTH"],
    "EDUCATION": ["SCHOOL", "UNIVERSITY", "COLLEGE", "EDUCATION", "ACADEMY"],
    "GOVERNMENT": ["GOVERNMENT", "COUNTY", "CITY", "STATE", "MUNICIPAL", "PUBLIC"]
}


def get_business_indicators_by_region(region_code: str) -> List[str]:
    """
    Get business entity indicators for a specific region

    Args:
        region_code: Two-letter region code (US, DE, FR, etc.)

    Returns:
        List of business indicators for that region
    """
    region_upper = region_code.upper()
    indicators = BUSINESS_INDICATORS.get(region_upper, BUSINESS_INDICATORS.get("US", []))

    # Always include common international indicators
    common_indicators = ["COMPANY", "CORP", "LIMITED", "LTD", "INC"]

    # Combine and remove duplicates
    all_indicators = list(set(indicators + common_indicators))

    return all_indicators


def get_all_business_indicators() -> List[str]:
    """
    Get all business indicators from all regions

    Returns:
        List of all unique business indicators
    """
    all_indicators = []

    for indicators in BUSINESS_INDICATORS.values():
        all_indicators.extend(indicators)

    # Add professional services and remove duplicates
    all_indicators.extend(PROFESSIONAL_SERVICES)

    return list(set(all_indicators))


def get_industry_indicators() -> Dict[str, List[str]]:
    """
    Get industry-specific indicators

    Returns:
        Dict mapping industry categories to their indicators
    """
    return INDUSTRY_INDICATORS.copy()


def is_business_entity(text: str, region_code: str = "US") -> bool:
    """
    Check if text contains business entity indicators

    Args:
        text: Text to check
        region_code: Region code for context

    Returns:
        True if text likely contains a business entity
    """
    if not text:
        return False

    text_upper = text.upper()
    indicators = get_business_indicators_by_region(region_code)

    return any(indicator in text_upper for indicator in indicators)


def get_business_score(text: str, region_code: str = "US") -> int:
    """
    Calculate business entity score for text

    Args:
        text: Text to score
        region_code: Region code for context

    Returns:
        Score indicating likelihood of being a business entity (0-100)
    """
    if not text:
        return 0

    score = 0
    text_upper = text.upper()

    # Regional business indicators
    regional_indicators = get_business_indicators_by_region(region_code)
    for indicator in regional_indicators:
        if indicator in text_upper:
            score += 40
            break

    # Professional services
    for indicator in PROFESSIONAL_SERVICES:
        if indicator in text_upper:
            score += 20
            break

    # Industry indicators
    for industry, indicators in INDUSTRY_INDICATORS.items():
        for indicator in indicators:
            if indicator in text_upper:
                score += 15
                break

    # General business words
    business_words = ["BUSINESS", "FIRM", "ORGANIZATION", "ENTERPRISE", "GROUP"]
    for word in business_words:
        if word in text_upper:
            score += 10
            break

    return min(score, 100)  # Cap at 100