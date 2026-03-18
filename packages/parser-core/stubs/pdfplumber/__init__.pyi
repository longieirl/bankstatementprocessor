"""Type stubs for pdfplumber library.

This stub file provides type hints for the pdfplumber library
to support static type checking with mypy and pyright.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Re-export Page from page module for compatibility
from pdfplumber.page import Page

class PDF:
    """Represents a PDF document."""

    pages: List[Page]
    metadata: Dict[str, Any]

    def close(self) -> None:
        """Close the PDF file."""
        ...

    def __enter__(self) -> PDF:
        """Context manager entry."""
        ...

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        ...

def open(
    path: Union[str, Path],
    password: Optional[str] = None,
    pages: Optional[List[int]] = None,
    laparams: Optional[Dict[str, Any]] = None,
) -> PDF:
    """Open a PDF file.

    Args:
        path: Path to the PDF file
        password: Optional password for encrypted PDFs
        pages: Optional list of page numbers to load (1-indexed)
        laparams: Optional layout analysis parameters

    Returns:
        A PDF object
    """
    ...
