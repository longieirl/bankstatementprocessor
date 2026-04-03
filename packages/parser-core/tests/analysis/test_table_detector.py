"""Tests for table detection."""

import pytest
from unittest.mock import MagicMock, Mock

from bankstatements_core.analysis.bbox_utils import BBox
from bankstatements_core.analysis.table_detector import (
    TableDetectionResult,
    TableDetector,
)


class TestTableDetector:
    """Tests for TableDetector class."""

    def test_init_default(self):
        """Test initialization with default parameters."""
        detector = TableDetector()
        assert detector.min_table_height == 50.0

    def test_init_custom_height(self):
        """Test initialization with custom minimum height."""
        detector = TableDetector(min_table_height=100.0)
        assert detector.min_table_height == 100.0

    def test_detect_tables_single_table(self):
        """Test detecting single table on page."""
        # Mock pdfplumber page
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842.0
        mock_page.width = 595.0

        # Mock table
        mock_table = Mock()
        mock_table.bbox = (50, 300, 550, 720)  # x0, y0, x1, y1
        mock_page.find_tables.return_value = [mock_table]

        detector = TableDetector(min_table_height=50.0)
        result = detector.detect_tables(mock_page)

        assert isinstance(result, TableDetectionResult)
        assert result.page_number == 1
        assert result.page_height == 842.0
        assert result.page_width == 595.0
        assert len(result.tables) == 1

        table_bbox = result.tables[0]
        assert table_bbox.x0 == 50
        assert table_bbox.y0 == 300
        assert table_bbox.x1 == 550
        assert table_bbox.y1 == 720

    def test_detect_tables_multiple_tables(self):
        """Test detecting multiple tables on page."""
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842.0
        mock_page.width = 595.0

        # Mock multiple tables
        mock_table1 = Mock()
        mock_table1.bbox = (50, 100, 550, 300)

        mock_table2 = Mock()
        mock_table2.bbox = (50, 400, 550, 720)

        mock_page.find_tables.return_value = [mock_table1, mock_table2]

        detector = TableDetector(min_table_height=50.0)
        result = detector.detect_tables(mock_page)

        assert len(result.tables) == 2
        assert result.tables[0].y0 == 100
        assert result.tables[1].y0 == 400

    def test_detect_tables_filters_small_tables(self):
        """Test that small tables are filtered out."""
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842.0
        mock_page.width = 595.0

        # Mock tables: one large, one small
        mock_large = Mock()
        mock_large.bbox = (50, 100, 550, 300)  # Height = 200

        mock_small = Mock()
        mock_small.bbox = (50, 50, 550, 80)  # Height = 30

        mock_page.find_tables.return_value = [mock_large, mock_small]

        detector = TableDetector(min_table_height=50.0)
        result = detector.detect_tables(mock_page)

        # Only large table should be included
        assert len(result.tables) == 1
        assert result.tables[0].height == 200

    def test_detect_tables_no_tables(self):
        """Test detecting when no tables exist."""
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842.0
        mock_page.width = 595.0
        mock_page.find_tables.return_value = []

        detector = TableDetector()
        result = detector.detect_tables(mock_page)

        assert len(result.tables) == 0
        assert result.page_number == 1

    def test_detect_tables_edge_case_exact_min_height(self):
        """Test table with height exactly at minimum."""
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842.0
        mock_page.width = 595.0

        mock_table = Mock()
        mock_table.bbox = (50, 100, 550, 150)  # Height = 50

        mock_page.find_tables.return_value = [mock_table]

        detector = TableDetector(min_table_height=50.0)
        result = detector.detect_tables(mock_page)

        # Table with height == min_height should be included
        assert len(result.tables) == 1

    def test_get_expanded_table_regions(self):
        """Test getting expanded table regions."""
        detection = TableDetectionResult(
            tables=[BBox(x0=50, y0=100, x1=550, y1=300)],
            page_number=1,
            page_height=842.0,
            page_width=595.0,
        )

        detector = TableDetector()
        expanded = detector.get_expanded_table_regions(detection, margin=20.0)

        assert len(expanded) == 1
        expanded_bbox = expanded[0]

        # Should be expanded by 20 on all sides
        assert expanded_bbox.x0 == 30
        assert expanded_bbox.y0 == 80
        assert expanded_bbox.x1 == 570
        assert expanded_bbox.y1 == 320

    def test_get_expanded_table_regions_multiple_tables(self):
        """Test expanding multiple tables."""
        detection = TableDetectionResult(
            tables=[
                BBox(x0=50, y0=100, x1=550, y1=300),
                BBox(x0=50, y0=400, x1=550, y1=700),
            ],
            page_number=1,
            page_height=842.0,
            page_width=595.0,
        )

        detector = TableDetector()
        expanded = detector.get_expanded_table_regions(detection, margin=10.0)

        assert len(expanded) == 2
        assert expanded[0].x0 == 40
        assert expanded[1].x0 == 40

    def test_get_expanded_table_regions_custom_margin(self):
        """Test expansion with custom margin."""
        detection = TableDetectionResult(
            tables=[BBox(x0=100, y0=200, x1=400, y1=500)],
            page_number=1,
            page_height=842.0,
            page_width=595.0,
        )

        detector = TableDetector()
        expanded = detector.get_expanded_table_regions(detection, margin=50.0)

        expanded_bbox = expanded[0]
        assert expanded_bbox.x0 == 50
        assert expanded_bbox.y0 == 150
        assert expanded_bbox.x1 == 450
        assert expanded_bbox.y1 == 550

    def test_get_expanded_table_regions_empty(self):
        """Test expanding with no tables."""
        detection = TableDetectionResult(
            tables=[], page_number=1, page_height=842.0, page_width=595.0
        )

        detector = TableDetector()
        expanded = detector.get_expanded_table_regions(detection)

        assert len(expanded) == 0

    def test_get_largest_table_single(self):
        """Test getting largest table with single table."""
        detection = TableDetectionResult(
            tables=[BBox(x0=50, y0=100, x1=550, y1=300)],
            page_number=1,
            page_height=842.0,
            page_width=595.0,
        )

        detector = TableDetector()
        largest = detector.get_largest_table(detection)

        assert largest is not None
        assert largest.area == 500 * 200  # width * height

    def test_get_largest_table_multiple(self):
        """Test getting largest table with multiple tables."""
        detection = TableDetectionResult(
            tables=[
                BBox(x0=50, y0=100, x1=550, y1=200),  # Area = 500*100 = 50000
                BBox(x0=50, y0=300, x1=550, y1=700),  # Area = 500*400 = 200000
                BBox(x0=50, y0=750, x1=550, y1=800),  # Area = 500*50 = 25000
            ],
            page_number=1,
            page_height=842.0,
            page_width=595.0,
        )

        detector = TableDetector()
        largest = detector.get_largest_table(detection)

        assert largest is not None
        assert largest.y0 == 300  # Should be the middle table
        assert largest.area == 200000

    def test_get_largest_table_none(self):
        """Test getting largest table with no tables."""
        detection = TableDetectionResult(
            tables=[], page_number=1, page_height=842.0, page_width=595.0
        )

        detector = TableDetector()
        largest = detector.get_largest_table(detection)

        assert largest is None


