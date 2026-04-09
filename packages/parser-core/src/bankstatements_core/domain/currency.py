"""Currency parsing and formatting utilities.

This module provides functions for parsing and formatting currency amounts,
handling common currency formats including symbols, thousands separators,
and negative values in parentheses.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class CurrencyParseError(ValueError):
    """Raised when currency parsing fails."""

    pass


def strip_currency_symbols(value: str) -> str:
    """Remove currency symbols and surrounding whitespace from an amount string.

    Strips €, $, £, ¥ and any whitespace characters. Also removes thousands
    separators (commas) to produce a plain numeric string.

    Args:
        value: Raw amount string (e.g. "€1,234.56", "$ 100.00")

    Returns:
        Cleaned string with symbols and commas removed (e.g. "1234.56")
    """
    cleaned = re.sub(r"[€$£¥\s]", "", value)
    return cleaned.replace(",", "")


def to_float(
    value: str | None,
    allow_negative: bool = True,
) -> float | None:
    """
    Convert currency string to float, handling common formats.

    Handles:
    - Currency symbols (€, $, £, etc.)
    - Thousands separators (comma)
    - Leading/trailing whitespace
    - Negative values in parentheses: (100.00) -> -100.00
    - Empty or None values

    Args:
        value: String representation of currency amount (or None)
        allow_negative: Whether to allow negative values (default: True)

    Returns:
        Float value or None if value is empty/invalid

    Examples:
        >>> to_float("€100.50")
        100.5
        >>> to_float("1,234.56")
        1234.56
        >>> to_float("(50.00)")
        -50.0
        >>> to_float("")
        None
    """
    # Handle None
    if value is None:
        return None

    # At this point, mypy knows value is str
    # Strip whitespace
    original_value = value
    value = value.strip()

    # Handle empty after stripping
    if not value:
        return None

    try:
        # Check for negative value in parentheses
        is_negative = False
        if value.startswith("(") and value.endswith(")"):
            is_negative = True
            value = value[1:-1].strip()

        # Remove currency symbols and spaces
        # Supports €, $, £, ¥, and common variations
        value = strip_currency_symbols(value)

        # Handle minus sign
        if value.startswith("-"):
            is_negative = True
            value = value[1:]
        elif value.startswith("+"):
            value = value[1:]

        # Validate we have something left to parse
        if not value:
            return None

        # Convert to float using Decimal for better precision
        decimal_value = Decimal(value)
        float_value = float(decimal_value)

        # Apply negativity
        if is_negative:
            if not allow_negative:
                logger.warning("Negative value not allowed: %s", original_value)
                return None
            float_value = -float_value

        return float_value

    except (ValueError, InvalidOperation) as e:
        logger.debug("Failed to parse currency value '%s': %s", original_value, e)
        return None


def reroute_cr_suffix(row: dict[str, str]) -> None:
    """Move a CR-suffixed Debit value to the Credit column.

    AIB CC statements encode credits (payments/refunds) as amounts suffixed
    with 'CR' (e.g. '300.00CR') in a single Amount column, which the template
    aliases to Debit. This function detects the suffix, strips it, writes the
    clean value to Credit, and clears Debit.

    Args:
        row: Row dictionary (modified in-place)
    """
    debit = row.get("Debit", "")
    if debit.upper().endswith("CR"):
        row["Credit"] = debit[:-2].strip()
        row["Debit"] = ""


def format_currency(
    value: float | None,
    currency_symbol: str = "€",
    decimal_places: int = 2,
) -> str:
    """
    Format float as currency string.

    Args:
        value: Numeric value to format (or None)
        currency_symbol: Currency symbol to use (default: "€")
        decimal_places: Number of decimal places (default: 2)

    Returns:
        Formatted currency string (empty string if value is None)

    Examples:
        >>> format_currency(1234.5)
        '€1,234.50'
        >>> format_currency(-50, "$")
        '-$50.00'
    """
    if value is None:
        return ""

    formatted = f"{abs(value):,.{decimal_places}f}"

    if value < 0:
        return f"-{currency_symbol}{formatted}"
    return f"{currency_symbol}{formatted}"
