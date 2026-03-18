"""Service for filtering transaction rows based on various criteria."""

from __future__ import annotations

import logging

from bankstatements_core.domain import Transaction, dicts_to_transactions, transactions_to_dicts
from bankstatements_core.exceptions import InputValidationError

logger = logging.getLogger(__name__)


class TransactionFilterService:
    """Filters transaction rows based on various criteria.

    This service provides a composable interface for applying different
    filters to transaction data, such as removing empty rows, header rows,
    and rows with invalid dates.

    Note:
        This service accepts list[dict] for backward compatibility but converts
        internally to Transaction objects for type-safe processing. All methods
        maintain the dict-based interface for existing code.
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

    def filter_empty_rows(self, rows: list[dict]) -> list[dict]:
        """Remove rows with no meaningful data.

        A row is considered empty if it has no valid date, details, or
        debit/credit amounts.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of non-empty transaction dicts

        Note:
            Uses Transaction domain model internally for type-safe validation.
        """
        # Convert to domain objects for type-safe processing
        transactions = dicts_to_transactions(rows)

        # Filter using domain methods
        filtered_transactions = [
            tx
            for tx in transactions
            if not self._is_empty_transaction(tx) and not self._is_balance_only_row(tx)
        ]

        removed = len(transactions) - len(filtered_transactions)
        if removed > 0:
            logger.info(f"Filtered out {removed} empty row(s)")

        # Convert back to dicts for backward compatibility
        return transactions_to_dicts(filtered_transactions)

    def filter_header_rows(self, rows: list[dict]) -> list[dict]:
        """Remove header rows that match column names.

        A row is considered a header if at least 50% of its non-empty fields
        contain values that match column names.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of non-header rows
        """
        filtered = [row for row in rows if not self._is_header_row(row)]
        removed = len(rows) - len(filtered)

        if removed > 0:
            logger.info(f"Filtered out {removed} header row(s)")

        return filtered

    def filter_invalid_dates(self, rows: list[dict]) -> list[dict]:
        """Remove rows with invalid or missing date values.

        A row is considered invalid if it has no valid date field or the
        date value doesn't look like an actual date.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of rows with valid dates

        Note:
            Uses Transaction domain model's has_valid_date() method plus
            additional parsing validation.
        """
        # Convert to domain objects
        transactions = dicts_to_transactions(rows)

        # Filter: has valid date AND date value is parseable
        valid_transactions = [
            tx
            for tx in transactions
            if tx.has_valid_date() and self._is_parseable_date(tx.date)
        ]

        removed = len(transactions) - len(valid_transactions)
        if removed > 0:
            logger.info(f"Filtered out {removed} row(s) with invalid dates")

        # Convert back to dicts
        return transactions_to_dicts(valid_transactions)

    def apply_all_filters(self, rows: list[dict]) -> list[dict]:
        """Apply all filters in sequence.

        Filters are applied in order: empty rows, header rows, invalid dates.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of filtered rows
        """
        original_count = len(rows)

        # Apply filters in sequence
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
        """Check if a transaction is empty (no meaningful data).

        Uses domain model's validation methods for type-safe checking.

        Args:
            tx: Transaction domain object

        Returns:
            True if transaction has no meaningful data, False otherwise
        """
        # Use domain model's validation methods
        return not (
            tx.has_valid_date()
            or tx.has_valid_details()
            or tx.is_debit()
            or tx.is_credit()
        )

    def _is_balance_only_row(self, tx: Transaction) -> bool:
        """Check if a row has only balance (likely orphaned/invalid row).

        These rows have:
        - Empty or whitespace-only details
        - No debit amount
        - No credit amount
        - Some text/number in balance field

        Valid "balance-only" rows (which should NOT be filtered) are handled by
        the row classifier - they need Details text (like "BALANCE FORWARD") to
        be classified as transactions. Rows that reach this filter with only
        balance and no details are orphaned/invalid data.

        Args:
            tx: Transaction domain object

        Returns:
            True if row should be filtered (balance-only, no details), False otherwise
        """
        # Must NOT have details, debit, or credit
        if tx.has_valid_details() or tx.is_debit() or tx.is_credit():
            return False

        # If balance is empty, this will be caught by _is_empty_transaction
        if not tx.balance or not tx.balance.strip():
            return False

        # Row has balance but no details/debit/credit
        # These are orphaned balance values (possibly from PDF extraction errors)
        # or footer/disclaimer text that ended up in the Balance column
        return True

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

            # Only check non-empty values
            if value and isinstance(value, str) and value.strip():
                non_empty_fields += 1

                # Check if value matches any column name (case-insensitive)
                value_lower = value.lower()
                for col_name in self._column_names:
                    if (
                        col_name.lower() in value_lower
                        or value_lower in col_name.lower()
                    ):
                        matches += 1
                        break

        # Need at least 50% match and at least 2 matches
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

        # Common non-date words found in bank statements
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

        # If it contains any non-date indicators, it's not a date
        if any(indicator in date_lower for indicator in non_date_indicators):
            return False

        # If it's very long (>25 chars), probably not a date
        if len(date_str) > 25:
            return False

        # If it contains common date indicators, accept it
        # This handles formats like "11 Aug", "01/12/23", "2023-01-15", etc.
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

        # If it's all digits, it might be a date (like "20230115")
        if date_str.replace(" ", "").isdigit():
            return True

        # Default to False for safety
        return False
