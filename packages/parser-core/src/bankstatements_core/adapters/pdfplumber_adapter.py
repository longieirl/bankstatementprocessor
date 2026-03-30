"""Adapter for pdfplumber library implementing PDF reader protocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pdfplumber

if TYPE_CHECKING:
    from pdfplumber.page import Page
    from pdfplumber.pdf import PDF


class PDFPlumberPageAdapter:
    """Adapter wrapping pdfplumber Page to implement IPDFPage protocol."""

    def __init__(self, page: Page):
        """Initialize page adapter.

        Args:
            page: pdfplumber Page object
        """
        self._page = page

    @property
    def underlying_page(self) -> Any:
        """Get the underlying pdfplumber Page object.

        This is useful for legacy code that expects pdfplumber.Page directly.

        Returns:
            The wrapped pdfplumber Page object
        """
        return self._page

    @property
    def width(self) -> float:
        """Page width in points."""
        return self._page.width

    @property
    def height(self) -> float:
        """Page height in points."""
        return self._page.height

    @property
    def page_number(self) -> int:
        """Page number (1-indexed)."""
        # pdfplumber.Page has page_number attribute but it's not in type stubs
        return self._page.page_number  # type: ignore[no-any-return, attr-defined]

    def extract_text(self) -> str:
        """Extract text from page.

        Returns:
            Text content of the page, or empty string if no text
        """
        result = self._page.extract_text()
        return result if result is not None else ""

    def extract_words(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Extract words with positioning information.

        Args:
            **kwargs: Additional arguments passed to pdfplumber extract_words()

        Returns:
            List of word dictionaries with keys: text, x0, top, x1, bottom
        """
        result = self._page.extract_words(**kwargs)
        return result if result is not None else []

    def extract_tables(self, table_settings: dict[str, Any] | None = None) -> list[Any]:
        """Extract tables from page.

        Args:
            table_settings: Optional table extraction settings

        Returns:
            List of table objects
        """
        if table_settings:
            result = self._page.extract_tables(table_settings=table_settings)
        else:
            result = self._page.extract_tables()
        return result if result is not None else []

    def find_tables(self, table_settings: dict[str, Any] | None = None) -> list[Any]:
        """Find tables on page without extracting data.

        Args:
            table_settings: Optional table detection settings

        Returns:
            List of table boundary objects
        """
        if table_settings:
            # pdfplumber.Page has find_tables method but it's not in type stubs
            result = self._page.find_tables(table_settings=table_settings)  # type: ignore[attr-defined]
        else:
            result = self._page.find_tables()  # type: ignore[attr-defined]
        return result if result is not None else []

    def crop(self, bbox: tuple[float, float, float, float]) -> PDFPlumberPageAdapter:
        """Crop page to bounding box.

        Args:
            bbox: Bounding box as (x0, y0, x1, y1)

        Returns:
            Cropped page wrapped in adapter
        """
        cropped_page = self._page.crop(bbox)
        return PDFPlumberPageAdapter(cropped_page)


class PDFPlumberDocumentAdapter:
    """Adapter wrapping pdfplumber PDF to implement IPDFDocument protocol."""

    def __init__(self, pdf_doc: PDF):
        """Initialize document adapter.

        Args:
            pdf_doc: pdfplumber PDF object
        """
        self._pdf_doc = pdf_doc
        self._pages_cache: list[PDFPlumberPageAdapter] | None = None

    @property
    def pages(self) -> list[PDFPlumberPageAdapter]:
        """List of pages in document (cached)."""
        if self._pages_cache is None:
            self._pages_cache = [
                PDFPlumberPageAdapter(page) for page in self._pdf_doc.pages
            ]
        return self._pages_cache

    def __enter__(self) -> PDFPlumberDocumentAdapter:
        """Context manager entry.

        Returns:
            Self for context manager usage
        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit.

        Args:
            *args: Exception information if any
        """
        self._pdf_doc.close()


class PDFPlumberReaderAdapter:
    """Adapter implementing IPDFReader using pdfplumber."""

    def open(self, pdf_path: Path) -> PDFPlumberDocumentAdapter:
        """Open PDF document for reading.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDF document adapter

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            IOError: If PDF cannot be opened
        """
        try:
            pdf_doc = pdfplumber.open(pdf_path)
            # pdfplumber.open returns pdfplumber.PDF but type system expects pdfplumber.pdf.PDF
            return PDFPlumberDocumentAdapter(pdf_doc)  # type: ignore[arg-type]
        except FileNotFoundError:
            raise FileNotFoundError(f"PDF file not found: {pdf_path}") from None
        except (OSError, ValueError, TypeError, RuntimeError) as e:
            # Expected errors: file I/O errors, invalid PDF structure, type errors, PDF library errors
            # PDFSyntaxError and other pdfminer exceptions inherit from RuntimeError or are library-specific
            raise OSError(f"Failed to open PDF {pdf_path}: {e}") from e
        except Exception as e:
            # Catch any other PDF library exceptions (PDFSyntaxError, etc.)
            # These are library-specific errors that indicate corrupted/invalid PDFs
            raise OSError(f"Failed to open PDF {pdf_path}: {e}") from e
