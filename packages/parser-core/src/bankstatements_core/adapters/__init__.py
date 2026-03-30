"""Adapters for external libraries implementing domain protocols."""

from bankstatements_core.adapters.pdfplumber_adapter import (
    PDFPlumberDocumentAdapter,
    PDFPlumberPageAdapter,
    PDFPlumberReaderAdapter,
)

__all__ = [
    "PDFPlumberDocumentAdapter",
    "PDFPlumberPageAdapter",
    "PDFPlumberReaderAdapter",
]
