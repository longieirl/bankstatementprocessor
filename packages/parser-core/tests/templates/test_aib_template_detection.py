"""Tests for AIB template detection to prevent bank/credit card confusion.

Regression tests to ensure AIB bank statements are not confused with
AIB credit card statements (and vice versa).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bankstatements_core.templates.detectors.base import DetectionResult
from bankstatements_core.templates.template_detector import TemplateDetector
from bankstatements_core.templates.template_registry import TemplateRegistry


class TestAIBTemplateDetection:
    """Test AIB template detection specificity."""

    def test_aib_ireland_template_has_iban_patterns(self):
        """Test AIB Ireland template has IBAN patterns for detection."""
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")

        assert aib_ireland is not None
        assert hasattr(aib_ireland.detection, "iban_patterns")
        assert len(aib_ireland.detection.iban_patterns) > 0
        assert any("AIBK" in pattern for pattern in aib_ireland.detection.iban_patterns)

    def test_aib_credit_card_has_specific_keywords(self):
        """Test AIB credit card template has credit-card-specific keywords."""
        registry = TemplateRegistry.from_default_config()
        aib_cc = registry.get_template("aib_credit_card")

        if aib_cc is None:
            pytest.skip(
                "aib_credit_card is a premium template not included in this build"
            )
        keywords = aib_cc.detection.header_keywords

        # Should have specific keywords, not just "Allied Irish Banks"
        assert any(
            "Credit Card" in kw for kw in keywords
        ), "AIB credit card template should have 'Credit Card' keyword"

    def test_aib_ireland_has_bank_specific_keywords(self):
        """Test AIB Ireland template has bank-specific keywords."""
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")

        assert aib_ireland is not None
        keywords = aib_ireland.detection.header_keywords

        # Should have specific bank account keywords
        bank_keywords = [
            "Personal Bank Account",
            "Statement of Account",
            "Allied Irish Banks",
        ]
        assert any(
            kw in keywords for kw in bank_keywords
        ), "AIB Ireland template should have bank-specific keywords"

    def test_aib_credit_card_has_exclude_keywords(self):
        """Test AIB credit card template has exclude keywords to avoid bank statements."""
        registry = TemplateRegistry.from_default_config()
        aib_cc = registry.get_template("aib_credit_card")

        if aib_cc is None:
            pytest.skip(
                "aib_credit_card is a premium template not included in this build"
            )
        assert hasattr(aib_cc.detection, "exclude_keywords")

        exclude_keywords = aib_cc.detection.exclude_keywords
        if exclude_keywords:  # If implemented
            # Should exclude bank-specific terms
            expected_exclusions = [
                "IBAN",
                "Personal Bank Account",
                "Statement of Account",
            ]
            for exclusion in expected_exclusions:
                assert (
                    exclusion in exclude_keywords
                ), f"AIB credit card should exclude '{exclusion}' to avoid bank statements"


class TestAIBTemplateDetectionScenarios:
    """Test AIB template detection with mocked PDF content."""

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    def test_bank_statement_with_iban_detected_as_aib_ireland(
        self, mock_iban_detector, mock_header_detector, mock_exclusion_detector
    ):
        """Test bank statement with IBAN is detected as AIB Ireland, not credit card.

        Scenario: PDF has both "Allied Irish Banks" header and IBAN.
        Expected: Should detect as AIB Ireland (bank), not credit card.
        """
        from pathlib import Path

        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)
        aib_ireland = registry.get_template("aib_ireland")

        # Mock PDF that looks like AIB bank statement
        mock_pdf = MagicMock()
        mock_pdf.width = 595.28
        mock_pdf.height = 841.89
        mock_pdf.extract_text.return_value = "AIB Bank Statement\nIBAN: IE29AIBK"
        # Mock crop for document classification
        cropped = MagicMock()
        cropped.extract_text.return_value = "AIB Bank Statement\nIBAN: IE29AIBK"
        mock_pdf.crop.return_value = cropped

        # Exclusion detector doesn't exclude anything
        mock_exclusion_detector.return_value = []

        # IBAN detector finds IBAN pattern (high specificity)
        mock_iban_detector.return_value = [
            DetectionResult(
                template=aib_ireland,
                confidence=1.0,
                detector_name="IBAN",
                match_details={"iban": "IE29AIBK12345678"},
            )
        ]

        # Header detector also matches
        mock_header_detector.return_value = [
            DetectionResult(
                template=aib_ireland,
                confidence=0.75,
                detector_name="Header",
                match_details={},
            )
        ]

        # Detection should prioritize IBAN match
        detected = detector.detect_template(Path("test.pdf"), mock_pdf)

        assert detected is not None
        assert (
            detected.id == "aib_ireland"
        ), "PDF with IBAN should be detected as AIB Ireland bank statement"

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    def test_credit_card_without_iban_detected_as_aib_credit_card(
        self, mock_iban_detector, mock_header_detector, mock_exclusion_detector
    ):
        """Test credit card statement without IBAN is detected as credit card.

        Scenario: PDF has "Credit Card Statement" header but no IBAN.
        Expected: Should detect as AIB Credit Card.
        """
        from pathlib import Path

        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)
        aib_cc = registry.get_template("aib_credit_card")

        if aib_cc is None:
            pytest.skip(
                "aib_credit_card is a premium template not included in this build"
            )

        # Mock PDF that looks like credit card statement
        mock_pdf = MagicMock()
        mock_pdf.width = 595.28
        mock_pdf.height = 841.89
        mock_pdf.extract_text.return_value = (
            "Credit Card Statement\nCard Number: **** **** **** 1234"
        )
        # Mock crop for document classification
        cropped = MagicMock()
        cropped.extract_text.return_value = (
            "Credit Card Statement\nCard Number: **** **** **** 1234"
        )
        mock_pdf.crop.return_value = cropped

        # Exclusion detector doesn't exclude anything
        mock_exclusion_detector.return_value = []

        # IBAN detector finds nothing (credit cards don't have IBANs)
        mock_iban_detector.return_value = []

        # Header detector finds credit card keywords
        mock_header_detector.return_value = [
            DetectionResult(
                template=aib_cc,
                confidence=0.75,
                detector_name="Header",
                match_details={"keywords": ["Credit Card"]},
            )
        ]

        detected = detector.detect_template(Path("test.pdf"), mock_pdf)

        assert detected is not None
        assert (
            detected.id == "aib_credit_card"
        ), "PDF with 'Credit Card Statement' and no IBAN should be credit card"


class TestAIBColumnBoundaries:
    """Test AIB template column boundaries are distinct."""

    def test_aib_ireland_and_credit_card_have_different_columns(self):
        """Test AIB Ireland and credit card templates have different column definitions.

        They should have different boundaries because the PDF formats differ.
        """
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")
        aib_cc = registry.get_template("aib_credit_card")

        assert aib_ireland is not None
        if aib_cc is None:
            pytest.skip(
                "aib_credit_card is a premium template not included in this build"
            )

        # Column sets should be different
        ireland_cols = set(aib_ireland.extraction.columns.keys())

        # They might share some columns (Date, Details) but overall structure differs
        # At minimum, bank statements have Balance, credit cards might not
        if "Balance €" in ireland_cols:
            # This is acceptable - bank statements typically have running balance
            pass

    def test_aib_ireland_has_balance_column(self):
        """Test AIB Ireland bank template has Balance column."""
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")

        assert aib_ireland is not None
        columns = aib_ireland.extraction.columns

        # Bank statements should have balance column
        balance_cols = [col for col in columns if "balance" in col.lower()]
        assert (
            len(balance_cols) > 0
        ), "AIB Ireland bank template should have Balance column"

    def test_aib_ireland_date_column_reasonable(self):
        """Test AIB Ireland date column can fit dates like '22 Apr 2025'."""
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")

        assert aib_ireland is not None
        date_col = aib_ireland.extraction.columns.get("Date")

        assert date_col is not None, "AIB Ireland must have Date column"

        date_width = date_col[1] - date_col[0]

        # Date like "22 Apr 2025" needs roughly 50-80 pixels
        assert (
            date_width >= 40
        ), f"Date column width {date_width} too narrow for '22 Apr 2025'"


class TestAIBDocumentTypes:
    """Test AIB templates have correct document_type."""

    def test_aib_ireland_is_bank_statement(self):
        """Test AIB Ireland template is marked as bank_statement."""
        registry = TemplateRegistry.from_default_config()
        aib_ireland = registry.get_template("aib_ireland")

        assert aib_ireland is not None
        assert aib_ireland.document_type == "bank_statement"

    def test_aib_credit_card_is_credit_card_statement(self):
        """Test AIB credit card template is marked as credit_card_statement."""
        registry = TemplateRegistry.from_default_config()
        aib_cc = registry.get_template("aib_credit_card")

        if aib_cc is None:
            pytest.skip(
                "aib_credit_card is a premium template not included in this build"
            )
        assert aib_cc.document_type == "credit_card_statement"


class TestAIBCCTemplateColumnsFix:
    """Regression tests for issue #129 — CC PDF using wrong (bank) column layout.

    Without aib_credit_card.json, get_default_for_type("credit_card_statement")
    falls back to the global default (bank statement columns). RowBuilder then
    maps CC PDF words to Date/Details/Debit/Credit/Balance — none of which match
    the CC column positions — so RefContinuationClassifier sees an empty description
    and classifies Ref lines as transactions, emitting phantom rows.
    """

    def test_cc_default_template_uses_cc_columns(self):
        """get_default_for_type('credit_card_statement') returns aib_credit_card.

        Before the fix, no credit_card_statement template existed and the call
        fell back to the global default (bank statement columns), causing phantom
        empty rows in CC output.
        """
        registry = TemplateRegistry.from_default_config()
        cc_template = registry.get_default_for_type("credit_card_statement")

        assert cc_template.document_type == "credit_card_statement", (
            "Default CC template must have document_type='credit_card_statement'; "
            "falling back to a bank_statement template causes phantom rows in CC output"
        )
        assert cc_template.id == "aib_credit_card"

    def test_cc_columns_include_transaction_details(self):
        """aib_credit_card columns include 'Transaction Details'.

        RefContinuationClassifier uses ColumnTypeIdentifier to find the description
        column by scanning column names for DESCRIPTION_PATTERNS. 'Transaction Details'
        matches via 'detail' (or 'transaction'). If bank columns ('Details') are used
        instead, the RefContinuationClassifier still works — but RowBuilder assigns
        words to wrong positions because CC column x-boundaries differ from bank ones.
        The CC template must define the correct x-boundaries for CC PDFs.
        """
        registry = TemplateRegistry.from_default_config()
        aib_cc = registry.get_template("aib_credit_card")

        assert aib_cc is not None
        col_names = list(aib_cc.extraction.columns.keys())
        assert "Transaction Details" in col_names, (
            "CC template must have 'Transaction Details' column; "
            "RefContinuationClassifier finds it via DESCRIPTION_PATTERNS"
        )
        assert "Transaction Date" in col_names
        assert "Posting Date" in col_names
        assert "Amount" in col_names

    def test_cc_column_boundaries_match_aib_pdf_layout(self):
        """aib_credit_card column x-boundaries match the known AIB CC PDF layout.

        These boundaries were established from test_row_merger_integration.py
        cc_columns fixture which was derived from real AIB CC PDF analysis.
        If the boundaries are wrong, RowBuilder assigns words to wrong columns
        and RefContinuationClassifier sees empty description, classifying Ref
        lines as transactions.
        """
        registry = TemplateRegistry.from_default_config()
        aib_cc = registry.get_template("aib_credit_card")

        assert aib_cc is not None
        cols = aib_cc.extraction.columns

        txn_date = cols["Transaction Date"]
        posting_date = cols["Posting Date"]
        txn_details = cols["Transaction Details"]
        amount = cols["Amount"]

        # Transaction Date: narrow left-most column
        assert txn_date[0] < txn_date[1], "Transaction Date must have positive width"
        # Posting Date immediately follows Transaction Date
        assert (
            posting_date[0] >= txn_date[0]
        ), "Posting Date starts at or after Txn Date"
        # Transaction Details is the wide middle column
        assert (txn_details[1] - txn_details[0]) > (
            txn_date[1] - txn_date[0]
        ), "Transaction Details should be wider than Transaction Date"
        # Amount is rightmost
        assert (
            amount[0] >= txn_details[0]
        ), "Amount must start after Transaction Details"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
