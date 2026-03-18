"""Tests for extraction parameters module."""

from __future__ import annotations

from bankstatements_core.extraction.extraction_params import (
    ADMINISTRATIVE_PATTERNS,
    CONTENT_DENSITY_THRESHOLD,
    ENABLE_PAGE_VALIDATION,
    MIN_COLUMN_COVERAGE,
    MIN_HEADER_KEYWORDS,
    MIN_TABLE_ROWS,
    MIN_TRANSACTION_RATIO,
    MIN_TRANSACTION_SCORE,
    REQUIRE_AMOUNT_COLUMN,
    REQUIRE_DATE_COLUMN,
    SLIDING_WINDOW_SIZE,
    TABLE_BOTTOM_Y,
    TABLE_TOP_Y,
)


class TestExtractionParams:
    """Test extraction parameter constants."""

    def test_table_bounds_constants(self):
        """Verify table boundary constants are defined."""
        assert TABLE_TOP_Y == 300
        assert TABLE_BOTTOM_Y == 720
        assert TABLE_TOP_Y < TABLE_BOTTOM_Y

    def test_dynamic_detection_params(self):
        """Verify dynamic detection parameters are defined."""
        assert isinstance(CONTENT_DENSITY_THRESHOLD, float)
        assert isinstance(SLIDING_WINDOW_SIZE, int)
        assert isinstance(MIN_TRANSACTION_SCORE, float)
        assert SLIDING_WINDOW_SIZE > 0

    def test_page_validation_params(self):
        """Verify page validation parameters are defined."""
        assert isinstance(ENABLE_PAGE_VALIDATION, bool)
        assert isinstance(MIN_TABLE_ROWS, int)
        assert isinstance(MIN_COLUMN_COVERAGE, float)
        assert isinstance(MIN_TRANSACTION_RATIO, float)
        assert isinstance(REQUIRE_DATE_COLUMN, bool)
        assert isinstance(REQUIRE_AMOUNT_COLUMN, bool)
        assert isinstance(MIN_HEADER_KEYWORDS, int)

    def test_administrative_patterns(self):
        """Verify administrative patterns are defined."""
        assert isinstance(ADMINISTRATIVE_PATTERNS, list)
        assert len(ADMINISTRATIVE_PATTERNS) > 0
        assert "BALANCE FORWARD" in ADMINISTRATIVE_PATTERNS
