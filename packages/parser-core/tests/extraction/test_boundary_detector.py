"""Tests for table boundary detection."""

from __future__ import annotations

import pytest

from bankstatements_core.extraction.boundary_detector import (
    BoundaryDetectionResult,
    TableBoundaryDetector,
)

# Test columns configuration
TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


class TestBoundaryDetectionResult:
    """Tests for BoundaryDetectionResult dataclass."""

    def test_create_result(self):
        """Test creating a BoundaryDetectionResult."""
        result = BoundaryDetectionResult(
            boundary_y=500, method="strong_pattern", confidence=1.0
        )
        assert result.boundary_y == 500
        assert result.method == "strong_pattern"
        assert result.confidence == 1.0

    def test_default_confidence(self):
        """Test default confidence value."""
        result = BoundaryDetectionResult(boundary_y=500, method="spatial_gap")
        assert result.confidence == 1.0


class TestTableBoundaryDetector:
    """Tests for TableBoundaryDetector."""

    def test_empty_words_returns_fallback(self):
        """Test that empty word list returns fallback boundary."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        boundary = detector.detect_boundary([])
        assert boundary == 720

    def test_no_transactions_returns_fallback(self):
        """Test that no transactions returns fallback boundary."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        # Words that don't form transactions
        words = [
            {"text": "Header", "x0": 60, "top": 350},
            {"text": "Text", "x0": 60, "top": 370},
        ]
        boundary = detector.detect_boundary(words)
        assert boundary == 720

    def test_group_words_by_y(self):
        """Test grouping words by Y-coordinate."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        words = [
            {"text": "Word1", "x0": 30, "top": 350},
            {"text": "Word2", "x0": 60, "top": 350},
            {"text": "Word3", "x0": 30, "top": 370},
        ]
        lines = detector._group_words_by_y(words)
        assert len(lines) == 2
        assert 350.0 in lines
        assert 370.0 in lines
        assert len(lines[350.0]) == 2
        assert len(lines[370.0]) == 1

    def test_group_words_filters_above_table_top(self):
        """Test that words above table_top_y are filtered out."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        words = [
            {"text": "Above", "x0": 30, "top": 250},  # Above table_top_y
            {"text": "Below", "x0": 30, "top": 350},  # Below table_top_y
        ]
        lines = detector._group_words_by_y(words)
        assert len(lines) == 1
        assert 350.0 in lines

    def test_find_transaction_positions(self):
        """Test finding transaction positions."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        # Create words that form a transaction row
        lines = {
            350.0: [
                {"text": "01", "x0": 30, "top": 350},
                {"text": "Jan", "x0": 35, "top": 350},
                {"text": "Purchase", "x0": 60, "top": 350},
                {"text": "50.00", "x0": 210, "top": 350},  # Debit
            ],
            370.0: [
                {"text": "Metadata", "x0": 60, "top": 370},
            ],
        }
        positions, last_y = detector._find_transaction_positions(
            lines, sorted([350.0, 370.0])
        )
        assert len(positions) == 1
        assert 350.0 in positions
        assert last_y == 350.0

    def test_detect_by_strong_patterns_end_of_statement(self):
        """Test detection by 'END OF STATEMENT' pattern."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        lines = {
            350.0: [{"text": "01", "x0": 30, "top": 350}],
            400.0: [
                {"text": "END", "x0": 60, "top": 400},
                {"text": "OF", "x0": 90, "top": 400},
                {"text": "STATEMENT", "x0": 110, "top": 400},
            ],
        }
        result = detector._detect_by_strong_patterns(
            lines, sorted([350.0, 400.0]), last_transaction_y=350.0
        )
        assert result is not None
        assert result.boundary_y == 390  # 400 - 10
        assert "END OF STATEMENT" in result.method
        assert result.confidence == 1.0

    def test_detect_by_strong_patterns_statement_total(self):
        """Test detection by 'STATEMENT TOTAL' pattern."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        lines = {
            350.0: [{"text": "01", "x0": 30, "top": 350}],
            400.0: [
                {"text": "Statement", "x0": 60, "top": 400},
                {"text": "Total", "x0": 110, "top": 400},
            ],
        }
        result = detector._detect_by_strong_patterns(
            lines, sorted([350.0, 400.0]), last_transaction_y=350.0
        )
        assert result is not None
        assert "STATEMENT TOTAL" in result.method

    def test_detect_by_strong_patterns_ignores_before_last_transaction(self):
        """Test that strong patterns before last transaction are ignored."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        lines = {
            300.0: [
                {"text": "END", "x0": 60, "top": 300},
                {"text": "OF", "x0": 90, "top": 300},
                {"text": "STATEMENT", "x0": 110, "top": 300},
            ],
            350.0: [{"text": "Transaction", "x0": 30, "top": 350}],
        }
        result = detector._detect_by_strong_patterns(
            lines, sorted([300.0, 350.0]), last_transaction_y=350.0
        )
        assert result is None  # Pattern before last transaction should be ignored

    def test_detect_by_spatial_gaps(self):
        """Test detection by large spatial gaps."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        # Create words with a large gap
        lines = {
            350.0: [
                {"text": "01", "x0": 30, "top": 350},
                {"text": "Jan", "x0": 35, "top": 350},
                {"text": "Purchase", "x0": 60, "top": 350},
                {"text": "50.00", "x0": 210, "top": 350},
            ],
            450.0: [  # 100px gap (> 50px threshold)
                {"text": "Footer", "x0": 60, "top": 450},
            ],
        }
        result = detector._detect_by_spatial_gaps(
            lines, sorted([350.0, 450.0]), last_transaction_y=350.0
        )
        assert result is not None
        assert result.boundary_y == 370  # 350 + 20
        assert result.method == "spatial_gap"
        assert result.confidence == 100.0  # Gap size

    def test_detect_by_spatial_gaps_requires_no_transactions_after(self):
        """Test that spatial gap detection requires no transactions after gap."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        lines = {
            350.0: [
                {"text": "01", "x0": 30, "top": 350},
                {"text": "Purchase", "x0": 60, "top": 350},
                {"text": "50.00", "x0": 210, "top": 350},
            ],
            450.0: [  # Large gap
                {"text": "02", "x0": 30, "top": 450},
                {"text": "Another", "x0": 60, "top": 450},
                {"text": "25.00", "x0": 210, "top": 450},  # Transaction after gap
            ],
        }
        result = detector._detect_by_spatial_gaps(
            lines, sorted([350.0, 450.0]), last_transaction_y=350.0
        )
        # Should return None because there's a transaction after the gap
        assert result is None

    def test_build_row_from_words(self):
        """Test building a row from words."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        row = detector._build_row_from_words(words)
        assert "01 Jan" in row["Date"]
        assert "Purchase" in row["Details"]
        assert "50.00" in row["Debit €"]

    def test_calculate_column_coverage_full(self):
        """Test column coverage calculation with full coverage."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        rows = [
            {
                "Date": "01 Jan",
                "Details": "Purchase",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "100.00",
            }
        ]
        coverage = detector._calculate_column_coverage(rows)
        assert coverage == 0.8  # 4 out of 5 columns (Credit is empty)

    def test_calculate_column_coverage_partial(self):
        """Test column coverage calculation with partial coverage."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        rows = [
            {
                "Date": "",
                "Details": "Text",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            }
        ]
        coverage = detector._calculate_column_coverage(rows)
        assert coverage == 0.2  # 1 out of 5 columns

    def test_calculate_column_coverage_empty(self):
        """Test column coverage calculation with empty rows."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        coverage = detector._calculate_column_coverage([])
        assert coverage == 0.0

    def test_detect_by_structure_breakdown(self):
        """Test detection by column structure breakdown."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        # Create lines where structure breaks down
        # Transaction at Y=350
        lines = {
            350.0: [
                {"text": "01", "x0": 30, "top": 350},
                {"text": "Purchase", "x0": 60, "top": 350},
                {"text": "50.00", "x0": 210, "top": 350},
            ]
        }
        # Then 8+ lines with poor column coverage (only Details column)
        for i in range(9):
            y = 370.0 + (i * 20)
            lines[y] = [{"text": "Footer text", "x0": 60, "top": y}]

        sorted_y = sorted(lines.keys())
        result = detector._detect_by_structure_breakdown(
            lines, sorted_y, last_transaction_y=350.0
        )
        assert result is not None
        assert result.method == "structure_breakdown"

    def test_detect_by_consecutive_non_transactions(self):
        """Test detection by consecutive non-transactions."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        # Create transaction followed by 15+ non-transaction rows
        lines = {
            350.0: [
                {"text": "01", "x0": 30, "top": 350},
                {"text": "Purchase", "x0": 60, "top": 350},
                {"text": "50.00", "x0": 210, "top": 350},
            ]
        }
        # 15 non-transaction rows
        for i in range(16):
            y = 370.0 + (i * 20)
            lines[y] = [{"text": "Footer", "x0": 60, "top": y}]

        sorted_y = sorted(lines.keys())
        result = detector._detect_by_consecutive_non_transactions(
            lines, sorted_y, last_transaction_y=350.0
        )
        assert result is not None
        assert result.method == "consecutive_non_transactions"
        assert result.boundary_y == 410  # 350 + 60

    def test_full_detection_flow_with_strong_pattern(self):
        """Test full detection flow when strong pattern is found."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        words = [
            # Transaction
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
            # End marker
            {"text": "END", "x0": 60, "top": 400},
            {"text": "OF", "x0": 90, "top": 400},
            {"text": "STATEMENT", "x0": 110, "top": 400},
        ]
        boundary = detector.detect_boundary(words)
        assert boundary == 390  # 400 - 10

    def test_full_detection_flow_no_clear_end(self):
        """Test full detection flow when no clear end is detected."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, fallback_bottom_y=720, table_top_y=300
        )
        words = [
            # Just one transaction with minimal following content
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
            {"text": "Some", "x0": 60, "top": 370},
            {"text": "text", "x0": 90, "top": 390},
        ]
        boundary = detector.detect_boundary(words)
        assert boundary == 720  # Fallback

    def test_configuration_via_constructor(self):
        """Test that detector accepts configuration via constructor parameters."""
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS,
            fallback_bottom_y=720,
            table_top_y=300,
            min_section_gap=100,
            structure_breakdown_threshold=10,
            dynamic_boundary_threshold=20,
        )
        assert detector.min_gap_threshold == 100
        assert detector.structure_breakdown_threshold == 10
        assert detector.consecutive_threshold == 20

    def test_injected_classifier_is_used(self):
        from unittest.mock import Mock

        from bankstatements_core.extraction.row_classifiers import RowClassifier

        mock_chain = Mock(spec=RowClassifier)
        mock_chain.classify.return_value = "metadata"
        detector = TableBoundaryDetector(
            columns=TEST_COLUMNS, row_classifier=mock_chain
        )
        words = [{"text": "Footer", "x0": 60, "top": 350}]
        detector.detect_boundary(words)
        mock_chain.classify.assert_called()

    def test_default_classifier_created_when_not_injected(self):
        detector = TableBoundaryDetector(columns=TEST_COLUMNS)
        assert detector._row_classifier is not None
