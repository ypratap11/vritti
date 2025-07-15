# src/processors/currency/amount_extractor.py - COMPLETE IMPROVED VERSION
"""
Improved multi-currency amount extraction with better precision
COMPLETE: All methods from original included + improvements
"""

import re
import logging
from typing import List, Dict, Any, Optional

from .currency_config import (
    CURRENCY_CONFIG, CURRENCY_RANGES, get_currency_info,
    get_currency_range, format_amount
)
from .currency_detector import detect_document_currency_and_region
from ..region.formatters import normalize_amount_text

logger = logging.getLogger(__name__)


class AmountExtractor:
    """Improved multi-currency amount extractor with better precision - COMPLETE VERSION"""

    def __init__(self):
        self.currency_patterns = self._build_currency_patterns()

    def _build_currency_patterns(self) -> Dict[str, List[Dict]]:
        """Build comprehensive currency patterns for all supported currencies (ORIGINAL + IMPROVED)"""
        patterns = {}

        for currency_code, currency_info in CURRENCY_CONFIG.items():
            symbol = currency_info["symbol"]
            escaped_symbol = re.escape(symbol)

            # Different number patterns based on currency decimal places
            if currency_info["decimal_places"] == 0:
                # No decimal places (JPY, KRW, IDR, VND)
                number_pattern = r'(\d{1,3}(?:,\d{3})*|\d+)'
            else:
                # With decimal places
                number_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'

            currency_patterns = [
                # HIGHEST priority: Explicit total/due patterns (IMPROVED)
                {
                    "pattern": rf'(?:TOTAL\s+AMOUNT\s+DUE|AMOUNT\s+DUE|TOTAL\s+DUE|BALANCE\s+DUE)[:\s]*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 10,
                    "description": f"{currency_code} Total Amount Due",
                    "context_required": True
                },
                {
                    "pattern": rf'(?:THIS\s+AMOUNT\s+DUE|PAYMENT\s+DUE)[:\s]*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 9,
                    "description": f"{currency_code} Payment Due",
                    "context_required": True
                },

                # High priority: Total patterns
                {
                    "pattern": rf'(?:GRAND\s+TOTAL|FINAL\s+TOTAL|ESTIMATE\s+TOTAL)[:\s]*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 8,
                    "description": f"{currency_code} Grand Total"
                },
                {
                    "pattern": rf'(?:TOTAL\s+AMOUNT|AMOUNT\s+TOTAL)[:\s]*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 8,
                    "description": f"{currency_code} Total Amount"
                },

                # Medium priority: Gross/Net totals (European invoices)
                {
                    "pattern": rf'(?:GROSS\s+AMOUNT|BETRAG\s+BRUTTO|MONTANT\s+TTC|IMPORTE\s+TOTAL)[:\s]*(?:INCL\.?\s*(?:VAT|TAX|MWST|TVA|IVA)?)?\s*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 7,
                    "description": f"{currency_code} Gross Amount"
                },

                # Standard TOTAL patterns
                {
                    "pattern": rf'TOTAL[:\s]*{escaped_symbol}?\s*{number_pattern}',
                    "priority": 5,
                    "description": f"{currency_code} Total"
                },

                # Currency-specific patterns (IMPROVED with validation)
                {
                    "pattern": rf'(?<!\w){escaped_symbol}\s*{number_pattern}(?!\w)',
                    "priority": 4,
                    "description": f"{currency_code} Symbol Amount",
                    "validation_required": True  # NEW: Extra validation for problematic symbols
                },

                # Currency code patterns
                {
                    "pattern": rf'{currency_code}\s*{number_pattern}',
                    "priority": 3,
                    "description": f"{currency_code} Code Amount"
                }
            ]

            patterns[currency_code] = currency_patterns

        return patterns

    def _build_improved_currency_patterns(self) -> Dict[str, List[Dict]]:
        """Build improved currency patterns with better context validation (ALTERNATIVE METHOD)"""
        # This is the improved version - keeping both for compatibility
        return self._build_currency_patterns()

    def extract_amounts(self, text: str) -> Dict[str, Any]:
        """
        Extract amounts from text with improved multi-currency support (ENHANCED ORIGINAL)

        Args:
            text: Document text to extract amounts from

        Returns:
            Dict with extracted amount information
        """
        logger.info("💰 Starting global multi-currency amount extraction...")

        # Detect document currency and region
        detected_info = detect_document_currency_and_region(text)
        logger.info(f"🌍 Detected: Region={detected_info['region']}, Currency={detected_info['currency']}")

        # Extract amounts using detected currency patterns first, then others
        all_amounts = []
        text_upper = text.upper()

        # Primary currency (detected)
        primary_currency = detected_info['currency']
        self._extract_with_currency_patterns(
            text_upper, primary_currency, detected_info, all_amounts, primary=True
        )

        # Secondary currencies (limited to avoid false positives - IMPROVED)
        if not all_amounts or max(a['score'] for a in all_amounts) < 1000:
            # Only check common secondary currencies to reduce false positives
            secondary_currencies = ['USD', 'EUR', 'GBP', 'CAD'] if primary_currency not in ['USD', 'EUR', 'GBP',
                                                                                            'CAD'] else []

            for currency_code in secondary_currencies:
                if currency_code != primary_currency:
                    self._extract_with_currency_patterns(
                        text_upper, currency_code, detected_info, all_amounts, primary=False
                    )
        else:
            # Original behavior: check all currencies
            for currency_code in CURRENCY_CONFIG.keys():
                if currency_code != primary_currency:
                    self._extract_with_currency_patterns(
                        text_upper, currency_code, detected_info, all_amounts, primary=False
                    )

        # Remove duplicates and sort by score
        unique_amounts = self._remove_duplicate_amounts(all_amounts)
        unique_amounts.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"🔍 Found {len(unique_amounts)} unique amounts:")
        for i, amt in enumerate(unique_amounts[:5]):
            logger.info(f"  {i + 1}. {amt['formatted']} (score: {amt['score']}) [{amt['pattern_used']}]")

        # Select final amount
        final_amount = unique_amounts[0]['formatted'] if unique_amounts else "Unknown"
        final_currency = unique_amounts[0]['currency'] if unique_amounts else detected_info['currency']

        return {
            'final_amount': final_amount,
            'currency': final_currency,
            'region': detected_info['region'],
            'all_detected_amounts': [a['formatted'] for a in unique_amounts[:10]],
            'amount_count': len(unique_amounts),
            'best_score': unique_amounts[0]['score'] if unique_amounts else 0,
            'detection_details': detected_info,
            'primary_currency': primary_currency
        }

    def _extract_with_currency_patterns(self, text: str, currency_code: str,
                                        detected_info: Dict, all_amounts: List,
                                        primary: bool = False) -> None:
        """Extract amounts using patterns for specific currency (ENHANCED ORIGINAL)"""

        patterns = self.currency_patterns.get(currency_code, [])
        currency_info = get_currency_info(currency_code)

        for pattern_info in patterns:
            pattern = pattern_info["pattern"]
            priority = pattern_info["priority"]
            description = pattern_info["description"]

            # Boost priority for primary (detected) currency
            if primary:
                priority += 5

            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Handle tuple results from multiple groups
                    if isinstance(match, tuple):
                        amount_str = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                    else:
                        amount_str = match

                    if not amount_str:
                        continue

                    # NEW: Additional validation for patterns that need it
                    if pattern_info.get('validation_required'):
                        if not self._validate_currency_context(amount_str, currency_code, text):
                            continue

                    try:
                        # Normalize and convert amount
                        normalized_amount = normalize_amount_text(amount_str, detected_info['region'])

                        # Clean and convert to float
                        clean_amount = self._clean_amount_string(normalized_amount, currency_code)
                        amount_value = float(clean_amount)

                        if amount_value > 0:
                            # Calculate score
                            score = self._calculate_amount_score(
                                amount_value, text, priority, detected_info, currency_code, primary
                            )

                            # NEW: Skip amounts with very low scores (likely false positives)
                            if score < 50:
                                continue

                            # Format amount
                            formatted_amount = format_amount(amount_value, currency_code)

                            all_amounts.append({
                                'value': amount_value,
                                'formatted': formatted_amount,
                                'currency': currency_code,
                                'score': score,
                                'pattern_used': description,
                                'priority': priority,
                                'region': detected_info['region'],
                                'is_primary_currency': primary,
                                'original_text': amount_str  # NEW: Keep original for debugging
                            })

                            if primary and score > 800:  # Only log high-confidence primary finds
                                logger.info(f"Found: {formatted_amount} (score: {score}, pattern: {description})")

                    except (ValueError, TypeError):
                        continue

            except re.error as e:
                logger.warning(f"Pattern error for {currency_code}: {e}")
                continue

    def _extract_with_improved_patterns(self, text: str, currency_code: str,
                                        detected_info: Dict, all_amounts: List,
                                        primary: bool = False) -> None:
        """Extract amounts using improved patterns with validation (ALTERNATIVE METHOD)"""
        # This is an alias to the main extraction method for compatibility
        return self._extract_with_currency_patterns(text, currency_code, detected_info, all_amounts, primary)

    def _validate_currency_context(self, amount_str: str, currency_code: str, full_text: str) -> bool:
        """NEW: Validate currency symbol context to avoid false positives"""
        currency_info = get_currency_info(currency_code)
        symbol = currency_info["symbol"]

        # Special validation for problematic symbols
        if symbol in ['R', 'Rp', 'RM', 'Rs']:
            # These symbols are often confused with regular text
            # Check if the symbol is actually preceded/followed by currency context

            # Look for the amount in context
            escaped_symbol = re.escape(symbol)
            clean_amount = amount_str.replace(symbol, "").strip()
            pattern = rf'\b{escaped_symbol}\s*{re.escape(clean_amount)}\b'

            # Check if it appears in a currency context
            currency_context_patterns = [
                rf'(?:TOTAL|AMOUNT|DUE|PRICE|COST|CHARGE|FEE)\s*:?\s*{pattern}',
                rf'{pattern}\s*(?:TOTAL|DUE|AMOUNT)',
                rf'(?:^|\n)\s*{pattern}\s*(?:$|\n)'  # Start/end of line
            ]

            for ctx_pattern in currency_context_patterns:
                if re.search(ctx_pattern, full_text, re.IGNORECASE | re.MULTILINE):
                    return True

            # If no currency context found, it's likely a false positive
            return False

        return True  # Other currencies are generally safer

    def _clean_amount_string(self, amount_str: str, currency_code: str) -> str:
        """Clean amount string for conversion to float (ENHANCED ORIGINAL)"""
        # Remove currency symbols and codes
        clean_amount = amount_str

        # Remove currency symbol
        currency_info = get_currency_info(currency_code)
        clean_amount = clean_amount.replace(currency_info["symbol"], "")

        # Remove currency code
        clean_amount = clean_amount.replace(currency_code, "")

        # Remove extra whitespace and common characters
        clean_amount = re.sub(r'[^\d.,]', '', clean_amount)

        # Handle European vs US number formatting (IMPROVED)
        if ',' in clean_amount and '.' in clean_amount:
            # Determine which is decimal separator based on position
            last_comma = clean_amount.rfind(',')
            last_dot = clean_amount.rfind('.')

            if last_comma > last_dot:
                # European format: 1.234.567,89
                clean_amount = clean_amount.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234,567.89
                clean_amount = clean_amount.replace(',', '')
        elif ',' in clean_amount:
            # Single comma - check context more precisely
            comma_parts = clean_amount.split(',')
            if len(comma_parts) == 2 and len(comma_parts[1]) <= 2:
                # Likely decimal separator: 123,45
                clean_amount = clean_amount.replace(',', '.')
            else:
                # Likely thousands separator: 1,234
                clean_amount = clean_amount.replace(',', '')

        return clean_amount

    def _clean_amount_string_improved(self, amount_str: str, currency_code: str) -> str:
        """Improved amount string cleaning (ALTERNATIVE METHOD)"""
        # This is an alias to the main cleaning method for compatibility
        return self._clean_amount_string(amount_str, currency_code)

    def _calculate_amount_score(self, amount_value: float, full_text: str,
                                pattern_priority: int, detected_info: Dict,
                                currency_code: str, is_primary: bool) -> int:
        """Calculate score for extracted amount (ENHANCED ORIGINAL)"""

        score = pattern_priority * 100  # Base score from pattern priority

        # Primary currency bonus
        if is_primary:
            score += 200

        # Currency-specific range validation
        min_amount, max_amount = get_currency_range(currency_code)

        if min_amount <= amount_value <= max_amount:
            score += 300
            # Sweet spot bonus
            if min_amount * 10 <= amount_value <= max_amount * 0.1:
                score += 150
        elif amount_value > max_amount * 10:
            score -= 500  # Way too high
        elif amount_value < min_amount * 0.1:
            score -= 300  # Way too low

        # Decimal places bonus for currencies that use them
        currency_info = get_currency_info(currency_code)
        if currency_info["decimal_places"] > 0 and amount_value != int(amount_value):
            score += 150

        # Context-based scoring (ENHANCED)
        amount_str = f"{amount_value:.2f}"
        high_value_keywords = [
            'TOTAL AMOUNT DUE', 'AMOUNT DUE', 'TOTAL DUE', 'BALANCE DUE',
            'GRAND TOTAL', 'FINAL TOTAL', 'GROSS AMOUNT', 'PAYMENT DUE'
        ]

        for keyword in high_value_keywords:
            if keyword in full_text and amount_str.replace('.', '') in full_text:
                score += 400
                break

        # Regional specific bonuses
        region = detected_info.get('region', 'US')
        if region == "IN" and currency_code == "INR" and 1000 <= amount_value <= 1000000:
            score += 150
        elif region == "MX" and currency_code == "MXN" and 500 <= amount_value <= 50000:
            score += 150
        elif region == "AE" and currency_code == "AED" and 100 <= amount_value <= 10000:
            score += 150

        # NEW: Additional penalties for likely false positives
        if currency_code in ['ZAR', 'MYR', 'IDR'] and not is_primary:
            score -= 100  # Reduce score for commonly confused currencies

        return max(score, 0)  # Never negative

    def _calculate_improved_amount_score(self, amount_value: float, amount_str: str,
                                         full_text: str, pattern_priority: int,
                                         detected_info: Dict, currency_code: str,
                                         is_primary: bool) -> int:
        """Calculate improved amount score with better validation (ALTERNATIVE METHOD)"""
        # Enhanced version of the original scoring
        score = self._calculate_amount_score(amount_value, full_text, pattern_priority, detected_info, currency_code,
                                             is_primary)

        # Additional context-based improvements
        amount_context = self._find_amount_context(amount_str, full_text)
        high_value_contexts = [
            'TOTAL AMOUNT DUE', 'AMOUNT DUE', 'GRAND TOTAL', 'FINAL TOTAL',
            'ESTIMATE TOTAL', 'BALANCE DUE', 'PAYMENT DUE'
        ]

        for context in high_value_contexts:
            if context in amount_context:
                score += 200  # Additional bonus for strong context
                break

        return score

    def _find_amount_context(self, amount_str: str, full_text: str) -> str:
        """NEW: Find the context around an amount for scoring"""
        # Look for the amount in the text and get surrounding context
        escaped_amount = re.escape(amount_str)
        pattern = rf'.{{0,50}}{escaped_amount}.{{0,50}}'

        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(0).upper() if match else ""

    def _remove_duplicate_amounts(self, amounts: List[Dict]) -> List[Dict]:
        """Remove duplicate amounts keeping highest scoring version (ORIGINAL)"""
        unique_amounts = []

        for amount in amounts:
            is_duplicate = False
            for existing in unique_amounts:
                # Consider amounts within 2% as duplicates for same currency
                if (amount['currency'] == existing['currency'] and
                        abs(amount['value'] - existing['value']) <= max(amount['value'], existing['value']) * 0.02):
                    if existing['score'] < amount['score']:
                        existing.update(amount)  # Keep higher scoring version
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_amounts.append(amount)

        return unique_amounts

    def _remove_duplicate_amounts_improved(self, amounts: List[Dict]) -> List[Dict]:
        """Improved duplicate removal with better similarity detection (ALTERNATIVE METHOD)"""
        unique_amounts = []

        for amount in amounts:
            is_duplicate = False

            for existing in unique_amounts:
                # Same currency and very similar value (tighter threshold)
                if (amount['currency'] == existing['currency'] and
                        abs(amount['value'] - existing['value']) <= max(amount['value'], existing['value']) * 0.01):

                    # Keep the higher scoring version
                    if existing['score'] < amount['score']:
                        existing.update(amount)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_amounts.append(amount)

        return unique_amounts


# Global extractor instance
amount_extractor = AmountExtractor()