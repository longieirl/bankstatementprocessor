"""Tests for document type enrichment in PDF extraction.

This module tests that document_type is correctly added to extracted transactions
based on the template's document_type field.
"""

from __future__ import annotations

import pytest

from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor
from bankstatements_core.extraction.row_post_processor import RowPostProcessor
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)


@pytest.fixture
def basic_columns():
    """Standard column definitions."""
    return {
        "Date": (26, 78),
        "Details": (78, 255),
        "Debit €": (255, 313),
        "Credit €": (313, 369),
        "Balance €": (369, 434),
    }


@pytest.fixture
def bank_statement_template():
    """Create a bank statement template."""
    return BankTemplate(
        id="test_bank",
        name="test_bank_statement",
        enabled=True,
        document_type="bank_statement",
        detection=TemplateDetectionConfig(
            filename_patterns=["*bank*.pdf"],
            header_keywords=["Bank Statement"],
            column_headers=["Date", "Details", "Debit", "Credit", "Balance"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={
                "Date": (26, 78),
                "Details": (78, 255),
                "Debit €": (255, 313),
                "Credit €": (313, 369),
                "Balance €": (369, 434),
            },
        ),
    )


@pytest.fixture
def credit_card_template():
    """Create a credit card statement template."""
    return BankTemplate(
        id="test_card",
        name="test_credit_card",
        enabled=True,
        document_type="credit_card_statement",
        detection=TemplateDetectionConfig(
            filename_patterns=["*card*.pdf"],
            header_keywords=["Credit Card Statement"],
            column_headers=["Date", "Details", "Amount"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={
                "Date": (26, 78),
                "Details": (78, 255),
                "Debit €": (255, 313),
                "Credit €": (313, 369),
                "Balance €": (369, 434),
            },
        ),
    )


@pytest.fixture
def loan_statement_template():
    """Create a loan statement template."""
    return BankTemplate(
        id="test_loan",
        name="test_loan",
        enabled=True,
        document_type="loan_statement",
        detection=TemplateDetectionConfig(
            filename_patterns=["*loan*.pdf"],
            header_keywords=["Loan Statement"],
            column_headers=["Date", "Details", "Payment"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={
                "Date": (26, 78),
                "Details": (78, 255),
                "Debit €": (255, 313),
                "Credit €": (313, 369),
                "Balance €": (369, 434),
            },
        ),
    )


class TestDocumentTypeEnrichment:
    """Test document_type enrichment in PDF extraction."""

    def test_bank_statement_document_type(self, bank_statement_template, basic_columns):
        """Test that bank statement template adds correct document_type."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=bank_statement_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=bank_statement_template,
            filename_date="",
            filename="test_bank.pdf",
        )
        row = {"Date": "01/12/2023", "Details": "Purchase", "Debit €": "100.00"}
        proc.process(row, "")
        assert "document_type" in row
        assert row["document_type"] == "bank_statement"
        assert row["Filename"] == "test_bank.pdf"

    def test_credit_card_document_type(self, credit_card_template, basic_columns):
        """Test that credit card template adds correct document_type."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=credit_card_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=credit_card_template,
            filename_date="",
            filename="test_card.pdf",
        )
        row = {"Date": "02/12/2023", "Details": "Card Purchase", "Debit €": "50.00"}
        proc.process(row, "")
        assert "document_type" in row
        assert row["document_type"] == "credit_card_statement"
        assert row["Filename"] == "test_card.pdf"

    def test_loan_statement_document_type(self, loan_statement_template, basic_columns):
        """Test that loan statement template adds correct document_type."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=loan_statement_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=loan_statement_template,
            filename_date="",
            filename="test_loan.pdf",
        )
        row = {"Date": "03/12/2023", "Details": "Loan Payment", "Debit €": "200.00"}
        proc.process(row, "")
        assert "document_type" in row
        assert row["document_type"] == "loan_statement"
        assert row["Filename"] == "test_loan.pdf"

    def test_no_template_defaults_to_bank_statement(self, basic_columns):
        """Test that absence of template defaults to 'bank_statement'."""
        extractor = PDFTableExtractor(columns=basic_columns, template=None)
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=None,
            filename_date="",
            filename="test_unknown.pdf",
        )
        row = {"Date": "04/12/2023", "Details": "Unknown", "Debit €": "75.00"}
        proc.process(row, "")
        assert "document_type" in row
        assert row["document_type"] == "bank_statement"

    def test_document_type_preserved_with_filename(
        self, credit_card_template, basic_columns
    ):
        """Test that document_type is added alongside Filename."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=credit_card_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=credit_card_template,
            filename_date="",
            filename="test_card.pdf",
        )
        row = {"Date": "05/12/2023", "Details": "Purchase", "Debit €": "25.00"}
        proc.process(row, "")
        assert "Filename" in row
        assert "document_type" in row
        assert row["Filename"] == "test_card.pdf"
        assert row["document_type"] == "credit_card_statement"


class TestDocumentTypeIntegration:
    """Integration tests for document type in processing."""

    def test_multiple_rows_same_template(self, credit_card_template, basic_columns):
        """Test that multiple rows from same template have same document_type."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=credit_card_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=credit_card_template,
            filename_date="",
            filename="card.pdf",
        )
        rows = [
            {"Date": "01/12/2023", "Details": "Purchase 1", "Debit €": "100.00"},
            {"Date": "02/12/2023", "Details": "Purchase 2", "Debit €": "50.00"},
            {"Date": "03/12/2023", "Details": "Purchase 3", "Debit €": "75.00"},
        ]
        for row in rows:
            proc.process(row, "")
        assert all(row["document_type"] == "credit_card_statement" for row in rows)

    def test_document_type_field_is_string(
        self, bank_statement_template, basic_columns
    ):
        """Test that document_type field is always a string."""
        extractor = PDFTableExtractor(
            columns=basic_columns, template=bank_statement_template
        )
        proc = RowPostProcessor(
            columns=basic_columns,
            row_classifier=extractor._row_classifier,
            template=bank_statement_template,
            filename_date="",
            filename="test.pdf",
        )
        row = {"Date": "01/12/2023", "Details": "Test", "Debit €": "100.00"}
        proc.process(row, "")
        assert isinstance(row.get("document_type"), str)
        assert row["document_type"] in [
            "bank_statement",
            "credit_card_statement",
            "loan_statement",
        ]
