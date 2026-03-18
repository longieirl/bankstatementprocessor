"""Totals calculation service for bank transactions.

This module provides a clean service interface for calculating column totals
and formatting totals rows for output.
"""

from __future__ import annotations

import logging

import pandas as pd

from bankstatements_core.utils import calculate_column_sum, is_date_column

logger = logging.getLogger(__name__)


class ColumnTotalsService:
    """
    Service for calculating column totals and formatting totals rows.

    Handles totals calculation with pattern matching and formatting
    for various output formats (CSV, Excel).
    """

    def __init__(self, totals_columns: list[str]):
        """
        Initialize totals calculation service.

        Args:
            totals_columns: List of column patterns to calculate totals for
        """
        self.totals_columns = totals_columns

    def calculate(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate totals for columns matching patterns.

        Args:
            df: DataFrame containing transaction data

        Returns:
            Dictionary mapping column names to their totals
        """
        totals = {}

        for col in df.columns:
            # Check if column matches any totals pattern
            if any(pattern.lower() in col.lower() for pattern in self.totals_columns):
                try:
                    totals[col] = calculate_column_sum(df, col)
                    logger.debug(
                        "Calculated total for column '%s': %.2f", col, totals[col]
                    )
                except (ValueError, TypeError) as e:
                    # Expected errors: non-numeric data, empty column
                    logger.warning(
                        "Cannot calculate total for column '%s': %s. Using 0.0",
                        col,
                        e,
                    )
                    totals[col] = 0.0
                # Let unexpected errors (KeyError, AttributeError, etc.) bubble up

        logger.info(
            "Calculated totals for %d columns matching patterns %s",
            len(totals),
            self.totals_columns,
        )

        return totals

    def format_totals_row(
        self, totals: dict[str, float], all_columns: list[str]
    ) -> list[str]:
        """
        Format totals into a row for CSV/Excel output.

        Args:
            totals: Dictionary of column totals
            all_columns: Ordered list of all columns

        Returns:
            List of formatted values for each column
        """
        totals_row = []

        for col_name in all_columns:
            if col_name in totals:
                # Format numeric total with 2 decimal places
                totals_row.append(f"{totals[col_name]:.2f}")
            elif is_date_column(col_name):
                # Date column gets "TOTAL" label
                totals_row.append("TOTAL")
            else:
                # Other columns are empty
                totals_row.append("")

        return totals_row
