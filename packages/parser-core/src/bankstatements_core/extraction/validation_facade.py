"""Page validation facade for PDF extraction.

This module provides a simplified interface for validating extracted
page structures. Extracted from pdf_table_extractor.py to improve
separation of concerns.
"""

from __future__ import annotations

from bankstatements_core.extraction.extraction_params import (
    MIN_COLUMN_COVERAGE,
    MIN_HEADER_KEYWORDS,
    MIN_TABLE_ROWS,
    MIN_TRANSACTION_RATIO,
    REQUIRE_AMOUNT_COLUMN,
    REQUIRE_DATE_COLUMN,
)


def validate_page_structure(
    rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
) -> bool:
    """Validate page structure (backward compatibility wrapper).

    This function now delegates to PageValidationService.

    Args:
        rows: List of extracted rows from the page
        columns: Column definitions to validate against

    Returns:
        True if page contains valid table structure
    """
    from bankstatements_core.services.page_validation import PageValidationService

    service = PageValidationService(
        min_table_rows=MIN_TABLE_ROWS,
        min_column_coverage=MIN_COLUMN_COVERAGE,
        min_transaction_ratio=MIN_TRANSACTION_RATIO,
        require_date_column=REQUIRE_DATE_COLUMN,
        require_amount_column=REQUIRE_AMOUNT_COLUMN,
    )

    return service.validate_page_structure(rows, columns)


def calculate_column_coverage(
    rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
) -> float:
    """Calculate column coverage (backward compatibility wrapper).

    This function now delegates to PageValidationService.

    Args:
        rows: List of extracted rows
        columns: Column definitions

    Returns:
        Float between 0.0-1.0 representing column coverage
    """
    from bankstatements_core.services.page_validation import PageValidationService

    service = PageValidationService()
    return service.calculate_column_coverage(rows, columns)


def has_column_type(
    columns: dict[str, tuple[int | float, int | float]],
    required_types: str | list[str],
) -> bool:
    """Check if columns contain required types (backward compatibility wrapper).

    This function now delegates to PageValidationService.

    Args:
        columns: Column definitions
        required_types: Single type string or list of acceptable types

    Returns:
        True if at least one required type is present
    """
    from bankstatements_core.services.page_validation import PageValidationService

    service = PageValidationService()
    return service.has_column_type(columns, required_types)


def detect_table_headers(
    words: list[dict], columns: dict[str, tuple[int | float, int | float]]
) -> bool:
    """Detect table headers (backward compatibility wrapper).

    This function delegates to HeaderDetectionService.

    Args:
        words: List of words from the page
        columns: Expected column structure

    Returns:
        True if table headers are detected
    """
    from bankstatements_core.services.header_detection import HeaderDetectionService

    service = HeaderDetectionService()
    return service.detect_headers(words, columns, min_keywords=MIN_HEADER_KEYWORDS)


def merge_continuation_lines(
    rows: list[dict], columns: dict[str, tuple[int | float, int | float]]
) -> list[dict]:
    """Merge continuation lines (backward compatibility wrapper).

    This function now delegates to RowMergerService.

    Args:
        rows: List of extracted rows containing transactions and continuation lines
        columns: Column definitions for processing

    Returns:
        List of rows with continuation lines merged into parent transactions
    """
    from bankstatements_core.services.row_merger import RowMergerService

    service = RowMergerService()
    return service.merge_continuation_lines(rows, columns)
