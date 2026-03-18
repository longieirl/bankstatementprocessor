"""Row classification using Chain of Responsibility pattern.

This module provides a flexible, extensible way to classify rows in bank statement
tables by applying a chain of specialized classifiers. Each classifier handles one
specific classification rule and can pass to the next classifier if it doesn't match.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from bankstatements_core.extraction.column_identifier import ColumnTypeIdentifier


class RowClassifier(ABC):
    """
    Abstract base class for row classifiers using Chain of Responsibility pattern.

    Each classifier in the chain can either:
    1. Classify the row and return the classification
    2. Pass to the next classifier in the chain
    """

    def __init__(self) -> None:
        """Initialize classifier with no next classifier."""
        self._next_classifier: RowClassifier | None = None

    def set_next(self, classifier: "RowClassifier") -> "RowClassifier":
        """
        Set the next classifier in the chain.

        Args:
            classifier: The next classifier to call if this one doesn't match

        Returns:
            The classifier that was set (for fluent interface)
        """
        self._next_classifier = classifier
        return classifier

    def classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str:
        """
        Classify a row, possibly delegating to the next classifier.

        Args:
            row: Dictionary containing row data
            columns: Column definitions for structure analysis

        Returns:
            Classification string: 'transaction', 'administrative', 'reference',
            'continuation', 'metadata'
        """
        # Try to classify with this classifier
        classification = self._do_classify(row, columns)

        if classification:
            return classification

        # If this classifier didn't match, try the next one
        if self._next_classifier:
            return self._next_classifier.classify(row, columns)

        # No classifier matched (shouldn't happen with proper chain setup)
        return "metadata"

    @abstractmethod
    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """
        Attempt to classify the row.

        Returns:
            Classification string if this classifier can classify the row,
            None if it should pass to the next classifier
        """
        pass

    @staticmethod
    def _get_row_values(row: dict) -> dict[str, str]:
        """Get non-empty values from row (excluding Filename)."""
        return {k: v for k, v in row.items() if v.strip() and k != "Filename"}

    @staticmethod
    def _get_description_text(
        row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str:
        """Extract description text from row."""
        description_col = ColumnTypeIdentifier.find_first_column_of_type(
            columns, "description"
        )
        if description_col:
            return row.get(description_col, "").strip()  # type: ignore[no-any-return]
        return ""

    @staticmethod
    def _get_amount_and_balance_info(
        row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> tuple[bool, bool]:
        """
        Check if row has amount (debit/credit) or balance data.

        Returns:
            Tuple of (has_amount, has_balance)
        """
        row_values = RowClassifier._get_row_values(row)

        balance_columns = ColumnTypeIdentifier.find_all_columns_of_type(
            columns, "balance"
        )
        amount_columns = ColumnTypeIdentifier.find_all_columns_of_type(
            columns, "debit"
        ) + ColumnTypeIdentifier.find_all_columns_of_type(columns, "credit")

        has_balance = any(k in row_values and row_values[k] for k in balance_columns)
        has_amount = any(k in row_values and row_values[k] for k in amount_columns)

        return has_amount, has_balance


class HeaderMetadataClassifier(RowClassifier):
    """Classifies rows that contain column headers or field labels."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect column headers and field labels."""
        row_values = self._get_row_values(row)
        all_text = " ".join(row_values.values()).lower()

        # Check for header patterns in combined text
        header_patterns = [
            r"'?\w*date'?\s*\([^)]*date[^)]*\)",  # 'TxnDate'(transactiondate)
            r"'?\w*date'?\s*\([^)]*\)",  # 'Date'(something)
            r"\btxndate\b",  # TxnDate field
            r"\btransactiondate\b",  # TransactionDate
            r"\bcolumn\s*header\b",  # Column Header
            r"\bfield\s*name\b",  # Field Name
            r"\btable\s*header\b",  # Table Header
            r"'[^']*'\([^)]*\)",  # 'Something'(description)
        ]

        if any(re.search(pattern, all_text) for pattern in header_patterns):
            return "metadata"

        # Check individual columns for header-like content
        for _col_name, col_value in row_values.items():
            col_value_lower = col_value.lower()
            if (
                col_value_lower.startswith("'")
                and "(" in col_value_lower  # 'Field'(description)
                or re.match(
                    r"^\w+(date|time|amount|balance|detail)", col_value_lower
                )  # FieldName patterns
                or col_value_lower
                in [
                    "date",
                    "details",
                    "amount",
                    "balance",
                    "debit",
                    "credit",
                    "reference",
                ]  # Simple headers
            ):
                return "metadata"

        return None


class AdministrativeClassifier(RowClassifier):
    """Classifies administrative entries like 'BALANCE FORWARD', 'Interest Rate'."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect administrative entries with context-aware logic."""
        description_text = self._get_description_text(row, columns)
        has_amount, has_balance = self._get_amount_and_balance_info(row, columns)

        # Strict administrative patterns (always administrative)
        strict_patterns = ["Lending @"]
        if any(pattern in description_text for pattern in strict_patterns):
            return "administrative"

        # Contextual patterns (administrative only under certain conditions)
        # BALANCE FORWARD: Only admin if no balance amount present
        if "BALANCE FORWARD" in description_text and not has_balance:
            return "administrative"

        # Interest Rate: Only admin if no monetary data
        if "Interest Rate" in description_text and not (has_balance or has_amount):
            return "administrative"

        return None


class ReferenceCodeClassifier(RowClassifier):
    """Classifies reference codes (e.g., IE followed by numbers)."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect reference code patterns."""
        description_text = self._get_description_text(row, columns)

        if re.match(r"^IE\d+$", description_text):
            return "reference"

        return None


