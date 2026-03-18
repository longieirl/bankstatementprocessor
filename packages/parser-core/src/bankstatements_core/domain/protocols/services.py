"""Service protocols for dependency inversion."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import pandas as pd

if TYPE_CHECKING:
    from bankstatements_core.templates.template_model import BankTemplate


class IPDFDiscovery(Protocol):
    """Protocol for discovering PDF files in directories."""

    def discover_pdfs(self, input_dir: Path, recursive: bool = False) -> list[Path]:
        """Discover PDF files in directory.

        Args:
            input_dir: Directory to search for PDFs
            recursive: Whether to search subdirectories recursively

        Returns:
            List of paths to discovered PDF files
        """
        ...


class ITransactionFilter(Protocol):
    """Protocol for filtering transaction rows."""

    def apply_all_filters(self, rows: list[dict]) -> list[dict]:
        """Apply all configured filters to rows.

        Args:
            rows: List of transaction dictionaries

        Returns:
            Filtered list of transactions
        """
        ...

    def filter_empty_rows(self, rows: list[dict]) -> list[dict]:
        """Filter out rows with insufficient data.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of non-empty transactions
        """
        ...

    def filter_header_rows(self, rows: list[dict]) -> list[dict]:
        """Filter out header rows that were incorrectly extracted.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of transactions with header rows removed
        """
        ...


class IIBANGrouping(Protocol):
    """Protocol for grouping transactions by IBAN."""

    def group_by_iban(
        self, transactions: list[dict], pdf_ibans: dict[str, str]
    ) -> dict[str, list[dict]]:
        """Group transactions by IBAN suffix (last 4 digits).

        Args:
            transactions: List of all transactions
            pdf_ibans: Dictionary mapping PDF filenames to IBANs

        Returns:
            Dictionary mapping IBAN suffix to list of transactions
        """
        ...


class IColumnTotals(Protocol):
    """Protocol for calculating column totals."""

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate totals for configured columns.

        Args:
            df: DataFrame containing transaction data

        Returns:
            Dictionary mapping column names to their totals
        """
        ...

    def format_totals_row(
        self, totals: dict[str, float], column_names: list[str]
    ) -> list[str]:
        """Format totals as a row matching column structure.

        Args:
            totals: Dictionary of column totals
            column_names: List of all column names

        Returns:
            List of formatted values for CSV row
        """
        ...


class ITemplateDetector(Protocol):
    """Protocol for detecting PDF bank statement templates."""

    def detect_template(self, pdf_path: Path, first_page: Any) -> "BankTemplate":
        """Detect template from PDF first page.

        Args:
            pdf_path: Path to PDF file
            first_page: First page of PDF (pdfplumber Page object or adapter)

        Returns:
            BankTemplate instance
        """
        ...


class IDuplicateDetector(Protocol):
    """Protocol for detecting duplicate transactions."""

    def detect_and_separate(
        self, transactions: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """Separate unique transactions from duplicates.

        Args:
            transactions: List of all transactions

        Returns:
            Tuple of (unique_transactions, duplicate_transactions)
        """
        ...


class ITransactionSorting(Protocol):
    """Protocol for sorting transactions."""

    def sort(self, transactions: list[dict]) -> list[dict]:
        """Sort transactions using configured strategy.

        Args:
            transactions: List of transactions to sort

        Returns:
            Sorted list of transactions
        """
        ...


class IMonthlySummary(Protocol):
    """Protocol for generating monthly transaction summaries."""

    def generate(self, transactions: list[dict]) -> dict[str, Any]:
        """Generate monthly summary from transactions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with monthly summaries and statistics
        """
        ...


class IExpenseAnalysis(Protocol):
    """Protocol for expense analysis service."""

    def analyze(self, transactions: list[dict]) -> dict[str, Any]:
        """Analyze transactions and generate expense insights.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with expense insights and analysis
        """
        ...
