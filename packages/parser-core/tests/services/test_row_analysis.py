"""Tests for RowAnalysisService."""

import pytest

from bankstatements_core.services.row_analysis import RowAnalysisService


class TestRowAnalysisService:
    """Test suite for RowAnalysisService."""

    @pytest.fixture
    def service(self):
        """Create RowAnalysisService instance."""
        return RowAnalysisService()

    def test_looks_like_date_slash_format(self, service):
        """Test date detection with slash format."""
        assert service.looks_like_date("01/12/2023") is True
        assert service.looks_like_date("1/1/23") is True
        assert service.looks_like_date("31/12/2023") is True

    def test_looks_like_date_dash_format(self, service):
        """Test date detection with dash format."""
        assert service.looks_like_date("01-12-2023") is True
        assert service.looks_like_date("15-06-23") is True

    def test_looks_like_date_month_name(self, service):
        """Test date detection with month names."""
        assert service.looks_like_date("15 Jan 2023") is True
        assert service.looks_like_date("1 January 2023") is True
        assert service.looks_like_date("25 Dec 23") is True

    def test_looks_like_date_month_name_no_year(self, service):
        """Test date detection with month name but no year."""
        assert service.looks_like_date("15 Jan") is True
        assert service.looks_like_date("1 December") is True

    def test_looks_like_date_compact_format(self, service):
        """Test date detection with compact format (no spaces)."""
        assert service.looks_like_date("01JAN2023") is True
        assert service.looks_like_date("15DEC23") is True

    def test_looks_like_date_not_date(self, service):
        """Test that non-dates are correctly identified."""
        assert service.looks_like_date("Hello World") is False
        assert service.looks_like_date("12345") is False
        assert service.looks_like_date("Random text") is False
        assert service.looks_like_date("") is False
