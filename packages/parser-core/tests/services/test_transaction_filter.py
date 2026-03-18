"""Tests for transaction filter service."""

from __future__ import annotations

import unittest

from bankstatements_core.services.transaction_filter import TransactionFilterService


class TestTransactionFilterService(unittest.TestCase):
    """Test TransactionFilterService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.column_names = ["Date", "Details", "Debit", "Credit"]
        self.service = TransactionFilterService(self.column_names)

    def test_filter_empty_rows(self):
        """Test filtering of empty rows."""
        rows = [
            {"Date": "01/01/23", "Details": "Test", "Debit": "100"},
            {"Date": "", "Details": "", "Debit": ""},  # Empty
            {"Date": "02/01/23", "Details": "Test2", "Debit": "200"},
            {"Date": "   ", "Details": "   ", "Debit": "   "},  # Whitespace only
        ]

        filtered = self.service.filter_empty_rows(rows)

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["Details"], "Test")
        self.assertEqual(filtered[1]["Details"], "Test2")

    def test_filter_empty_rows_with_filename(self):
        """Test that Filename field is ignored in empty check."""
        rows = [
            {
                "Date": "",
                "Details": "",
                "Filename": "test.pdf",
            },  # Has filename but no data
            {"Date": "01/01/23", "Details": "Test", "Filename": "test.pdf"},
        ]

        filtered = self.service.filter_empty_rows(rows)

        # First row should be filtered despite having Filename
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Details"], "Test")

    def test_filter_header_rows(self):
        """Test filtering of header rows."""
        rows = [
            {
                "Date": "Date",
                "Details": "Details",
                "Debit": "Debit",
            },  # Perfect header match
            {"Date": "01/01/23", "Details": "Test", "Debit": "100"},
            {
                "Date": "DATE",
                "Details": "DETAILS",
                "Debit": "DEBIT",
                "Credit": "CREDIT",
            },  # Header in uppercase
        ]

        filtered = self.service.filter_header_rows(rows)

        # Should filter both header rows
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Details"], "Test")

    def test_filter_header_rows_partial_match(self):
        """Test header filtering with partial column name matches."""
        rows = [
            {"Date": "01/01/23", "Details": "Some details here", "Debit": "100"},
            {"Date": "DATE", "Details": "DETAILS", "Debit": "DEBIT"},  # 100% match
        ]

        filtered = self.service.filter_header_rows(rows)

        # Should filter the header row
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Debit"], "100")

    def test_filter_invalid_dates(self):
        """Test filtering of rows with invalid dates."""
        rows = [
            {"Date": "01/01/23", "Details": "Test"},
            {"Date": "Product", "Details": "Not a date"},  # Invalid
            {"Date": "11 Aug", "Details": "Valid partial date"},
            {"Date": "", "Details": "Empty date"},  # Invalid
            {"Date": "Total", "Details": "Not a date"},  # Invalid
        ]

        filtered = self.service.filter_invalid_dates(rows)

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["Date"], "01/01/23")
        self.assertEqual(filtered[1]["Date"], "11 Aug")

    def test_is_parseable_date_valid_formats(self):
        """Test date validation with valid formats."""
        valid_dates = [
            "01/01/23",
            "11 Aug",
            "2023-01-15",
            "15/06/2023",
            "11 August",
            "20230115",  # All digits
        ]

        for date_str in valid_dates:
            self.assertTrue(
                self.service._is_parseable_date(date_str),
                f"Expected {date_str} to be valid",
            )

    def test_is_parseable_date_invalid_formats(self):
        """Test date validation rejects non-dates."""
        invalid_dates = [
            "Product",
            "Total",
            "Account",
            "Balance",
            "Transaction Details",
            "Statement",
            "Description",
            "Debit Amount",
            "Credit",
            "This is a very long description that is clearly not a date",
        ]

        for date_str in invalid_dates:
            self.assertFalse(
                self.service._is_parseable_date(date_str),
                f"Expected {date_str} to be invalid",
            )

    def test_apply_all_filters(self):
        """Test applying all filters in sequence."""
        rows = [
            {"Date": "Date", "Details": "Details", "Debit": "Debit"},  # Header
            {"Date": "", "Details": "", "Debit": ""},  # Empty
            {"Date": "01/01/23", "Details": "Test1", "Debit": "100"},
            {
                "Date": "Product",
                "Details": "Not a date",
                "Debit": "200",
            },  # Invalid date
            {"Date": "02/01/23", "Details": "Test2", "Debit": "300"},
            {"Date": "   ", "Details": "   ", "Debit": "   "},  # Whitespace
        ]

        filtered = self.service.apply_all_filters(rows)

        # Should keep only the 2 valid transactions
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["Details"], "Test1")
        self.assertEqual(filtered[1]["Details"], "Test2")

    def test_filter_empty_rows_with_non_string_value(self):
        """Test empty row filtering with non-string values."""
        rows = [
            {"Date": "01/01/23", "Details": "Test", "Amount": 100},  # Non-string number
            {"Date": "", "Details": "", "Amount": 0},  # Zero is falsy
            {
                "Date": "02/01/23",
                "Details": "Test2",
                "Amount": None,
            },  # None with other data
        ]

        filtered = self.service.filter_empty_rows(rows)

        # First and third should be kept (they have non-empty data)
        self.assertEqual(len(filtered), 2)

    def test_header_row_less_than_50_percent_match(self):
        """Test that rows with less than 50% column name matches aren't filtered."""
        rows = [
            {"Date": "01/01/23", "Details": "Date of Transaction", "Debit": "100"},
            # "Date of Transaction" contains "Date" but other fields don't match
        ]

        filtered = self.service.filter_header_rows(rows)

        # Should keep the row (not enough matches)
        self.assertEqual(len(filtered), 1)

    def test_header_row_requires_minimum_2_matches(self):
        """Test that header detection requires at least 2 field matches."""
        rows = [
            {"Date": "Date", "Details": "Some text", "Debit": "100", "Credit": "200"},
            # Only 1 match (Date), should not be filtered
        ]

        filtered = self.service.filter_header_rows(rows)

        # Should keep the row (not enough matches)
        self.assertEqual(len(filtered), 1)


if __name__ == "__main__":
    unittest.main()
