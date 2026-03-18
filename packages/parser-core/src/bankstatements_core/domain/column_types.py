"""Column type classification for financial data.

This module provides pure functions for identifying and classifying column types
in bank statement tables. Extracted from extraction layer to fix layer violation
where services were importing from extraction.

One sentence: "Defines column type classification for financial data"
"""

from __future__ import annotations

from enum import Enum


class ColumnType(Enum):
    """Semantic types for bank statement table columns."""

    DATE = "date"
    DESCRIPTION = "description"
    DEBIT = "debit"
    CREDIT = "credit"
    BALANCE = "balance"
    OTHER = "other"


# Pattern mappings for each column type
DATE_PATTERNS = ["date", "time", "when"]
DESCRIPTION_PATTERNS = [
    "detail",
    "description",
    "memo",
    "reference",
    "transaction",
    "desc",
]
DEBIT_PATTERNS = ["debit", "withdrawal", "out", "expense", "charge"]
CREDIT_PATTERNS = ["credit", "deposit", "in", "income", "payment"]
BALANCE_PATTERNS = ["balance", "total", "amount", "sum"]


def identify_column_type(column_name: str) -> ColumnType:
    """
    Identify the semantic type of a column based on its name.

    Args:
        column_name: The name of the column to analyze

    Returns:
        ColumnType enum indicating the semantic type

    Examples:
        >>> identify_column_type("Transaction Date")
        ColumnType.DATE
        >>> identify_column_type("Debit €")
        ColumnType.DEBIT
        >>> identify_column_type("Balance")
        ColumnType.BALANCE
    """
    name_lower = column_name.lower()

    # Check date patterns
    if any(pattern in name_lower for pattern in DATE_PATTERNS):
        return ColumnType.DATE

    # Check description patterns
    if any(pattern in name_lower for pattern in DESCRIPTION_PATTERNS):
        return ColumnType.DESCRIPTION

    # Check debit patterns
    if any(pattern in name_lower for pattern in DEBIT_PATTERNS):
        return ColumnType.DEBIT

    # Check credit patterns
    if any(pattern in name_lower for pattern in CREDIT_PATTERNS):
        return ColumnType.CREDIT

    # Check balance patterns
    if any(pattern in name_lower for pattern in BALANCE_PATTERNS):
        return ColumnType.BALANCE

    return ColumnType.OTHER


def get_columns_by_type(
    columns: dict[str, tuple[int, int]], column_type: ColumnType
) -> list[str]:
    """
    Get all column names of a specific semantic type.

    Args:
        columns: Dictionary mapping column names to (x_min, x_max) boundaries
        column_type: The type of columns to find

    Returns:
        List of column names matching the specified type

    Examples:
        >>> columns = {"Date": (0, 50), "Details": (50, 200), "Debit €": (200, 250)}
        >>> get_columns_by_type(columns, ColumnType.DEBIT)
        ['Debit €']
    """
    matching_columns = []
    for col_name in columns.keys():
        if identify_column_type(col_name) == column_type:
            matching_columns.append(col_name)
    return matching_columns


def has_column_types(
    columns: dict[str, tuple[int, int]], required_types: set[ColumnType]
) -> bool:
    """
    Check if columns contain at least one column of each required type.

    Args:
        columns: Dictionary mapping column names to (x_min, x_max) boundaries
        required_types: Set of column types that must be present

    Returns:
        True if all required types are present, False otherwise

    Examples:
        >>> columns = {"Date": (0, 50), "Debit €": (200, 250)}
        >>> has_column_types(columns, {ColumnType.DATE, ColumnType.DEBIT})
        True
        >>> has_column_types(columns, {ColumnType.DATE, ColumnType.CREDIT})
        False
    """
    found_types = set()
    for col_name in columns.keys():
        col_type = identify_column_type(col_name)
        if col_type in required_types:
            found_types.add(col_type)

    return required_types.issubset(found_types)


def get_type_as_string(column_name: str) -> str:
    """
    Get the column type as a string (for backward compatibility).

    This function maintains compatibility with existing code that expects
    string return values instead of enum values.

    Args:
        column_name: The name of the column to analyze

    Returns:
        String representation of the column type

    Examples:
        >>> get_type_as_string("Date")
        'date'
        >>> get_type_as_string("Debit €")
        'debit'
    """
    return identify_column_type(column_name).value


def find_first_column_of_type(
    columns: dict[str, tuple[int | float, int | float]],
    col_type: str,
) -> str | None:
    """
    Find the first column matching a specific semantic type.

    This helper function eliminates the repeated pattern of iterating through
    columns to find one of a specific type.

    Args:
        columns: Dictionary mapping column names to (x_min, x_max) boundaries
        col_type: String representation of the column type to find
                 (e.g., 'date', 'description', 'debit', 'credit')

    Returns:
        The first column name matching the type, or None if not found

    Examples:
        >>> columns = {"Date": (0, 50), "Details": (50, 200), "Debit €": (200, 250)}
        >>> find_first_column_of_type(columns, "description")
        'Details'
        >>> find_first_column_of_type(columns, "credit")
        None
    """
    for col_name in columns.keys():
        if get_type_as_string(col_name) == col_type:
            return col_name
    return None


def find_all_columns_of_type(
    columns: dict[str, tuple[int | float, int | float]],
    col_type: str,
) -> list[str]:
    """
    Find all columns matching a specific semantic type.

    Args:
        columns: Dictionary mapping column names to (x_min, x_max) boundaries
        col_type: String representation of the column type to find

    Returns:
        List of all column names matching the type

    Examples:
        >>> columns = {"Debit €": (0, 50), "Debit USD": (50, 100), "Credit €": (100, 150)}
        >>> find_all_columns_of_type(columns, "debit")
        ['Debit €', 'Debit USD']
    """
    return [
        col_name
        for col_name in columns.keys()
        if get_type_as_string(col_name) == col_type
    ]
