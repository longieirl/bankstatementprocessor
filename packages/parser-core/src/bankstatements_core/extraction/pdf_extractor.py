"""PDF table extraction orchestration.

This module provides a clean, testable interface for extracting table data from
PDF bank statements with proper separation of concerns.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.pdf_reader import IPDFReader

from bankstatements_core.extraction.iban_extractor import IBANExtractor
from bankstatements_core.extraction.page_header_analyser import PageHeaderAnalyser
from bankstatements_core.extraction.row_builder import RowBuilder
from bankstatements_core.extraction.row_classifiers import create_row_classifier_chain
from bankstatements_core.extraction.row_post_processor import (
    RowPostProcessor,
    extract_filename_date,
)

logger = logging.getLogger(__name__)


class PDFTableExtractor:
    """
    Orchestrates extraction of table data from PDF files.

    Delegates to focused collaborators:
    - PageHeaderAnalyser: credit card detection and IBAN extraction
    - RowBuilder: word-to-row conversion and classification filtering
    - RowPostProcessor: date propagation and metadata tagging
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
        self.columns = columns
        self.table_top_y = table_top_y
        self.table_bottom_y = table_bottom_y
        self.enable_dynamic_boundary = enable_dynamic_boundary
        self.page_validation_enabled = enable_page_validation
        self.header_check_enabled = enable_header_check
        self.header_check_top_y = header_check_top_y
        self.extraction_config = extraction_config
        self.template = template

        self._row_classifier = create_row_classifier_chain()
        self._row_builder = RowBuilder(columns, self._row_classifier)
        self._header_analyser = PageHeaderAnalyser(IBANExtractor())

        if pdf_reader is None:
            from bankstatements_core.adapters.pdfplumber_adapter import (
                PDFPlumberReaderAdapter,
            )

            self._pdf_reader: IPDFReader = PDFPlumberReaderAdapter()  # type: ignore[assignment]
        else:
            self._pdf_reader = pdf_reader

    def extract(self, pdf_path: Path) -> tuple[list[dict], int, str | None]:
        """Extract table data from PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Tuple of (extracted rows, total page count, IBAN if found)
        """
        rows: list[dict] = []
        current_date = ""
        iban = None

        filename_date = extract_filename_date(pdf_path.name)
        post_processor = RowPostProcessor(
            columns=self.columns,
            row_classifier=self._row_classifier,
            template=self.template,
            filename_date=filename_date,
            filename=pdf_path.name,
        )

        with self._pdf_reader.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if page_num == 1 and self._header_analyser.is_credit_card_statement(
                    page, self.table_top_y
                ):
                    logger.warning(
                        f"Credit card statement detected in {pdf_path.name}. "
                        f"Credit card statements are not currently supported. Skipping file."
                    )
                    return [], len(pdf.pages), None

                if iban is None and page_num == 1:
                    iban = self._header_analyser.extract_iban(page)
                    if iban:
                        logger.info(
                            f"IBAN found on page {page_num}: {iban[:4]}****{iban[-4:]}"
                        )

                page_rows = self._extract_page(page, page_num)
                if page_rows is None:
                    continue

                logger.info(
                    f"Page {page_num}: Valid table structure found, "
                    f"processing {len(page_rows)} rows"
                )

                for row in page_rows:
                    current_date = post_processor.process(row, current_date)
                    if row:
                        rows.append(row)

            return rows, len(pdf.pages), iban

    def _extract_page(self, page: Any, page_num: int) -> list[dict] | None:
        """Extract rows from a single page.

        Args:
            page: pdfplumber page object
            page_num: Page number for logging

        Returns:
            List of extracted rows, or None if page should be skipped
        """
        words = self._determine_boundaries_and_extract(page, page_num)
        if words is None:
            return None

        page_rows = self._row_builder.build_rows(words)

        if self.page_validation_enabled:
            from bankstatements_core.extraction.validation_facade import (
                validate_page_structure,
            )

            if not validate_page_structure(page_rows, self.columns):
                logger.info(
                    f"Page {page_num}: Invalid table structure detected, "
                    f"skipping {len(page_rows)} rows"
                )
                return None

        from bankstatements_core.extraction.validation_facade import (
            merge_continuation_lines,
        )

        return merge_continuation_lines(page_rows, self.columns)

    def _determine_boundaries_and_extract(
        self, page: Any, page_num: int
    ) -> list[dict] | None:
        """Determine table boundaries and extract words (with per-page boundary support).

        Args:
            page: pdfplumber page object
            page_num: Page number for logging (1-indexed)

        Returns:
            List of word dictionaries, or None if page should be skipped
        """
        if self.extraction_config is not None:
            table_top_y = self.extraction_config.get_table_top_y(page_num)
            table_bottom_y = self.extraction_config.get_table_bottom_y(page_num)
            header_check_top_y = self.extraction_config.get_header_check_top_y(page_num)
        else:
            table_top_y = self.table_top_y
            table_bottom_y = self.table_bottom_y
            header_check_top_y = self.header_check_top_y

        if self.enable_dynamic_boundary:
            max_extraction_y = min(table_bottom_y + 100, page.height)
            initial_area = page.crop((0, table_top_y, page.width, max_extraction_y))
            all_words = initial_area.extract_words(use_text_flow=True)

            if self.header_check_enabled:
                from bankstatements_core.extraction.validation_facade import (
                    detect_table_headers,
                )

                header_top = (
                    header_check_top_y
                    if header_check_top_y is not None
                    else max(0, table_top_y - 50)
                )
                header_area = page.crop((0, header_top, page.width, page.height))
                header_words = header_area.extract_words(use_text_flow=True)

                if not detect_table_headers(header_words, self.columns):
                    logger.info(f"Page {page_num}: No table headers detected, skipping")
                    return None

            from bankstatements_core.extraction.extraction_facade import (
                detect_table_end_boundary_smart,
            )

            dynamic_bottom_y = detect_table_end_boundary_smart(
                all_words,
                table_top_y,
                self.columns,
                table_bottom_y,
                row_classifier=self._row_classifier,
            )

            if dynamic_bottom_y > table_bottom_y:
                logger.warning(
                    f"Page {page_num}: Dynamic boundary ({dynamic_bottom_y}) exceeds "
                    f"static boundary ({table_bottom_y}), using static boundary"
                )
                dynamic_bottom_y = table_bottom_y

            table_area = page.crop((0, table_top_y, page.width, dynamic_bottom_y))
            return table_area.extract_words(use_text_flow=True)  # type: ignore[no-any-return]

        # Static boundary path
        table_area = page.crop((0, table_top_y, page.width, table_bottom_y))
        words = table_area.extract_words(use_text_flow=True)

        if self.header_check_enabled:
            from bankstatements_core.extraction.validation_facade import (
                detect_table_headers,
            )

            header_top = (
                header_check_top_y
                if header_check_top_y is not None
                else max(0, table_top_y - 50)
            )
            header_area = page.crop((0, header_top, page.width, table_bottom_y))
            header_words = header_area.extract_words(use_text_flow=True)

            if not detect_table_headers(header_words, self.columns):
                logger.info(f"Page {page_num}: No table headers detected, skipping")
                return None

        return words  # type: ignore[no-any-return]
