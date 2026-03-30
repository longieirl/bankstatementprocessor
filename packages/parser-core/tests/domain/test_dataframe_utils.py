"""Tests for DataFrame analysis utilities."""

from __future__ import annotations

import pandas as pd

from bankstatements_core.domain.dataframe_utils import (
    calculate_column_sum,
    is_date_column,
)


class TestCalculateColumnSum:
    """Test the calculate_column_sum function."""

    def test_sum_basic_floats(self):
        """Test summing basic float strings."""
        df = pd.DataFrame({"Amount": ["100.50", "200.00", "50.25"]})
        assert calculate_column_sum(df, "Amount") == 350.75

    def test_sum_with_currency_symbols(self):
        """Test summing values with currency symbols."""
        df = pd.DataFrame({"Amount": ["€100.50", "$200", "£50.25"]})
        result = calculate_column_sum(df, "Amount")
        assert abs(result - 350.75) < 0.01

    def test_sum_with_none_values(self):
        """Test summing with None values."""
        df = pd.DataFrame({"Amount": ["100.50", None, "50.25"]})
        assert calculate_column_sum(df, "Amount") == 150.75

    def test_sum_with_nan_values(self):
        """Test summing with NaN values."""
        df = pd.DataFrame({"Amount": ["100.50", pd.NA, "50.25"]})
        result = calculate_column_sum(df, "Amount")
        assert abs(result - 150.75) < 0.01

    def test_sum_empty_dataframe(self):
        """Test summing empty DataFrame."""
        df = pd.DataFrame({"Amount": []})
        assert calculate_column_sum(df, "Amount") == 0.0

    def test_sum_all_empty_strings(self):
        """Test summing all empty strings."""
        df = pd.DataFrame({"Amount": ["", "", ""]})
        assert calculate_column_sum(df, "Amount") == 0.0

    def test_sum_negative_values(self):
        """Test summing negative values."""
        df = pd.DataFrame({"Amount": ["100.50", "-50.00", "25.00"]})
        assert calculate_column_sum(df, "Amount") == 75.5


class TestIsDateColumn:
    """Test the is_date_column function."""

    def test_date_column_lowercase(self):
        """Test 'date' in lowercase."""
        assert is_date_column("date") is True

    def test_date_column_uppercase(self):
        """Test 'DATE' in uppercase."""
        assert is_date_column("DATE") is True

    def test_date_column_mixed_case(self):
        """Test 'Date' in mixed case."""
        assert is_date_column("Date") is True

    def test_non_date_columns(self):
        """Test non-date column names."""
        assert is_date_column("Amount") is False
        assert is_date_column("Details") is False
        assert is_date_column("Balance") is False
        assert is_date_column("Dated") is False
        assert is_date_column("Date_Time") is False
        assert is_date_column("") is False
