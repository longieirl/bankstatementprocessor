"""Tests for individual detectors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from bankstatements_core.templates.detectors import (
    ColumnHeaderDetector,
    DetectionResult,
    FilenameDetector,
    HeaderDetector,
    IBANDetector,
)
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)


def get_best_match(results: list[DetectionResult]) -> BankTemplate | None:
    """Helper to get best matching template from detection results.

    Filters out excluded templates (confidence=0.0) and returns template
    with highest confidence, or None if no matches.
    """
    if not results:
        return None

    # Filter out excluded
    valid = [r for r in results if r.confidence > 0.0]
    if not valid:
        return None

    # Return highest confidence
    valid.sort(key=lambda r: r.confidence, reverse=True)
    return valid[0].template


@pytest.fixture
def mock_page():
    """Create mock PDF page."""
    page = MagicMock()
    page.height = 841.89  # A4 page height in points
    page.width = 595.28  # A4 page width in points
    # Make crop return self for chaining
    page.crop.return_value = page
    return page


@pytest.fixture
def aib_template():
    """Create AIB template for testing."""
    return BankTemplate(
        id="aib",
        name="Allied Irish Banks",
        enabled=True,
        detection=TemplateDetectionConfig(
            iban_patterns=["IE[0-9]{2}AIBK.*"],
            filename_patterns=["Statement JL CA *.pdf"],
            header_keywords=["Allied Irish Banks", "AIB"],
            column_headers=["Date", "Details", "Debit", "Credit"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        ),
    )


@pytest.fixture
def revolut_template():
    """Create Revolut template for testing with specific REVO IBAN pattern."""
    return BankTemplate(
        id="revolut",
        name="Revolut",
        enabled=True,
        detection=TemplateDetectionConfig(
            iban_patterns=["[A-Z]{2}[0-9]{2}REVO[0-9A-Z]+"],
            filename_patterns=["account-statement_*.pdf"],
            header_keywords=["Revolut", "revolut.com"],
            column_headers=["Date", "Description", "Money out", "Money in"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (42, 120)},
        ),
    )


@pytest.fixture
def default_template():
    """Create Default template for testing without IBAN pattern."""
    return BankTemplate(
        id="default",
        name="Default Bank Statement",
        enabled=True,
        detection=TemplateDetectionConfig(
            iban_patterns=[],  # No IBAN pattern - relies on column headers
            column_headers=["Date", "Details", "Debit", "Credit", "Balance"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        ),
    )


class TestIBANDetector:
    """Tests for IBANDetector."""

    def test_name(self):
        """Test detector name."""
        detector = IBANDetector()
        assert detector.name == "IBAN"

    def test_detect_aib_iban(self, mock_page, aib_template, revolut_template):
        """Test detecting AIB by IBAN pattern."""
        mock_page.extract_text.return_value = "IBAN: IE29AIBK93115212345678"

        detector = IBANDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == aib_template

    def test_detect_revolut_iban(self, mock_page, aib_template, revolut_template):
        """Test detecting Revolut by IBAN pattern with REVO bank code."""
        mock_page.extract_text.return_value = "Account: IE27REVO99036083303656"

        detector = IBANDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == revolut_template

    def test_detect_default_template_skipped_no_iban_pattern(
        self, mock_page, default_template, revolut_template
    ):
        """Test that default template is skipped when it has no IBAN pattern."""
        # Both IBANs present, but default should not match (no IBAN pattern)
        mock_page.extract_text.return_value = "IBAN: IE27REVO99036083303656"

        detector = IBANDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [default_template, revolut_template],
        )

        # Should match Revolut, not Default
        assert get_best_match(results) == revolut_template

    def test_detect_revolut_prioritized_over_generic(
        self, mock_page, default_template, revolut_template
    ):
        """Test that Revolut-specific IBAN pattern matches before generic pattern."""
        mock_page.extract_text.return_value = "IBAN: IE27REVO99036083303656"

        # Pass templates in order that would fail if default had generic pattern
        detector = IBANDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [default_template, revolut_template],
        )

        # Should match Revolut specifically, not fall back to default
        assert get_best_match(results) == revolut_template
        assert get_best_match(results).id == "revolut"

    def test_detect_no_iban(self, mock_page, aib_template):
        """Test no detection when IBAN not found."""
        mock_page.extract_text.return_value = "No IBAN here"

        detector = IBANDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None

    def test_detect_no_text(self, mock_page, aib_template):
        """Test no detection when page has no text."""
        mock_page.extract_text.return_value = None

        detector = IBANDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None


class TestFilenameDetector:
    """Tests for FilenameDetector."""

    def test_name(self):
        """Test detector name."""
        detector = FilenameDetector()
        assert detector.name == "Filename"

    def test_detect_aib_filename(self, mock_page, aib_template, revolut_template):
        """Test detecting AIB by filename pattern."""
        detector = FilenameDetector()
        results = detector.detect(
            Path("Statement JL CA 2025-01.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == aib_template

    def test_detect_revolut_filename(self, mock_page, aib_template, revolut_template):
        """Test detecting Revolut by filename pattern."""
        detector = FilenameDetector()
        results = detector.detect(
            Path("account-statement_2025-01-01_2025-12-31_en-ie_abc123.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == revolut_template

    def test_detect_no_match(self, mock_page, aib_template):
        """Test no detection when filename doesn't match."""
        detector = FilenameDetector()
        results = detector.detect(
            Path("random_file.pdf"),
            mock_page,
            [aib_template],
        )

        assert get_best_match(results) is None

    def test_detect_with_no_patterns_skips_template(self, mock_page):
        """Test that templates without filename_patterns are skipped by filename detector."""
        # Create template without filename_patterns
        template_no_patterns = BankTemplate(
            id="testbank",
            name="Test Bank",
            enabled=True,
            detection=TemplateDetectionConfig(
                iban_patterns=["IE[0-9]{2}TEST.*"],
                # filename_patterns omitted (empty list)
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        detector = FilenameDetector()
        results = detector.detect(
            Path("any_file.pdf"),
            mock_page,
            [template_no_patterns],
        )

        # Should NOT match because filename detection is skipped for templates without patterns
        assert get_best_match(results) is None

    def test_get_filename_patterns_default(self, mock_page):
        """Test that get_filename_patterns() returns default for templates without patterns."""
        template_no_patterns = BankTemplate(
            id="testbank",
            name="Test Bank",
            enabled=True,
            detection=TemplateDetectionConfig(
                iban_patterns=["IE[0-9]{2}TEST.*"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        # The model method provides a default, even though detector won't use it
        assert template_no_patterns.detection.filename_patterns == []
        assert template_no_patterns.detection.get_filename_patterns() == ["*.pdf"]


class TestHeaderDetector:
    """Tests for HeaderDetector."""

    def test_name(self):
        """Test detector name."""
        detector = HeaderDetector()
        assert detector.name == "Header"

    def test_detect_aib_header(self, mock_page, aib_template, revolut_template):
        """Test detecting AIB by header keyword."""
        mock_page.extract_text.return_value = """
        Allied Irish Banks
        Bank Statement
        """

        detector = HeaderDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == aib_template

    def test_detect_revolut_header(self, mock_page, aib_template, revolut_template):
        """Test detecting Revolut by header keyword."""
        mock_page.extract_text.return_value = """
        Revolut
        Account Statement
        """

        detector = HeaderDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == revolut_template

    def test_detect_case_insensitive(self, mock_page, aib_template):
        """Test case-insensitive header matching."""
        mock_page.extract_text.return_value = "aLLiEd IrIsH BaNkS"

        detector = HeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) == aib_template

    def test_detect_no_match(self, mock_page, aib_template):
        """Test no detection when keyword not found."""
        mock_page.extract_text.return_value = "Some other bank"

        detector = HeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None

    def test_detect_no_text(self, mock_page, aib_template):
        """Test no detection when page has no text."""
        mock_page.extract_text.return_value = None

        detector = HeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None


class TestColumnHeaderDetector:
    """Tests for ColumnHeaderDetector."""

    def test_name(self):
        """Test detector name."""
        detector = ColumnHeaderDetector()
        assert detector.name == "ColumnHeader"

    def test_detect_aib_headers(self, mock_page, aib_template, revolut_template):
        """Test detecting AIB by column headers."""
        mock_page.extract_text.return_value = """
        Date    Details    Debit €    Credit €    Balance €
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == aib_template

    def test_detect_revolut_headers(self, mock_page, aib_template, revolut_template):
        """Test detecting Revolut by column headers."""
        mock_page.extract_text.return_value = """
        Date    Description    Money out    Money in    Balance
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [aib_template, revolut_template],
        )

        assert get_best_match(results) == revolut_template

    def test_detect_partial_match(self, mock_page, aib_template):
        """Test detection with 70% of headers matching."""
        mock_page.extract_text.return_value = """
        Date    Details    Debit €
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) == aib_template

    def test_detect_insufficient_match(self, mock_page, aib_template):
        """Test no detection when less than 70% of headers match."""
        mock_page.extract_text.return_value = """
        Date    Random
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None

    def test_detect_no_text(self, mock_page, aib_template):
        """Test no detection when page has no text."""
        mock_page.extract_text.return_value = None

        detector = ColumnHeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None

    def test_detect_default_template_by_column_headers(
        self, mock_page, default_template
    ):
        """Test that default template is detected by column headers when IBAN fails."""
        mock_page.extract_text.return_value = """
        Date    Details    Debit €    Credit €    Balance €
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [default_template])

        assert get_best_match(results) == default_template
        assert get_best_match(results).id == "default"

    def test_detect_default_vs_revolut_by_column_headers(
        self, mock_page, default_template, revolut_template
    ):
        """Test that correct template is chosen based on column headers."""
        # Revolut-specific headers
        mock_page.extract_text.return_value = """
        Date    Description    Money out    Money in    Balance
        """

        detector = ColumnHeaderDetector()
        results = detector.detect(
            Path("test.pdf"),
            mock_page,
            [default_template, revolut_template],
        )

        assert get_best_match(results) == revolut_template
        assert get_best_match(results).id == "revolut"


class TestCardNumberDetector:
    """Tests for CardNumberDetector."""

    def test_name(self):
        """Test detector name."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        detector = CardNumberDetector()
        assert detector.name == "CardNumber"

    def test_detect_masked_card_number(self, mock_page):
        """Test detecting credit card by masked card number."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        aib_cc_template = BankTemplate(
            id="aib_credit_card",
            name="AIB Credit Card",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "card_number_patterns": [r"\*{4}\s*\*{4}\s*\*{4}\s*[0-9]{4}"]
                },
                header_keywords=[
                    "Credit Card"
                ],  # Need at least one legacy detection method
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=320,
                table_bottom_y=720,
                columns={"Date": (29, 78)},
            ),
        )

        mock_page.extract_text.return_value = "Card Number: **** **** **** 1234"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Card Number: **** **** **** 1234"
        mock_page.crop.return_value = mock_cropped

        detector = CardNumberDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_cc_template])

        assert get_best_match(results) == aib_cc_template
        assert results[0].confidence >= 0.90

    def test_detect_partial_masked_card_number(self, mock_page):
        """Test detecting card number with partial masking (4402 60** **** 9459)."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        cc_template = BankTemplate(
            id="credit_card_default",
            name="Default Credit Card",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "card_number_patterns": [
                        r"[0-9]{4}\s*[0-9]{2}\*{2}\s*\*{4}\s*[0-9]{4}"
                    ]
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 100)},
            ),
        )

        mock_page.extract_text.return_value = "4402 60** **** 9459"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "4402 60** **** 9459"
        mock_page.crop.return_value = mock_cropped

        detector = CardNumberDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [cc_template])

        assert get_best_match(results) == cc_template

    def test_detect_no_card_number(self, mock_page):
        """Test no detection when card number not found."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        cc_template = BankTemplate(
            id="credit_card_default",
            name="Default Credit Card",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "card_number_patterns": [r"\*{4}\s*\*{4}\s*\*{4}\s*[0-9]{4}"]
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 100)},
            ),
        )

        mock_page.extract_text.return_value = "IBAN: IE29AIBK93115212345678"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "IBAN: IE29AIBK93115212345678"
        mock_page.crop.return_value = mock_cropped

        detector = CardNumberDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [cc_template])

        assert get_best_match(results) is None

    def test_skip_templates_without_card_patterns(self, mock_page, aib_template):
        """Test that bank templates without card patterns are skipped."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        mock_page.extract_text.return_value = "**** **** **** 1234"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "**** **** **** 1234"
        mock_page.crop.return_value = mock_cropped

        detector = CardNumberDetector()
        results = detector.detect(
            Path("test.pdf"), mock_page, [aib_template]
        )  # Bank template has no card_number_patterns

        assert get_best_match(results) is None

    def test_invalid_regex_pattern_handling(self, mock_page):
        """Test handling of invalid regex patterns."""
        from bankstatements_core.templates.detectors import CardNumberDetector

        bad_template = BankTemplate(
            id="bad_cc",
            name="Bad Credit Card",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={"card_number_patterns": ["[invalid(regex"]},
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 100)},
            ),
        )

        mock_page.extract_text.return_value = "**** **** **** 1234"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "**** **** **** 1234"
        mock_page.crop.return_value = mock_cropped

        detector = CardNumberDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [bad_template])

        # Should not crash, should return empty results
        assert get_best_match(results) is None