class FXContinuationClassifier(RowClassifier):
    """Classifies foreign exchange continuation lines."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect FX continuation patterns."""
        description_text = self._get_description_text(row, columns)
        row_values = self._get_row_values(row)

        fx_patterns = [
            r"^\d+\.\d+\s+GBP@$",  # "8.99 GBP@"
            r"^\d+\.\d{6,}$",  # Exchange rates like "0.828571"
            r"^INCL FX FEE\s+[€E]\d+\.\d+$",  # "INCL FX FEE E0.45"
            r"^\d+@\s+\d+\.\d+\s+EACH$",  # "1@ 0.50 EACH"
        ]

        for pattern in fx_patterns:
            if re.match(pattern, description_text):
                # Validate: FX continuations typically have no debit/credit amounts
                amount_columns = ColumnTypeIdentifier.find_all_columns_of_type(
                    columns, "debit"
                ) + ColumnTypeIdentifier.find_all_columns_of_type(columns, "credit")

                has_debit_credit = any(
                    k in row_values and row_values[k] for k in amount_columns
                )

                if not has_debit_credit:
                    return "continuation"

        return None


class TimestampMetadataClassifier(RowClassifier):
    """Classifies timestamp and metadata patterns."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect timestamp patterns."""
        description_text = self._get_description_text(row, columns)

        # Timestamp pattern like "01JAN2023 TIME 14:30"
        if re.search(r"\d{2}[A-Z]{3}\d{2,4}\s+TIME\s+\d{2}:\d{2}", description_text):
            return "metadata"

        return None


class TransactionClassifier(RowClassifier):
    """Classifies transaction rows based on multiple indicators."""

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Detect transaction rows."""
        description_text = self._get_description_text(row, columns)
        row_values = self._get_row_values(row)
        has_amount, has_balance = self._get_amount_and_balance_info(row, columns)

        # Check for transaction prefixes
        has_transaction_prefix = any(
            description_text.startswith(prefix)
            for prefix in ["VDC-", "VDP-", "VDA-", "ATM", "D/D"]
        )

        # Check for meaningful date
        date_columns = ColumnTypeIdentifier.find_all_columns_of_type(columns, "date")

        has_meaningful_date = any(
            k in row_values
            and row_values[k]
            and not any(
                header_pattern in row_values[k].lower()
                for header_pattern in [
                    "txndate",
                    "transactiondate",
                    "field",
                    "column",
                    "amount(",
                    "balance(",
                    "debit(",
                    "credit(",
                    "date(",
                ]
            )
            and self._looks_like_date(row_values[k])
            for k in date_columns
        )

        # Classify as transaction if it has key indicators
        # IMPORTANT: A row must have meaningful content to be a transaction
        # - has_balance alone CAN be sufficient IF there's also description text
        # - Balance-only rows with no description are likely footer/disclaimer text
        if has_amount or has_transaction_prefix or has_meaningful_date:
            return "transaction"

        # Special case: Balance with description (e.g., "BALANCE FORWARD")
        # This is a valid transaction type
        if has_balance and description_text:
            return "transaction"

        # Balance alone without description/date/amount is likely footer text
        # (e.g., disclaimer text that ends up in Balance column due to PDF layout)
        return None

    @staticmethod
    def _looks_like_date(text: str) -> bool:
        """Check if text looks like a valid date."""
        # Common date patterns
        date_patterns = [
            r"^\d{1,2}/\d{1,2}/\d{2,4}$",  # DD/MM/YY or DD/MM/YYYY
            r"^\d{1,2}-\d{1,2}-\d{2,4}$",  # DD-MM-YY or DD-MM-YYYY
            r"^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}$",  # DD MMM YYYY or DD Month YYYY
            r"^\d{1,2}\s+[A-Za-z]{3,9}$",  # DD MMM (without year)
            r"^\d{2}[A-Z]{3}\d{2,4}$",  # DDMMMYY or DDMMMYYYY
        ]
        text = text.strip()
        return any(re.match(pattern, text) for pattern in date_patterns)


class DefaultMetadataClassifier(RowClassifier):
    """
    Default classifier that returns 'metadata' for any unclassified rows.

    This should be the last classifier in the chain.
    """

    def _do_classify(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str | None:
        """Always return metadata as default classification."""
        return "metadata"


def create_row_classifier_chain() -> RowClassifier:
    """
    Create and configure the chain of row classifiers.

    The order matters - classifiers are applied in sequence:
    1. HeaderMetadataClassifier - Detect column headers first
    2. AdministrativeClassifier - Detect administrative entries
    3. ReferenceCodeClassifier - Detect reference codes
    4. FXContinuationClassifier - Detect FX continuation lines
    5. TimestampMetadataClassifier - Detect timestamps
    6. TransactionClassifier - Detect transactions
    7. DefaultMetadataClassifier - Catch-all for anything else

    Returns:
        The head of the classifier chain
    """
    # Create classifiers
    header_classifier = HeaderMetadataClassifier()
    admin_classifier = AdministrativeClassifier()
    reference_classifier = ReferenceCodeClassifier()
    fx_classifier = FXContinuationClassifier()
    timestamp_classifier = TimestampMetadataClassifier()
    transaction_classifier = TransactionClassifier()
    default_classifier = DefaultMetadataClassifier()

    # Build the chain
    header_classifier.set_next(admin_classifier)
    admin_classifier.set_next(reference_classifier)
    reference_classifier.set_next(fx_classifier)
    fx_classifier.set_next(timestamp_classifier)
    timestamp_classifier.set_next(transaction_classifier)
    transaction_classifier.set_next(default_classifier)

    return header_classifier
