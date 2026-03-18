"""Services module for bank statement processing."""

from __future__ import annotations

from bankstatements_core.services.duplicate_detector import DuplicateDetectionService
from bankstatements_core.services.extraction_orchestrator import ExtractionOrchestrator
from bankstatements_core.services.iban_grouping import IBANGroupingService
from bankstatements_core.services.monthly_summary import MonthlySummaryService
from bankstatements_core.services.pdf_discovery import PDFDiscoveryService
from bankstatements_core.services.sorting_service import (
    ChronologicalSortingStrategy,
    NoSortingStrategy,
    SortingStrategy,
    TransactionSortingService,
)
from bankstatements_core.services.totals_calculator import ColumnTotalsService
from bankstatements_core.services.transaction_filter import TransactionFilterService

__all__ = [
    "ChronologicalSortingStrategy",
    "ColumnTotalsService",
    "DuplicateDetectionService",
    "ExtractionOrchestrator",
    "IBANGroupingService",
    "MonthlySummaryService",
    "NoSortingStrategy",
    "PDFDiscoveryService",
    "SortingStrategy",
    "TransactionFilterService",
    "TransactionSortingService",
]