class TestLoanReferenceDetector:
    """Tests for LoanReferenceDetector."""

    def test_name(self):
        """Test detector name."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        detector = LoanReferenceDetector()
        assert detector.name == "LoanReference"

    def test_detect_loan_ref(self, mock_page):
        """Test detecting loan by loan reference."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        loan_template = BankTemplate(
            id="loan_default",
            name="Default Loan Statement",
            document_type="loan_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "loan_reference_patterns": [
                        r"Loan\s*(?:Ref|Reference):\s*[A-Z0-9-]+"
                    ]
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        mock_page.extract_text.return_value = "Loan Ref: 123456789"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Loan Ref: 123456789"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [loan_template])

        assert get_best_match(results) == loan_template
        assert results[0].confidence >= 0.90

    def test_detect_mortgage_account(self, mock_page):
        """Test detecting mortgage by account number."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        loan_template = BankTemplate(
            id="loan_default",
            name="Default Loan Statement",
            document_type="loan_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "loan_reference_patterns": [r"Mortgage\s*Account:\s*[A-Z0-9-]+"]
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        mock_page.extract_text.return_value = "Mortgage Account: ABC-12345"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Mortgage Account: ABC-12345"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [loan_template])

        assert get_best_match(results) == loan_template

    def test_detect_no_loan_ref(self, mock_page):
        """Test no detection when loan reference not found."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        loan_template = BankTemplate(
            id="loan_default",
            name="Default Loan Statement",
            document_type="loan_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "loan_reference_patterns": [r"Loan\s*Ref:\s*[A-Z0-9-]+"]
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        mock_page.extract_text.return_value = "IBAN: IE29AIBK93115212345678"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "IBAN: IE29AIBK93115212345678"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [loan_template])

        assert get_best_match(results) is None

    def test_skip_templates_without_loan_patterns(self, mock_page, aib_template):
        """Test that bank templates without loan patterns are skipped."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        mock_page.extract_text.return_value = "Loan Ref: 123456"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Loan Ref: 123456"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [aib_template])

        assert get_best_match(results) is None

    def test_invalid_regex_pattern_handling(self, mock_page):
        """Test handling of invalid regex patterns."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        bad_template = BankTemplate(
            id="bad_loan",
            name="Bad Loan",
            document_type="loan_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={"loan_reference_patterns": ["[invalid(regex"]},
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        mock_page.extract_text.return_value = "Loan Ref: 123456"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Loan Ref: 123456"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [bad_template])

        # Should not crash, should return empty results
        assert get_best_match(results) is None

    def test_high_confidence_for_specific_patterns(self, mock_page):
        """Test that longer patterns get higher confidence."""
        from bankstatements_core.templates.detectors import LoanReferenceDetector

        loan_template = BankTemplate(
            id="loan_default",
            name="Default Loan Statement",
            document_type="loan_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                document_identifiers={
                    "loan_reference_patterns": [
                        r"Mortgage\s*Account\s*Reference:\s*[A-Z0-9-]+"
                    ]  # Long pattern (>20 chars)
                },
                header_keywords=["Test"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        mock_page.extract_text.return_value = "Mortgage Account Reference: ABC-12345"
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Mortgage Account Reference: ABC-12345"
        mock_page.crop.return_value = mock_cropped

        detector = LoanReferenceDetector()
        results = detector.detect(Path("test.pdf"), mock_page, [loan_template])

        assert results[0].confidence == 0.95  # Should get bonus for long pattern
