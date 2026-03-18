"""Content analysis facade for PDF extraction.

This module provides a simplified interface for analyzing content
density in extracted PDFs. Extracted from pdf_table_extractor.py
to improve separation of concerns.
"""

from __future__ import annotations

from bankstatements_core.extraction.extraction_params import SLIDING_WINDOW_SIZE


def analyze_content_density(
    word_groups: dict[float, list[dict]],
    columns: dict[str, tuple[int | float, int | float]],
    window_size: int = SLIDING_WINDOW_SIZE,
) -> list[tuple[float, float]]:
    """Calculate transaction density in sliding windows (backward compat wrapper).

    This function now delegates to ContentDensityService.

    Args:
        word_groups: Words grouped by Y-coordinate
        columns: Column definitions for row processing
        window_size: Number of rows to analyze together

    Returns:
        List of tuples (y_coordinate, density_score)
    """
    from bankstatements_core.services.content_density import ContentDensityService

    service = ContentDensityService(window_size=window_size)
    return service.analyze_content_density(word_groups, columns)
