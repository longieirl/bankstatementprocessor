"""Table detection utilities for PDF analysis.

This module provides functionality to detect transaction tables in PDF pages
using pdfplumber's table detection capabilities.
"""

import logging
from dataclasses import dataclass
from typing import Any

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
            f"Detecting tables on page {page_num} (size: {page_width}x{page_height})"
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
                f"  Table {i+1}: {bbox} (height={bbox.height:.1f}px, area={bbox.area:.0f}px²)"
            )

            # Filter by minimum height
            if bbox.height >= self.min_table_height:
                detected_bboxes.append(bbox)
                logger.debug(
                    f"    ✓ Table {i+1} accepted (height >= {self.min_table_height})"
                )
            else:
                logger.debug(
                    f"    ✗ Table {i+1} rejected (height {bbox.height:.1f} < {self.min_table_height})"
                )

        # Fallback: If no tables detected with find_tables, try text-based detection
        if not detected_bboxes:
            logger.debug("No tables found with pdfplumber, trying text-based fallback")
            text_table = self._detect_text_based_table(page)
            if text_table:
                detected_bboxes.append(text_table)
                logger.info(
                    f"✓ Found table using text-based fallback: {text_table} "
                    f"(height={text_table.height:.1f}px)"
                )

        logger.info(
            f"Page {page_num}: {len(detected_bboxes)} tables detected "
            f"({len(tables) - len(detected_bboxes)} filtered)"
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
            logger.debug(f"Expanded table {bbox} -> {expanded_bbox} (margin={margin})")

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
        logger.debug(f"Largest table: {largest} (area={largest.area:.0f}px²)")
        return largest

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
        from collections import defaultdict

        # Stricter keywords that are more likely to be column headers
        # Avoid words that commonly appear in transaction descriptions
        HEADER_KEYWORDS = [
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

        # Words that suggest it's a transaction, not a header
        TRANSACTION_INDICATORS = ["forward", "interest", "lending", "@"]

        words = page.extract_words()
        if not words:
            return None

        # Group words by Y-position to find rows
        y_groups = defaultdict(list)
        for word in words:
            y_key = round(word["top"] / 5) * 5  # Group by 5px buckets
            y_groups[y_key].append(word)

        # Find row with column headers (stricter matching)
        header_y = None
        for y_pos, words_at_y in sorted(y_groups.items()):
            text_at_y = " ".join([w["text"].lower() for w in words_at_y])

            # Check if it looks like transaction data (exclude these rows)
            if any(indicator in text_at_y for indicator in TRANSACTION_INDICATORS):
                continue

            # Count matching header keywords
            keyword_count = sum(1 for kw in HEADER_KEYWORDS if kw in text_at_y)

            # Require at least 3 keywords AND check word count suggests headers
            if keyword_count >= 3 and len(words_at_y) >= 4 and len(words_at_y) <= 10:
                header_y = y_pos
                logger.debug(
                    f"Found header row at Y={y_pos} with {keyword_count} keywords: "
                    f"{text_at_y[:60]}..."
                )
                break

        if not header_y:
            logger.debug("No header row found in text")
            return None

        # Find dense text region INCLUDING header and below (transaction rows)
        table_y_positions = [header_y]  # Include the header itself

        # Footer keywords that indicate end of transaction table
        FOOTER_KEYWORDS = [
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

        # Track where footer section begins
        footer_start_y = None
        last_transaction_y = header_y

        for y_pos, words_at_y in sorted(y_groups.items()):
            if y_pos <= header_y:
                continue

            # Check if this row contains footer keywords
            text_at_y = " ".join([w["text"].lower() for w in words_at_y])
            is_footer = any(keyword in text_at_y for keyword in FOOTER_KEYWORDS)

            if is_footer:
                # Found footer - mark where it starts
                footer_start_y = y_pos
                logger.debug(f"Footer detected at Y={y_pos}: {text_at_y[:50]}...")
                break

            # Check for large gap from last transaction (likely footer section)
            gap_from_last = y_pos - last_transaction_y
            if gap_from_last > 100 and len(words_at_y) < 10:
                # Large gap + sparse content = likely footer section
                footer_start_y = y_pos
                logger.debug(
                    f"Large gap ({gap_from_last:.1f}px) detected at Y={y_pos}, "
                    f"footer section likely starts here"
                )
                break

            # Consider rows with 3+ words as potential table rows
            if len(words_at_y) >= 3:
                table_y_positions.append(y_pos)
                last_transaction_y = y_pos

        if len(table_y_positions) < 2:  # Need at least header + 1 data row
            logger.debug("No transaction rows found below header")
            return None

        # Calculate table boundaries - START from header row
        # Add small margin (5px) above header to catch all header words
        table_top_y = header_y - 5  # Include margin above header

        # Calculate table_bottom_y: extend to just before footer (for multi-page support)
        # This ensures transactions on subsequent pages are captured
        if footer_start_y is not None:
            # Footer found - extend table to just before footer (leave 10px margin)
            table_bottom_y = footer_start_y - 10
            logger.debug(
                f"Table extended to footer boundary: Y={table_bottom_y:.1f} "
                f"(footer starts at Y={footer_start_y:.1f})"
            )
        else:
            # No footer found - use last transaction + margin (single page case)
            if len(table_y_positions) >= 3:
                # Calculate average row spacing
                row_spacings = []
                sorted_positions = sorted(table_y_positions)
                for i in range(1, len(sorted_positions)):
                    spacing = sorted_positions[i] - sorted_positions[i - 1]
                    if spacing < 50:
                        row_spacings.append(spacing)

                if row_spacings:
                    avg_row_spacing = sum(row_spacings) / len(row_spacings)
                    bottom_margin = avg_row_spacing * 1.5
                    logger.debug(
                        f"Calculated bottom margin: {bottom_margin:.1f}px "
                        f"(avg row spacing: {avg_row_spacing:.1f}px × 1.5)"
                    )
                else:
                    bottom_margin = 20
                    logger.debug("Using fallback bottom margin: 20px")
            else:
                bottom_margin = 20
                logger.debug("Using default bottom margin for single row: 20px")

            table_bottom_y = max(table_y_positions) + bottom_margin
            logger.debug(
                f"No footer found, using last transaction + margin: Y={table_bottom_y:.1f}"
            )
        logger.debug(
            f"Table boundary: Y={table_top_y:.1f} to Y={table_bottom_y:.1f} "
            f"(height={table_bottom_y - table_top_y:.1f}px, {len(table_y_positions)} rows)"
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
                f"Text-based table too small: height={bbox.height:.1f}px "
                f"< {self.min_table_height}px"
            )
            return None

        logger.debug(
            f"Text-based table detected: {bbox} (height={bbox.height:.1f}px, "
            f"header at Y={header_y})"
        )
        return bbox
