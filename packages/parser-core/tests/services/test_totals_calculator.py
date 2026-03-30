"""Tests for totals calculator service."""

from __future__ import annotations

import pandas as pd

from bankstatements_core.services.totals_calculator import ColumnTotalsService


class TestColumnTotalsService:
    """Tests for ColumnTotalsService."""

    def test_initialization(self):
        """Test service initialization."""
        totals_columns = ["debit", "credit"]
        service = ColumnTotalsService(totals_columns)
        assert service.totals_columns == totals_columns

    def test_calculate_single_column(self):
        """Test calculating totals for single column."""
        service = ColumnTotalsService(["debit"])
        df = pd.DataFrame(
            {
                "Date": ["01/01/23", "02/01/23"],
                "Debit €": ["50.00", "30.00"],
                "Credit €": ["", ""],
            }
        )

        totals = service.calculate(df)

        assert "Debit €" in totals
        assert totals["Debit €"] == 80.00
        assert "Credit €" not in totals  # Not in totals_columns pattern

    def test_calculate_multiple_columns(self):
        """Test calculating totals for multiple columns."""
        service = ColumnTotalsService(["debit", "credit"])
        df = pd.DataFrame(
            {
                "Date": ["01/01/23", "02/01/23"],
                "Debit €": ["50.00", "30.00"],
                "Credit €": ["100.00", "25.00"],
            }
        )

        totals = service.calculate(df)

        assert totals["Debit €"] == 80.00
        assert totals["Credit €"] == 125.00

    def test_calculate_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        service = ColumnTotalsService(["DEBIT", "CrEdIt"])
        df = pd.DataFrame(
            {
                "debit €": ["50.00", "30.00"],
                "Credit $": ["100.00", "25.00"],
            }
        )

        totals = service.calculate(df)

        assert "debit €" in totals
        assert "Credit $" in totals

    def test_calculate_empty_dataframe(self):
        """Test calculating totals for empty DataFrame."""
        service = ColumnTotalsService(["debit", "credit"])
        df = pd.DataFrame(columns=["Date", "Debit €", "Credit €"])

        totals = service.calculate(df)

        # Empty dataframe should still calculate (likely 0.0 or handle gracefully)
        assert isinstance(totals, dict)

    def test_calculate_with_invalid_column_data(self):
        """Test handling invalid column data."""
        service = ColumnTotalsService(["debit"])
        df = pd.DataFrame(
            {
                "Debit €": ["invalid", "50.00"],
                "Credit €": ["100.00", "25.00"],
            }
        )

        totals = service.calculate(df)

        # Should handle errors gracefully and return 0.0 or valid sum
        assert "Debit €" in totals
        assert isinstance(totals["Debit €"], float)

    def test_format_totals_row_with_totals(self):
        """Test formatting totals row with values."""
        service = ColumnTotalsService(["debit", "credit"])
        totals = {"Debit €": 80.50, "Credit €": 125.75}
        all_columns = ["Date", "Details", "Debit €", "Credit €", "Balance"]

        row = service.format_totals_row(totals, all_columns)

        assert len(row) == 5
        assert row[0] == "TOTAL"  # Date column
        assert row[1] == ""  # Details column
        assert row[2] == "80.50"  # Debit € column
        assert row[3] == "125.75"  # Credit € column
        assert row[4] == ""  # Balance column (not in totals)

    def test_format_totals_row_no_date_column(self):
        """Test formatting when no date column exists."""
        service = ColumnTotalsService(["amount"])
        totals = {"Amount": 100.00}
        all_columns = ["ID", "Amount", "Description"]

        row = service.format_totals_row(totals, all_columns)

        assert len(row) == 3
        assert row[0] == ""  # ID column (not date, not in totals)
        assert row[1] == "100.00"  # Amount column
        assert row[2] == ""  # Description column

    def test_format_totals_row_empty_totals(self):
        """Test formatting with no totals."""
        service = ColumnTotalsService(["debit"])
        totals = {}
        all_columns = ["Date", "Debit €", "Credit €"]

        row = service.format_totals_row(totals, all_columns)

        assert len(row) == 3
        assert row[0] == "TOTAL"  # Date column
        assert row[1] == ""  # Debit € (no total)
        assert row[2] == ""  # Credit € (no total)

    def test_format_totals_row_rounds_to_two_decimals(self):
        """Test that values are formatted with 2 decimal places."""
        service = ColumnTotalsService(["amount"])
        totals = {"Amount": 123.456789}
        all_columns = ["Date", "Amount"]

        row = service.format_totals_row(totals, all_columns)

        assert row[1] == "123.46"  # Rounded to 2 decimals

    def test_calculate_with_multiple_patterns(self):
        """Test calculating with multiple column patterns."""
        service = ColumnTotalsService(["debit", "balance", "fee"])
        df = pd.DataFrame(
            {
                "Debit €": ["50.00"],
                "Balance": ["1000.00"],
                "Fee $": ["5.00"],
                "Description": ["Test"],
            }
        )

        totals = service.calculate(df)

        assert len(totals) == 3
        assert "Debit €" in totals
        assert "Balance" in totals
        assert "Fee $" in totals
        assert "Description" not in totals

    def test_calculate_with_partial_pattern_match(self):
        """Test that partial matches work (pattern is substring)."""
        service = ColumnTotalsService(["deb"])  # Partial match
        df = pd.DataFrame(
            {
                "Debit €": ["50.00"],  # Contains "deb"
                "Credit €": ["100.00"],  # Does not contain "deb"
            }
        )

        totals = service.calculate(df)

        assert "Debit €" in totals
        assert "Credit €" not in totals

    def test_format_with_date_column_variations(self):
        """Test formatting with date column (only exact 'Date' gets TOTAL label)."""
        service = ColumnTotalsService(["amount"])
        totals = {"Amount": 50.00}
        all_columns = ["Date", "Transaction Date", "Amount"]

        row = service.format_totals_row(totals, all_columns)

        # Only exact "Date" column gets "TOTAL", others are empty
        assert row[0] == "TOTAL"
        assert row[1] == ""  # "Transaction Date" not recognized as date
        assert row[2] == "50.00"
