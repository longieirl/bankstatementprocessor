"""Tests for RowPostProcessor and extract_filename_date."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bankstatements_core.extraction.row_post_processor import (
    RowPostProcessor,
    extract_filename_date,
)

TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


def _make_classifier(row_type="transaction"):
    c = Mock()
    c.classify.return_value = row_type
    return c


def _make_processor(
    filename="statement.pdf", filename_date="", template=None, row_type="transaction"
):
    return RowPostProcessor(
        columns=TEST_COLUMNS,
        row_classifier=_make_classifier(row_type),
        template=template,
        filename_date=filename_date,
        filename=filename,
    )


class TestExtractFilenameDate:
    def test_valid_date_extracted(self):
        assert extract_filename_date("statement_20250202.pdf") == "02 Feb 2025"

    def test_no_date_returns_empty(self):
        assert extract_filename_date("statement.pdf") == ""

    def test_invalid_date_returns_empty(self):
        assert extract_filename_date("file_99991399.pdf") == ""

    def test_date_at_start(self):
        assert extract_filename_date("20240101_bank.pdf") == "01 Jan 2024"


class TestRowPostProcessor:
    def test_date_propagated_from_row(self):
        proc = _make_processor()
        row = {
            "Date": "01/01/2024",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "")
        assert updated == "01/01/2024"

    def test_current_date_propagated_to_dateless_row(self):
        proc = _make_processor()
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "01/01/2024")
        assert row["Date"] == "01/01/2024"
        assert updated == "01/01/2024"

    def test_filename_date_used_when_no_current_date(self):
        proc = _make_processor(filename_date="15 Mar 2025")
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "")
        assert row["Date"] == "15 Mar 2025"
        assert updated == "15 Mar 2025"

    def test_filename_tagged(self):
        proc = _make_processor(filename="my_statement.pdf")
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["Filename"] == "my_statement.pdf"

    def test_default_document_type_when_no_template(self):
        proc = _make_processor(template=None)
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "bank_statement"
        assert row["template_id"] is None

    def test_template_document_type_and_id(self):
        template = Mock()
        template.document_type = "current_account"
        template.id = "aib_current"
        proc = _make_processor(template=template)
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "current_account"
        assert row["template_id"] == "aib_current"

    def test_non_transaction_row_not_modified(self):
        proc = _make_processor(row_type="metadata")
        row = {
            "Date": "",
            "Details": "Opening Balance",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "05/01/2024")
        assert "Filename" not in row
        assert updated == "05/01/2024"

    def test_current_date_not_overwritten_by_filename_date(self):
        """filename_date should only be used when current_date is also empty."""
        proc = _make_processor(filename_date="01 Jan 2025")
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "15/03/2025")
        assert row["Date"] == "15/03/2025"  # current_date wins over filename_date
        assert updated == "15/03/2025"
