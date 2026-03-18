"""Totals column configuration parsing.

This module provides functionality to parse and validate column totals
configuration from environment variables or configuration strings.

Extracted from processor.py to break layer violation where app.py
imported configuration parsing from the orchestration layer.
"""

from __future__ import annotations


def parse_totals_columns(totals_config: str) -> list[str]:
    """
    Parse the totals configuration from environment variable or config string.

    Args:
        totals_config: Comma-separated list of column names/patterns to total
                      Example: "debit,credit" or "Debit €,Credit €"

    Returns:
        List of column name patterns to match (lowercased for case-insensitive matching)

    Examples:
        >>> parse_totals_columns("debit,credit")
        ['debit', 'credit']

        >>> parse_totals_columns("Debit €, Credit €, Balance €")
        ['debit €', 'credit €', 'balance €']

        >>> parse_totals_columns("")
        []
    """
    if not totals_config:
        return []

    # Split by comma, strip whitespace, convert to lowercase for case-insensitive matching
    return [col.strip().lower() for col in totals_config.split(",") if col.strip()]
