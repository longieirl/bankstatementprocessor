"""Content Density Analysis Service for bank statement extraction.

This module provides services for analyzing transaction density in PDF pages using
sliding window analysis to determine optimal table boundaries.
"""

from __future__ import annotations

import logging

from bankstatements_core.extraction.word_utils import assign_words_to_columns

logger = logging.getLogger(__name__)


class ContentDensityService:
    """Service for analyzing content density in extracted PDF data.

    Uses sliding window analysis to calculate transaction density at different
    Y-coordinates, helping identify optimal table boundaries.
    """

    def __init__(self, window_size: int = 5):
        """Initialize content density service.

        Args:
            window_size: Number of rows to analyze together in sliding window
        """
        self.window_size = window_size

    def analyze_content_density(
        self,
        word_groups: dict[float, list[dict]],
        columns: dict[str, tuple[int | float, int | float]],
    ) -> list[tuple[float, float]]:
        """Calculate transaction density in sliding Y-coordinate windows.

        Args:
            word_groups: Words grouped by Y-coordinate
            columns: Column definitions for row processing

        Returns:
            List of tuples (y_coordinate, density_score)

        Examples:
            >>> service = ContentDensityService(window_size=3)
            >>> word_groups = {100.0: [{"x0": 10, "text": "Data"}]}
            >>> columns = {"Col1": (0, 50)}
            >>> scores = service.analyze_content_density(word_groups, columns)
            >>> len(scores) >= 0
            True
        """
        if not word_groups:
            return []

        # Sort Y coordinates
        sorted_y_coords = sorted(word_groups.keys())
        density_scores = []

        # If we have fewer rows than window size, analyze each row individually
        effective_window_size = min(self.window_size, len(sorted_y_coords))
        if effective_window_size < 2:
            effective_window_size = 1

        for i in range(len(sorted_y_coords) - effective_window_size + 1):
            window_y_coords = sorted_y_coords[i : i + effective_window_size]
            transaction_count = 0
            total_rows = 0

            for y_coord in window_y_coords:
                # Form row from words at this Y coordinate
                row = assign_words_to_columns(word_groups[y_coord], columns)

                if any(row.values()):  # Only count non-empty rows
                    total_rows += 1
                    if self._classify_row_type(row, columns) == "transaction":
                        transaction_count += 1

            # Calculate density for this window
            density = transaction_count / total_rows if total_rows > 0 else 0.0

            # Use appropriate Y coordinate for the window
            if effective_window_size == 1:
                representative_y = window_y_coords[0]
            else:
                representative_y = window_y_coords[effective_window_size // 2]

            density_scores.append((representative_y, density))

        return density_scores

    def _classify_row_type(
        self, row: dict, columns: dict[str, tuple[int | float, int | float]]
    ) -> str:
        """Classify row type using the global classifier chain.

        Args:
            row: Dictionary containing row data
            columns: Column definitions for structure analysis

        Returns:
            String classification: 'transaction', etc.
        """
        from bankstatements_core.extraction.row_classifiers import (  # noqa: PLC0415
            create_row_classifier_chain,
        )

        if not hasattr(self, "_classifier"):
            self._classifier = create_row_classifier_chain()
        return self._classifier.classify(row, columns)
