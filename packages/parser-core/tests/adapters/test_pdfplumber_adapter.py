"""Tests for pdfplumber adapter implementing PDF reader protocol."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from bankstatements_core.adapters.pdfplumber_adapter import (
    PDFPlumberDocumentAdapter,
    PDFPlumberPageAdapter,
    PDFPlumberReaderAdapter,
)
from bankstatements_core.domain.protocols.pdf_reader import (
    IPDFDocument,
    IPDFPage,
    IPDFReader,
)


class TestPDFPlumberPageAdapter:
    """Tests for PDFPlumberPageAdapter."""

    def test_implements_ipdfpage_protocol(self):
        """Test that adapter implements IPDFPage protocol."""
        mock_page = Mock()
        mock_page.width = 595.0
        mock_page.height = 842.0
        mock_page.page_number = 1

        adapter = PDFPlumberPageAdapter(mock_page)

        # Should have all IPDFPage protocol methods
        assert hasattr(adapter, "width")
        assert hasattr(adapter, "height")
        assert hasattr(adapter, "page_number")
        assert hasattr(adapter, "extract_text")
        assert hasattr(adapter, "extract_words")
        assert hasattr(adapter, "extract_tables")
        assert hasattr(adapter, "find_tables")
        assert hasattr(adapter, "crop")

    def test_properties(self):
        """Test page properties."""
        mock_page = Mock()
        mock_page.width = 595.0
        mock_page.height = 842.0
        mock_page.page_number = 1

        adapter = PDFPlumberPageAdapter(mock_page)

        assert adapter.width == 595.0
        assert adapter.height == 842.0
        assert adapter.page_number == 1

    def test_extract_text_returns_content(self):
        """Test extract_text returns page text."""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test content"

        adapter = PDFPlumberPageAdapter(mock_page)
        text = adapter.extract_text()

        assert text == "Test content"
        mock_page.extract_text.assert_called_once()

    def test_extract_text_returns_empty_on_none(self):
        """Test extract_text returns empty string when None."""
        mock_page = Mock()
        mock_page.extract_text.return_value = None

        adapter = PDFPlumberPageAdapter(mock_page)
        text = adapter.extract_text()

        assert text == ""

    def test_extract_words(self):
        """Test extract_words returns word dictionaries."""
        mock_page = Mock()
        mock_words = [
            {"text": "Hello", "x0": 10, "top": 20, "x1": 50, "bottom": 30},
            {"text": "World", "x0": 60, "top": 20, "x1": 100, "bottom": 30},
        ]
        mock_page.extract_words.return_value = mock_words

        adapter = PDFPlumberPageAdapter(mock_page)
        words = adapter.extract_words()

        assert len(words) == 2
        assert words[0]["text"] == "Hello"
        assert words[1]["text"] == "World"

    def test_extract_words_returns_empty_on_none(self):
        """Test extract_words returns empty list when None."""
        mock_page = Mock()
        mock_page.extract_words.return_value = None

        adapter = PDFPlumberPageAdapter(mock_page)
        words = adapter.extract_words()

        assert words == []

    def test_extract_tables(self):
        """Test extract_tables."""
        mock_page = Mock()
        mock_tables = [["Row1"], ["Row2"]]
        mock_page.extract_tables.return_value = mock_tables

        adapter = PDFPlumberPageAdapter(mock_page)
        tables = adapter.extract_tables()

        assert tables == mock_tables

    def test_extract_tables_with_settings(self):
        """Test extract_tables with custom settings."""
        mock_page = Mock()
        mock_tables = [["Row1"]]
        mock_page.extract_tables.return_value = mock_tables

        adapter = PDFPlumberPageAdapter(mock_page)
        settings = {"vertical_strategy": "lines"}
        tables = adapter.extract_tables(table_settings=settings)

        assert tables == mock_tables
        mock_page.extract_tables.assert_called_once_with(table_settings=settings)

    def test_find_tables(self):
        """Test find_tables."""
        mock_page = Mock()
        mock_table_objs = [Mock(bbox=(10, 20, 100, 200))]
        mock_page.find_tables.return_value = mock_table_objs

        adapter = PDFPlumberPageAdapter(mock_page)
        tables = adapter.find_tables()

        assert len(tables) == 1
        assert tables == mock_table_objs

    def test_find_tables_with_settings(self):
        """Test find_tables with custom settings."""
        mock_page = Mock()
        mock_table_objs = [Mock(bbox=(10, 20, 100, 200))]
        mock_page.find_tables.return_value = mock_table_objs

        adapter = PDFPlumberPageAdapter(mock_page)
        settings = {"vertical_strategy": "lines"}
        tables = adapter.find_tables(table_settings=settings)

        assert tables == mock_table_objs
        mock_page.find_tables.assert_called_once_with(table_settings=settings)

    def test_underlying_page_property(self):
        """Test underlying_page property returns wrapped page."""
        mock_page = Mock()
        adapter = PDFPlumberPageAdapter(mock_page)

        assert adapter.underlying_page is mock_page

    def test_crop(self):
        """Test crop returns new adapter with cropped page."""
        mock_page = Mock()
        mock_cropped = Mock()
        mock_page.crop.return_value = mock_cropped

        adapter = PDFPlumberPageAdapter(mock_page)
        bbox = (50, 100, 200, 300)
        cropped_adapter = adapter.crop(bbox)

        assert isinstance(cropped_adapter, PDFPlumberPageAdapter)
        mock_page.crop.assert_called_once_with(bbox)


class TestPDFPlumberDocumentAdapter:
    """Tests for PDFPlumberDocumentAdapter."""

    def test_implements_ipdfdocument_protocol(self):
        """Test that adapter implements IPDFDocument protocol."""
        mock_pdf = Mock()
        mock_pdf.pages = []

        adapter = PDFPlumberDocumentAdapter(mock_pdf)

        # Should have all IPDFDocument protocol methods
        assert hasattr(adapter, "pages")
        assert hasattr(adapter, "__enter__")
        assert hasattr(adapter, "__exit__")

    def test_pages_property(self):
        """Test pages property returns list of page adapters."""
        mock_page1 = Mock()
        mock_page1.width = 595.0
        mock_page2 = Mock()
        mock_page2.width = 595.0

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]

        adapter = PDFPlumberDocumentAdapter(mock_pdf)
        pages = adapter.pages

        assert len(pages) == 2
        assert all(isinstance(p, PDFPlumberPageAdapter) for p in pages)

    def test_pages_cached(self):
        """Test pages are cached after first access."""
        mock_pdf = Mock()
        mock_pdf.pages = [Mock(), Mock()]

        adapter = PDFPlumberDocumentAdapter(mock_pdf)

        # Access twice
        pages1 = adapter.pages
        pages2 = adapter.pages

        # Should be same objects (cached)
        assert pages1 is pages2

    def test_context_manager(self):
        """Test context manager functionality."""
        mock_pdf = Mock()
        mock_pdf.pages = []

        adapter = PDFPlumberDocumentAdapter(mock_pdf)

        # Enter context
        result = adapter.__enter__()
        assert result is adapter

        # Exit context
        adapter.__exit__(None, None, None)
        mock_pdf.close.assert_called_once()


class TestPDFPlumberReaderAdapter:
    """Tests for PDFPlumberReaderAdapter."""

    def test_implements_ipdfreader_protocol(self):
        """Test that adapter implements IPDFReader protocol."""
        adapter = PDFPlumberReaderAdapter()

        # Should have open method
        assert hasattr(adapter, "open")
        assert callable(adapter.open)

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber")
    def test_open_returns_document_adapter(self, mock_pdfplumber):
        """Test open returns PDFPlumberDocumentAdapter."""
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        try:
            # Mock pdfplumber.open
            mock_pdf = Mock()
            mock_pdf.pages = []
            mock_pdfplumber.open.return_value = mock_pdf

            adapter = PDFPlumberReaderAdapter()
            doc = adapter.open(pdf_path)

            assert isinstance(doc, PDFPlumberDocumentAdapter)
            mock_pdfplumber.open.assert_called_once_with(pdf_path)
        finally:
            pdf_path.unlink()

    def test_open_raises_filenotfound_for_nonexistent(self):
        """Test open raises FileNotFoundError for nonexistent files."""
        adapter = PDFPlumberReaderAdapter()
        nonexistent = Path("/tmp/definitely_does_not_exist_12345.pdf")

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            adapter.open(nonexistent)

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber")
    def test_open_raises_ioerror_on_failure(self, mock_pdfplumber):
        """Test open raises IOError when pdfplumber fails."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        try:
            # Mock pdfplumber.open to raise exception
            mock_pdfplumber.open.side_effect = Exception("Corrupted PDF")

            adapter = PDFPlumberReaderAdapter()

            with pytest.raises(IOError, match="Failed to open PDF"):
                adapter.open(pdf_path)
        finally:
            pdf_path.unlink()


