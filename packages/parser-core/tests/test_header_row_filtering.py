"""Tests for header row filtering in processor."""

from __future__ import annotations

from pathlib import Path

import pytest

from bankstatements_core.config.processor_config import ExtractionConfig, ProcessorConfig
from bankstatements_core.processor import BankStatementProcessor


def create_test_processor(**kwargs):
    """Helper to create processor with test configuration."""
    input_dir = kwargs.pop("input_dir", Path("input"))
    output_dir = kwargs.pop("output_dir", Path("output"))
    columns = kwargs.pop("columns", None)

    extraction_config = ExtractionConfig(columns=columns)
    config = ProcessorConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        extraction=extraction_config,
    )
    return BankStatementProcessor(config=config)


class TestHeaderRowFiltering:
    """Test that header rows are never written to output files."""

    def test_is_header_row_exact_match(self):
        """Test that rows with values matching column names are detected as headers."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
                "Balance €": (300, 350),
            },
        )

        # Header row where values match column names
        header_row = {
            "Date": "Date",
            "Details": "Details",
            "Debit €": "Debit €",
            "Credit €": "Credit €",
            "Balance €": "Balance €",
            "Filename": "test.pdf",
        }

        assert processor._is_header_row(header_row) is True

    def test_is_header_row_partial_match(self):
        """Test that rows with partial column name matches are detected as headers."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        # Header row with some empty fields but enough matches
        header_row = {
            "Date": "",
            "Details": "",
            "Debit €": "Debit €",
            "Credit €": "Credit €",
            "Filename": "test.pdf",
        }

        assert processor._is_header_row(header_row) is True

    def test_is_header_row_case_insensitive(self):
        """Test that header detection is case-insensitive."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        # Header row with different case
        header_row = {
            "Date": "date",
            "Details": "DETAILS",
            "Debit €": "debit €",
            "Credit €": "CREDIT €",
            "Filename": "test.pdf",
        }

        assert processor._is_header_row(header_row) is True

    def test_is_header_row_transaction_row(self):
        """Test that actual transaction rows are not detected as headers."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
                "Balance €": (300, 350),
            },
        )

        # Actual transaction row
        transaction_row = {
            "Date": "01 Jan 2025",
            "Details": "Purchase at store",
            "Debit €": "50.00",
            "Credit €": "",
            "Balance €": "1000.00",
            "Filename": "test.pdf",
        }

        assert processor._is_header_row(transaction_row) is False

    def test_is_header_row_mixed_content(self):
        """Test that rows with mixed transaction/header content are handled correctly."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        # Row with one header value and one transaction value (should not be detected as header)
        mixed_row = {
            "Date": "01 Jan",
            "Details": "Transaction",
            "Debit €": "Debit €",  # Header value
            "Credit €": "",
            "Filename": "test.pdf",
        }

        # Only 1 out of 3 checked fields match (33%), so not a header
        assert processor._is_header_row(mixed_row) is False

    def test_filter_header_rows_removes_headers(self):
        """Test that filter_header_rows removes all header rows."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        rows = [
            {
                "Date": "Date",
                "Details": "Details",
                "Debit €": "Debit €",
                "Credit €": "Credit €",
                "Filename": "test.pdf",
            },
            {
                "Date": "01 Jan",
                "Details": "Transaction",
                "Debit €": "50.00",
                "Credit €": "",
                "Filename": "test.pdf",
            },
            {
                "Date": "",
                "Details": "",
                "Debit €": "Debit €",
                "Credit €": "Credit €",
                "Filename": "test.pdf",
            },
        ]

        filtered = processor._filter_header_rows(rows)

        # Should only keep the transaction row
        assert len(filtered) == 1
        assert filtered[0]["Details"] == "Transaction"

    def test_filter_header_rows_keeps_transactions(self):
        """Test that filter_header_rows keeps all valid transactions."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        rows = [
            {
                "Date": "01 Jan",
                "Details": "Purchase",
                "Debit €": "50.00",
                "Credit €": "",
                "Filename": "test.pdf",
            },
            {
                "Date": "02 Jan",
                "Details": "Deposit",
                "Debit €": "",
                "Credit €": "100.00",
                "Filename": "test.pdf",
            },
        ]

        filtered = processor._filter_header_rows(rows)

        # Should keep all transactions
        assert len(filtered) == 2

    def test_filter_header_rows_empty_list(self):
        """Test filtering an empty list."""
        processor = create_test_processor(
            columns={"Date": (0, 100)},
        )

        filtered = processor._filter_header_rows([])

        assert filtered == []

    def test_header_row_with_currency_symbols(self):
        """Test header rows with currency symbols are detected."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
                "Balance €": (300, 350),
            },
        )

        # Header row from actual duplicate (from user's example)
        header_row = {
            "Date": "",
            "Details": "",
            "Debit €": "Debit €",
            "Credit €": "Credit €",
            "Balance €": "Balance €",
            "Filename": "Statement JL CA 202502.pdf",
        }

        assert processor._is_header_row(header_row) is True

    def test_combined_empty_and_header_filtering(self):
        """Test that both empty rows and header rows are filtered together."""
        processor = create_test_processor(
            columns={
                "Date": (0, 100),
                "Details": (100, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            },
        )

        rows = [
            # Empty row
            {
                "Date": "",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Filename": "test.pdf",
            },
            # Header row
            {
                "Date": "Date",
                "Details": "Details",
                "Debit €": "Debit €",
                "Credit €": "Credit €",
                "Filename": "test.pdf",
            },
            # Valid transaction
            {
                "Date": "01 Jan",
                "Details": "Purchase",
                "Debit €": "50.00",
                "Credit €": "",
                "Filename": "test.pdf",
            },
            # Another header row
            {
                "Date": "",
                "Details": "",
                "Debit €": "Debit €",
                "Credit €": "Credit €",
                "Filename": "test.pdf",
            },
        ]

        # Apply both filters as done in the processor
        non_empty = processor._filter_empty_rows(rows)
        non_header = processor._filter_header_rows(non_empty)

        # Should only keep the valid transaction
        assert len(non_header) == 1
        assert non_header[0]["Details"] == "Purchase"
