"""Row Merger Service for bank statement transactions.

This module provides services for merging continuation lines with their parent
transactions, handling FX details, quantity specifications, and other multi-line
transaction data.
"""

from __future__ import annotations

import logging

from bankstatements_core.domain.column_types import (
    find_first_column_of_type,
    get_type_as_string,
)

logger = logging.getLogger(__name__)


class RowMergerService:
    """Service for merging continuation lines with parent transactions.

    Handles merging of:
    - FX (Foreign Exchange) details
    - Quantity specifications
    - Other multi-line transaction descriptions
    - Date carry-forward for grouped transactions
    """

    def __init__(self) -> None:
        """Initialize the row merger service."""
        self._last_transaction_row: dict | None = None

    def merge_continuation_lines(
        self, rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
    ) -> list[dict]:
        """Merge continuation lines with their parent transactions.

        Args:
            rows: List of extracted rows containing transactions and continuation lines
            columns: Column definitions for processing

        Returns:
            List of rows with continuation lines merged into parent transactions

        Examples:
            >>> service = RowMergerService()
            >>> rows = [
            ...     {"Date": "01/01/23", "Details": "Payment", "Debit": "100"},
            ...     {"Date": "", "Details": "FX Rate: 1.23", "Debit": ""}
            ... ]
            >>> merged = service.merge_continuation_lines(rows, columns)
            >>> len(merged)
            1
        """
        if not rows:
            return rows

        # Reset state for this batch
        self._last_transaction_row = None

        # Find description and date columns
        description_col = find_first_column_of_type(columns, "description")
        date_col = find_first_column_of_type(columns, "date")

        if not description_col:
            return rows  # Can't merge without description column

        merged_rows = []
        i = 0

        while i < len(rows):
            current_row = rows[i].copy()
            row_type = self._classify_row_type(current_row, columns)

            if row_type == "transaction":
                # Look ahead for continuation lines
                continuation_parts = []
                j = i + 1

                while j < len(rows):
                    next_row = rows[j]
                    next_type = self._classify_row_type(next_row, columns)

                    if next_type == "continuation":
                        # Extract the continuation text
                        continuation_text = next_row.get(description_col, "").strip()
                        if continuation_text:
                            continuation_parts.append(continuation_text)

                        # If this continuation line has a balance, preserve it
                        current_row = self._preserve_balance_from_continuation(
                            current_row, next_row, columns
                        )

                        j += 1
                    elif next_type == "transaction":
                        # Found next transaction, stop looking for continuations
                        break
                    else:
                        # Other row types (administrative, etc.) - stop looking
                        break

                # Merge continuation parts into the main transaction description
                if continuation_parts:
                    original_desc = current_row.get(description_col, "").strip()
                    merged_desc = original_desc + " " + " ".join(continuation_parts)
                    current_row[description_col] = merged_desc.strip()

                # Store current row as last transaction for date carry-forward
                self._last_transaction_row = current_row.copy()

                merged_rows.append(current_row)
                i = j  # Skip to after the last continuation line

            elif row_type == "continuation":
                # Continuation line without preceding transaction
                # Check if it's missing a date (date grouping pattern)
                if date_col and self._last_transaction_row:
                    current_date = current_row.get(date_col, "").strip()
                    if not current_date:
                        # Carry forward date from last transaction
                        last_date = self._last_transaction_row.get(date_col, "").strip()
                        if last_date:
                            current_row[date_col] = last_date
                            logger.debug(
                                f"Carried forward date '{last_date}' to continuation row"
                            )
                            # Reclassify - it might be a transaction now
                            row_type = self._classify_row_type(current_row, columns)

                if row_type == "transaction":
                    # After date carry-forward, it's now a transaction
                    self._last_transaction_row = current_row.copy()
                    merged_rows.append(current_row)
                else:
                    # Still a continuation - skip orphaned line
                    logger.warning(f"Orphaned continuation line: {current_row}")
                i += 1

            else:
                # Non-transaction, non-continuation row - keep as is
                merged_rows.append(current_row)
                i += 1

        return merged_rows

    def _classify_row_type(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str:
        """Classify row type using the global classifier chain.

        Args:
            row: Dictionary containing row data
            columns: Column definitions for structure analysis

        Returns:
            String classification: 'transaction', 'continuation', etc.
        """
        # Import here to avoid circular dependency
        from bankstatements_core.extraction.row_classification_facade import (
            classify_row_type,
        )

        return classify_row_type(row, columns)

    def _preserve_balance_from_continuation(
        self,
        current_row: dict,
        continuation_row: dict,
        columns: dict[str, tuple[int | float, int | float]],
    ) -> dict:
        """Preserve balance value from continuation line if main row is missing it.

        Args:
            current_row: Main transaction row
            continuation_row: Continuation line row
            columns: Column definitions

        Returns:
            Updated current_row with balance preserved if needed
        """
        for col_name in columns.keys():
            if get_type_as_string(col_name) == "balance":
                balance_value = continuation_row.get(col_name, "").strip()
                if balance_value and not current_row.get(col_name, "").strip():
                    current_row[col_name] = balance_value

        return current_row
