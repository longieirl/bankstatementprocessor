"""Column boundary detection for PDF table analysis.

This module provides automatic detection of column boundaries from table content
by clustering X-coordinates of words.
"""

import logging
from typing import Any

from bankstatements_core.analysis.bbox_utils import BBox

logger = logging.getLogger(__name__)


class ColumnAnalyzer:
    """Automatically detect column boundaries from table content."""

    def __init__(
        self,
        x_tolerance: float = 3.0,
        min_cluster_size: int = 2,
        gap_threshold: float = 20.0,
    ):
        """Initialize column analyzer.

        Args:
            x_tolerance: Tolerance for grouping X coordinates into clusters
            min_cluster_size: Minimum number of words to form a cluster
            gap_threshold: Minimum gap between clusters to create boundary
        """
        self.x_tolerance = x_tolerance
        self.min_cluster_size = min_cluster_size
        self.gap_threshold = gap_threshold

    def analyze_columns(
        self, page: Any, table_bbox: BBox
    ) -> dict[str, tuple[float, float]]:
        """Analyze table and detect column boundaries.

        Args:
            page: pdfplumber page object
            table_bbox: Bounding box of table to analyze

        Returns:
            Dictionary mapping column names to (x_min, x_max) tuples
        """
        logger.debug(f"Analyzing columns in table {table_bbox}")

        # Extract words within table bbox
        words = page.extract_words(
            x_tolerance=self.x_tolerance, y_tolerance=3.0, keep_blank_chars=False
        )

        # Filter words inside table
        table_words = [
            word
            for word in words
            if (
                table_bbox.x0 <= word["x0"] <= table_bbox.x1
                and table_bbox.y0 <= word["top"] <= table_bbox.y1
            )
        ]

        if not table_words:
            logger.warning("No words found in table region")
            return {}

        logger.debug(f"Found {len(table_words)} words in table region")

        # Find header row first
        header_words = self._find_header_words(table_words, table_bbox)

        if header_words:
            # Strategy: Use header words to define columns
            logger.debug(f"Using {len(header_words)} header words to define columns")
            boundaries, column_names = self._create_columns_from_headers(
                header_words, table_bbox
            )
        else:
            # Fallback: Use transaction data clustering
            logger.debug("No headers found, using transaction data for columns")
            clusters = self._cluster_x_coordinates(table_words)
            boundaries = self._detect_boundaries_from_clusters(clusters)
            column_names = [f"Column{i+1}" for i in range(len(boundaries))]

        logger.debug(f"Detected {len(boundaries)} column boundaries")

        # Build result dictionary
        columns = {}
        for i, (x_min, x_max) in enumerate(boundaries):
            column_name = column_names[i] if i < len(column_names) else f"Column{i+1}"
            columns[column_name] = (x_min, x_max)
            logger.debug(f"  {column_name}: ({x_min:.1f}, {x_max:.1f})")

        logger.info(f"Detected {len(columns)} columns")
        return columns

    def _cluster_x_coordinates(self, words: list[dict]) -> list[float]:
        """Cluster word X coordinates to find column alignment points.

        Args:
            words: List of word dictionaries with x0 coordinates

        Returns:
            List of cluster center X coordinates, sorted
        """
        if not words:
            return []

        # Collect all X coordinates (left edges)
        x_coords = sorted([word["x0"] for word in words])

        # Cluster using simple tolerance-based grouping
        clusters = []
        current_cluster = [x_coords[0]]

        for x in x_coords[1:]:
            if x - current_cluster[-1] <= self.x_tolerance:
                current_cluster.append(x)
            else:
                # End current cluster, start new one
                if len(current_cluster) >= self.min_cluster_size:
                    cluster_center = sum(current_cluster) / len(current_cluster)
                    clusters.append(cluster_center)
                current_cluster = [x]

        # Don't forget last cluster
        if len(current_cluster) >= self.min_cluster_size:
            cluster_center = sum(current_cluster) / len(current_cluster)
            clusters.append(cluster_center)

        logger.debug(
            f"Clustered {len(x_coords)} X-coords into {len(clusters)} clusters"
        )
        return sorted(clusters)

    def _detect_boundaries_from_clusters(
        self, clusters: list[float]
    ) -> list[tuple[float, float]]:
        """Detect column boundaries from cluster centers.

        Args:
            clusters: List of cluster center X coordinates

        Returns:
            List of (x_min, x_max) tuples representing column boundaries
        """
        if not clusters:
            return []

        boundaries = []

        # First column starts at first cluster
        for i in range(len(clusters)):
            x_min = clusters[i]

            # Find end of column
            if i < len(clusters) - 1:
                # Gap to next cluster
                gap = clusters[i + 1] - clusters[i]

                if gap >= self.gap_threshold:
                    # Significant gap - column ends midway
                    x_max = clusters[i] + (gap / 2)
                else:
                    # Small gap - columns are close, use midpoint
                    x_max = (clusters[i] + clusters[i + 1]) / 2
            # Last column - extend to reasonable width
            elif i > 0:
                avg_width = (clusters[i] - clusters[0]) / i
                x_max = clusters[i] + avg_width
            else:
                x_max = clusters[i] + 100  # Default width

            boundaries.append((x_min, x_max))

        return boundaries

    def _find_header_words(
        self, table_words: list[dict], table_bbox: BBox
    ) -> list[dict]:
        """Find words in the header row of the table.

        Args:
            table_words: Words within table
            table_bbox: Table bounding box

        Returns:
            List of words in the first row (header)
        """
        if not table_words:
            return []

        # Find the first row (lowest Y position) - this is the header
        # Group by Y position to identify distinct rows
        min_y = min(word["top"] for word in table_words)

        # Header words are within 5px of the minimum Y (same row)
        header_threshold = min_y + 5

        header_words = [word for word in table_words if word["top"] <= header_threshold]

        logger.debug(
            f"Found {len(header_words)} words in header row "
            f"(Y={min_y:.1f}, threshold={header_threshold:.1f})"
        )
        return header_words

    def _assign_column_names(
        self, boundaries: list[tuple[float, float]], header_words: list[dict]
    ) -> list[str]:
        """Assign names to columns based on header words.

        Strategy: Each header word should be assigned to its BEST matching column only.
        Groups adjacent header words that belong together (e.g., "Debit" + "€").

        Args:
            boundaries: List of (x_min, x_max) column boundaries
            header_words: Words from header row

        Returns:
            List of column names (same length as boundaries)
        """
        if not header_words:
            return [f"Column{i+1}" for i in range(len(boundaries))]

        # Sort header words by X position
        header_words_sorted = sorted(header_words, key=lambda w: w["x0"])

        # Group adjacent words (within 10px) into multi-word headers
        word_groups = []
        current_group = [header_words_sorted[0]]

        for word in header_words_sorted[1:]:
            # If word is close to previous word (within 10px), add to current group
            prev_word = current_group[-1]
            if word["x0"] - prev_word["x1"] <= 10:
                current_group.append(word)
            else:
                # Start new group
                word_groups.append(current_group)
                current_group = [word]

        # Don't forget last group
        word_groups.append(current_group)

        # Assign each word group to the best matching column boundary
        column_names: list[str | None] = [None] * len(boundaries)

        for group in word_groups:
            # Calculate group center
            group_x0 = min(w["x0"] for w in group)
            group_x1 = max(w["x1"] for w in group)
            group_center = (group_x0 + group_x1) / 2

            # Find best matching boundary (closest center)
            best_col_idx = None
            min_distance = float("inf")

            for col_idx, (x_min, x_max) in enumerate(boundaries):
                col_center = (x_min + x_max) / 2
                distance = abs(group_center - col_center)

                # Only consider if group is reasonably close to column
                if distance < 100 and distance < min_distance:
                    min_distance = distance
                    best_col_idx = col_idx

            if best_col_idx is not None:
                # Concatenate words in group
                name = " ".join(w["text"] for w in group)
                column_names[best_col_idx] = name

                logger.debug(
                    f"Column {best_col_idx} [{boundaries[best_col_idx][0]:.1f}, "
                    f"{boundaries[best_col_idx][1]:.1f}]: '{name}'"
                )

        # Fill in any unassigned columns with generic names
        result_names: list[str] = []
        for i in range(len(column_names)):
            name_val = column_names[i]
            if name_val is None:
                name = f"Column{i+1}"
                result_names.append(name)
                logger.debug(
                    f"Column {i} [{boundaries[i][0]:.1f}, {boundaries[i][1]:.1f}]: "
                    f"'{name}' (no match)"
                )
            else:
                result_names.append(name_val)

        return result_names

    def _resolve_overlapping_boundaries(
        self, boundaries: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Resolve overlapping column boundaries.

        When columns overlap, adjust boundaries so column i ends just before
        column i+1 starts (1px gap to prevent extraction issues).

        Args:
            boundaries: List of (x_min, x_max) tuples that may overlap

        Returns:
            List of non-overlapping (x_min, x_max) tuples
        """
        if len(boundaries) <= 1:
            return boundaries

        resolved = []

        for i in range(len(boundaries)):
            x_min, x_max = boundaries[i]

            if i < len(boundaries) - 1:
                # Check if this column overlaps with next
                next_x_min, next_x_max = boundaries[i + 1]

                if x_max > next_x_min:
                    # Overlap detected - column should end just before next starts
                    # Leave 1px gap to avoid extraction ambiguity
                    new_x_max = next_x_min - 1
                    logger.debug(
                        f"Overlap detected: Column {i} [{x_min:.1f}, {x_max:.1f}] "
                        f"overlaps Column {i+1} [{next_x_min:.1f}, {next_x_max:.1f}]"
                    )
                    logger.debug(
                        f"  Adjusting Column {i} x_max: {x_max:.1f} -> {new_x_max:.1f}"
                    )
                    x_max = new_x_max

            resolved.append((x_min, x_max))

        return resolved

    def _create_columns_from_headers(
        self, header_words: list[dict], table_bbox: BBox
    ) -> tuple[list[tuple[float, float]], list[str]]:
        """Create column boundaries and names directly from header words.

        Args:
            header_words: Words from header row
            table_bbox: Table bounding box

        Returns:
            Tuple of (boundaries, column_names)
        """
        # Sort header words by X position
        header_words_sorted = sorted(header_words, key=lambda w: w["x0"])

        # Group adjacent words (within 10px) into multi-word headers
        word_groups = []
        current_group = [header_words_sorted[0]]

        for word in header_words_sorted[1:]:
            prev_word = current_group[-1]
            if word["x0"] - prev_word["x1"] <= 10:
                current_group.append(word)
            else:
                word_groups.append(current_group)
                current_group = [word]
        word_groups.append(current_group)

        logger.debug(
            f"Grouped {len(header_words)} header words into {len(word_groups)} columns"
        )

        # Create boundaries and names from word groups
        boundaries = []
        column_names = []

        for group in word_groups:
            # Column starts slightly before first word (to catch content left of header)
            x_min = min(w["x0"] for w in group) - 5
            # Column extends to last word's right edge
            x_max = max(w["x1"] for w in group)

            # Extend x_max to include content below this header
            # (add reasonable padding, e.g., 50px)
            x_max += 50

            # Ensure x_min doesn't go negative
            x_min = max(0, x_min)

            boundaries.append((x_min, x_max))

            # Concatenate words for column name
            name = " ".join(w["text"] for w in group)
            column_names.append(name)

            logger.debug(f"  Column: '{name}' at [{x_min:.1f}, {x_max:.1f}]")

        # Resolve overlaps by adjusting boundaries
        boundaries = self._resolve_overlapping_boundaries(boundaries)

        # Log adjusted boundaries
        for i, (x_min, x_max) in enumerate(boundaries):
            if i < len(column_names):
                logger.debug(
                    f"  Adjusted '{column_names[i]}': [{x_min:.1f}, {x_max:.1f}]"
                )

        return boundaries, column_names
