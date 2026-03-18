"""Domain protocols for dependency inversion."""

from bankstatements_core.domain.protocols.file_io import (
    IFileDeleter,
    IFileReader,
    IJsonWriter,
)
from bankstatements_core.domain.protocols.pdf_reader import (
    IPDFDocument,
    IPDFPage,
    IPDFReader,
)
from bankstatements_core.domain.protocols.services import (
    IColumnTotals,
    IDuplicateDetector,
    IIBANGrouping,
    IMonthlySummary,
    IPDFDiscovery,
    ITemplateDetector,
    ITransactionFilter,
    ITransactionSorting,
)

__all__ = [
    "IJsonWriter",
    "IFileDeleter",
    "IFileReader",
    "IPDFReader",
    "IPDFDocument",
    "IPDFPage",
    "IPDFDiscovery",
    "ITransactionFilter",
    "IIBANGrouping",
    "IColumnTotals",
    "ITemplateDetector",
    "IDuplicateDetector",
    "ITransactionSorting",
    "IMonthlySummary",
]
