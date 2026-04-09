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
        self,
        rows: list[dict],
        columns: dict[str, tuple[int | float, int | float]],
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

        self._last_transaction_row = None

        description_col = find_first_column_of_type(columns, "description")
        date_col = find_first_column_of_type(columns, "date")

        if not description_col:
            return rows

        merged_rows = []
        i = 0

        while i < len(rows):
            current_row = rows[i].copy()
            row_type = self._classify_row_type(current_row, columns)

            if row_type == "transaction":
                if self._is_date_only_split(current_row, rows, i, date_col, columns):
                    next_row = rows[i + 1].copy()
                    next_row[date_col] = current_row[date_col]
                    rows[i + 1] = next_row
                    logger.debug(
                        "Date-only split row: carried date '%s' into next row",
                        current_row[date_col],
                    )
                    i += 1
                    continue

                current_row, j = self._collect_continuations(
                    current_row, rows, i, description_col, columns
                )
                self._last_transaction_row = current_row.copy()
                merged_rows.append(current_row)
                i = j

            elif row_type == "continuation":
                current_row, row_type = self._handle_orphaned_continuation(
                    current_row, row_type, date_col, columns
                )
                if row_type == "transaction":
                    self._last_transaction_row = current_row.copy()
                    merged_rows.append(current_row)
                else:
                    logger.warning("Orphaned continuation line: %s", current_row)
                i += 1

            else:
                merged_rows.append(current_row)
                i += 1

        return merged_rows

    def _is_date_only_split(
        self,
        current_row: dict,
        rows: list[dict],
        i: int,
        date_col: str | None,
        columns: dict[str, tuple[int | float, int | float]],
    ) -> bool:
        """Return True when this row is a date-only PDF split that should be carried forward.

        Detects AIB CC Y-split rows where the transaction date lands at a slightly
        different Y-coordinate, causing RowBuilder to emit a standalone date-only row.
        """
        desc_col = find_first_column_of_type(columns, "description")
        return bool(
            date_col
            and desc_col
            and current_row.get(date_col, "").strip()
            and not current_row.get(desc_col, "").strip()
            and self._is_date_only_row(current_row, columns)
            and i + 1 < len(rows)
            and self._classify_row_type(rows[i + 1], columns) == "transaction"
            and not rows[i + 1].get(date_col, "").strip()
        )

    def _collect_continuations(
        self,
        current_row: dict,
        rows: list[dict],
        i: int,
        description_col: str,
        columns: dict[str, tuple[int | float, int | float]],
    ) -> tuple[dict, int]:
        """Scan ahead and merge any continuation lines into current_row.

        Returns the updated row and the index of the next unprocessed row.
        """
        continuation_parts: list[str] = []
        j = i + 1

        while j < len(rows):
            next_row = rows[j]
            next_type = self._classify_row_type(next_row, columns)

            if next_type == "continuation":
                text = next_row.get(description_col, "").strip()
                if text:
                    continuation_parts.append(text)
                current_row = self._preserve_balance_from_continuation(
                    current_row, next_row, columns
                )
                j += 1
            else:
                break

        if continuation_parts:
            original_desc = current_row.get(description_col, "").strip()
            current_row[description_col] = (
                original_desc + " " + " ".join(continuation_parts)
            ).strip()

        return current_row, j

    def _handle_orphaned_continuation(
        self,
        current_row: dict,
        row_type: str,
        date_col: str | None,
        columns: dict[str, tuple[int | float, int | float]],
    ) -> tuple[dict, str]:
        """Attempt to promote an orphaned continuation by carrying forward the last date."""
        if (
            date_col
            and self._last_transaction_row
            and not current_row.get(date_col, "").strip()
        ):
            last_date = self._last_transaction_row.get(date_col, "").strip()
            if last_date:
                current_row[date_col] = last_date
                logger.debug("Carried forward date '%s' to continuation row", last_date)
                row_type = self._classify_row_type(current_row, columns)
        return current_row, row_type

    def _is_date_only_row(
        self,
        row: dict,
        columns: dict[str, tuple[int | float, int | float]],
    ) -> bool:
        """Return True if the row contains only date-column values and nothing else.

        Used to detect AIB CC Y-split rows where the Transaction Date lands at a
        slightly different Y-coordinate than the Posting Date / Details / Amount,
        causing RowBuilder to emit a standalone date-only row.

        Args:
            row: Row dictionary to inspect
            columns: Column definitions

        Returns:
            True if all non-empty, non-Filename values belong to date-type columns
        """
        from bankstatements_core.domain.column_types import (  # noqa: PLC0415
            get_type_as_string,
        )

        non_empty = {k: v for k, v in row.items() if v.strip() and k != "Filename"}
        if not non_empty:
            return False
        return all(get_type_as_string(k) == "date" for k in non_empty)

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
        from bankstatements_core.extraction.row_classifiers import (  # noqa: PLC0415
            create_row_classifier_chain,
        )

        if not hasattr(self, "_classifier"):
            self._classifier = create_row_classifier_chain()
        return self._classifier.classify(row, columns)

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
