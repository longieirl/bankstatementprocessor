"""Tests for column analysis service."""

import pandas as pd

from bankstatements_core.services.column_analysis import ColumnAnalysisService


class TestColumnAnalysisService:
    """Tests for ColumnAnalysisService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ColumnAnalysisService()

    def test_parse_totals_columns_with_single_column(self):
        """Test parsing single column."""
        result = self.service.parse_totals_columns("debit")
        assert result == ["debit"]

    def test_parse_totals_columns_with_multiple_columns(self):
        """Test parsing multiple columns."""
        result = self.service.parse_totals_columns("debit,credit,balance")
        assert result == ["debit", "credit", "balance"]

    def test_parse_totals_columns_with_whitespace(self):
        """Test parsing with whitespace."""
        result = self.service.parse_totals_columns("  Debit , Credit  , Balance  ")
        assert result == ["debit", "credit", "balance"]

    def test_parse_totals_columns_with_empty_string(self):
        """Test parsing empty string."""
        result = self.service.parse_totals_columns("")
        assert result == []

    def test_parse_totals_columns_with_none(self):
        """Test parsing None."""
        result = self.service.parse_totals_columns(None)
        assert result == []

    def test_parse_totals_columns_lowercases_names(self):
        """Test that column names are lowercased."""
        result = self.service.parse_totals_columns("DEBIT,Credit,BaLaNcE")
        assert result == ["debit", "credit", "balance"]

    def test_parse_totals_columns_filters_empty_patterns(self):
        """Test that empty patterns are filtered out."""
        result = self.service.parse_totals_columns("debit,,credit,  ,balance")
        assert result == ["debit", "credit", "balance"]

    def test_find_matching_columns(self):
        """Test finding columns matching patterns."""
        df = pd.DataFrame(
            {
                "Date": ["01/01/23"],
                "Details": ["Test"],
                "Debit €": ["50.00"],
                "Credit €": ["0.00"],
                "Balance €": ["100.00"],
            }
        )

        patterns = ["debit", "credit"]
        matching = self.service.find_matching_columns(df, patterns)

        assert len(matching) == 2
        assert "Debit €" in matching
        assert "Credit €" in matching
        assert "Balance €" not in matching

    def test_find_matching_columns_case_insensitive(self):
        """Test pattern matching is case-insensitive."""
        df = pd.DataFrame(
            {
                "DEBIT €": ["50.00"],
                "debit amount": ["25.00"],
            }
        )

        patterns = ["debit"]
        matching = self.service.find_matching_columns(df, patterns)

        assert len(matching) == 2
        assert "DEBIT €" in matching
        assert "debit amount" in matching

    def test_find_matching_columns_no_match(self):
        """Test when no columns match patterns."""
        df = pd.DataFrame(
            {
                "Date": ["01/01/23"],
                "Details": ["Test"],
            }
        )

        patterns = ["debit", "credit"]
        matching = self.service.find_matching_columns(df, patterns)

        assert len(matching) == 0

    def test_find_matching_columns_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        patterns = ["debit"]
        matching = self.service.find_matching_columns(df, patterns)

        assert len(matching) == 0
