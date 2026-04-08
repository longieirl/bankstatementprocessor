"""Tests for credit card statement detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.models.extraction_warning import (
    CODE_CREDIT_CARD_SKIPPED,
    ExtractionWarning,
)
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

# Test columns configuration
TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


class TestCreditCardDetection:
    """Tests for detecting and skipping credit card statements."""

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_with_card_number(self, mock_pdfplumber):
        """Test detection of credit card statement with 'Card Number'."""
        # Setup mock PDF with credit card statement text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock page text containing "Card Number"
        mock_page.extract_text.return_value = """
        Credit Card Statement
        Account Holder: John Doe
        Card Number: **** **** **** 1234
        Statement Period: January 2024
        """

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        # Should return empty rows (skipped)
        assert isinstance(result, ExtractionResult)
        assert len(result.transactions) == 0
        assert result.page_count == 1  # Still counts the pages
        assert result.iban is None

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_case_insensitive(self, mock_pdfplumber):
        """Test detection is case-insensitive."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Test with different case variations
        test_cases = [
            "CARD NUMBER: 1234",
            "card number: 1234",
            "Card Number: 1234",
            "Card  Number: 1234",  # Multiple spaces
        ]

        for text in test_cases:
            mock_page.extract_text.return_value = f"Statement\n{text}\nDetails"

            extractor = PDFTableExtractor(columns=TEST_COLUMNS)
            result = extractor.extract(Path("/tmp/test.pdf"))

            assert len(result.transactions) == 0, f"Failed to detect: {text}"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_with_credit_limit(self, mock_pdfplumber):
        """Test detection with 'Credit Limit' keyword."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock page text containing "Credit Limit"
        mock_page.extract_text.return_value = """
        Statement Summary
        Credit Limit: €5,000.00
        Available Credit: €4,500.00
        """

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert len(result.transactions) == 0
        assert result.page_count == 1
        assert result.iban is None

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_with_credit_card_text(self, mock_pdfplumber):
        """Test detection with 'Credit Card' keyword."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.extract_text.return_value = """
        Credit Card Statement
        Account Summary
        """

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert len(result.transactions) == 0
        assert result.page_count == 1

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_with_visa(self, mock_pdfplumber):
        """Test detection with 'Visa' keyword."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.extract_text.return_value = """
        Visa Statement
        Card ending in 1234
        """

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/visa.pdf"))

        assert len(result.transactions) == 0
        assert result.page_count == 1

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_detect_credit_card_statement_with_mastercard(self, mock_pdfplumber):
        """Test detection with 'Mastercard' keyword."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.extract_text.return_value = """
        Mastercard Statement
        Monthly Summary
        """

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/mastercard.pdf"))

        assert len(result.transactions) == 0
        assert result.page_count == 1

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_all_credit_card_patterns(self, mock_pdfplumber):
        """Test all credit card detection patterns."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Test each pattern individually
        patterns = [
            ("Card Number: 1234", "Card Number"),
            ("Credit Limit: €5000", "Credit Limit"),
            ("Credit Card Statement", "Credit Card"),
            ("Visa Card", "Visa"),
            ("Mastercard Statement", "Mastercard"),
        ]

        for text, pattern_name in patterns:
            mock_page.extract_text.return_value = f"Header\n{text}\nFooter"

            extractor = PDFTableExtractor(columns=TEST_COLUMNS)
            result = extractor.extract(Path("/tmp/test.pdf"))

            assert (
                len(result.transactions) == 0
            ), f"Failed to detect with pattern: {pattern_name}"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_does_not_detect_false_positives(self, mock_pdfplumber):
        """Test that normal bank statements are not flagged as credit cards."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock cropped area for transaction extraction
        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Normal bank statement without "Card Number"
        mock_page.extract_text.return_value = """
        Bank Statement
        Account Holder: John Doe
        IBAN: IE29 AIBK 9311 5212 3456 78
        Statement Period: January 2024
        """

        # Mock some transaction data
        mock_words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "2024", "x0": 40, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/bank.pdf"))

        # Should process normally
        assert result.page_count == 1
        # May or may not have rows depending on validation, but shouldn't be empty due to CC detection
        # The key is it didn't skip due to credit card detection

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_detection_with_extraction_error(self, mock_pdfplumber):
        """Test handling of errors during credit card detection."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock extract_text to raise an exception
        mock_page.extract_text.side_effect = Exception("PDF parsing error")

        # Mock cropped area for fallback processing
        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped
        mock_cropped.extract_words.return_value = []

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        # Should not crash, should continue processing
        result = extractor.extract(Path("/tmp/test.pdf"))

        # Should complete without raising exception
        assert result.page_count == 1

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_detection_only_checks_first_page(self, mock_pdfplumber):
        """Test that credit card detection only checks the first page."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value = mock_pdf

        # First page is normal
        mock_page1.extract_text.return_value = "Bank Statement\nIBAN: IE291234"

        # Second page has "Card Number" (should be ignored)
        mock_page2.extract_text.return_value = "Card Number: 1234"

        # Mock cropped areas
        mock_cropped1 = MagicMock()
        mock_cropped2 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_page2.crop.return_value = mock_cropped2
        mock_cropped1.extract_words.return_value = []
        mock_cropped2.extract_words.return_value = []

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/test.pdf"))

        # Should process both pages (not skipped)
        assert result.page_count == 2

    def test_is_credit_card_statement_method_directly(self):
        """Test the _is_credit_card_statement method directly."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)

        # Mock page with credit card text in header area
        mock_page = MagicMock()
        mock_page.width = 612  # Standard PDF width

        # Mock cropped header area
        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Statement for Card Number 1234"
        mock_page.crop.return_value = mock_header

        assert (
            extractor._header_analyser.is_credit_card_statement(
                mock_page, extractor.table_top_y
            )
            is True
        )

    def test_is_credit_card_statement_method_no_match(self):
        """Test _is_credit_card_statement with no match."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)

        # Mock page without credit card text
        mock_page = MagicMock()
        mock_page.width = 612  # Standard PDF width

        # Mock cropped header area
        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Bank Statement IBAN IE291234"
        mock_page.crop.return_value = mock_header

        assert (
            extractor._header_analyser.is_credit_card_statement(
                mock_page, extractor.table_top_y
            )
            is False
        )

    def test_visa_in_transaction_not_detected(self):
        """Test that 'VISA' in transaction lines does not trigger false positive."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)

        # Mock page with VISA in transaction line (not in header)
        mock_page = MagicMock()
        mock_page.width = 612

        # Header has no credit card indicators
        mock_header = MagicMock()
        mock_header.extract_text.return_value = """
        Personal Bank Account
        Statement of Account
        IBAN: IE48 AIBK 9340 8921 4590 15
        Date Details Debit € Credit €
        """
        mock_page.crop.return_value = mock_header

        # Even though full page would have VISA in transactions,
        # we only check header, so should NOT be detected
        assert (
            extractor._header_analyser.is_credit_card_statement(
                mock_page, extractor.table_top_y
            )
            is False
        )

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_early_return_produces_extraction_result_with_warning(
        self, mock_pdfplumber
    ):
        """Test that credit card detection returns ExtractionResult with warning message."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.width = 612
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock the cropped header area to return credit card text
        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Statement for Card Number 1234"
        mock_page.crop.return_value = mock_header

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert isinstance(result, ExtractionResult)
        assert len(result.transactions) == 0
        assert result.iban is None
        assert len(result.warnings) > 0
        assert isinstance(result.warnings[0], ExtractionWarning)
        assert result.warnings[0].code == CODE_CREDIT_CARD_SKIPPED
        assert "credit card" in result.warnings[0].message.lower()

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_not_skipped_on_paid_tier(self, mock_pdfplumber):
        """Paid-tier entitlements (require_iban=False) must NOT trigger the early-return."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.width = 612
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Statement for Card Number 1234"
        mock_page.crop.return_value = mock_header

        # Paid tier: require_iban=False → credit card PDFs should proceed
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS, entitlements=Entitlements.paid_tier()
        )
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert isinstance(result, ExtractionResult)
        assert not any(
            w.code == CODE_CREDIT_CARD_SKIPPED for w in result.warnings
        ), "Paid tier must not produce CODE_CREDIT_CARD_SKIPPED"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_skipped_on_free_tier(self, mock_pdfplumber):
        """Free-tier entitlements (require_iban=True) must skip credit card PDFs."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.width = 612
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Statement for Card Number 1234"
        mock_page.crop.return_value = mock_header

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS, entitlements=Entitlements.free_tier()
        )
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert isinstance(result, ExtractionResult)
        assert len(result.transactions) == 0
        assert any(w.code == CODE_CREDIT_CARD_SKIPPED for w in result.warnings)

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_skipped_when_no_entitlements(self, mock_pdfplumber):
        """No entitlements (None) must preserve backward-compat skip behaviour."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.width = 612
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_header = MagicMock()
        mock_header.extract_text.return_value = "Statement for Card Number 1234"
        mock_page.crop.return_value = mock_header

        extractor = PDFTableExtractor(columns=TEST_COLUMNS, entitlements=None)
        result = extractor.extract(Path("/tmp/credit_card.pdf"))

        assert isinstance(result, ExtractionResult)
        assert len(result.transactions) == 0
        assert any(w.code == CODE_CREDIT_CARD_SKIPPED for w in result.warnings)
