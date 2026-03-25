"""Service for detecting table headers in PDF pages.

This service consolidates header detection logic that was previously duplicated
across multiple files, providing a unified interface for header area calculation
and detection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bankstatements_core.extraction.word_utils import group_words_by_y

if TYPE_CHECKING:
    import pdfplumber

logger = logging.getLogger(__name__)


class HeaderDetectionService:
    """Detects table headers in PDF pages.

    This service provides methods for:
    - Calculating header check areas based on table boundaries
    - Detecting whether a page contains recognizable table headers
    - Grouping words by vertical position for header analysis
    """

    # Common header keywords to look for (including variations)
    HEADER_KEYWORDS = {
        "date",
        "trans date",
        "transaction date",
        "posting date",
        "value date",
        "details",
        "description",
        "particulars",
        "narrative",
        "amount",
        "debit",
        "dr",
        "withdrawal",
        "payments",
        "credit",
        "cr",
        "deposit",
        "lodgement",
        "balance",
        "running balance",
        "closing balance",
        "transaction",
        "reference",
        "ref",
        "ref no",
        "memo",
    }

    def calculate_header_area(
        self,
        table_top_y: int | float,
        header_check_top_y: int | float | None = None,
        default_offset: int = 50,
    ) -> int | float:
        """Calculate the top Y coordinate for header detection area.

        Args:
            table_top_y: Top Y coordinate of the table data area
            header_check_top_y: Optional explicit header check top Y coordinate
            default_offset: Default offset above table_top_y to look for headers

        Returns:
            Top Y coordinate for header detection area

        Examples:
            >>> service = HeaderDetectionService()
            >>> # Explicit header area
            >>> service.calculate_header_area(300, header_check_top_y=250)
            250
            >>> # Auto-calculated header area (50px above table)
            >>> service.calculate_header_area(300)
            250
            >>> # Edge case: table at top of page
            >>> service.calculate_header_area(30)
            0
        """
        if header_check_top_y is not None:
            # Template explicitly specifies where to look for headers
            return header_check_top_y

        # Auto-calculate: look `default_offset` px above table_top_y for headers
        return max(0, table_top_y - default_offset)

    def detect_headers(
        self,
        words: list[dict],
        columns: dict[str, tuple[int | float, int | float]],
        max_rows_to_check: int = 5,
        min_keywords: int = 2,
    ) -> bool:
        """Detect if a page contains recognizable table headers.

        This method checks the combined text of top rows for header keywords.
        This matches the behavior of the original detect_table_headers function.

        Args:
            words: List of word dictionaries from pdfplumber extraction
            columns: Column definitions mapping names to (x0, x1) boundaries
            max_rows_to_check: Maximum number of top rows to analyze
            min_keywords: Minimum number of header keywords required

        Returns:
            True if headers detected, False otherwise

        Examples:
            >>> service = HeaderDetectionService()
            >>> words = [
            ...     {"text": "Date", "top": 100, "x0": 50},
            ...     {"text": "Details", "top": 100, "x0": 150},
            ...     {"text": "Amount", "top": 100, "x0": 400}
            ... ]
            >>> columns = {
            ...     "Date": (40, 120),
            ...     "Details": (130, 380),
            ...     "Amount": (390, 500)
            ... }
            >>> service.detect_headers(words, columns)
            True
        """
        if not words:
            logger.debug("No words found on page for header detection")
            return False

        # Group words by Y coordinate to find potential header rows
        rows_by_y = group_words_by_y(words)

        # Check top few rows for header-like content
        top_rows = sorted(rows_by_y.keys())[:max_rows_to_check]
        logger.debug(f"Checking {len(top_rows)} rows for table headers")

        for y_coord in top_rows:
            row_words = rows_by_y[y_coord]
            row_text = " ".join([w.get("text", "") for w in row_words]).lower()

            # Count how many header keywords appear in this row
            header_matches = sum(
                1 for keyword in self.HEADER_KEYWORDS if keyword in row_text
            )

            logger.debug(
                f"Row at Y={y_coord}: '{row_text[:60]}...' - {header_matches} header keywords found"
            )

            # If we find min_keywords+ header indicators in a row, it's likely a table header
            if header_matches >= min_keywords:
                logger.debug(
                    f"✓ Table headers detected with {header_matches} keywords (threshold: {min_keywords})"
                )
                return True

        logger.debug(
            f"✗ No table headers detected (need {min_keywords}+ header keywords in top {max_rows_to_check} rows)"
        )
        return False

    def check_page_for_headers(
        self,
        page: pdfplumber.page.Page,
        columns: dict[str, tuple[int | float, int | float]],
        table_top_y: int | float,
        table_bottom_y: int | float,
        header_check_top_y: int | float | None = None,
        min_keywords: int = 2,
    ) -> bool:
        """Check a PDF page for table headers (convenience method).

        This method combines header area calculation, word extraction, and
        header detection into a single operation.

        Args:
            page: pdfplumber Page object
            columns: Column definitions
            table_top_y: Top Y coordinate of table data area
            table_bottom_y: Bottom Y coordinate of table data area
            header_check_top_y: Optional explicit header check area
            min_keywords: Minimum number of header keywords required

        Returns:
            True if headers detected, False otherwise

        Examples:
            >>> import pdfplumber
            >>> service = HeaderDetectionService()
            >>> with pdfplumber.open("statement.pdf") as pdf:
            ...     page = pdf.pages[0]
            ...     columns = {"Date": (50, 150), "Amount": (400, 500)}
            ...     has_headers = service.check_page_for_headers(
            ...         page, columns, table_top_y=300, table_bottom_y=720
            ...     )
        """
        # Calculate header detection area
        header_top = self.calculate_header_area(table_top_y, header_check_top_y)

        # Extract words from header area
        header_area = page.crop((0, header_top, page.width, table_bottom_y))
        header_words = header_area.extract_words(use_text_flow=True)

        # Detect headers
        return self.detect_headers(header_words, columns, min_keywords=min_keywords)