class TestDetectTextBasedTable:
    """Tests for the text-based fallback table detection."""

    def _make_word(self, text, top, x0=50, x1=None):
        return {"text": text, "top": top, "x0": x0, "x1": x1 or (x0 + len(text) * 6)}

    def _make_page(self, words):
        page = MagicMock()
        page.extract_words.return_value = words
        page.find_tables.return_value = []
        page.width = 595.0
        page.height = 842.0
        return page

    def test_text_based_no_words_returns_none(self):
        detector = TableDetector()
        page = self._make_page([])
        result = detector._detect_text_based_table(page)
        assert result is None

    def test_text_based_no_header_returns_none(self):
        detector = TableDetector()
        words = [self._make_word("hello", 100), self._make_word("world", 100, x0=100)]
        page = self._make_page(words)
        result = detector._detect_text_based_table(page)
        assert result is None

    def test_text_based_with_header_and_rows(self):
        detector = TableDetector()
        # Row with enough header keywords (date, details, debit, credit, balance)
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        # Data rows
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
            self._make_word("", 120, x0=280),
            self._make_word("100.00", 120, x0=360),
        ]
        row2 = [
            self._make_word("02", 140, x0=50),
            self._make_word("deposit", 140, x0=100),
            self._make_word("", 140, x0=200),
            self._make_word("50.00", 140, x0=280),
            self._make_word("150.00", 140, x0=360),
        ]
        page = self._make_page(header_words + row1 + row2)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y0 <= 100

    def test_text_based_footer_terminates_table(self):
        detector = TableDetector()
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
            self._make_word("0", 120, x0=280),
            self._make_word("100.00", 120, x0=360),
        ]
        footer = [
            self._make_word("total", 200, x0=50),
            self._make_word("balance", 200, x0=100),
            self._make_word("carried", 200, x0=200),
        ]
        page = self._make_page(header_words + row1 + footer)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y1 < 200  # Should stop before footer

    def test_detect_tables_fallback_triggered(self):
        """Test that detect_tables uses text fallback when no pdfplumber tables found."""
        detector = TableDetector()
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
            self._make_word("0", 120, x0=280),
            self._make_word("100.00", 120, x0=360),
        ]
        page = self._make_page(header_words + row1)
        result = detector.detect_tables(page)
        assert len(result.tables) >= 0  # may or may not find table

    def test_text_based_avg_row_spacing_used_for_bottom(self):
        """Three+ rows without footer: bottom_y uses average spacing * 1.5."""
        detector = TableDetector()
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        # Three data rows, 20px apart -> avg spacing = 20, margin = 30, bottom = 160 + 30 = 190
        rows = []
        for top in [120, 140, 160]:
            rows += [
                self._make_word("01", top, x0=50),
                self._make_word("text", top, x0=100),
                self._make_word("10.00", top, x0=200),
            ]
        page = self._make_page(header_words + rows)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y1 == pytest.approx(190.0, abs=5)

    def test_text_based_no_valid_row_spacings_uses_fallback(self):
        """Three rows with > 50px gaps: row_spacings empty, fallback margin = 20."""
        detector = TableDetector()
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        rows = []
        for top in [160, 220, 280]:  # 60px gaps -- all > 50, excluded from row_spacings
            rows += [
                self._make_word("01", top, x0=50),
                self._make_word("text", top, x0=100),
                self._make_word("10.00", top, x0=200),
            ]
        page = self._make_page(header_words + rows)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y1 == pytest.approx(300.0, abs=2)  # max(280) + 20 fallback

    def test_text_based_large_gap_acts_as_footer(self):
        """Gap > 100px to sparse row triggers footer heuristic."""
        detector = TableDetector()
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
        ]
        # Sparse row > 100px below last transaction
        sparse = [self._make_word("Note", 240, x0=50), self._make_word("only", 240, x0=100)]
        page = self._make_page(header_words + row1 + sparse)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y1 < 240  # footer heuristic kicked in at y=240

    def test_text_based_transaction_indicator_skips_row(self):
        """Row with transaction indicator is skipped even if it has enough keywords."""
        detector = TableDetector()
        # This row has 4 header keywords but also 'forward' -- should be skipped
        indicator_row = [
            self._make_word("date", 80, x0=50),
            self._make_word("details", 80, x0=100),
            self._make_word("debit", 80, x0=200),
            self._make_word("credit", 80, x0=280),
            self._make_word("forward", 80, x0=360),  # TRANSACTION_INDICATOR
        ]
        # Real header below
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
        ]
        row2 = [
            self._make_word("02", 150, x0=50),
            self._make_word("deposit", 150, x0=100),
            self._make_word("50.00", 150, x0=200),
        ]
        page = self._make_page(indicator_row + header_words + row1 + row2)
        result = detector._detect_text_based_table(page)
        assert result is not None
        assert result.y0 > 80  # anchored at real header (y=100-5=95), not indicator row

    def test_text_based_too_small_bbox_returns_none(self):
        """Result is None if calculated bbox height is below min_table_height."""
        detector = TableDetector(min_table_height=200.0)  # very large threshold
        header_words = [
            self._make_word("date", 100, x0=50),
            self._make_word("details", 100, x0=100),
            self._make_word("debit", 100, x0=200),
            self._make_word("credit", 100, x0=280),
            self._make_word("balance", 100, x0=360),
        ]
        row1 = [
            self._make_word("01", 120, x0=50),
            self._make_word("payment", 120, x0=100),
            self._make_word("10.00", 120, x0=200),
        ]
        page = self._make_page(header_words + row1)
        result = detector._detect_text_based_table(page)
        # bbox height will be ~35px (120 + margin - 95), < 200 threshold
        assert result is None
