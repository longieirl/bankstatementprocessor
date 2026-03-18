"""IBAN (International Bank Account Number) extraction from PDF documents.

This module provides functionality to extract IBAN numbers from bank statement PDFs.
IBANs follow ISO 13616 standard with country-specific formats.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class IBANExtractor:
    """
    Extracts IBAN (International Bank Account Number) from PDF text.

    Supports common IBAN formats from European countries including:
    - Ireland (IE): 22 characters
    - UK (GB): 22 characters
    - Germany (DE): 22 characters
    - France (FR): 27 characters
    - And many more...
    """

    # IBAN format: 2-letter country code + 2 check digits + up to 30 alphanumeric characters
    # Common formats by country (code: length)
    IBAN_LENGTHS = {
        "AD": 24,  # Andorra
        "AE": 23,  # UAE
        "AL": 28,  # Albania
        "AT": 20,  # Austria
        "AZ": 28,  # Azerbaijan
        "BA": 20,  # Bosnia
        "BE": 16,  # Belgium
        "BG": 22,  # Bulgaria
        "BH": 22,  # Bahrain
        "BR": 29,  # Brazil
        "BY": 28,  # Belarus
        "CH": 21,  # Switzerland
        "CR": 22,  # Costa Rica
        "CY": 28,  # Cyprus
        "CZ": 24,  # Czech Republic
        "DE": 22,  # Germany
        "DK": 18,  # Denmark
        "DO": 28,  # Dominican Republic
        "EE": 20,  # Estonia
        "EG": 29,  # Egypt
        "ES": 24,  # Spain
        "FI": 18,  # Finland
        "FO": 18,  # Faroe Islands
        "FR": 27,  # France
        "GB": 22,  # United Kingdom
        "GE": 22,  # Georgia
        "GI": 23,  # Gibraltar
        "GL": 18,  # Greenland
        "GR": 27,  # Greece
        "GT": 28,  # Guatemala
        "HR": 21,  # Croatia
        "HU": 28,  # Hungary
        "IE": 22,  # Ireland
        "IL": 23,  # Israel
        "IQ": 23,  # Iraq
        "IS": 26,  # Iceland
        "IT": 27,  # Italy
        "JO": 30,  # Jordan
        "KW": 30,  # Kuwait
        "KZ": 20,  # Kazakhstan
        "LB": 28,  # Lebanon
        "LC": 32,  # Saint Lucia
        "LI": 21,  # Liechtenstein
        "LT": 20,  # Lithuania
        "LU": 20,  # Luxembourg
        "LV": 21,  # Latvia
        "MC": 27,  # Monaco
        "MD": 24,  # Moldova
        "ME": 22,  # Montenegro
        "MK": 19,  # North Macedonia
        "MR": 27,  # Mauritania
        "MT": 31,  # Malta
        "MU": 30,  # Mauritius
        "NL": 18,  # Netherlands
        "NO": 15,  # Norway
        "PK": 24,  # Pakistan
        "PL": 28,  # Poland
        "PS": 29,  # Palestine
        "PT": 25,  # Portugal
        "QA": 29,  # Qatar
        "RO": 24,  # Romania
        "RS": 22,  # Serbia
        "SA": 24,  # Saudi Arabia
        "SE": 24,  # Sweden
        "SI": 19,  # Slovenia
        "SK": 24,  # Slovakia
        "SM": 27,  # San Marino
        "TN": 24,  # Tunisia
        "TR": 26,  # Turkey
        "UA": 29,  # Ukraine
        "VA": 22,  # Vatican
        "VG": 24,  # British Virgin Islands
        "XK": 20,  # Kosovo
    }

    def __init__(self) -> None:
        """Initialize IBAN extractor with compiled regex patterns."""
        # Pattern 1: IBAN with optional spaces (most common in PDFs)
        # Example: IE29 AIBK 9311 5212 3456 78 or IE29AIBK93115212345678
        self.pattern_with_spaces = re.compile(
            r"\b([A-Z]{2}\d{2}[A-Z0-9\s]{10,30})\b", re.IGNORECASE
        )

        # Pattern 2: IBAN without spaces (continuous)
        # Example: IE29AIBK93115212345678
        self.pattern_no_spaces = re.compile(
            r"\b([A-Z]{2}\d{2}[A-Z0-9]{10,30})\b", re.IGNORECASE
        )

        # Pattern 3: IBAN with various separators (-, ., space)
        # Example: IE29-AIBK-9311-5212-3456-78
        self.pattern_with_separators = re.compile(
            r"\b([A-Z]{2}\d{2}[\s\-\.]*(?:[A-Z0-9][\s\-\.]*){10,30})\b", re.IGNORECASE
        )

    def extract_iban(self, text: str) -> str | None:
        """
        Extract IBAN from text.

        Tries multiple patterns and validates the result.
        Returns the first valid IBAN found.

        Args:
            text: Text to search for IBAN

        Returns:
            IBAN string if found and valid, None otherwise
        """
        if not text:
            return None

        # Try different patterns in order of specificity
        patterns = [
            self.pattern_no_spaces,  # Most specific
            self.pattern_with_spaces,  # Common in PDFs
            self.pattern_with_separators,  # Less common but possible
        ]

        for pattern in patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Clean the match (remove spaces, hyphens, dots)
                cleaned_iban = re.sub(r"[\s\-\.]", "", match).upper()

                # Validate the IBAN
                if self.is_valid_iban(cleaned_iban):
                    logger.info(f"Found valid IBAN: {self._mask_iban(cleaned_iban)}")
                    return cleaned_iban

        return None

    def is_valid_iban(self, iban: str) -> bool:
        """
        Validate IBAN format and structure.

        Checks:
        1. Correct length for country code
        2. Country code exists in known list
        3. Check digits are numeric
        4. Basic mod-97 checksum validation (optional, can be slow)

        Args:
            iban: IBAN string to validate (should be cleaned, no spaces)

        Returns:
            True if IBAN appears valid, False otherwise
        """
        if not iban or len(iban) < 15:  # Minimum IBAN length
            return False

        # Extract country code and check digits
        country_code = iban[:2].upper()
        check_digits = iban[2:4]

        # Check if country code is valid
        if country_code not in self.IBAN_LENGTHS:
            logger.debug(f"Unknown country code: {country_code}")
            return False

        # Check if length matches expected length for country
        expected_length = self.IBAN_LENGTHS[country_code]
        if len(iban) != expected_length:
            logger.debug(
                f"Invalid length for {country_code}: "
                f"expected {expected_length}, got {len(iban)}"
            )
            return False

        # Check digits must be numeric
        if not check_digits.isdigit():
            logger.debug(f"Check digits not numeric: {check_digits}")
            return False

        # Verify only alphanumeric characters
        if not iban.isalnum():
            logger.debug("IBAN contains non-alphanumeric characters")
            return False

        # Optional: Full mod-97 checksum validation
        # Uncomment if you want strict validation (slower)
        # return self._validate_checksum(iban)

        return True

    def _validate_checksum(self, iban: str) -> bool:
        """
        Validate IBAN using mod-97 checksum algorithm.

        This is the official IBAN validation method but can be slow
        for large batch processing.

        Args:
            iban: IBAN string to validate

        Returns:
            True if checksum is valid, False otherwise
        """
        # Move first 4 characters to end
        rearranged = iban[4:] + iban[:4]

        # Replace letters with numbers (A=10, B=11, ..., Z=35)
        numeric_iban = ""
        for char in rearranged:
            if char.isdigit():
                numeric_iban += char
            else:
                # A=10, B=11, etc.
                numeric_iban += str(ord(char) - ord("A") + 10)

        # Calculate mod 97
        return int(numeric_iban) % 97 == 1

    def _mask_iban(self, iban: str) -> str:
        """
        Mask IBAN for logging (show only first 4 and last 4 characters).

        Args:
            iban: IBAN to mask

        Returns:
            Masked IBAN string
        """
        if len(iban) <= 8:
            return iban
        return f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"

    def extract_iban_from_pdf_words(self, words: list) -> str | None:
        """
        Extract IBAN from pdfplumber words list.

        Args:
            words: List of word dictionaries from pdfplumber
                   Each word has 'text', 'x0', 'top', etc.

        Returns:
            IBAN if found, None otherwise
        """
        if not words:
            return None

        # Concatenate all text with spaces
        full_text = " ".join(word.get("text", "") for word in words)

        # Extract IBAN from concatenated text
        return self.extract_iban(full_text)

    def extract_iban_from_page_text(self, page_text: str) -> str | None:
        """
        Extract IBAN from full page text.

        Args:
            page_text: Full text content of a PDF page

        Returns:
            IBAN if found, None otherwise
        """
        return self.extract_iban(page_text)
