"""Column analysis service for bank statement processing.

This module provides services for analyzing and processing column data,
including pattern matching, totals calculation, and monthly summaries.
"""

from __future__ import annotations

import logging

import pandas as pd

from bankstatements_core.services.monthly_summary import MonthlySummaryService
from bankstatements_core.utils import calculate_column_sum

logger = logging.getLogger(__name__)


class ColumnAnalysisService:
    """Service for analyzing and processing column data.

    Provides functionality for:
    - Parsing column patterns from configuration
    - Finding columns that match patterns
    - Calculating column totals
    - Generating monthly summaries
    """

    def parse_totals_columns(self, totals_config: str) -> list[str]:
        """
        Parse the totals configuration from environment variable.

        Takes a comma-separated string of column patterns and returns a
        normalized list for pattern matching.

        Args:
            totals_config: Comma-separated list of column names/patterns to total

        Returns:
            List of column name patterns to match (lowercased)

        Examples:
            >>> service = ColumnAnalysisService()
            >>> service.parse_totals_columns("debit,credit,balance")
            ['debit', 'credit', 'balance']
            >>> service.parse_totals_columns("  Debit , Credit  ")
            ['debit', 'credit']
            >>> service.parse_totals_columns("")
            []
        """
        if not totals_config:
            return []

        return [
            pattern.strip().lower()
            for pattern in totals_config.split(",")
            if pattern.strip()
        ]

    def find_matching_columns(
        self, column_names: list[str], patterns: list[str]
    ) -> list[str]:
        """
        Find column names that match the given patterns.

        Uses case-insensitive partial matching to find columns that contain
        any of the specified patterns.

        Args:
            column_names: List of actual column names from CSV
            patterns: List of patterns to match (case-insensitive partial matching)

        Returns:
            List of matching column names (in order of first match)

        Examples:
            >>> service = ColumnAnalysisService()
            >>> columns = ["Date", "Details", "Debit", "Credit", "Balance", "Filename"]
            >>> service.find_matching_columns(columns, ["debit", "credit"])
            ['Debit', 'Credit']
            >>> service.find_matching_columns(columns, ["balance"])
            ['Balance']
            >>> service.find_matching_columns(columns, ["amount"])
            []
        """
        matching_columns = []

        for pattern in patterns:
            for col_name in column_names:
                if pattern in col_name.lower() and col_name not in matching_columns:
                    matching_columns.append(col_name)

        return matching_columns

    def calculate_column_totals(
        self, df: pd.DataFrame, columns_to_total: list[str]
    ) -> dict[str, float]:
        """
        Calculate totals for specified columns using vectorized operations.

        Uses pandas vectorization for better performance. Handles various value
        formats (empty, string with currency symbols, etc.) and gracefully
        handles conversion failures.

        Args:
            df: DataFrame containing transaction data
            columns_to_total: List of column names to calculate totals for

        Returns:
            Dictionary mapping column names to their totals

        Examples:
            >>> service = ColumnAnalysisService()
            >>> df = pd.DataFrame({
            ...     "Debit €": ["10.50", "€20", ""],
            ...     "Credit €": ["100", ""]
            ... })
            >>> service.calculate_column_totals(df, ["Debit €", "Credit €"])
            {'Debit €': 30.5, 'Credit €': 100.0}
            >>> service.calculate_column_totals(df, ["Missing"])
            {}
        """
        totals = {}

        for col_name in columns_to_total:
            if col_name not in df.columns:
                logger.warning("Column '%s' not found in DataFrame", col_name)
                continue

            try:
                totals[col_name] = calculate_column_sum(df, col_name)
            except (ValueError, TypeError) as e:
                # Expected errors: non-numeric data, type conversion failures
                logger.warning(
                    "Failed to calculate total for column '%s': %s. Using 0.0",
                    col_name,
                    e,
                )
                totals[col_name] = 0.0
            # Let unexpected errors bubble up

        return totals

    def generate_monthly_summary(
        self, transactions: list[dict], column_names: list[str]
    ) -> dict:
        """
        Generate monthly summary statistics from transactions.

        Automatically identifies debit and credit columns and delegates to
        MonthlySummaryService for calculation.

        Args:
            transactions: List of transaction dictionaries
            column_names: List of all column names to identify debit/credit columns

        Returns:
            Dictionary with monthly summaries containing:
            - month: Month in YYYY-MM format
            - debit_total: Sum of debit amounts for the month
            - debit_count: Number of debit transactions for the month
            - credit_total: Sum of credit amounts for the month
            - credit_count: Number of credit transactions for the month

        Examples:
            >>> service = ColumnAnalysisService()
            >>> transactions = [
            ...     {"Date": "01/01/2024", "Debit": "100", "Credit": ""},
            ...     {"Date": "15/01/2024", "Debit": "", "Credit": "200"},
            ... ]
            >>> columns = ["Date", "Debit", "Credit"]
            >>> summary = service.generate_monthly_summary(transactions, columns)
            >>> summary["2024-01"]["debit_total"]
            100.0
            >>> summary["2024-01"]["credit_total"]
            200.0
        """
        # Find debit and credit columns
        debit_columns = self.find_matching_columns(column_names, ["debit"])
        credit_columns = self.find_matching_columns(column_names, ["credit"])

        # Use service to generate summary
        service = MonthlySummaryService(debit_columns, credit_columns)
        return service.generate(transactions)
