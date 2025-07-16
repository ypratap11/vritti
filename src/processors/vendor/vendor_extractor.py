# src/processors/vendor/vendor_extractor.py - COMPLETE IMPROVED VERSION
"""
Improved vendor extraction with better precision and context awareness
COMPLETE: All methods from original included
"""

import re
import logging
from typing import List, Dict, Any, Optional

from .business_indicators import get_business_indicators_by_region
from ..currency.currency_detector import detect_document_currency_and_region

logger = logging.getLogger(__name__)


class VendorExtractor:
    """Improved vendor extractor with better precision - COMPLETE VERSION"""

    def __init__(self):
        self.vendor_patterns = self._build_vendor_patterns()
        # Words to avoid (footer/metadata terms)
        self.avoid_words = {
            'ESTIMATE', 'INVOICE', 'BILL', 'RECEIPT', 'STATEMENT', 'ORDER',
            'PAGE', 'COPY', 'TOTAL', 'AMOUNT', 'DUE', 'DATE', 'NUMBER',
            'CUSTOMER', 'CLIENT', 'SERVICE', 'PAYMENT', 'BALANCE',
            'DESCRIPTION', 'QUANTITY', 'PRICE', 'TAX', 'SUBTOTAL'
        }

    def _build_vendor_patterns(self) -> List[Dict[str, Any]]:
        """Build improved vendor extraction patterns"""
        patterns = [
            # High priority: Explicit vendor patterns
            {
                "pattern": r'(?:FROM|INVOICE\s+FROM|BILL\s+FROM|SENDER):\s*(.+?)(?:\n|$)',
                "priority": 10,
                "description": "Explicit FROM pattern"
            },
            {
                "pattern": r'(?:FACTURA\s+DE|RECHNUNG\s+VON|FACTURE\s+DE):\s*(.+?)(?:\n|$)',
                "priority": 10,
                "description": "Multi-language FROM pattern"
            },
            # Explicit vendor patterns
            {
                "pattern": r'(?:FROM|VENDOR|SUPPLIER):\s*(.+?)(?:\n|$)',
                "priority": 10,
                "description": "Explicit vendor pattern"
            },
            # Medium priority: Header area patterns
            {
                "pattern": r'^(.+?)(?:\n.*(?:INVOICE|FACTURA|RECHNUNG|FACTURE))',
                "priority": 8,
                "description": "Header before invoice keyword"
            },
            # Business name with indicators (stricter)
            {
                "pattern": r'^([A-Z][A-Za-z\s&]{3,40}(?:LLC|INC|CORP|LTD|COMPANY|CO\.)\b)',
                "priority": 9,
                "description": "Business entity pattern"
            },
        ]
        return patterns

    def extract_vendor(self, text: str) -> Dict[str, Any]:
        """Extract vendor with improved precision"""
        logger.info("🏢 Starting improved vendor extraction...")

        # Detect region
        detected_info = detect_document_currency_and_region(text)
        region = detected_info.get('region', 'US')
        logger.info(f"🌍 Detected region: {region}")

        vendor_candidates = []

        # Strategy 1: Pattern-based extraction
        pattern_candidates = self._extract_with_patterns(text)
        vendor_candidates.extend(pattern_candidates)

        # Strategy 2: Enhanced header analysis (most important) - PRIORITIZE IMPROVED VERSION
        header_candidates_improved = self._extract_from_header_improved(text, region)
        vendor_candidates.extend(header_candidates_improved)

        # Strategy 2b: Original header analysis (fallback)
        header_candidates = self._extract_from_header(text, region)
        vendor_candidates.extend(header_candidates)

        # Strategy 3: Business indicator analysis (improved) - PRIORITIZE IMPROVED VERSION
        business_candidates_improved = self._extract_with_business_indicators_improved(text, region)
        vendor_candidates.extend(business_candidates_improved)

        # Strategy 3b: Original business indicator analysis (fallback)
        business_candidates = self._extract_with_business_indicators(text, region)
        vendor_candidates.extend(business_candidates)

        # Strategy 4: Structure-based extraction
        structure_candidates = self._extract_from_structure(text, region)
        vendor_candidates.extend(structure_candidates)

        # Remove duplicates and sort
        unique_candidates = self._remove_duplicate_vendors(vendor_candidates)
        unique_candidates.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"🔍 Found {len(unique_candidates)} vendor candidates:")
        for i, candidate in enumerate(unique_candidates[:3]):
            logger.info(f"  {i + 1}. {candidate['name']} (score: {candidate['score']}) [{candidate['source']}]")

        best_vendor = unique_candidates[0] if unique_candidates else None

        return {
            'name': best_vendor['name'] if best_vendor else "Unknown",
            'candidates': [v['name'] for v in unique_candidates[:3]],
            'best_score': best_vendor['score'] if best_vendor else 0,
            'region': region,
            'method': 'improved_vendor_extraction',
            'source': best_vendor['source'] if best_vendor else 'none'
        }

    def _extract_with_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract vendors using regex patterns"""
        candidates = []

        for pattern_info in self.vendor_patterns:
            pattern = pattern_info["pattern"]
            priority = pattern_info["priority"]
            description = pattern_info["description"]

            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    cleaned_vendor = self._clean_vendor_name(match)
                    if cleaned_vendor and self._is_valid_vendor_name_improved(cleaned_vendor):
                        score = priority * 10 + self._calculate_vendor_quality_score(cleaned_vendor)

                        candidates.append({
                            'name': cleaned_vendor,
                            'score': score,
                            'source': f'pattern_{description}',
                            'method': 'regex_pattern'
                        })

            except re.error as e:
                logger.warning(f"Pattern error: {e}")
                continue

        return candidates

    def _extract_from_header(self, text: str, region: str) -> List[Dict[str, Any]]:
        """Extract vendor from document header area (ORIGINAL METHOD)"""
        candidates = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Analyze first 10 lines
        for i, line in enumerate(lines[:10]):
            cleaned_line = self._clean_vendor_name(line)

            if cleaned_line and self._is_valid_vendor_name(cleaned_line):
                # Score based on position and characteristics
                position_score = max(10 - i, 1) * 10  # Earlier lines get higher scores
                quality_score = self._calculate_vendor_quality_score(cleaned_line)
                business_score = self._calculate_business_indicator_score(cleaned_line, region)

                total_score = position_score + quality_score + business_score

                candidates.append({
                    'name': cleaned_line,
                    'score': total_score,
                    'source': f'header_line_{i}',
                    'method': 'header_analysis'
                })

        return candidates

    def _extract_from_header_improved(self, text: str, region: str) -> List[Dict[str, Any]]:
        """Improved header extraction with better context awareness"""
        candidates = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Focus on first 8 lines for vendor detection
        for i, line in enumerate(lines[:8]):
            if not line:
                continue

            # Skip obvious non-vendor lines
            if self._should_skip_line(line):
                continue

            # Look for company name patterns
            company_candidates = self._extract_company_names_from_line(line, i, region)
            candidates.extend(company_candidates)

        return candidates

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (non-vendor content)"""
        line_upper = line.upper()

        # Skip lines with avoid words
        for word in self.avoid_words:
            if word in line_upper:
                return True

        # Skip lines that are mostly numbers or symbols
        if re.match(r'^[\d\s\-\(\)#:$,.\+]+$', line):
            return True

        # Skip very short lines (less than 3 chars)
        if len(line.strip()) < 3:
            return True

        # Skip lines with excessive punctuation
        punct_count = sum(1 for c in line if c in '!@#$%^&*()_+-=[]{}|;:,.<>?')
        if punct_count > len(line) * 0.3:
            return True

        return False

    def _extract_company_names_from_line(self, line: str, line_index: int, region: str) -> List[Dict[str, Any]]:
        """Extract potential company names from a single line"""
        candidates = []

        # Pattern 1: Full company names with business indicators
        business_indicators = get_business_indicators_by_region(region)
        for indicator in business_indicators:
            if indicator.upper() in line.upper():
                # Extract the company name with the indicator
                pattern = rf'([A-Z][A-Za-z\s&\.]{2, 40}\s+{re.escape(indicator)})\b'
                matches = re.findall(pattern, line, re.IGNORECASE)

                for match in matches:
                    cleaned_name = self._clean_vendor_name(match)
                    if self._is_valid_vendor_name_improved(cleaned_name):
                        score = 200 + (8 - line_index) * 20  # Higher score for earlier lines
                        candidates.append({
                            'name': cleaned_name,
                            'score': score,
                            'source': f'company_with_indicator_{indicator}',
                            'method': 'header_business_indicator'
                        })

        # Pattern 2: Multi-word company names (likely in header) - ENHANCED
        if line_index < 5:  # Focus on top lines
            words = line.split()
            if 2 <= len(words) <= 6:  # Reasonable company name length
                # Check if it looks like a company name
                if self._looks_like_company_name(line):
                    cleaned_name = self._clean_vendor_name(line)
                    if self._is_valid_vendor_name_improved(cleaned_name):
                        # BOOST score for lines containing common business patterns
                        score = 150 + (5 - line_index) * 30

                        # Special boost for automotive/dealer patterns
                        if any(word in line.upper() for word in ['NISSAN', 'TOYOTA', 'FORD', 'HONDA', 'BMW', 'AUDI']):
                            score += 100
                        if any(word in line.upper() for word in
                               ['DUBLIN', 'DOWNTOWN', 'CITY', 'METRO', 'NORTH', 'SOUTH', 'EAST', 'WEST']):
                            score += 50

                        candidates.append({
                            'name': cleaned_name,
                            'score': score,
                            'source': f'header_company_line_{line_index}',
                            'method': 'header_multiword'
                        })

        return candidates

    def _looks_like_company_name(self, line: str) -> bool:
        """Check if line looks like a company name - ENHANCED"""
        # Should have mostly letters and spaces
        letter_ratio = sum(1 for c in line if c.isalpha()) / len(line) if len(line) > 0 else 0
        if letter_ratio < 0.6:
            return False

        # Should start with capital letter
        if not line[0].isupper():
            return False

        # Should not be all uppercase (unless short) - RELAXED for business names
        if len(line) > 15 and line.isupper() and not any(word in line.upper() for word in
                                                         ['NISSAN', 'TOYOTA', 'FORD', 'HONDA', 'BMW', 'AUDI', 'CORP',
                                                          'LLC', 'INC']):
            return False

        # Should not contain common non-company patterns
        bad_patterns = [r'\d{3,}', r'@', r'\.com', r'http', r'www', r'ESTIMATE', r'INVOICE', r'TOTAL']
        for pattern in bad_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return False

        # POSITIVE indicators for company names
        positive_indicators = [
            'NISSAN', 'TOYOTA', 'FORD', 'HONDA', 'BMW', 'AUDI',  # Auto brands
            'DUBLIN', 'DOWNTOWN', 'CITY', 'METRO', 'NORTH', 'SOUTH',  # Location indicators
            'CORP', 'LLC', 'INC', 'COMPANY', 'LTD',  # Business indicators
            'AUTOMOTIVE', 'MOTORS', 'CARS', 'AUTO'  # Auto-related
        ]

        line_upper = line.upper()
        if any(indicator in line_upper for indicator in positive_indicators):
            return True

        return True

    def _extract_with_business_indicators(self, text: str, region: str) -> List[Dict[str, Any]]:
        """Extract vendors using business entity indicators (ORIGINAL METHOD)"""
        candidates = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        business_indicators = get_business_indicators_by_region(region)

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Check if line contains business indicators
            for indicator in business_indicators:
                if indicator.upper() in line_upper:
                    cleaned_line = self._clean_vendor_name(line)

                    if cleaned_line and self._is_valid_vendor_name(cleaned_line):
                        # High score for business indicators
                        base_score = 150
                        quality_score = self._calculate_vendor_quality_score(cleaned_line)
                        position_bonus = max(20 - i, 0)  # Bonus for earlier positions

                        total_score = base_score + quality_score + position_bonus

                        candidates.append({
                            'name': cleaned_line,
                            'score': total_score,
                            'source': f'business_indicator_{indicator}',
                            'method': 'business_indicator'
                        })
                        break

        return candidates

    def _extract_with_business_indicators_improved(self, text: str, region: str) -> List[Dict[str, Any]]:
        """Improved business indicator extraction"""
        candidates = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        business_indicators = get_business_indicators_by_region(region)

        for i, line in enumerate(lines[:15]):  # Check more lines but weight by position
            if self._should_skip_line(line):
                continue

            line_upper = line.upper()

            for indicator in business_indicators:
                if indicator.upper() in line_upper:
                    # Extract the business name more precisely
                    # Look for the complete business name including the indicator
                    pattern = rf'([A-Z][A-Za-z\s&\.-]{{2,50}}\s+{re.escape(indicator)})\b'
                    matches = re.findall(pattern, line, re.IGNORECASE)

                    if not matches:
                        # Fallback: take the whole line if it's reasonable
                        if self._looks_like_company_name(line):
                            matches = [line]

                    for match in matches:
                        cleaned_name = self._clean_vendor_name(match)
                        if self._is_valid_vendor_name_improved(cleaned_name):
                            # Score based on indicator strength and position
                            base_score = 180
                            position_bonus = max(30 - i * 2, 0)
                            indicator_bonus = 50 if indicator in ['LLC', 'INC', 'CORP', 'COMPANY'] else 30

                            total_score = base_score + position_bonus + indicator_bonus

                            candidates.append({
                                'name': cleaned_name,
                                'score': total_score,
                                'source': f'business_indicator_{indicator}_line_{i}',
                                'method': 'business_indicator_improved'
                            })
                            break  # Only one match per line

        return candidates

    def _extract_from_structure(self, text: str, region: str) -> List[Dict[str, Any]]:
        """Extract vendor using document structure analysis"""
        candidates = []

        # Look for vendor in structured areas
        structured_patterns = [
            # Address block patterns
            r'([^,\n]+(?:LLC|INC|CORP|GMBH|SARL|LTD)[^,\n]*)',

            # Company name patterns
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:LLC|INC|CORP|GMBH|SARL|LTD)))',

            # Multi-word company patterns
            r'([A-Z][A-Z\s]{10,50}(?:LLC|INC|CORP|GMBH|SARL|LTD))',
        ]

        for pattern in structured_patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    cleaned_vendor = self._clean_vendor_name(match)

                    if cleaned_vendor and self._is_valid_vendor_name(cleaned_vendor):
                        score = 100 + self._calculate_vendor_quality_score(cleaned_vendor)

                        candidates.append({
                            'name': cleaned_vendor,
                            'score': score,
                            'source': 'structure_analysis',
                            'method': 'structured_pattern'
                        })

            except re.error:
                continue

        return candidates

    def _is_valid_vendor_name(self, vendor_name: str) -> bool:
        """Validate if text could be a vendor name (ORIGINAL METHOD)"""
        if not vendor_name or len(vendor_name) < 3:
            return False

        # Skip very long lines (likely descriptions)
        if len(vendor_name) > 80:
            return False

        # Skip lines that are mostly numbers
        if sum(c.isdigit() for c in vendor_name) > len(vendor_name) * 0.7:
            return False

        # Skip common non-vendor patterns
        invalid_patterns = [
            r'^\d+$',  # Only numbers
            r'^[^a-zA-Z]*$',  # No letters
            r'TOTAL|AMOUNT|DUE|DATE|NUMBER|INVOICE',  # Common invoice fields
        ]

        vendor_upper = vendor_name.upper()
        for pattern in invalid_patterns:
            if re.search(pattern, vendor_upper):
                return False

        return True

    def _is_valid_vendor_name_improved(self, vendor_name: str) -> bool:
        """Improved vendor name validation"""
        if not vendor_name or len(vendor_name) < 3:
            return False

        # More restrictive length check
        if len(vendor_name) > 60:
            return False

        # Check avoid words
        vendor_upper = vendor_name.upper()
        for avoid_word in self.avoid_words:
            if avoid_word in vendor_upper:
                return False

        # Should have reasonable letter-to-number ratio
        letter_count = sum(1 for c in vendor_name if c.isalpha())
        total_count = len(vendor_name)
        if letter_count < total_count * 0.5:  # At least 50% letters
            return False

        # Should not be mostly punctuation
        punct_count = sum(1 for c in vendor_name if not c.isalnum() and c != ' ')
        if punct_count > total_count * 0.3:
            return False

        return True

    def _clean_vendor_name(self, vendor_text: str) -> str:
        """Clean and normalize vendor name"""
        if not vendor_text:
            return ""

        # Remove common junk patterns
        junk_patterns = [
            r'\s*IF NOT RECEIVED.*$',
            r'\s*BILL TO.*$',
            r'\s*INVOICE TO.*$',
            r'\s*SHIP TO.*$',
            r'\s*PLEASE MAKE.*$',
            r'\s*ACCOUNT NUMBER.*$',
            r'\s*DUE DATE.*$',
            r'\s*AMOUNT DUE.*$',
            r'\s*TOTAL.*$',
            r'\s*INVOICE NUMBER.*$',
            r'^\s*PO BOX.*$',
            r'^\s*P\.O\..*$',
            r'.*@.*',  # Email addresses
            r'.*\.com.*',  # Websites
            r'.*\d{3}[-.\s]\d{3}[-.\s]\d{4}.*',  # Phone numbers
        ]

        cleaned = vendor_text.strip()

        for pattern in junk_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Take only the first line if multiline
        cleaned = cleaned.split('\n')[0].strip()

        # Remove leading/trailing punctuation except business-related ones
        cleaned = re.sub(r'^[^\w\s]+|[^\w\s.&-]+$', '', cleaned)

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Capitalize properly if needed
        if cleaned.isupper() and len(cleaned) > 10:
            cleaned = cleaned.title()

        return cleaned.strip()

    def _calculate_vendor_quality_score(self, vendor_name: str) -> int:
        """Calculate quality score for vendor name"""
        score = 0

        # Length scoring (optimal length)
        if 10 <= len(vendor_name) <= 40:
            score += 30
        elif 5 <= len(vendor_name) <= 60:
            score += 20
        else:
            score -= 10

        # Character composition
        if any(c.isupper() for c in vendor_name):
            score += 10
        if any(c.islower() for c in vendor_name):
            score += 10

        # Penalty for too many numbers
        if sum(c.isdigit() for c in vendor_name) > 3:
            score -= 20

        # Penalty for special characters (except business-related ones)
        special_chars = sum(1 for c in vendor_name if not c.isalnum() and c not in ' .,&-')
        score -= special_chars * 5

        return score

    def _calculate_business_indicator_score(self, vendor_name: str, region: str) -> int:
        """Calculate score based on business indicators"""
        score = 0
        vendor_upper = vendor_name.upper()

        business_indicators = get_business_indicators_by_region(region)

        for indicator in business_indicators:
            if indicator.upper() in vendor_upper:
                score += 50
                break

        # Additional business-related words
        business_words = [
            'COMPANY', 'CORP', 'CORPORATION', 'GROUP', 'SERVICES', 'SOLUTIONS',
            'ENTERPRISES', 'SYSTEMS', 'TECHNOLOGIES', 'CONSULTING', 'MANAGEMENT'
        ]

        for word in business_words:
            if word in vendor_upper:
                score += 20
                break

        return score

    def _remove_duplicate_vendors(self, vendor_candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate vendors keeping highest scoring version"""
        unique_vendors = []

        for vendor in vendor_candidates:
            is_duplicate = False
            vendor_name = vendor['name'].upper()

            for existing in unique_vendors:
                existing_name = existing['name'].upper()

                # Check for exact match, substring, or high similarity
                if (vendor_name == existing_name or
                        vendor_name in existing_name or
                        existing_name in vendor_name or
                        self._calculate_similarity(vendor_name, existing_name) > 0.8):

                    # Keep the higher scoring version
                    if existing['score'] < vendor['score']:
                        existing.update(vendor)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_vendors.append(vendor)

        return unique_vendors

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (simple implementation)"""
        if not str1 or not str2:
            return 0.0

        # Simple character-based similarity
        common_chars = sum(1 for c in str1 if c in str2)
        max_len = max(len(str1), len(str2))

        return common_chars / max_len if max_len > 0 else 0.0


# Global extractor instance
vendor_extractor = VendorExtractor()