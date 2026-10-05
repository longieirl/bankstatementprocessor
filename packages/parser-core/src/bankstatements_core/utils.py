"""Utility functions for data type conversions and formatting.

This module serves as a facade, re-exporting functionality from focused modules.
For new code, prefer importing directly from the specific modules.

Backward compatibility maintained for existing imports.
"""

from __future__ import annotations

import logging
from pathlib import Path

# Environment parsing - delegate to existing EnvironmentParser
from bankstatements_core.config.environment_parser import EnvironmentParser

# Currency utilities
from bankstatements_core.domain.currency import (
    CurrencyParseError,
    format_currency,
    strip_currency_symbols,
    to_float,
)

# DataFrame utilities
from bankstatements_core.domain.dataframe_utils import (
    calculate_column_sum,
    is_date_column,
)

# File discovery - delegate to existing PDFDiscoveryService
from bankstatements_core.services.pdf_discovery import PDFDiscoveryService

logger = logging.getLogger(__name__)

__all__ = [
    "CurrencyParseError",
    "calculate_column_sum",
    "discover_pdfs",
    "format_currency",
    "is_date_column",
    "log_summary",
    "parse_bool_env",
    "parse_int_env",
    "strip_currency_symbols",
    "to_float",
]


def log_summary(summary: dict) -> None:
    """Log processing summary in structured format."""
    logger.info("========== SUMMARY ==========")
    logger.info("PDFs read: %d", summary["pdf_count"])
    logger.info(
        "PDFs extracted: %d", summary.get("pdfs_extracted", summary["pdf_count"])
    )
    logger.info("Pages read: %d", summary["pages_read"])
    logger.info("Unique transactions: %d", summary["transactions"])
    logger.info("Duplicate transactions: %d", summary["duplicates"])

    if "csv_path" in summary:
        logger.info("CSV output: %s", summary["csv_path"])
    if "json_path" in summary:
        logger.info("JSON output: %s", summary["json_path"])
    if "excel_path" in summary:
        logger.info("Excel output: %s", summary["excel_path"])
    if "duplicates_path" in summary:
        logger.info("Duplicates output: %s", summary["duplicates_path"])
    if "monthly_summary_path" in summary:
        logger.info("Monthly summary output: %s", summary["monthly_summary_path"])

    logger.info("=============================")


def parse_int_env(var_name: str, default: int) -> int:
    """
    Parse an integer environment variable with error handling.

    Delegates to EnvironmentParser.parse_int() for backward compatibility.

    Args:
        var_name: Name of the environment variable
        default: Default value if variable is not set

    Returns:
        Parsed integer value

    Raises:
        ValueError: If the variable value cannot be parsed as integer

    Examples:
        >>> import os
        >>> os.environ['TABLE_TOP'] = '300'
        >>> parse_int_env('TABLE_TOP', 0)
        300
    """
    return EnvironmentParser.parse_int(var_name, default)


def parse_bool_env(var_name: str, default: bool = False) -> bool:
    """
    Parse a boolean environment variable.

    Delegates to EnvironmentParser.parse_bool() for backward compatibility.

    Args:
        var_name: Name of the environment variable
        default: Default value if variable is not set

    Returns:
        Boolean value (True if value.lower() == "true", False otherwise)

    Examples:
        >>> import os
        >>> os.environ['ENABLE_FEATURE'] = 'true'
        >>> parse_bool_env('ENABLE_FEATURE', False)
        True
        >>> parse_bool_env('MISSING_VAR', False)
        False
    """
    return EnvironmentParser.parse_bool(var_name, default)


def discover_pdfs(input_dir: Path, recursive: bool) -> list[Path]:
    """
    Discover PDF files in the given directory.

    Delegates to PDFDiscoveryService.discover() for backward compatibility.

    Args:
        input_dir: Directory to scan for PDF files
        recursive: Whether recursive scan is requested

    Returns:
        Sorted list of PDF file paths
    """
    service = PDFDiscoveryService()
    return service.discover_pdfs(input_dir, recursive)
