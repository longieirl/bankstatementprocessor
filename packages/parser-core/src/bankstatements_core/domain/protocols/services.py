"""Service protocols for dependency inversion."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import pandas as pd

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction
    from bankstatements_core.templates.template_model import BankTemplate


class IPDFDiscovery(Protocol):
    """Protocol for discovering PDF files in directories."""

    def discover_pdfs(self, input_dir: Path, recursive: bool = False) -> list[Path]:
        """Discover PDF files in directory."""
        ...


class ITransactionFilter(Protocol):
    """Protocol for filtering transaction rows."""

    def apply_all_filters(self, rows: list[Transaction]) -> list[Transaction]:
        """Apply all configured filters to rows."""
        ...

    def filter_empty_rows(self, rows: list[Transaction]) -> list[Transaction]:
        """Filter out rows with insufficient data."""
        ...

    def filter_header_rows(self, rows: list[Transaction]) -> list[Transaction]:
        """Filter out header rows that were incorrectly extracted."""
        ...


class IIBANGrouping(Protocol):
    """Protocol for grouping transactions by IBAN."""

    def group_by_iban(
        self,
        transactions: list[Transaction],
        pdf_ibans: dict[str, str],
    ) -> dict[str, list[Transaction]]:
        """Group transactions by IBAN suffix (last 4 digits)."""
        ...


class ICardGrouping(Protocol):
    """Protocol for grouping transactions by card number."""

    def group_by_card(
        self,
        transactions: list[Transaction],
        pdf_card_numbers: dict[str, str],
    ) -> dict[str, list[Transaction]]:
        """Group transactions by card suffix (last 4 digits)."""
        ...


class IColumnTotals(Protocol):
    """Protocol for calculating column totals."""

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate totals for configured columns."""
        ...

    def format_totals_row(
        self, totals: dict[str, float], column_names: list[str]
    ) -> list[str]:
        """Format totals as a row matching column structure."""
        ...


class ITemplateDetector(Protocol):
    """Protocol for detecting PDF bank statement templates."""

    def detect_template(self, pdf_path: Path, first_page: Any) -> BankTemplate:
        """Detect template from PDF first page."""
        ...


class IDuplicateDetector(Protocol):
    """Protocol for detecting duplicate transactions."""

    def detect_and_separate(
        self,
        transactions: list[Transaction],
    ) -> tuple[list[Transaction], list[Transaction]]:
        """Separate unique transactions from duplicates."""
        ...


class ITransactionSorting(Protocol):
    """Protocol for sorting transactions."""

    def sort(self, transactions: list[Transaction]) -> list[Transaction]:
        """Sort transactions using configured strategy."""
        ...


class IMonthlySummary(Protocol):
    """Protocol for generating monthly transaction summaries."""

    def generate(self, transactions: list[dict]) -> dict[str, Any]:
        """Generate monthly summary from transactions."""
        ...


class IExpenseAnalysis(Protocol):
    """Protocol for expense analysis service."""

    def analyze(self, transactions: list[dict]) -> dict[str, Any]:
        """Analyze transactions and generate expense insights."""
        ...
