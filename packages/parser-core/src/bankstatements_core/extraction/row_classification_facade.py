"""Row classification facade for PDF extraction.

This module provides a simplified interface for classifying and analyzing
extracted PDF rows. Extracted from pdf_table_extractor.py to improve
separation of concerns.
"""

from __future__ import annotations

from bankstatements_core.extraction.row_classifiers import create_row_classifier_chain

# Create the row classifier chain once at module level for reuse
_ROW_CLASSIFIER_CHAIN = create_row_classifier_chain()


def classify_row_type(
    row: dict, columns: dict[str, tuple[int | float, int | float]]
) -> str:
    """Classify row type using chain of responsibility pattern.

    Classifies rows as 'transaction', 'administrative', 'reference',
    'continuation', or 'metadata'. Delegates to a Chain of Responsibility
    implementation for better maintainability and extensibility.

    Args:
        row: Dictionary containing row data
        columns: Column definitions for structure analysis

    Returns:
        String classification
    """
    return _ROW_CLASSIFIER_CHAIN.classify(row, columns)


def _looks_like_date(text: str) -> bool:
    """Check if text looks like a valid date (backward compatibility wrapper).

    This function now delegates to RowAnalysisService for consistency.

    Args:
        text: Text to check

    Returns:
        True if text appears to be a date
    """
    from bankstatements_core.services.row_analysis import RowAnalysisService

    service = RowAnalysisService()
    return service.looks_like_date(text)


def calculate_row_completeness_score(
    row: dict, columns: dict[str, tuple[int, int]]
) -> float:
    """Score row completeness (backward compatibility wrapper).

    This function now delegates to RowAnalysisService.

    Args:
        row: Dictionary containing row data
        columns: Column definitions for weight calculation

    Returns:
        Float score between 0.0 and 1.0
    """
    from bankstatements_core.services.row_analysis import RowAnalysisService

    service = RowAnalysisService()
    return service.calculate_row_completeness_score(row, columns)
