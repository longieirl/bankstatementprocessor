"""Table detection utilities for PDF analysis.

This module provides functionality to detect transaction tables in PDF pages
using pdfplumber's table detection capabilities.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar

from bankstatements_core.analysis.bbox_utils import BBox, expand_bbox

logger = logging.getLogger(__name__)


@dataclass
class TableDetectionResult:
    """Result of table detection on a PDF page.

    Attributes:
        tables: List of detected table bounding boxes
        page_number: Page number (1-indexed)
        page_height: Height of the page in points
        page_width: Width of the page in points
    """

    tables: list[BBox]
    page_number: int
    page_height: float
    page_width: float


class TableDetector:
    """Detects transaction tables in PDF pages."""

    HEADER_KEYWORDS: ClassVar[list[str]] = [
        "date",
        "details",
        "description",
        "debit",
        "credit",
        "amount",
        "transaction",
        "reference",
        "particulars",
    ]
    TRANSACTION_INDICATORS: ClassVar[list[str]] = [
        "forward",
        "interest",
        "lending",
        "@",
    ]
    FOOTER_KEYWORDS: ClassVar[list[str]] = [
        "continued",
        "overleaf",
        "page",
        "total",
        "balance brought forward",
        "balance carried forward",
        "end of statement",
        "thank you",
        "overdrawn",
        "for important information",
        "standard conditions",
        "regulated by",
        "authorised limit",
    ]

    def __init__(self, min_table_height: float = 50.0):
        """Initialize table detector.

        Args:
            min_table_height: Minimum height in points for a table to be considered
                            valid. Filters out small tables (headers/footers).
        """
        self.min_table_height = min_table_height

    def detect_tables(self, page: Any) -> TableDetectionResult:
        """Detect tables on a PDF page.

        Args:
            page: pdfplumber page object

        Returns:
            TableDetectionResult containing detected tables and page info
        """
        page_num = page.page_number
        page_height = page.height
        page_width = page.width

        logger.debug(
            "Detecting tables on page %s (size: %sx%s)",
            page_num,
            page_width,
            page_height,
        )

        # Use pdfplumber's find_tables
        tables = page.find_tables()

        # Convert to BBox objects and filter by height
        detected_bboxes = []
        for i, table in enumerate(tables):
            bbox = BBox(
                x0=table.bbox[0], y0=table.bbox[1], x1=table.bbox[2], y1=table.bbox[3]
            )

            logger.debug(
                "  Table %s: %s (height=%.1fpx, area=%.0fpx²)",
                i + 1,
                bbox,
                bbox.height,
                bbox.area,
            )

            # Filter by minimum height
            if bbox.height >= self.min_table_height:
                detected_bboxes.append(bbox)
                logger.debug(
                    "    ✓ Table %s accepted (height >= %s)",
                    i + 1,
                    self.min_table_height,
                )
            else:
                logger.debug(
                    "    ✗ Table %s rejected (height %.1f < %s)",
                    i + 1,
                    bbox.height,
                    self.min_table_height,
                )

        # Fallback: If no tables detected with find_tables, try text-based detection
        if not detected_bboxes:
            logger.debug("No tables found with pdfplumber, trying text-based fallback")
            text_table = self._detect_text_based_table(page)
            if text_table:
                detected_bboxes.append(text_table)
                logger.info(
                    "✓ Found table using text-based fallback: %s (height=%.1fpx)",
                    text_table,
                    text_table.height,
                )

        logger.info(
            "Page %s: %s tables detected (%s filtered)",
            page_num,
            len(detected_bboxes),
            len(tables) - len(detected_bboxes),
        )

        return TableDetectionResult(
            tables=detected_bboxes,
            page_number=page_num,
            page_height=page_height,
            page_width=page_width,
        )

    def get_expanded_table_regions(
        self, detection: TableDetectionResult, margin: float = 20.0
    ) -> list[BBox]:
        """Get expanded table regions for overlap detection.

        Creates a buffer zone around each table to catch IBANs that are
        close to but not directly overlapping the table.

        Args:
            detection: TableDetectionResult from detect_tables
            margin: Margin in points to expand on all sides

        Returns:
            List of expanded BBox objects
        """
        expanded = []
        for bbox in detection.tables:
            expanded_bbox = expand_bbox(bbox, margin=margin)
            expanded.append(expanded_bbox)
            logger.debug(
                "Expanded table %s -> %s (margin=%s)", bbox, expanded_bbox, margin
            )

        return expanded

    def get_largest_table(self, detection: TableDetectionResult) -> BBox | None:
        """Get the largest table by area from detection results.

        Args:
            detection: TableDetectionResult from detect_tables

        Returns:
            BBox of largest table, or None if no tables detected
        """
        if not detection.tables:
            return None

        largest = max(detection.tables, key=lambda bbox: bbox.area)
        logger.debug("Largest table: %s (area=%.0fpx²)", largest, largest.area)
        return largest

    def _group_words_by_row(self, words: list[dict]) -> dict[int, list[dict]]:
        """Group pdfplumber word dicts into 5-pixel Y-buckets."""
        y_groups: dict[int, list[dict]] = defaultdict(list)
        for word in words:
            y_key = round(word["top"] / 5) * 5
            y_groups[y_key].append(word)
        return dict(y_groups)

    def _find_header_row(self, y_groups: dict[int, list[dict]]) -> int | None:
        """Find first Y-position matching column header pattern.

        A row matches if it contains no transaction indicators, matches at least
        3 header keywords, and has between 4 and 10 words (inclusive).
        """
        for y_pos, words_at_y in sorted(y_groups.items()):
            text_at_y = " ".join(w["text"].lower() for w in words_at_y)
            if any(ind in text_at_y for ind in self.TRANSACTION_INDICATORS):
                continue
            keyword_count = sum(1 for kw in self.HEADER_KEYWORDS if kw in text_at_y)
            if keyword_count >= 3 and 4 <= len(words_at_y) <= 10:
                logger.debug(
                    "Found header row at Y=%s with %s keywords: %s...",
                    y_pos,
                    keyword_count,
                    text_at_y[:60],
                )
                return y_pos
        return None

    def _find_footer_boundary(
        self, y_groups: dict[int, list[dict]], header_y: int
    ) -> tuple[int | None, list[int]]:
        """Scan rows below header for footer boundary and accumulate table row positions.

        Returns (footer_start_y, data_y_positions) where data_y_positions contains
        only rows BELOW the header (the caller prepends header_y before the len < 2 guard).
        """
        data_y_positions: list[int] = []
        footer_start_y = None
        last_transaction_y = header_y

        for y_pos, words_at_y in sorted(y_groups.items()):
            if y_pos <= header_y:
                continue

            text_at_y = " ".join(w["text"].lower() for w in words_at_y)
            if any(kw in text_at_y for kw in self.FOOTER_KEYWORDS):
                footer_start_y = y_pos
                logger.debug("Footer detected at Y=%s: %s...", y_pos, text_at_y[:50])
                break

            gap_from_last = y_pos - last_transaction_y
            if gap_from_last > 100 and len(words_at_y) < 10:
                footer_start_y = y_pos
                logger.debug(
                    "Large gap (%.1fpx) detected at Y=%s, footer section likely starts here",
                    gap_from_last,
                    y_pos,
                )
                break

            if len(words_at_y) >= 3:
                data_y_positions.append(y_pos)
                last_transaction_y = y_pos

        return footer_start_y, data_y_positions

    def _calculate_bottom_y(
        self, table_y_positions: list[int], footer_start_y: int | None
    ) -> float:
        """Calculate the bottom Y coordinate of the table region."""
        if footer_start_y is not None:
            table_bottom_y = footer_start_y - 10
            logger.debug(
                "Table extended to footer boundary: Y=%.1f (footer starts at Y=%.1f)",
                table_bottom_y,
                footer_start_y,
            )
            return table_bottom_y

        if len(table_y_positions) >= 3:
            sorted_positions = sorted(table_y_positions)
            row_spacings = [
                sorted_positions[i] - sorted_positions[i - 1]
                for i in range(1, len(sorted_positions))
                if sorted_positions[i] - sorted_positions[i - 1] < 50
            ]
            if row_spacings:
                avg_row_spacing = sum(row_spacings) / len(row_spacings)
                bottom_margin = avg_row_spacing * 1.5
                logger.debug(
                    "Calculated bottom margin: %.1fpx (avg row spacing: %.1fpx × 1.5)",  # noqa: RUF001
                    bottom_margin,
                    avg_row_spacing,
                )
            else:
                bottom_margin = 20
                logger.debug("Using fallback bottom margin: 20px")
        else:
            bottom_margin = 20
            logger.debug("Using default bottom margin for single row: 20px")

        table_bottom_y = max(table_y_positions) + bottom_margin
        logger.debug(
            "No footer found, using last transaction + margin: Y=%.1f",
            table_bottom_y,
        )
        return table_bottom_y

    def _detect_text_based_table(self, page: Any) -> BBox | None:
        """Detect table region from text patterns (fallback method).

        For PDFs without explicit table borders, this method:
        1. Looks for column header keywords (Date, Details, Debit, Credit, Balance)
        2. Identifies dense text region INCLUDING and below headers
        3. Calculates table boundaries from text positions

        Args:
            page: pdfplumber page object

        Returns:
            BBox of detected table, or None if no table found
        """
        words = page.extract_words()
        if not words:
            return None

        # Group words by Y-position to find rows
        y_groups = self._group_words_by_row(words)

        header_y = self._find_header_row(y_groups)
        if not header_y:
            logger.debug("No header row found in text")
            return None

        # Find dense text region INCLUDING header and below (transaction rows)
        footer_start_y, data_y_positions = self._find_footer_boundary(
            y_groups, header_y
        )
        table_y_positions = [header_y, *data_y_positions]

        if len(table_y_positions) < 2:  # Need at least header + 1 data row
            logger.debug("No transaction rows found below header")
            return None

        # Calculate table boundaries - START from header row
        # Add small margin (5px) above header to catch all header words
        table_top_y = header_y - 5  # Include margin above header

        table_bottom_y = self._calculate_bottom_y(table_y_positions, footer_start_y)
        logger.debug(
            "Table boundary: Y=%.1f to Y=%.1f (height=%.1fpx, %s rows)",
            table_top_y,
            table_bottom_y,
            table_bottom_y - table_top_y,
            len(table_y_positions),
        )

        # Get X boundaries from all table words (including header)
        table_words = []
        for y_pos in table_y_positions:
            table_words.extend(y_groups[y_pos])

        if not table_words:
            return None

        table_x0 = min(w["x0"] for w in table_words)
        table_x1 = max(w["x1"] for w in table_words)

        bbox = BBox(x0=table_x0, y0=table_top_y, x1=table_x1, y1=table_bottom_y)

        # Validate minimum height
        if bbox.height < self.min_table_height:
            logger.debug(
                "Text-based table too small: height=%.1fpx < %spx",
                bbox.height,
                self.min_table_height,
            )
            return None

        logger.debug(
            "Text-based table detected: %s (height=%.1fpx, header at Y=%s)",
            bbox,
            bbox.height,
            header_y,
        )
        return bbox
