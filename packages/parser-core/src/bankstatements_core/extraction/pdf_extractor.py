"""PDF table extraction orchestration.

This module provides a clean, testable interface for extracting table data from
PDF bank statements with proper separation of concerns.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.pdf_reader import IPDFReader

from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions
from bankstatements_core.domain.models.extraction_warning import (
    CODE_CREDIT_CARD_SKIPPED,
    ExtractionWarning,
)
from bankstatements_core.extraction.iban_extractor import IBANExtractor
from bankstatements_core.extraction.page_header_analyser import PageHeaderAnalyser
from bankstatements_core.extraction.row_builder import RowBuilder
from bankstatements_core.extraction.row_classifiers import create_row_classifier_chain
from bankstatements_core.extraction.row_post_processor import (
    RowPostProcessor,
    StatefulPageRowProcessor,
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

    def __init__(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        columns: dict[str, tuple[int | float, int | float]],
        table_top_y: int = 300,
        table_bottom_y: int = 720,
        enable_dynamic_boundary: bool = False,
        enable_page_validation: bool = True,
        enable_header_check: bool = True,
        header_check_top_y: int | None = None,
        pdf_reader: IPDFReader | None = None,
        extraction_config: Any | None = None,
        template: Any | None = None,
        entitlements: Any | None = None,
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
        self._entitlements = entitlements

        self._row_classifier = create_row_classifier_chain()
        self._row_builder = RowBuilder(columns, self._row_classifier)
        self._header_analyser = PageHeaderAnalyser(IBANExtractor())

        if pdf_reader is None:
            from bankstatements_core.adapters.pdfplumber_adapter import (  # noqa: PLC0415
                PDFPlumberReaderAdapter,
            )

            self._pdf_reader: IPDFReader = PDFPlumberReaderAdapter()  # type: ignore[assignment]
        else:
            self._pdf_reader = pdf_reader

    def extract(self, pdf_path: Path) -> ExtractionResult:
        """Extract table data from PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ExtractionResult containing extracted transactions, page count,
            IBAN if found, source file path, and any document-level warnings
        """
        rows: list[dict] = []
        iban = None
        card_number: str | None = None

        filename_date = extract_filename_date(pdf_path.name)
        page_processor = StatefulPageRowProcessor(
            RowPostProcessor(
                columns=self.columns,
                row_classifier=self._row_classifier,
                template=self.template,
                filename_date=filename_date,
                filename=pdf_path.name,
            )
        )

        with self._pdf_reader.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                if page_num == 1 and self._header_analyser.is_credit_card_statement(
                    page, self.table_top_y
                ):
                    if self._entitlements is None or self._entitlements.require_iban:
                        logger.warning(
                            "Credit card statement detected in %s. Credit card statements are not currently supported. Skipping file.",
                            pdf_path.name,
                        )
                        return ExtractionResult(
                            transactions=[],
                            page_count=len(pdf.pages),
                            iban=None,
                            source_file=pdf_path,
                            warnings=[
                                ExtractionWarning(
                                    code=CODE_CREDIT_CARD_SKIPPED,
                                    message="credit card statement detected, skipped",
                                )
                            ],
                        )

                if iban is None and page_num == 1:
                    iban = self._header_analyser.extract_iban(page)
                    if iban:
                        logger.info(
                            "IBAN found on page %s: %s****%s",
                            page_num,
                            iban[:4],
                            iban[-4:],
                        )

                # Extract card number on page 1 for CC statements (paid tier only)
                if page_num == 1 and card_number is None:
                    extracted = self._extract_card_number(page)
                    if extracted is not None:
                        card_number = extracted
                    elif self._header_analyser.is_credit_card_statement(
                        page, self.table_top_y
                    ):
                        # CC PDF detected on paid tier but no card pattern matched
                        card_number = "unknown"

                page_rows = self._extract_page(page, page_num)
                if page_rows is None:
                    continue

                logger.info(
                    "Page %s: Valid table structure found, processing %s rows",
                    page_num,
                    len(page_rows),
                )

                rows.extend(page_processor.process_page(page_rows))

            return ExtractionResult(
                transactions=dicts_to_transactions(rows),
                page_count=len(pdf.pages),
                iban=iban,
                source_file=pdf_path,
                card_number=card_number,
            )

    def _extract_card_number(self, page: Any) -> str | None:
        """Extract card number from page header using template card_number_patterns.

        Crops the header area (0, 0, width, 400) -- same bbox as CardNumberDetector --
        and runs the template's card_number_patterns regex loop.

        Args:
            page: pdfplumber page object (page 1 only)

        Returns:
            Matched card number string, or None if no match found.
        """
        if self.template is None:
            return None
        patterns = self.template.detection.get_card_number_patterns()
        if not patterns:
            return None
        header_bbox = (0, 0, page.width, 400)
        try:
            text = page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            text = page.extract_text()
        if not text:
            return None
        for pattern in patterns:
            try:
                match = re.search(pattern, text)
                if match:
                    return str(match.group(0))
            except re.error:
                logger.warning("Invalid card_number_pattern: %s", pattern)
        return None

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
            from bankstatements_core.services.page_validation import (  # noqa: PLC0415
                PageValidationService,
            )

            if not PageValidationService().validate_page_structure(
                page_rows, self.columns
            ):
                logger.info(
                    "Page %s: Invalid table structure detected, skipping %s rows",
                    page_num,
                    len(page_rows),
                )
                return None

        from bankstatements_core.services.row_merger import (  # noqa: PLC0415
            RowMergerService,
        )

        return RowMergerService().merge_continuation_lines(page_rows, self.columns)

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
                from bankstatements_core.extraction.extraction_params import (  # noqa: PLC0415
                    MIN_HEADER_KEYWORDS,
                )
                from bankstatements_core.services.header_detection import (  # noqa: PLC0415
                    HeaderDetectionService,
                )

                header_top = (
                    header_check_top_y
                    if header_check_top_y is not None
                    else max(0, table_top_y - 50)
                )
                header_area = page.crop((0, header_top, page.width, page.height))
                header_words = header_area.extract_words(use_text_flow=True)

                if not HeaderDetectionService().detect_headers(
                    header_words, self.columns, min_keywords=MIN_HEADER_KEYWORDS
                ):
                    logger.info(
                        "Page %s: No table headers detected, skipping", page_num
                    )
                    return None

            from bankstatements_core.extraction.extraction_facade import (  # noqa: PLC0415
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
                    "Page %s: Dynamic boundary (%s) exceeds static boundary (%s), using static boundary",
                    page_num,
                    dynamic_bottom_y,
                    table_bottom_y,
                )
                dynamic_bottom_y = table_bottom_y

            table_area = page.crop((0, table_top_y, page.width, dynamic_bottom_y))
            return table_area.extract_words(use_text_flow=True)  # type: ignore[no-any-return]

        # Static boundary path
        table_area = page.crop((0, table_top_y, page.width, table_bottom_y))
        words = table_area.extract_words(use_text_flow=True)

        if self.header_check_enabled:
            from bankstatements_core.extraction.extraction_params import (  # noqa: PLC0415
                MIN_HEADER_KEYWORDS,
            )
            from bankstatements_core.services.header_detection import (  # noqa: PLC0415
                HeaderDetectionService,
            )

            header_top = (
                header_check_top_y
                if header_check_top_y is not None
                else max(0, table_top_y - 50)
            )
            header_area = page.crop((0, header_top, page.width, table_bottom_y))
            header_words = header_area.extract_words(use_text_flow=True)

            if not HeaderDetectionService().detect_headers(
                header_words, self.columns, min_keywords=MIN_HEADER_KEYWORDS
            ):
                logger.info("Page %s: No table headers detected, skipping", page_num)
                return None

        return words  # type: ignore[no-any-return]
