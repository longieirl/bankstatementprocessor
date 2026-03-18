"""DataFrame analysis utilities.

This module provides utilities for analyzing pandas DataFrames,
including column summation and column type identification.
"""

from __future__ import annotations

import pandas as pd

from bankstatements_core.domain.currency import to_float


def calculate_column_sum(df: pd.DataFrame, column_name: str) -> float:
    """
    Calculate sum of a column, converting values to float and handling NaN.

    Args:
        df: DataFrame containing the column
        column_name: Name of the column to sum

    Returns:
        Sum of the column values as float

    Examples:
        >>> df = pd.DataFrame({'Amount': ['100.50', '€200', None, '50.25']})
        >>> calculate_column_sum(df, 'Amount')
        350.75
    """
    # Apply handles NaN already, no need for fillna (avoids FutureWarning)
    numeric_series = df[column_name].apply(
        lambda x: to_float(str(x)) if pd.notna(x) else 0.0
    )
    return float(numeric_series.sum())


def is_date_column(col_name: str) -> bool:
    """
    Check if a column name represents a date column.

    Args:
        col_name: Column name to check

    Returns:
        True if column is a date column, False otherwise

    Examples:
        >>> is_date_column('Date')
        True
        >>> is_date_column('date')
        True
        >>> is_date_column('Amount')
        False
    """
    return col_name.lower() == "date"
