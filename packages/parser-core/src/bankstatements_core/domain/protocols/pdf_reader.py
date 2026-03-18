"""PDF reading protocols for dependency inversion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class IPDFPage(Protocol):
    """Protocol for PDF page operations."""

    @property
    def width(self) -> float:
        """Page width in points."""
        ...

    @property
    def height(self) -> float:
        """Page height in points."""
        ...

    @property
    def page_number(self) -> int:
        """Page number (1-indexed)."""
        ...

    def extract_text(self) -> str:
        """Extract text from page.

        Returns:
            Text content of the page, or empty string if no text
        """
        ...

    def extract_words(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Extract words with positioning information.

        Args:
            **kwargs: Additional extraction arguments (e.g., use_text_flow)

        Returns:
            List of word dictionaries with keys: text, x0, top, x1, bottom
        """
        ...

    def extract_tables(self, table_settings: dict[str, Any] | None = None) -> list[Any]:
        """Extract tables from page.

        Args:
            table_settings: Optional table extraction settings

        Returns:
            List of table objects
        """
        ...

    def find_tables(self, table_settings: dict[str, Any] | None = None) -> list[Any]:
        """Find tables on page without extracting data.

        Args:
            table_settings: Optional table detection settings

        Returns:
            List of table boundary objects
        """
        ...

    def crop(self, bbox: tuple[float, float, float, float]) -> IPDFPage:
        """Crop page to bounding box.

        Args:
            bbox: Bounding box as (x0, y0, x1, y1)

        Returns:
            Cropped page
        """
        ...


class IPDFDocument(Protocol):
    """Protocol for PDF document operations."""

    @property
    def pages(self) -> list[IPDFPage]:
        """List of pages in document."""
        ...

    def __enter__(self) -> IPDFDocument:
        """Context manager entry.

        Returns:
            Self for context manager usage
        """
        ...

    def __exit__(self, *args: Any) -> None:
        """Context manager exit.

        Args:
            *args: Exception information if any
        """
        ...


class IPDFReader(Protocol):
    """Protocol for opening PDF documents."""

    def open(self, pdf_path: Path) -> IPDFDocument:
        """Open PDF document for reading.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDF document interface

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            IOError: If PDF cannot be opened
        """
        ...
