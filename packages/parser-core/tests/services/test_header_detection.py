"""Tests for HeaderDetectionService."""

from __future__ import annotations

import pytest

from bankstatements_core.services.header_detection import HeaderDetectionService


class TestHeaderDetectionService:
    """Test suite for HeaderDetectionService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return HeaderDetectionService()

    @pytest.fixture
    def sample_columns(self):
        """Sample column definitions."""
        return {
            "Date": (50, 150),
            "Details": (160, 400),
            "Amount": (410, 500),
        }

    def test_calculate_header_area_explicit(self, service):
        """Test header area calculation with explicit value."""
        result = service.calculate_header_area(table_top_y=300, header_check_top_y=250)
        assert result == 250

    def test_calculate_header_area_auto(self, service):
        """Test header area calculation with auto-calculation."""
        result = service.calculate_header_area(table_top_y=300)
        assert result == 250  # 300 - 50 default offset

    def test_calculate_header_area_edge_case(self, service):
        """Test header area at page top."""
        result = service.calculate_header_area(table_top_y=30)
        assert result == 0  # max(0, 30 - 50) = 0

    def test_calculate_header_area_custom_offset(self, service):
        """Test header area with custom offset."""
        result = service.calculate_header_area(table_top_y=300, default_offset=100)
        assert result == 200  # 300 - 100

    def test_detect_headers_empty_words(self, service, sample_columns):
        """Test detection with empty word list."""
        result = service.detect_headers([], sample_columns)
        assert result is False

    def test_detect_headers_no_keywords(self, service, sample_columns):
        """Test detection with no header keywords."""
        words = [
            {"text": "foo", "top": 100},
            {"text": "bar", "top": 100},
            {"text": "baz", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns)
        assert result is False

    def test_detect_headers_with_keywords(self, service, sample_columns):
        """Test detection with header keywords present."""
        words = [
            {"text": "Date", "top": 100},
            {"text": "Details", "top": 100},
            {"text": "Amount", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is True

    def test_detect_headers_single_keyword(self, service, sample_columns):
        """Test detection with only one keyword (below threshold)."""
        words = [
            {"text": "Date", "top": 100},
            {"text": "foo", "top": 100},
            {"text": "bar", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is False

    def test_detect_headers_case_insensitive(self, service, sample_columns):
        """Test that keyword detection is case-insensitive."""
        words = [
            {"text": "DATE", "top": 100},
            {"text": "DETAILS", "top": 100},
            {"text": "AMOUNT", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is True

    def test_detect_headers_partial_match(self, service, sample_columns):
        """Test detection with partial keyword matches."""
        words = [
            {"text": "Transaction Date", "top": 100},
            {"text": "Description", "top": 100},
            {"text": "Debit Amount", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is True

    def test_detect_headers_multiple_rows(self, service, sample_columns):
        """Test detection across multiple rows."""
        words = [
            # Row 1 - no keywords
            {"text": "foo", "top": 50},
            {"text": "bar", "top": 50},
            # Row 2 - has keywords
            {"text": "Date", "top": 100},
            {"text": "Details", "top": 100},
            {"text": "Amount", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is True

    def test_detect_headers_beyond_max_rows(self, service, sample_columns):
        """Test that headers beyond max_rows are not detected."""
        words = []
        # Add 5 rows without keywords
        for i in range(5):
            words.extend(
                [
                    {"text": "foo", "top": i * 20},
                    {"text": "bar", "top": i * 20},
                ]
            )
        # Add 6th row with keywords (should be ignored)
        words.extend(
            [
                {"text": "Date", "top": 120},
                {"text": "Details", "top": 120},
                {"text": "Amount", "top": 120},
            ]
        )

        result = service.detect_headers(
            words, sample_columns, max_rows_to_check=5, min_keywords=2
        )
        assert result is False

    def test_detect_headers_custom_min_keywords(self, service, sample_columns):
        """Test detection with custom minimum keywords."""
        words = [
            {"text": "Date", "top": 100},
            {"text": "Details", "top": 100},
            {"text": "Amount", "top": 100},
        ]
        # Require 4 keywords (should fail)
        result = service.detect_headers(words, sample_columns, min_keywords=4)
        assert result is False

        # Require 1 keyword (should pass)
        result = service.detect_headers(words, sample_columns, min_keywords=1)
        assert result is True

    def test_group_words_by_y_coordinate(self, service):
        """Test word grouping by Y coordinate."""
        words = [
            {"text": "A", "top": 100.0},
            {"text": "B", "top": 100.5},  # Close to 100, should group
            {"text": "C", "top": 105.0},
            {"text": "D", "top": 105.2},  # Close to 105, should group
        ]
        grouped = service._group_words_by_y_coordinate(words)

        # Should have 2 groups (rounded to 100 and 105)
        assert len(grouped) == 2
        assert 100.0 in grouped
        assert 105.0 in grouped
        assert len(grouped[100.0]) == 2  # A and B
        assert len(grouped[105.0]) == 2  # C and D

    def test_header_keywords_coverage(self, service):
        """Test that service has comprehensive header keywords."""
        # Verify key banking terms are included
        assert "date" in service.HEADER_KEYWORDS
        assert "details" in service.HEADER_KEYWORDS
        assert "amount" in service.HEADER_KEYWORDS
        assert "debit" in service.HEADER_KEYWORDS
        assert "credit" in service.HEADER_KEYWORDS
        assert "balance" in service.HEADER_KEYWORDS

        # Verify variations are included
        assert "transaction date" in service.HEADER_KEYWORDS
        assert "posting date" in service.HEADER_KEYWORDS
        assert "running balance" in service.HEADER_KEYWORDS

    def test_detect_headers_with_banking_variations(self, service, sample_columns):
        """Test detection with banking-specific header variations."""
        words = [
            {"text": "Trans Date", "top": 100},
            {"text": "Running Balance", "top": 100},
            {"text": "Lodgement", "top": 100},
        ]
        result = service.detect_headers(words, sample_columns, min_keywords=2)
        assert result is True


class TestHeaderDetectionIntegration:
    """Integration tests for HeaderDetectionService."""

    def test_detect_headers_realistic_bank_statement(self):
        """Test with realistic bank statement header."""
        service = HeaderDetectionService()

        # Realistic bank statement header words
        words = [
            {"text": "Transaction", "top": 95},
            {"text": "Date", "top": 95},
            {"text": "Value", "top": 95},
            {"text": "Date", "top": 95},
            {"text": "Details", "top": 95},
            {"text": "Debit", "top": 95},
            {"text": "Credit", "top": 95},
            {"text": "Balance", "top": 95},
        ]

        columns = {
            "Transaction Date": (50, 120),
            "Value Date": (130, 200),
            "Details": (210, 400),
            "Debit": (410, 480),
            "Credit": (490, 560),
            "Balance": (570, 640),
        }

        result = service.detect_headers(words, columns, min_keywords=2)
        assert result is True

    def test_detect_headers_with_noise(self):
        """Test header detection with noisy data."""
        service = HeaderDetectionService()

        # Header with some noise/extra text
        words = [
            {"text": "Bank", "top": 90},
            {"text": "Statement", "top": 90},
            {"text": "Account", "top": 92},
            {"text": "Number:", "top": 92},
            {"text": "IE12345", "top": 92},
            {"text": "Date", "top": 100},  # Actual header
            {"text": "Details", "top": 100},
            {"text": "Amount", "top": 100},
        ]

        columns = {
            "Date": (50, 150),
            "Details": (160, 400),
            "Amount": (410, 500),
        }

        result = service.detect_headers(words, columns, min_keywords=2)
        assert result is True
