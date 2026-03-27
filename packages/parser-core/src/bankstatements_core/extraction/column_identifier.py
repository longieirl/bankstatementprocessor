"""Column identification logic for bank statement tables (backward compatibility).

This module now delegates to the domain layer for actual column type identification.
Maintains backward compatibility by providing the ColumnTypeIdentifier class interface.

The core logic has been moved to src/domain/column_types.py to fix a layer violation
where services were importing from the extraction layer.
"""

from __future__ import annotations

# Import and re-export from domain layer
from bankstatements_core.domain.column_types import (
    ColumnType,
    find_all_columns_of_type,
    find_first_column_of_type,
    get_columns_by_type,
    get_type_as_string,
    has_column_types,
    identify_column_type,
)

__all__ = ["ColumnType", "ColumnTypeIdentifier"]


class ColumnTypeIdentifier:
    """
    Identifies the semantic type of columns in bank statement tables.

    This class now delegates to pure functions in the domain layer
    (src.domain.column_types) for backward compatibility.

    The identification is pattern-based, matching common naming conventions found
    in bank statements across different financial institutions.
    """

    # Pattern mappings for each column type (re-exported from domain)
    from bankstatements_core.domain.column_types import (  # noqa: PLC0415
        BALANCE_PATTERNS,
        CREDIT_PATTERNS,
        DATE_PATTERNS,
        DEBIT_PATTERNS,
        DESCRIPTION_PATTERNS,
    )

    @classmethod
    def identify(cls, column_name: str) -> ColumnType:
        """
        Identify the semantic type of a column based on its name.

        Delegates to domain layer function for actual implementation.

        Args:
            column_name: The name of the column to analyze

        Returns:
            ColumnType enum indicating the semantic type

        Examples:
            >>> ColumnTypeIdentifier.identify("Transaction Date")
            ColumnType.DATE
            >>> ColumnTypeIdentifier.identify("Debit €")
            ColumnType.DEBIT
            >>> ColumnTypeIdentifier.identify("Balance")
            ColumnType.BALANCE
        """
        return identify_column_type(column_name)

    @classmethod
    def get_columns_by_type(
        cls, columns: dict[str, tuple[int, int]], column_type: ColumnType
    ) -> list[str]:
        """
        Get all column names of a specific semantic type.

        Delegates to domain layer function for actual implementation.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries
            column_type: The type of columns to find

        Returns:
            List of column names matching the specified type

        Examples:
            >>> columns = {"Date": (0, 50), "Details": (50, 200), "Debit €": (200, 250)}
            >>> ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.DEBIT)
            ['Debit €']
        """
        return get_columns_by_type(columns, column_type)

    @classmethod
    def has_type(
        cls, columns: dict[str, tuple[int, int]], required_types: set[ColumnType]
    ) -> bool:
        """
        Check if columns contain at least one column of each required type.

        Delegates to domain layer function for actual implementation.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries
            required_types: Set of column types that must be present

        Returns:
            True if all required types are present, False otherwise

        Examples:
            >>> columns = {"Date": (0, 50), "Debit €": (200, 250)}
            >>> ColumnTypeIdentifier.has_type(columns, {ColumnType.DATE, ColumnType.DEBIT})
            True
            >>> ColumnTypeIdentifier.has_type(columns, {ColumnType.DATE, ColumnType.CREDIT})
            False
        """
        return has_column_types(columns, required_types)

    @classmethod
    def get_type_as_string(cls, column_name: str) -> str:
        """
        Get the column type as a string (for backward compatibility).

        Delegates to domain layer function for actual implementation.

        Args:
            column_name: The name of the column to analyze

        Returns:
            String representation of the column type

        Examples:
            >>> ColumnTypeIdentifier.get_type_as_string("Date")
            'date'
            >>> ColumnTypeIdentifier.get_type_as_string("Debit €")
            'debit'
        """
        return get_type_as_string(column_name)

    @classmethod
    def find_first_column_of_type(
        cls,
        columns: dict[str, tuple[int | float, int | float]],
        col_type: str,
    ) -> str | None:
        """
        Find the first column matching a specific semantic type.

        Delegates to domain layer function for actual implementation.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries
            col_type: String representation of the column type to find
                     (e.g., 'date', 'description', 'debit', 'credit')

        Returns:
            The first column name matching the type, or None if not found

        Examples:
            >>> columns = {"Date": (0, 50), "Details": (50, 200), "Debit €": (200, 250)}
            >>> ColumnTypeIdentifier.find_first_column_of_type(columns, "description")
            'Details'
            >>> ColumnTypeIdentifier.find_first_column_of_type(columns, "credit")
            None
        """
        return find_first_column_of_type(columns, col_type)

    @classmethod
    def find_all_columns_of_type(
        cls,
        columns: dict[str, tuple[int | float, int | float]],
        col_type: str,
    ) -> list[str]:
        """
        Find all columns matching a specific semantic type.

        Delegates to domain layer function for actual implementation.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries
            col_type: String representation of the column type to find

        Returns:
            List of all column names matching the type

        Examples:
            >>> columns = {"Debit €": (0, 50), "Debit USD": (50, 100), "Credit €": (100, 150)}
            >>> ColumnTypeIdentifier.find_all_columns_of_type(columns, "debit")
            ['Debit €', 'Debit USD']
        """
        return find_all_columns_of_type(columns, col_type)
