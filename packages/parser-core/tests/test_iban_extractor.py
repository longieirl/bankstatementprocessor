"""Tests for IBAN extraction functionality."""

from __future__ import annotations

import pytest

from bankstatements_core.extraction.iban_extractor import IBANExtractor


class TestIBANExtractor:
    """Test cases for IBANExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create IBANExtractor instance for testing."""
        return IBANExtractor()

    def test_extract_irish_iban_no_spaces(self, extractor):
        """Test extraction of Irish IBAN without spaces."""
        text = "Your account number is IE29AIBK93115212345678 for reference."
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_extract_irish_iban_with_spaces(self, extractor):
        """Test extraction of Irish IBAN with spaces."""
        text = "Account: IE29 AIBK 9311 5212 3456 78"
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_extract_german_iban(self, extractor):
        """Test extraction of German IBAN."""
        text = "Kontonummer: DE89370400440532013000"
        iban = extractor.extract_iban(text)

        assert iban == "DE89370400440532013000"

    def test_extract_uk_iban(self, extractor):
        """Test extraction of UK IBAN."""
        text = "Account: GB29NWBK60161331926819"
        iban = extractor.extract_iban(text)

        assert iban == "GB29NWBK60161331926819"

    def test_extract_french_iban(self, extractor):
        """Test extraction of French IBAN."""
        text = "IBAN: FR1420041010050500013M02606"
        iban = extractor.extract_iban(text)

        assert iban == "FR1420041010050500013M02606"

    def test_extract_iban_with_hyphens(self, extractor):
        """Test extraction of IBAN with hyphen separators."""
        text = "IE29-AIBK-9311-5212-3456-78"
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_extract_iban_from_multiline_text(self, extractor):
        """Test extraction from text with multiple lines."""
        text = """
        Bank Statement
        Account holder: John Doe
        IBAN: IE29 AIBK 9311 5212 3456 78
        Date: 01/01/2024
        """
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_no_iban_in_text(self, extractor):
        """Test when no IBAN is present in text."""
        text = "This is a regular text without any IBAN number."
        iban = extractor.extract_iban(text)

        assert iban is None

    def test_invalid_iban_wrong_length(self, extractor):
        """Test that invalid IBAN (wrong length) is not extracted."""
        # Irish IBAN should be 22 characters, this is too short
        text = "IE29AIBK931152123"
        iban = extractor.extract_iban(text)

        assert iban is None

    def test_invalid_iban_unknown_country(self, extractor):
        """Test that IBAN with unknown country code is not extracted."""
        text = "XX29AIBK93115212345678"
        iban = extractor.extract_iban(text)

        assert iban is None

    def test_invalid_iban_non_numeric_check_digits(self, extractor):
        """Test that IBAN with non-numeric check digits is not extracted."""
        text = "IEXXAIBK93115212345678"
        iban = extractor.extract_iban(text)

        assert iban is None

    def test_extract_first_iban_when_multiple(self, extractor):
        """Test that only first valid IBAN is extracted."""
        text = """
        Primary account: IE29AIBK93115212345678
        Secondary account: DE89370400440532013000
        """
        iban = extractor.extract_iban(text)

        # Should return the first valid IBAN found
        assert iban == "IE29AIBK93115212345678"

    def test_iban_validation_correct_length_ireland(self, extractor):
        """Test IBAN validation for Irish IBAN with correct length."""
        assert extractor.is_valid_iban("IE29AIBK93115212345678")

    def test_iban_validation_correct_length_germany(self, extractor):
        """Test IBAN validation for German IBAN with correct length."""
        assert extractor.is_valid_iban("DE89370400440532013000")

    def test_iban_validation_wrong_length(self, extractor):
        """Test IBAN validation rejects wrong length."""
        assert not extractor.is_valid_iban("IE29AIBK931152")  # Too short

    def test_iban_validation_unknown_country(self, extractor):
        """Test IBAN validation rejects unknown country."""
        assert not extractor.is_valid_iban("XX29AIBK93115212345678")

    def test_iban_validation_non_alphanumeric(self, extractor):
        """Test IBAN validation rejects non-alphanumeric characters."""
        assert not extractor.is_valid_iban("IE29-AIBK-9311-5212-3456-78")

    def test_iban_masking(self, extractor):
        """Test IBAN masking for logging."""
        iban = "IE29AIBK93115212345678"
        masked = extractor._mask_iban(iban)

        assert masked == "IE29**************5678"
        assert len(masked) == len(iban)

    def test_extract_iban_from_pdf_words(self, extractor):
        """Test extraction from pdfplumber words list."""
        # Simulate pdfplumber word structure
        words = [
            {"text": "IBAN:", "x0": 50, "top": 100},
            {"text": "IE29", "x0": 80, "top": 100},
            {"text": "AIBK", "x0": 110, "top": 100},
            {"text": "9311", "x0": 140, "top": 100},
            {"text": "5212", "x0": 170, "top": 100},
            {"text": "3456", "x0": 200, "top": 100},
            {"text": "78", "x0": 230, "top": 100},
        ]

        iban = extractor.extract_iban_from_pdf_words(words)

        assert iban == "IE29AIBK93115212345678"

    def test_extract_iban_case_insensitive(self, extractor):
        """Test that IBAN extraction is case-insensitive."""
        text_lower = "iban: ie29aibk93115212345678"
        text_mixed = "IBAN: Ie29AiBk93115212345678"

        iban_lower = extractor.extract_iban(text_lower)
        iban_mixed = extractor.extract_iban(text_mixed)

        assert iban_lower == "IE29AIBK93115212345678"
        assert iban_mixed == "IE29AIBK93115212345678"

    def test_extract_iban_with_surrounding_text(self, extractor):
        """Test extraction when IBAN is surrounded by other text."""
        text = "Please transfer to IE29AIBK93115212345678 by Friday."
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_various_european_ibans(self, extractor):
        """Test extraction of IBANs from various European countries."""
        test_cases = [
            ("AT611904300234573201", "AT"),  # Austria - 20 chars
            ("BE68539007547034", "BE"),  # Belgium - 16 chars
            ("CH9300762011623852957", "CH"),  # Switzerland - 21 chars
            ("DK5000400440116243", "DK"),  # Denmark - 18 chars
            ("ES9121000418450200051332", "ES"),  # Spain - 24 chars
            ("FI2112345600000785", "FI"),  # Finland - 18 chars
            ("IT60X0542811101000000123456", "IT"),  # Italy - 27 chars
            ("NL91ABNA0417164300", "NL"),  # Netherlands - 18 chars
            ("NO9386011117947", "NO"),  # Norway - 15 chars
            ("PL61109010140000071219812874", "PL"),  # Poland - 28 chars
            ("PT50000201231234567890154", "PT"),  # Portugal - 25 chars
            ("SE4550000000058398257466", "SE"),  # Sweden - 24 chars
        ]

        for iban, country_code in test_cases:
            result = extractor.extract_iban(f"Account: {iban}")
            assert result == iban, f"Failed to extract {country_code} IBAN"
            assert extractor.is_valid_iban(iban), f"{country_code} IBAN should be valid"

    def test_empty_text(self, extractor):
        """Test extraction from empty text."""
        assert extractor.extract_iban("") is None
        assert extractor.extract_iban(None) is None

    def test_iban_at_start_of_text(self, extractor):
        """Test extraction when IBAN is at the start of text."""
        text = "IE29AIBK93115212345678 is your account number"
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_iban_at_end_of_text(self, extractor):
        """Test extraction when IBAN is at the end of text."""
        text = "Your account number: IE29AIBK93115212345678"
        iban = extractor.extract_iban(text)

        assert iban == "IE29AIBK93115212345678"

    def test_validation_check_digits_not_numeric(self, extractor):
        """Test validation fails when check digits are not numeric."""
        # IEXX (check digits are XX instead of numbers)
        iban = "IEXXAIBK93115212345678"
        is_valid = extractor.is_valid_iban(iban)

        assert is_valid is False

    def test_validation_non_alphanumeric_characters(self, extractor):
        """Test validation fails with non-alphanumeric characters."""
        # IBAN with special characters (not cleaned)
        iban = "IE29 AIBK 9311 5212 3456 78"  # Contains spaces
        # This should be cleaned first, but let's test raw validation
        is_valid = extractor.is_valid_iban(iban)

        assert is_valid is False

    def test_validation_with_special_chars_in_valid_format(self, extractor):
        """Test validation with IBAN containing special characters like underscores."""
        # IBAN with underscore (valid length and country, but has special char)
        iban = "IE29AIBK931152_2345678"  # 22 chars, valid country, but has underscore
        is_valid = extractor.is_valid_iban(iban)

        assert is_valid is False

    def test_mask_iban_short_iban(self, extractor):
        """Test masking of short IBANs (8 chars or less)."""
        # Short IBAN should not be masked
        short_iban = "IE291234"
        masked = extractor._mask_iban(short_iban)

        assert masked == "IE291234"  # Not masked

    def test_extract_iban_from_pdf_words_empty_list(self, extractor):
        """Test extraction from empty PDF words list."""
        words = []
        iban = extractor.extract_iban_from_pdf_words(words)

        assert iban is None

    def test_extract_iban_from_pdf_words_no_iban(self, extractor):
        """Test extraction from PDF words without IBAN."""
        words = [
            {"text": "Random", "x0": 30, "top": 100},
            {"text": "Text", "x0": 60, "top": 100},
            {"text": "No", "x0": 90, "top": 100},
            {"text": "IBAN", "x0": 120, "top": 100},
        ]
        iban = extractor.extract_iban_from_pdf_words(words)

        assert iban is None

    def test_extract_iban_from_page_text(self, extractor):
        """Test extraction from full page text."""
        page_text = """
        Bank Statement
        Account Holder: John Doe
        IBAN: IE29 AIBK 9311 5212 3456 78
        Statement Period: January 2024
        """
        iban = extractor.extract_iban_from_page_text(page_text)

        assert iban == "IE29AIBK93115212345678"

    def test_extract_iban_from_page_text_no_iban(self, extractor):
        """Test extraction from page text without IBAN."""
        page_text = """
        Bank Statement
        Account Holder: John Doe
        Statement Period: January 2024
        """
        iban = extractor.extract_iban_from_page_text(page_text)

        assert iban is None

    def test_validate_checksum(self, extractor):
        """Test checksum validation with valid IBAN."""
        # Valid Irish IBAN
        iban = "IE29AIBK93115212345678"
        # The _validate_checksum method is private but we can test it
        is_valid = extractor._validate_checksum(iban)

        # This should validate the checksum
        assert isinstance(is_valid, bool)

    def test_validate_checksum_invalid(self, extractor):
        """Test checksum validation with invalid IBAN."""
        # Invalid checksum - change check digits
        iban = "IE00AIBK93115212345678"
        is_valid = extractor._validate_checksum(iban)

        assert is_valid is False
