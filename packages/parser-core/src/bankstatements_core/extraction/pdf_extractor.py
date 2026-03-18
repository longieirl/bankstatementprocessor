"""PDF table extraction orchestration.

This module provides a clean, testable interface for extracting table data from
PDF bank statements with proper separation of concerns.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.pdf_reader import IPDFReader

from bankstatements_core.extraction.column_identifier import ColumnTypeIdentifier
from bankstatements_core.extraction.iban_extractor import IBANExtractor
from bankstatements_core.extraction.row_classifiers import create_row_classifier_chain

logger = logging.getLogger(__name__)


class PDFTableExtractor:
    """
    Orchestrates extraction of table data from PDF files.

    Handles page iteration, boundary detection, word grouping, row extraction,
    continuation line merging, and date propagation.
    """

    def __init__(
        self,
        columns: dict[str, tuple[int | float, int | float]],
        table_top_y: int = 300,
        table_bottom_y: int = 720,
        enable_dynamic_boundary: bool = False,
        enable_page_validation: bool = True,
        enable_header_check: bool = True,
        header_check_top_y: int | None = None,
        pdf_reader: "IPDFReader | None" = None,
        extraction_config: "Any | None" = None,
        template: "Any | None" = None,
    ):
        """
        Initialize PDF table extractor.

        Args:
            columns: Column definitions mapping names to (x_min, x_max) boundaries
            table_top_y: Top Y coordinate for table extraction (default for all pages)
            table_bottom_y: Bottom Y coordinate for table extraction (default for all pages)
            enable_dynamic_boundary: Whether to use dynamic table end detection
            enable_page_validation: Whether to validate page structure (default: True)
            enable_header_check: Whether to check for table headers (default: True)
            header_check_top_y: Y-coordinate to start header search (None = auto-calculate)
            pdf_reader: Optional PDF reader for dependency injection (default: use pdfplumber adapter)
            extraction_config: Optional TemplateExtractionConfig for per-page boundary support
            template: Optional BankTemplate for document type information
        """
        self.columns = columns
        self.table_top_y = table_top_y
        self.table_bottom_y = table_bottom_y
        self.iban_extractor = IBANExtractor()
        self.enable_dynamic_boundary = enable_dynamic_boundary
        self._row_classifier = create_row_classifier_chain()

        # Inject PDF reader or use default pdfplumber adapter
        if pdf_reader is None:
            from bankstatements_core.adapters.pdfplumber_adapter import (
                PDFPlumberReaderAdapter,
            )

            self._pdf_reader: IPDFReader = PDFPlumberReaderAdapter()  # type: ignore[assignment]
        else:
            self._pdf_reader = pdf_reader

        # Page validation setting (enabled by default to ensure table presence)
        self.page_validation_enabled = enable_page_validation

        # Header check setting
        self.header_check_enabled = enable_header_check

        # Header check area (template-specific or auto-calculated)
        self.header_check_top_y = header_check_top_y

        # Store extraction config for per-page boundary support (NEW)
        self.extraction_config = extraction_config

        # Store template for document type information (NEW)
        self.template = template

    def extract(self, pdf_path: Path) -> tuple[list[dict], int, str | None]:
        """
        Extract table data from PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Tuple of (extracted rows, total page count, IBAN if found)
        """
        rows: list[dict] = []
        filename = pdf_path.name
        current_date = ""
        iban = None  # Will store the first IBAN found

        # Extract date from filename as fallback
        filename_date = self._extract_filename_date(filename)

        with self._pdf_reader.open(pdf_path) as pdf:
            pages_processed = 0

            for page_num, page in enumerate(pdf.pages, 1):
                # Check first page for credit card statement
                if page_num == 1 and self._is_credit_card_statement(page):
                    logger.warning(
                        f"Credit card statement detected in {filename}. "
                        f"Credit card statements are not currently supported. Skipping file."
                    )
                    # Return empty results - this will skip the entire PDF
                    return [], len(pdf.pages), None

                # Try to extract IBAN from first page if not found yet
                if iban is None and page_num == 1:
                    iban = self._extract_iban_from_page(page)
                    if iban:
                        logger.info(
                            f"IBAN found on page {page_num}: {iban[:4]}****{iban[-4:]}"
                        )

                page_rows = self._extract_page(page, page_num)

                if page_rows is None:
                    # Page was skipped (invalid structure or no headers)
                    continue

                # Page validation passed
                pages_processed += 1
                logger.info(
                    f"Page {page_num}: Valid table structure found, "
                    f"processing {len(page_rows)} rows"
                )

                # Process rows and propagate dates
                for row in page_rows:
                    current_date = self._process_row(
                        row, current_date, filename_date, filename
                    )
                    if row:  # Row may be None if filtered
                        rows.append(row)

            return rows, len(pdf.pages), iban

    def _extract_page(self, page: Any, page_num: int) -> list[dict] | None:
        """
        Extract rows from a single page.

        Args:
            page: pdfplumber page object
            page_num: Page number for logging

        Returns:
            List of extracted rows, or None if page should be skipped
        """
        # Determine boundaries and extract words
        words = self._determine_boundaries_and_extract(page, page_num)
        if words is None:
            return None  # Page skipped

        # Group words by Y position and build rows
        page_rows = self._extract_rows_from_words(words)

        # Validate page structure
        if self.page_validation_enabled:
            from bankstatements_core.pdf_table_extractor import validate_page_structure

            if not validate_page_structure(page_rows, self.columns):
                logger.info(
                    f"Page {page_num}: Invalid table structure detected, "
                    f"skipping {len(page_rows)} rows"
                )
                return None

        # Merge continuation lines
        from bankstatements_core.pdf_table_extractor import merge_continuation_lines

        page_rows = merge_continuation_lines(page_rows, self.columns)

        return page_rows

    def _determine_boundaries_and_extract(
        self, page: Any, page_num: int
    ) -> list[dict] | None:
        """
        Determine table boundaries and extract words (with per-page boundary support).

        Args:
            page: pdfplumber page object
            page_num: Page number for logging (1-indexed)

        Returns:
            List of word dictionaries, or None if page should be skipped
        """
        # Get page-specific boundaries if extraction_config is available (NEW)
        if self.extraction_config is not None:
            table_top_y = self.extraction_config.get_table_top_y(page_num)
            table_bottom_y = self.extraction_config.get_table_bottom_y(page_num)
            header_check_top_y = self.extraction_config.get_header_check_top_y(page_num)
        else:
            # Fallback to instance defaults
            table_top_y = self.table_top_y
            table_bottom_y = self.table_bottom_y
            header_check_top_y = self.header_check_top_y

        if self.enable_dynamic_boundary:
            # Extract all words initially for boundary detection
            # Use table_bottom_y as upper limit to prevent extracting footer content
            max_extraction_y = min(
                table_bottom_y + 100, page.height
            )  # Allow 100px margin for detection
            initial_area = page.crop((0, table_top_y, page.width, max_extraction_y))
            all_words = initial_area.extract_words(use_text_flow=True)

            # Check for table headers in dynamic mode
            if self.header_check_enabled:
                from bankstatements_core.pdf_table_extractor import detect_table_headers

                # Use template-specific header check area or auto-calculate
                if header_check_top_y is not None:
                    # Template explicitly specifies where to look for headers
                    header_top = header_check_top_y
                else:
                    # Auto-calculate: look 50px above table_top_y for headers
                    header_top = max(0, table_top_y - 50)

                # Extract header area for detection
                header_area = page.crop((0, header_top, page.width, page.height))
                header_words = header_area.extract_words(use_text_flow=True)

                if not detect_table_headers(header_words, self.columns):
                    logger.info(f"Page {page_num}: No table headers detected, skipping")
                    return None

            # Detect dynamic boundary
            from bankstatements_core.pdf_table_extractor import (
                detect_table_end_boundary_smart,
            )

            dynamic_bottom_y = detect_table_end_boundary_smart(
                all_words, table_top_y, self.columns, table_bottom_y
            )

            # Safety check: Cap dynamic boundary at static boundary to prevent over-extraction
            # Dynamic detection should refine the boundary, not expand beyond static limits
            if dynamic_bottom_y > table_bottom_y:
                logger.warning(
                    f"Page {page_num}: Dynamic boundary ({dynamic_bottom_y}) exceeds "
                    f"static boundary ({table_bottom_y}), using static boundary"
                )
                dynamic_bottom_y = table_bottom_y

            # Extract with dynamic boundary
            table_area = page.crop((0, table_top_y, page.width, dynamic_bottom_y))
            words = table_area.extract_words(use_text_flow=True)
        else:
            # Use static boundary
            table_area = page.crop((0, table_top_y, page.width, table_bottom_y))
            words = table_area.extract_words(use_text_flow=True)

            # Check for table headers in static mode
            if self.header_check_enabled:
                from bankstatements_core.pdf_table_extractor import detect_table_headers

                # Use template-specific header check area or auto-calculate
                if header_check_top_y is not None:
                    # Template explicitly specifies where to look for headers
                    header_top = header_check_top_y
                else:
                    # Auto-calculate: look 50px above table_top_y for headers
                    header_top = max(0, table_top_y - 50)

                header_area = page.crop((0, header_top, page.width, table_bottom_y))
                header_words = header_area.extract_words(use_text_flow=True)

                if not detect_table_headers(header_words, self.columns):
                    logger.info(f"Page {page_num}: No table headers detected, skipping")
                    return None

        return words  # type: ignore[no-any-return]

    def _extract_rows_from_words(self, words: list[dict]) -> list[dict]:
        """
        Group words by Y position and build row dictionaries.

        Args:
            words: List of word dictionaries from pdfplumber

        Returns:
            List of row dictionaries
        """
        # Group words by Y coordinate
        lines: dict[float, list[dict]] = {}
        for w in words:
            y_key = round(w["top"], 0)
            lines.setdefault(y_key, []).append(w)

        page_rows = []
        for _, line_words in sorted(lines.items()):
            row = dict.fromkeys(self.columns, "")

            # Assign words to columns based on X position
            # Get list of column names to determine rightmost column
            column_names = list(self.columns.keys())
            rightmost_column = column_names[-1] if column_names else None

            for w in line_words:
                x0 = w["x0"]  # Left edge of word
                # Right edge: real pdfplumber always provides x1, but for tests we estimate
                # Using smaller multiplier (3) to avoid over-estimating word width
                x1 = w.get("x1", x0 + max(len(w["text"]) * 3, 10))
                text = w["text"]

                for col, (xmin, xmax) in self.columns.items():
                    # BOUNDARY CHECKING STRATEGY:
                    # - For rightmost column (usually Balance): STRICT check (prevents footer bleed)
                    # - For other columns: RELAXED check (just x0 within bounds)
                    # This balances protection against footer text with flexibility for amounts
                    if col == rightmost_column:
                        # Strict: word must be FULLY contained
                        if xmin <= x0 and x1 <= xmax:
                            row[col] += text + " "
                            break
                    else:
                        # Relaxed: word just needs to START within column
                        if xmin <= x0 < xmax:
                            row[col] += text + " "
                            break

            # Normalize and filter
            row = {k: v.strip() for k, v in row.items()}

            # Include transactions and continuation lines
            if any(row.values()):
                row_type = self._row_classifier.classify(row, self.columns)
                if row_type in ["transaction", "continuation"]:
                    page_rows.append(row)

        return page_rows

    def _process_row(
        self,
        row: dict,
        current_date: str,
        filename_date: str,
        filename: str,
    ) -> str:
        """
        Process a row: propagate dates, add filename, filter non-transactions.

        Args:
            row: Row dictionary to process (modified in-place)
            current_date: Current date being tracked
            filename_date: Date extracted from filename
            filename: Source filename

        Returns:
            Updated current_date value
        """
        # Only process actual transactions after merging
        if self._row_classifier.classify(row, self.columns) != "transaction":
            return current_date

        # Find date column
        date_col = ColumnTypeIdentifier.find_first_column_of_type(self.columns, "date")

        # Propagate dates
        if date_col and row.get(date_col):
            current_date = row[date_col]
        elif date_col and (current_date or filename_date):
            # Use last seen date or filename date
            fallback_date = current_date or filename_date
            row[date_col] = fallback_date
            if not current_date:
                current_date = fallback_date

        # Tag with source filename
        row["Filename"] = filename

        # Add document type and template ID from template
        if self.template:
            row["document_type"] = self.template.document_type
            row["template_id"] = self.template.id
        else:
            row["document_type"] = "bank_statement"  # Default fallback
            row["template_id"] = None

        return current_date

    def _extract_filename_date(self, filename: str) -> str:
        """
        Extract date from filename (YYYYMMDD pattern).

        Args:
            filename: Filename to extract date from

        Returns:
            Formatted date string (e.g., "02 Feb 2025"), or empty string if no date
        """
        date_match = re.search(r"(\d{8})", filename)
        if not date_match:
            return ""

        date_str = date_match.group(1)
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            return date_obj.strftime("%d %b %Y")
        except ValueError:
            return ""

    def _is_credit_card_statement(self, page: Any) -> bool:
        """
        Check if a PDF page contains credit card statement indicators.

        Credit card statements are not currently supported and should be skipped.
        Checks for keywords like 'Card Number', 'Credit Limit', 'Credit Card',
        'Visa', or 'Mastercard' in the HEADER area only (before transaction table).

        Args:
            page: pdfplumber page object

        Returns:
            True if credit card statement detected, False otherwise
        """
        try:
            # Extract text from header area only (before transaction table starts)
            # Use table_top_y to exclude transaction table area
            header_area = page.crop((0, 0, page.width, self.table_top_y))
            header_text = header_area.extract_text()

            if header_text:
                # Search for credit card indicators (case-insensitive)
                # These patterns are strong indicators of a credit card statement
                credit_card_patterns = [
                    r"card\s+number",  # Card Number
                    r"credit\s+limit",  # Credit Limit
                    r"credit\s+card",  # Credit Card
                    r"\bvisa\b",  # Visa (word boundary to avoid "advisa")
                    r"\bmastercard\b",  # Mastercard
                ]

                for pattern in credit_card_patterns:
                    if re.search(pattern, header_text, re.IGNORECASE):
                        logger.debug(
                            f"Credit card indicator found in header: pattern '{pattern}' matched"
                        )
                        return True
            return False
        except (AttributeError, ValueError, TypeError) as e:
            # Expected errors: page object issues, regex errors, text extraction failures
            logger.warning(f"Error checking for credit card statement: {e}")
            return False
        # Let unexpected errors bubble up

    def _extract_iban_from_page(self, page: Any) -> str | None:
        """
        Extract IBAN from a PDF page header area.

        Only extracts from the header/metadata section (before transaction table)
        to avoid false positives from IBANs mentioned in transaction descriptions.

        Args:
            page: pdfplumber page object

        Returns:
            IBAN string if found, None otherwise
        """
        try:
            # Extract text from header area only (before transaction table starts)
            # This ensures we get the account IBAN, not IBANs from transaction descriptions
            # Use a fixed generous header area (Y=350) to ensure IBAN is captured
            # regardless of table_top_y setting
            iban_header_y = 350
            header_area = page.crop((0, 0, page.width, iban_header_y))
            header_text = header_area.extract_text()

            if header_text:
                iban = self.iban_extractor.extract_iban(header_text)
                if iban:
                    return iban

            # If not found in header text, try extracting from header words
            header_words = header_area.extract_words(use_text_flow=True)
            if header_words:
                iban = self.iban_extractor.extract_iban_from_pdf_words(header_words)
                if iban:
                    return iban

        except (AttributeError, ValueError, KeyError, TypeError) as e:
            # Expected errors: page object issues, crop failures, extraction errors, type mismatches
            logger.warning(f"Error extracting IBAN from page: {e}")
        # Let unexpected errors bubble up

        return None
