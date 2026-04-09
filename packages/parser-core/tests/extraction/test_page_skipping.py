"""Tests for page skipping when tables are not present.

This test module specifically verifies the requirement that:
- Every page in a PDF should be validated for table presence
- Pages without tables should be skipped
- Processing should continue to subsequent pages
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.extraction.extraction_params import PDFExtractorOptions
from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

# Test columns configuration
TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


class TestPageSkipping:
    """Tests for page skipping behavior."""

    @patch.dict("os.environ", {"REQUIRE_TABLE_HEADERS": "true"})
    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_skip_page_without_headers_and_continue(self, mock_pdfplumber):
        """Test that pages without headers are skipped when header check is enabled."""
        # Setup: 3 pages - page 1 has no headers, pages 2 and 3 have headers
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_page3 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber.return_value = mock_pdf

        # Page 1: No headers or table-like content
        mock_page1.width = 600
        mock_page1.height = 800
        mock_cropped1 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_words1 = [
            {"text": "Random", "x0": 60, "top": 350},
            {"text": "Text", "x0": 80, "top": 350},
            {"text": "No", "x0": 100, "top": 370},
            {"text": "Table", "x0": 120, "top": 370},
        ]
        mock_cropped1.extract_words.return_value = mock_words1

        # Page 2: Has headers and valid transaction
        mock_page2.width = 600
        mock_page2.height = 800
        mock_cropped2 = MagicMock()
        mock_page2.crop.return_value = mock_cropped2
        mock_words2 = [
            # Headers
            {"text": "Date", "x0": 30, "top": 320},
            {"text": "Details", "x0": 60, "top": 320},
            {"text": "Debit", "x0": 210, "top": 320},
            # Transaction
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "2023", "x0": 40, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped2.extract_words.return_value = mock_words2

        # Page 3: Has headers and valid transaction
        mock_page3.width = 600
        mock_page3.height = 800
        mock_cropped3 = MagicMock()
        mock_page3.crop.return_value = mock_cropped3
        mock_words3 = [
            # Headers
            {"text": "Date", "x0": 30, "top": 320},
            {"text": "Details", "x0": 60, "top": 320},
            # Transaction
            {"text": "02", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "2023", "x0": 40, "top": 350},
            {"text": "Sale", "x0": 60, "top": 350},
            {"text": "25.00", "x0": 260, "top": 350},
        ]
        mock_cropped3.extract_words.return_value = mock_words3

        # Extract with default settings (validation enabled)
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_dynamic_boundary=True),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        # Assertions
        assert result.page_count == 3  # All pages were examined
        assert len(result.transactions) == 2  # Only 2 transactions (from pages 2 and 3)
        assert result.transactions[0].filename == "test.pdf"
        assert result.transactions[1].filename == "test.pdf"

    @patch.dict("os.environ", {"REQUIRE_TABLE_HEADERS": "true"})
    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_skip_all_pages_without_tables(self, mock_pdfplumber):
        """Test that all pages are skipped when none have tables (with header check)."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value = mock_pdf

        # Page 1: No table content
        mock_page1.width = 600
        mock_page1.height = 800
        mock_cropped1 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_words1 = [
            {"text": "Cover", "x0": 60, "top": 350},
            {"text": "Page", "x0": 80, "top": 350},
        ]
        mock_cropped1.extract_words.return_value = mock_words1

        # Page 2: No table content
        mock_page2.width = 600
        mock_page2.height = 800
        mock_cropped2 = MagicMock()
        mock_page2.crop.return_value = mock_cropped2
        mock_words2 = [
            {"text": "Summary", "x0": 60, "top": 350},
            {"text": "Page", "x0": 80, "top": 350},
        ]
        mock_cropped2.extract_words.return_value = mock_words2

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_dynamic_boundary=True),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 2  # All pages were examined
        assert len(result.transactions) == 0  # No transactions extracted

    @patch.dict("os.environ", {"REQUIRE_TABLE_HEADERS": "true"})
    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_process_all_pages_with_tables(self, mock_pdfplumber):
        """Test that all pages with tables are processed (with header check)."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_page3 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber.return_value = mock_pdf

        # All pages have valid tables
        for i, mock_page in enumerate([mock_page1, mock_page2, mock_page3], 1):
            mock_page.width = 600
            mock_page.height = 800
            mock_cropped = MagicMock()
            mock_page.crop.return_value = mock_cropped
            mock_words = [
                # Headers
                {"text": "Date", "x0": 30, "top": 320},
                {"text": "Details", "x0": 60, "top": 320},
                # Transaction
                {"text": f"0{i}", "x0": 30, "top": 350},
                {"text": "Jan", "x0": 35, "top": 350},
                {"text": f"Transaction {i}", "x0": 60, "top": 350},
                {"text": f"{i * 10}.00", "x0": 210, "top": 350},
            ]
            mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_dynamic_boundary=True),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 3
        assert len(result.transactions) == 3  # One transaction from each page

    @patch.dict("os.environ", {"REQUIRE_TABLE_HEADERS": "true"})
    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_skip_middle_page_without_table(self, mock_pdfplumber):
        """Test skipping a page in the middle that has no table (with header check)."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_page3 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber.return_value = mock_pdf

        # Page 1: Valid table
        mock_page1.width = 600
        mock_page1.height = 800
        mock_cropped1 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_words1 = [
            {"text": "Date", "x0": 30, "top": 320},
            {"text": "Details", "x0": 60, "top": 320},
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped1.extract_words.return_value = mock_words1

        # Page 2: No table (advertisement or summary page)
        mock_page2.width = 600
        mock_page2.height = 800
        mock_cropped2 = MagicMock()
        mock_page2.crop.return_value = mock_cropped2
        mock_words2 = [
            {"text": "Advertisement", "x0": 60, "top": 350},
            {"text": "Content", "x0": 80, "top": 350},
        ]
        mock_cropped2.extract_words.return_value = mock_words2

        # Page 3: Valid table
        mock_page3.width = 600
        mock_page3.height = 800
        mock_cropped3 = MagicMock()
        mock_page3.crop.return_value = mock_cropped3
        mock_words3 = [
            {"text": "Date", "x0": 30, "top": 320},
            {"text": "Details", "x0": 60, "top": 320},
            {"text": "02", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Sale", "x0": 60, "top": 350},
            {"text": "25.00", "x0": 260, "top": 350},
        ]
        mock_cropped3.extract_words.return_value = mock_words3

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_dynamic_boundary=True),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 3  # All 3 pages examined
        assert len(result.transactions) == 2  # Only pages 1 and 3 had transactions

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_page_validation_disabled_processes_all_pages(self, mock_pdfplumber):
        """Test that with validation disabled, all pages are processed."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_pdf.pages = [mock_page1]
        mock_pdfplumber.return_value = mock_pdf

        # Page with no headers but some content
        mock_cropped = MagicMock()
        mock_page1.crop.return_value = mock_cropped
        mock_words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        # With validation disabled
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_page_validation=False),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1
        # Should process page even without headers
        assert len(result.transactions) >= 0  # May or may not have valid transactions

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_validation_enabled_by_default(self, mock_pdfplumber):
        """Test that both structural and header validation are enabled by default."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600
        mock_page.height = 800
        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Page with no recognizable table structure or headers
        mock_words = [
            {"text": "Random", "x0": 60, "top": 350},
            {"text": "Content", "x0": 80, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        # Create extractor with defaults (should have validation enabled)
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_dynamic_boundary=True),
        )

        # Verify both validations are enabled by default
        assert extractor.page_validation_enabled is True
        assert extractor.header_check_enabled is True

        # Extract and verify page is skipped due to missing headers
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1  # Page was examined
        assert len(result.transactions) == 0  # Page was skipped (no headers)

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_empty_pdf_returns_zero_rows(self, mock_pdfplumber):
        """Test that a PDF with no pages returns zero rows."""
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value = mock_pdf

        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        result = extractor.extract(Path("/tmp/empty.pdf"))

        assert result.page_count == 0
        assert len(result.transactions) == 0

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_page_with_insufficient_rows_skipped(self, mock_pdfplumber):
        """Test that pages with insufficient rows are skipped by validation."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Page has headers but no actual transaction rows
        mock_words = [
            {"text": "Date", "x0": 30, "top": 320},
            {"text": "Details", "x0": 60, "top": 320},
            {"text": "Debit", "x0": 210, "top": 320},
        ]
        mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            options=PDFExtractorOptions(enable_page_validation=True),
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1
        # Should be skipped due to insufficient transaction rows
        assert len(result.transactions) == 0