class TestProtocolCompliance:
    """Tests demonstrating protocol compliance."""

    def test_function_accepting_ipdfreader(self):
        """Test that functions can accept IPDFReader protocol."""

        def read_first_page_text(reader: IPDFReader, path: Path) -> str:
            """Example function accepting IPDFReader."""
            with reader.open(path) as doc:
                if doc.pages:
                    return doc.pages[0].extract_text()
                return ""

        # Can pass adapter to function
        adapter = PDFPlumberReaderAdapter()
        assert callable(adapter.open)

    def test_function_accepting_ipdfdocument(self):
        """Test that functions can accept IPDFDocument protocol."""

        def count_pages(doc: IPDFDocument) -> int:
            """Example function accepting IPDFDocument."""
            return len(doc.pages)

        mock_pdf = Mock()
        mock_pdf.pages = [Mock(), Mock(), Mock()]

        doc_adapter = PDFPlumberDocumentAdapter(mock_pdf)
        count = count_pages(doc_adapter)

        assert count == 3

    def test_function_accepting_ipdfpage(self):
        """Test that functions can accept IPDFPage protocol."""

        def get_page_dimensions(page: IPDFPage) -> tuple[float, float]:
            """Example function accepting IPDFPage."""
            return (page.width, page.height)

        mock_page = Mock()
        mock_page.width = 595.0
        mock_page.height = 842.0

        page_adapter = PDFPlumberPageAdapter(mock_page)
        dims = get_page_dimensions(page_adapter)

        assert dims == (595.0, 842.0)
