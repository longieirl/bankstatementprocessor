"""Column configuration for PDF table extraction.

This module provides column definitions and configuration parsing functionality.
Extracted from pdf_table_extractor.py to break layer violation where app.py
imported configuration from the extraction layer.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# ---- Default Column X boundaries ----
# Note: Additional columns are automatically added during processing:
#   - Filename: Source PDF filename
#   - document_type: Type of financial document ("bank_statement" | "credit_card_statement" | "loan_statement")
#   - transaction_type: Type of transaction ("purchase" | "payment" | "fee" | "refund" | "transfer" | "interest" | "other")
DEFAULT_COLUMNS: dict[str, tuple[int | float, int | float]] = {
    "Date": (26, 78),
    "Details": (78, 255),
    "Debit": (255, 313),
    "Credit": (313, 369),
    "Balance": (369, 434),  # Reduced from 450 to prevent side panel text
}


def get_column_names(
    columns: dict[str, tuple[int | float, int | float]] | None = None,
    include_filename: bool = True,
) -> list[str]:
    """Get column names as a list for DataFrame creation.

    Args:
        columns: Dictionary of column definitions
        include_filename: Whether to include 'Filename' column

    Returns:
        List of column names

    Examples:
        >>> get_column_names()
        ['Date', 'Details', 'Debit', 'Credit', 'Balance', 'Filename']

        >>> get_column_names(include_filename=False)
        ['Date', 'Details', 'Debit', 'Credit', 'Balance']

        >>> custom_cols = {"Date": (0, 100), "Amount": (100, 200)}
        >>> get_column_names(custom_cols)
        ['Date', 'Amount', 'Filename']
    """
    if columns is None:
        columns = DEFAULT_COLUMNS

    column_names = list(columns.keys())

    if include_filename and "Filename" not in column_names:
        column_names.append("Filename")

    return column_names


def parse_columns_from_env(
    env_var: str = "TABLE_COLUMNS",
) -> dict[str, tuple[int | float, int | float]]:
    """Parse column configuration from environment variable.

    Args:
        env_var: Environment variable name (default: "TABLE_COLUMNS")

    Returns:
        Dictionary mapping column names to (x_min, x_max) boundaries

    Environment variable format (JSON):
        TABLE_COLUMNS='{"Date": [26, 78], "Details": [78, 255]}'

    Examples:
        >>> os.environ['TABLE_COLUMNS'] = '{"Date": [0, 100], "Amount": [100, 200]}'
        >>> parse_columns_from_env()
        {'Date': (0, 100), 'Amount': (100, 200)}
    """
    columns_json = os.getenv(env_var)
    if not columns_json:
        return DEFAULT_COLUMNS

    try:
        # Parse JSON from environment variable
        columns_data = json.loads(columns_json)

        # Convert list values to tuples
        columns: dict[str, tuple[int | float, int | float]] = {}
        for name, bounds in columns_data.items():
            if isinstance(bounds, list) and len(bounds) == 2:
                columns[name] = (int(bounds[0]), int(bounds[1]))
            else:
                raise ValueError(
                    f"Invalid bounds format for column '{name}': "
                    f"expected [x_min, x_max]"
                )

        return columns

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(
            "Failed to parse %s environment variable: %s",
            env_var,
            str(e),
            exc_info=True,
        )
        logger.info("Using default columns: %s", list(DEFAULT_COLUMNS.keys()))
        return DEFAULT_COLUMNS


def get_columns_config() -> dict[str, tuple[int | float, int | float]]:
    """Get column configuration from environment or use defaults.

    This is a convenience function that wraps parse_columns_from_env()
    with the default environment variable name.

    Returns:
        Dictionary mapping column names to (x_min, x_max) boundaries

    Examples:
        >>> get_columns_config()
        {'Date': (26, 78), 'Details': (78, 255), ...}
    """
    return parse_columns_from_env("TABLE_COLUMNS")
