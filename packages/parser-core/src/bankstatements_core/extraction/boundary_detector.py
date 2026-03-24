"""Table boundary detection using Template Method pattern.

This module provides intelligent detection of table end boundaries in PDF bank
statements using a multi-criteria approach with 5 detection phases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bankstatements_core.extraction.row_classifiers import RowClassifier, create_row_classifier_chain

logger = logging.getLogger(__name__)


@dataclass
class BoundaryDetectionResult:
    """Result of boundary detection operation.

    Attributes:
        boundary_y: Y-coordinate where table should end
        method: Detection method used (e.g., 'strong_pattern', 'spatial_gap')
        confidence: Confidence level (0.0-1.0) in the detection
    """

    boundary_y: int
    method: str
    confidence: float = 1.0


class TableBoundaryDetector:
    """
    Detects table end boundaries using Template Method pattern.

    Uses a multi-phase detection approach:
    1. Strong textual end indicators (TOTAL, END OF STATEMENT, etc.)
    2. Large spatial gaps between content areas
    3. Complete breakdown of column structure
    4. Ultra-conservative consecutive non-transaction thresholds
    5. Administrative content density analysis
    """

    def __init__(
        self,
        columns: dict[str, tuple[int | float, int | float]],
        fallback_bottom_y: int = 720,
        table_top_y: int = 300,
        min_section_gap: int = 50,
        structure_breakdown_threshold: int = 8,
        dynamic_boundary_threshold: int = 15,
        row_classifier: RowClassifier | None = None,
    ):
        """
        Initialize boundary detector.

        Args:
            columns: Column definitions for row analysis
            fallback_bottom_y: Static boundary to use if no clear end detected
            table_top_y: Top boundary of table area
            min_section_gap: Minimum gap in pixels to consider a section boundary
            structure_breakdown_threshold: Number of empty columns to consider structure broken
            dynamic_boundary_threshold: Consecutive non-transaction rows before ending extraction
            row_classifier: Optional RowClassifier chain; creates default if not provided
        """
        self.columns = columns
        self.fallback_bottom_y = fallback_bottom_y
        self.table_top_y = table_top_y
        self._row_classifier = row_classifier if row_classifier is not None else create_row_classifier_chain()

        # Configuration parameters
        self.min_gap_threshold = min_section_gap
        self.structure_breakdown_threshold = structure_breakdown_threshold
        self.consecutive_threshold = dynamic_boundary_threshold

    def detect_boundary(self, words: list[dict]) -> int:
        """
        Main template method for detecting table end boundary.

        Applies detection phases in sequence, returning as soon as a
        confident boundary is detected.

        Args:
            words: List of all words from the page

        Returns:
            Y-coordinate where table should end
        """
        if not words:
            return self.fallback_bottom_y

        # Phase 0: Group words and find transaction positions
        lines = self._group_words_by_y(words)
        if not lines:
            return self.fallback_bottom_y

        sorted_y_coords = sorted(lines.keys())
        transaction_positions, last_transaction_y = self._find_transaction_positions(
            lines, sorted_y_coords
        )

        if not transaction_positions:
            logger.debug("No transactions found - using fallback boundary")
            return self.fallback_bottom_y

        # Phase 1: Strong end indicators
        result = self._detect_by_strong_patterns(
            lines, sorted_y_coords, last_transaction_y
        )
        if result:
            logger.debug(
                f"Strong end indicator found by {result.method} at Y={result.boundary_y}"
            )
            return result.boundary_y

        # Phase 2: Spatial gaps
        result = self._detect_by_spatial_gaps(
            lines, sorted_y_coords, last_transaction_y
        )
        if result:
            logger.debug(
                f"Spatial gap detected at Y={result.boundary_y} "
                f"(gap={result.confidence}px)"
            )
            return result.boundary_y

        # Phase 3: Column structure breakdown
        result = self._detect_by_structure_breakdown(
            lines, sorted_y_coords, last_transaction_y
        )
        if result:
            logger.debug(
                f"Column structure breakdown detected - ending at Y={result.boundary_y}"
            )
            return result.boundary_y

        # Phase 4: Consecutive non-transactions
        result = self._detect_by_consecutive_non_transactions(
            lines, sorted_y_coords, last_transaction_y
        )
        if result:
            logger.debug(
                f"Ultra-conservative: {result.confidence} consecutive "
                f"non-transaction rows - ending at Y={result.boundary_y}"
            )
            return result.boundary_y

        # No clear end detected - use fallback
        logger.debug("No clear table end detected - using fallback boundary")
        return self.fallback_bottom_y

    def _group_words_by_y(self, words: list[dict]) -> dict[float, list[dict]]:
        """
        Group words by Y-coordinate (rounded).

        Args:
            words: List of word dictionaries with 'top', 'x0', 'text' keys

        Returns:
            Dictionary mapping Y-coordinate to list of words at that Y
        """
        lines: dict[float, list[dict]] = {}
        for w in words:
            if w["top"] >= self.table_top_y:
                y_key = round(w["top"], 0)
                lines.setdefault(y_key, []).append(w)
        return lines

    def _find_transaction_positions(
        self, lines: dict[float, list[dict]], sorted_y_coords: list[float]
    ) -> tuple[list[float], float | None]:
        """
        Find all Y-coordinates that contain transactions.

        Args:
            lines: Words grouped by Y-coordinate
            sorted_y_coords: Sorted list of Y-coordinates

        Returns:
            Tuple of (list of transaction Y-coordinates, last transaction Y)
        """
        transaction_positions = []
        last_transaction_y = None

        for y_coord in sorted_y_coords:
            row = self._build_row_from_words(lines[y_coord])

            if any(row.values()):
                row_type = self._row_classifier.classify(row, self.columns)
                if row_type == "transaction":
                    transaction_positions.append(y_coord)
                    last_transaction_y = y_coord

        return transaction_positions, last_transaction_y

    def _detect_by_strong_patterns(
        self,
        lines: dict[float, list[dict]],
        sorted_y_coords: list[float],
        last_transaction_y: float | None,
    ) -> BoundaryDetectionResult | None:
        """
        Detect boundary using strong textual end indicators.

        Args:
            lines: Words grouped by Y-coordinate
            sorted_y_coords: Sorted list of Y-coordinates
            last_transaction_y: Y-coordinate of last transaction (or None)

        Returns:
            BoundaryDetectionResult if strong pattern found, None otherwise
        """
        strong_end_patterns = [
            "END OF STATEMENT",
            "STATEMENT TOTAL",
            "CLOSING BALANCE",
            "FINAL BALANCE",
            "ACCOUNT TOTAL",
            "*** END ***",
            "STATEMENT CONTINUES",
            "CONTINUED ON NEXT PAGE",
        ]

        for y_coord in sorted_y_coords:
            if last_transaction_y is not None and y_coord <= last_transaction_y:
                continue  # Only look after last transaction

            # Get all text on this line
            line_text = " ".join([w["text"] for w in lines[y_coord]]).upper()

            for pattern in strong_end_patterns:
                if pattern in line_text:
                    return BoundaryDetectionResult(
                        boundary_y=int(y_coord - 10),  # Small buffer before indicator
                        method=f"strong_pattern:{pattern}",
                        confidence=1.0,
                    )

        return None

    def _detect_by_spatial_gaps(
        self,
        lines: dict[float, list[dict]],
        sorted_y_coords: list[float],
        last_transaction_y: float | None,
    ) -> BoundaryDetectionResult | None:
        """
        Detect boundary using large spatial gaps between content areas.

        Args:
            lines: Words grouped by Y-coordinate
            sorted_y_coords: Sorted list of Y-coordinates
            last_transaction_y: Y-coordinate of last transaction (or None)

        Returns:
            BoundaryDetectionResult if spatial gap found, None otherwise
        """
        for i in range(len(sorted_y_coords) - 1):
            current_y = sorted_y_coords[i]
            next_y = sorted_y_coords[i + 1]
            gap = next_y - current_y

            # If there's a large gap after transactions, might indicate end
            if (
                gap >= self.min_gap_threshold
                and last_transaction_y is not None
                and current_y >= last_transaction_y
            ):
                # But only if the content after the gap looks non-transactional
                post_gap_y_coords = [y for y in sorted_y_coords if y >= next_y][:5]
                post_gap_transactions = 0

                for y_coord in post_gap_y_coords:
                    row = self._build_row_from_words(lines[y_coord])

                    if (
                        any(row.values())
                        and self._row_classifier.classify(row, self.columns)
                        == "transaction"
                    ):
                        post_gap_transactions += 1

                # If no transactions found after the gap, consider it a section break
                if post_gap_transactions == 0:
                    return BoundaryDetectionResult(
                        boundary_y=int(current_y + 20),
                        method="spatial_gap",
                        confidence=gap,  # Gap size as confidence indicator
                    )

        return None

    def _detect_by_structure_breakdown(
        self,
        lines: dict[float, list[dict]],
        sorted_y_coords: list[float],
        last_transaction_y: float | None,
    ) -> BoundaryDetectionResult | None:
        """
        Detect boundary when column structure breaks down for extended area.

        Args:
            lines: Words grouped by Y-coordinate
            sorted_y_coords: Sorted list of Y-coordinates
            last_transaction_y: Y-coordinate of last transaction (or None)

        Returns:
            BoundaryDetectionResult if structure breakdown found, None otherwise
        """
        structure_breakdown_count = 0

        for y_coord in sorted_y_coords:
            if last_transaction_y is not None and y_coord <= last_transaction_y:
                continue

            row = self._build_row_from_words(lines[y_coord])

            if any(row.values()):
                # Check if this row has any structure (data in expected columns)
                column_coverage = self._calculate_column_coverage([row])
                if column_coverage < 0.3:  # Less than 30% of columns have data
                    structure_breakdown_count += 1
                else:
                    structure_breakdown_count = 0  # Reset on structured content

            # If structure has broken down for many consecutive rows
            if structure_breakdown_count >= self.structure_breakdown_threshold:
                boundary_y = y_coord - (structure_breakdown_count * 15)
                min_boundary = (
                    int(last_transaction_y + 30)
                    if last_transaction_y is not None
                    else int(boundary_y)
                )
                return BoundaryDetectionResult(
                    boundary_y=max(int(boundary_y), min_boundary),
                    method="structure_breakdown",
                    confidence=float(structure_breakdown_count),
                )

        return None

    def _detect_by_consecutive_non_transactions(
        self,
        lines: dict[float, list[dict]],
        sorted_y_coords: list[float],
        last_transaction_y: float | None,
    ) -> BoundaryDetectionResult | None:
        """
        Detect boundary using ultra-conservative consecutive non-transaction count.

        Args:
            lines: Words grouped by Y-coordinate
            sorted_y_coords: Sorted list of Y-coordinates
            last_transaction_y: Y-coordinate of last transaction (or None)

        Returns:
            BoundaryDetectionResult if threshold reached, None otherwise
        """
        consecutive_non_transaction_count = 0

        for y_coord in sorted_y_coords:
            if last_transaction_y is not None and y_coord <= last_transaction_y:
                continue

            row = self._build_row_from_words(lines[y_coord])

            if any(row.values()):
                row_type = self._row_classifier.classify(row, self.columns)
                if row_type == "transaction":
                    consecutive_non_transaction_count = 0  # Reset - found transaction!
                else:
                    consecutive_non_transaction_count += 1

                    if consecutive_non_transaction_count >= self.consecutive_threshold:
                        boundary_y = (
                            int(last_transaction_y + 60)
                            if last_transaction_y is not None
                            else self.fallback_bottom_y
                        )
                        return BoundaryDetectionResult(
                            boundary_y=boundary_y,
                            method="consecutive_non_transactions",
                            confidence=float(consecutive_non_transaction_count),
                        )

        return None

    def _build_row_from_words(self, words: list[dict]) -> dict[str, str]:
        """
        Build a row dictionary from words by assigning to columns.

        Args:
            words: List of words at the same Y-coordinate

        Returns:
            Dictionary mapping column names to concatenated text
        """
        row = dict.fromkeys(self.columns, "")

        for w in words:
            x0 = w["x0"]
            text = w["text"]
            for col, (xmin, xmax) in self.columns.items():
                if xmin <= x0 < xmax:
                    row[col] += text + " "
                    break

        return {k: v.strip() for k, v in row.items()}

    def _calculate_column_coverage(self, rows: list[dict[str, str]]) -> float:
        """
        Calculate what percentage of columns have data in the given rows.

        Args:
            rows: List of row dictionaries

        Returns:
            Float between 0.0 and 1.0 representing column coverage
        """
        if not rows:
            return 0.0

        total_columns = len(self.columns)
        columns_with_data = set()

        for row in rows:
            for col_name, value in row.items():
                if value and value.strip():
                    columns_with_data.add(col_name)

        return len(columns_with_data) / total_columns if total_columns > 0 else 0.0
