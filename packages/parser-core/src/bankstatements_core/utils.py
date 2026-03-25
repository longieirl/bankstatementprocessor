"""Utility functions for data type conversions and formatting.

This module serves as a facade, re-exporting functionality from focused modules.
For new code, prefer importing directly from the specific modules.

Backward compatibility maintained for existing imports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

# Environment parsing - delegate to existing EnvironmentParser
from bankstatements_core.config.environment_parser import EnvironmentParser

# Currency utilities
from bankstatements_core.domain.currency import (
    CurrencyParseError,
    format_currency,
    to_float,
)

# DataFrame utilities
from bankstatements_core.domain.dataframe_utils import (
    calculate_column_sum,
    is_date_column,
)

# File discovery - delegate to existing PDFDiscoveryService
from bankstatements_core.services.pdf_discovery import PDFDiscoveryService

if TYPE_CHECKING:
    from bankstatements_core.entitlements import Entitlements

logger = logging.getLogger(__name__)

__all__ = [
    "CurrencyParseError",
    "to_float",
    "format_currency",
    "calculate_column_sum",
    "is_date_column",
    "parse_int_env",
    "parse_bool_env",
    "discover_pdfs",
    "log_summary",
]


def log_summary(summary: dict) -> None:
    """Log processing summary in structured format."""
    logger.info("========== SUMMARY ==========")
    logger.info("PDFs read: %d", summary["pdf_count"])
    logger.info("PDFs extracted: %d", summary.get("pdfs_extracted", summary["pdf_count"]))
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


def discover_pdfs(
    input_dir: Path, recursive: bool, entitlements: "Entitlements"
) -> list[Path]:
    """
    Discover PDF files with entitlement enforcement for recursive scanning.

    Delegates to PDFDiscoveryService.discover() for backward compatibility.

    This function enforces tier-based access control for recursive directory
    scanning. FREE tier users can only scan the top-level directory, while
    PAID tier users can recursively scan subdirectories.

    Args:
        input_dir: Directory to scan for PDF files
        recursive: Whether recursive scan is requested
        entitlements: Entitlements to enforce

    Returns:
        Sorted list of PDF file paths

    Raises:
        EntitlementError: If recursive scan requested but not allowed

    Examples:
        >>> from bankstatements_core.entitlements import Entitlements
        >>> from pathlib import Path
        >>> # FREE tier - recursive blocked
        >>> ent = Entitlements.free_tier()
        >>> pdfs = discover_pdfs(Path("input"), recursive=False, entitlements=ent)
        >>> # PAID tier - recursive allowed
        >>> ent = Entitlements.paid_tier()
        >>> pdfs = discover_pdfs(Path("input"), recursive=True, entitlements=ent)
    """
    service = PDFDiscoveryService(entitlements)
    return service.discover_pdfs(input_dir, recursive)
