"""Service for filtering transaction rows based on various criteria."""

from __future__ import annotations

import logging

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.exceptions import InputValidationError

logger = logging.getLogger(__name__)


class TransactionFilterService:
    """Filters transactions based on various criteria.

    This service provides a composable interface for applying different
    filters to transaction data, such as removing empty rows, header rows,
    and rows with invalid dates.
    """

    def __init__(self, column_names: list[str]):
        """Initialize the transaction filter service.

        Args:
            column_names: List of column names in the transaction data

        Raises:
            InputValidationError: If column_names is invalid
        """
        if not column_names:
            raise InputValidationError("column_names cannot be empty")
        if not isinstance(column_names, list):
            raise InputValidationError(
                f"column_names must be list, got {type(column_names).__name__}"
            )
        if not all(isinstance(name, str) for name in column_names):
            raise InputValidationError("column_names must contain only strings")
        self._column_names = column_names

    def filter_empty_rows(self, rows: list[Transaction]) -> list[Transaction]:
        """Remove rows with no meaningful data.

        A row is considered empty if it has no valid date, details, or
        debit/credit amounts.

        Args:
            rows: List of Transaction objects

        Returns:
            List of non-empty Transaction objects
        """
        filtered = [
            tx
            for tx in rows
            if not self._is_empty_transaction(tx) and not self._is_balance_only_row(tx)
        ]

        removed = len(rows) - len(filtered)
        if removed > 0:
            logger.info(f"Filtered out {removed} empty row(s)")

        return filtered

    def filter_header_rows(self, rows: list[Transaction]) -> list[Transaction]:
        """Remove header rows that match column names.

        A row is considered a header if at least 50% of its non-empty fields
        contain values that match column names.

        Args:
            rows: List of Transaction objects

        Returns:
            List of non-header Transaction objects
        """
        filtered = [tx for tx in rows if not self._is_header_transaction(tx)]
        removed = len(rows) - len(filtered)

        if removed > 0:
            logger.info(f"Filtered out {removed} header row(s)")

        return filtered

    def filter_invalid_dates(self, rows: list[Transaction]) -> list[Transaction]:
        """Remove rows with invalid or missing date values.

        A row is considered invalid if it has no valid date field or the
        date value doesn't look like an actual date.

        Args:
            rows: List of Transaction objects

        Returns:
            List of Transaction objects with valid dates
        """
        valid = [
            tx
            for tx in rows
            if tx.has_valid_date() and self._is_parseable_date(tx.date)
        ]

        removed = len(rows) - len(valid)
        if removed > 0:
            logger.info(f"Filtered out {removed} row(s) with invalid dates")

        return valid

    def apply_all_filters(self, rows: list[Transaction]) -> list[Transaction]:
        """Apply all filters in sequence.

        Filters are applied in order: empty rows, header rows, invalid dates.

        Args:
            rows: List of Transaction objects

        Returns:
            List of filtered Transaction objects
        """
        original_count = len(rows)

        rows = self.filter_empty_rows(rows)
        rows = self.filter_header_rows(rows)
        rows = self.filter_invalid_dates(rows)

        final_count = len(rows)
        total_removed = original_count - final_count

        if total_removed > 0:
            logger.info(
                f"Total filtering: removed {total_removed} row(s) "
                f"from {original_count} (kept {final_count})"
            )

        return rows

    def _is_empty_transaction(self, tx: Transaction) -> bool:
        """Check if a transaction is empty (no meaningful data)."""
        return not (
            tx.has_valid_date()
            or tx.has_valid_details()
            or tx.is_debit()
            or tx.is_credit()
        )

    def _is_balance_only_row(self, tx: Transaction) -> bool:
        """Check if a row has only balance (likely orphaned/invalid row)."""
        if tx.has_valid_details() or tx.is_debit() or tx.is_credit():
            return False
        if not tx.balance or not tx.balance.strip():
            return False
        return True

    def _is_header_transaction(self, tx: Transaction) -> bool:
        """Check if a Transaction is a header row by inspecting its field values."""
        # Build a dict of only the data columns — exclude metadata fields
        # (source_page, confidence_score, extraction_warnings, document_type,
        # transaction_type) so they don't inflate non_empty_fields and dilute
        # the 50% header-match threshold.
        row = {
            "Date": tx.date,
            "Details": tx.details,
            "Debit": tx.debit,
            "Credit": tx.credit,
            "Balance": tx.balance,
        }
        return self._is_header_row(row)

    def _is_header_row(self, row: dict) -> bool:
        """Check if a row is a header row.

        A row is considered a header if at least 50% of its non-empty fields
        contain values that match column names.

        Args:
            row: Transaction dictionary

        Returns:
            True if row is a header, False otherwise
        """
        matches = 0
        non_empty_fields = 0

        for key, value in row.items():
            if key == "Filename":
                continue

            if value and isinstance(value, str) and value.strip():
                non_empty_fields += 1

                value_lower = value.lower()
                for col_name in self._column_names:
                    if (
                        col_name.lower() in value_lower
                        or value_lower in col_name.lower()
                    ):
                        matches += 1
                        break

        if non_empty_fields >= 2 and matches >= (non_empty_fields / 2):
            return True

        return False

    def _is_parseable_date(self, date_str: str) -> bool:
        """Check if a string looks like it could be a date.

        This does a lightweight check to filter out obvious non-dates like
        "Product", "Total", "Account", etc. without being too strict about
        partial dates like "11 Aug" which are valid bank statement formats.

        Args:
            date_str: String to check

        Returns:
            True if string looks like a date, False otherwise
        """
        if not date_str or not date_str.strip():
            return False

        non_date_indicators = [
            "product",
            "account",
            "total",
            "balance",
            "transaction",
            "statement",
            "details",
            "debit",
            "credit",
            "description",
        ]

        date_lower = date_str.lower()

        if any(indicator in date_lower for indicator in non_date_indicators):
            return False

        if len(date_str) > 25:
            return False

        date_indicators = [
            "/",
            "-",
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]

        if any(indicator in date_lower for indicator in date_indicators):
            return True

        if date_str.replace(" ", "").isdigit():
            return True

        return False
