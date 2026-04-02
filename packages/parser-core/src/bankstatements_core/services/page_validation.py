"""Page Validation Service for bank statement extraction.

This module provides services for validating PDF page structure before extraction,
ensuring pages contain recognizable table structures with appropriate columns and data.
"""

from __future__ import annotations

import logging

from bankstatements_core.domain.column_types import get_type_as_string
from bankstatements_core.extraction.word_utils import (
    calculate_column_coverage as _calculate_column_coverage_impl,
)

logger = logging.getLogger(__name__)


class PageValidationService:
    """Service for validating PDF page structure.

    Validates pages contain:
    - Sufficient rows
    - Required column coverage
    - Mandatory column types (date, amounts)
    - Minimum transaction ratio
    """

    def __init__(
        self,
        min_table_rows: int = 1,
        min_column_coverage: float = 0.2,
        min_transaction_ratio: float = 0.1,
        require_date_column: bool = False,
        require_amount_column: bool = False,
    ):
        """Initialize page validation service.

        Args:
            min_table_rows: Minimum rows required for valid table
            min_column_coverage: Minimum column coverage ratio (0.0-1.0)
            min_transaction_ratio: Minimum transaction/total rows ratio (0.0-1.0)
            require_date_column: Whether date column is mandatory
            require_amount_column: Whether amount columns are mandatory
        """
        self.min_table_rows = min_table_rows
        self.min_column_coverage = min_column_coverage
        self.min_transaction_ratio = min_transaction_ratio
        self.require_date_column = require_date_column
        self.require_amount_column = require_amount_column

    def validate_page_structure(
        self, rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
    ) -> bool:
        """Validate if a page contains a recognizable table structure.

        Args:
            rows: List of extracted rows from the page
            columns: Column definitions to validate against

        Returns:
            True if page contains valid table structure, False otherwise

        Examples:
            >>> service = PageValidationService(min_table_rows=2)
            >>> rows = [{"Date": "01/01/23", "Details": "Payment"}]
            >>> columns = {"Date": (0, 100), "Details": (100, 200)}
            >>> service.validate_page_structure(rows, columns)
            False
        """
        if len(rows) < self.min_table_rows:
            logger.debug(
                "Page rejected: insufficient rows (%s < %s)",
                len(rows),
                self.min_table_rows,
            )
            return False

        # Check column coverage - how many expected columns have data
        column_coverage = self.calculate_column_coverage(rows, columns)
        if column_coverage < self.min_column_coverage:
            logger.debug(
                "Page rejected: low column coverage (%.1%s < %.1%s)",
                column_coverage,
                self.min_column_coverage,
            )
            return False

        # Check for required column types
        if self.require_date_column and not self.has_column_type(columns, "date"):
            logger.debug("Page rejected: no date column found")
            return False

        if self.require_amount_column and not self.has_column_type(
            columns, ["debit", "credit", "balance"]
        ):
            logger.debug("Page rejected: no amount columns found")
            return False

        # Check for meaningful transaction content
        transaction_rows = sum(
            1 for row in rows if self._classify_row_type(row, columns) == "transaction"
        )

        # Check minimum transaction ratio (configurable)
        if len(rows) > 0:
            transaction_ratio = transaction_rows / len(rows)
            if transaction_ratio < self.min_transaction_ratio:
                logger.debug(
                    "Page rejected: low transaction ratio (%.1%s < %.1%s)",
                    transaction_ratio,
                    self.min_transaction_ratio,
                )
                return False

        logger.debug(
            "Page accepted: %s transactions out of %s rows", transaction_rows, len(rows)
        )
        return True

    def calculate_column_coverage(
        self, rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
    ) -> float:
        """Calculate what percentage of columns have meaningful data.

        Delegates to word_utils.calculate_column_coverage for the canonical implementation.

        Args:
            rows: List of extracted rows
            columns: Column definitions

        Returns:
            Float between 0.0-1.0 representing column coverage

        Examples:
            >>> service = PageValidationService()
            >>> rows = [{"A": "data", "B": ""}, {"A": "", "B": "data"}]
            >>> columns = {"A": (0, 50), "B": (50, 100), "C": (100, 150)}
            >>> service.calculate_column_coverage(rows, columns)
            0.666...
        """
        return _calculate_column_coverage_impl(rows, columns)

    def has_column_type(
        self,
        columns: dict[str, tuple[int | float, int | float]],
        required_types: str | list[str],
    ) -> bool:
        """Check if columns contain required semantic types.

        Args:
            columns: Column definitions
            required_types: Single type string or list of acceptable types

        Returns:
            True if at least one required type is present

        Examples:
            >>> service = PageValidationService()
            >>> columns = {"Date": (0, 50), "Amount": (50, 100)}
            >>> service.has_column_type(columns, "date")
            True
            >>> service.has_column_type(columns, ["debit", "credit"])
            False
        """
        if isinstance(required_types, str):
            required_types = [required_types]

        for col_name in columns.keys():
            col_type = get_type_as_string(col_name)
            if col_type in required_types:
                return True

        return False

    def _classify_row_type(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str:
        """Classify row type using the global classifier chain.

        Args:
            row: Dictionary containing row data
            columns: Column definitions for structure analysis

        Returns:
            String classification: 'transaction', etc.
        """
        from bankstatements_core.extraction.row_classifiers import (  # noqa: PLC0415
            create_row_classifier_chain,
        )

        if not hasattr(self, "_classifier"):
            self._classifier = create_row_classifier_chain()
        return self._classifier.classify(row, columns)
