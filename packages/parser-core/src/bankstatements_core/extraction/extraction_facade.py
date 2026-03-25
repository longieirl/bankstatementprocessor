"""Main extraction facade for PDF table processing.

This module provides simplified interfaces for PDF table extraction
and boundary detection. Extracted from pdf_table_extractor.py to
improve separation of concerns.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bankstatements_core.config.column_config import DEFAULT_COLUMNS
from bankstatements_core.extraction.extraction_params import TABLE_BOTTOM_Y, TABLE_TOP_Y
from bankstatements_core.domain import ExtractionResult

if TYPE_CHECKING:
    from bankstatements_core.extraction.row_classifiers import RowClassifier
    from bankstatements_core.templates.template_model import BankTemplate


def detect_table_end_boundary_smart(
    words: list[dict],
    table_top_y: int,
    columns: dict[str, tuple[int | float, int | float]],
    fallback_bottom_y: int = TABLE_BOTTOM_Y,
    min_section_gap: int = 50,
    structure_breakdown_threshold: int = 8,
    dynamic_boundary_threshold: int = 15,
    row_classifier: "RowClassifier | None" = None,
) -> int:
    """
    Detect table end intelligently (facade).

    This function delegates to TableBoundaryDetector for the actual detection logic.

    Args:
        words: List of all words from the page
        table_top_y: Top boundary of table area
        columns: Column definitions
        fallback_bottom_y: Fallback bottom boundary if detection fails
        min_section_gap: Minimum gap in pixels to consider a section boundary
        structure_breakdown_threshold: Number of empty columns to consider structure broken
        dynamic_boundary_threshold: Consecutive non-transaction rows before ending extraction
        row_classifier: Optional RowClassifier chain; creates default if not provided

    Returns:
        Detected bottom Y coordinate
    """
    from bankstatements_core.extraction.boundary_detector import TableBoundaryDetector

    detector = TableBoundaryDetector(
        columns=columns,
        fallback_bottom_y=fallback_bottom_y,
        table_top_y=table_top_y,
        min_section_gap=min_section_gap,
        structure_breakdown_threshold=structure_breakdown_threshold,
        dynamic_boundary_threshold=dynamic_boundary_threshold,
        row_classifier=row_classifier,
    )

    return detector.detect_boundary(words)


def extract_tables_from_pdf(
    pdf_path: Path,
    table_top_y: int = TABLE_TOP_Y,
    table_bottom_y: int = TABLE_BOTTOM_Y,
    columns: dict[str, tuple[int | float, int | float]] | None = None,
    enable_dynamic_boundary: bool = False,
    enable_page_validation: bool | None = None,
    enable_header_check: bool | None = None,
    template: "BankTemplate" | None = None,
) -> ExtractionResult:
    """
    Extract table data from PDF within specified bounds (facade function).

    This function delegates to PDFTableExtractor class for actual extraction.

    Args:
        pdf_path: Path to the PDF file
        table_top_y: Top Y coordinate for table extraction
        table_bottom_y: Bottom Y coordinate for table extraction
        columns: Dictionary mapping column names to (x_min, x_max) boundaries
        enable_dynamic_boundary: Whether to use dynamic table end detection
        enable_page_validation: Whether to validate page structure
        enable_header_check: Whether to check for table headers
        template: Optional BankTemplate to use for extraction configuration

    Returns:
        ExtractionResult containing extracted transactions, page count, IBAN,
        source file path, and any document-level warnings
    """
    from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

    # If template provided, use template configuration
    if template is not None:
        table_top_y = template.extraction.table_top_y
        table_bottom_y = template.extraction.table_bottom_y
        columns = template.extraction.columns
        if enable_page_validation is None:
            enable_page_validation = template.extraction.enable_page_validation
        if enable_header_check is None:
            enable_header_check = template.extraction.enable_header_check
        header_check_top_y = template.extraction.header_check_top_y
    else:
        header_check_top_y = None

    if columns is None:
        columns = DEFAULT_COLUMNS

    # Provide defaults if still None
    if enable_page_validation is None:
        enable_page_validation = True
    if enable_header_check is None:
        enable_header_check = True

    extractor = PDFTableExtractor(
        columns=columns,
        table_top_y=table_top_y,
        table_bottom_y=table_bottom_y,
        enable_dynamic_boundary=enable_dynamic_boundary,
        enable_page_validation=enable_page_validation,
        enable_header_check=enable_header_check,
        header_check_top_y=header_check_top_y,
        extraction_config=template.extraction if template is not None else None,
        template=template,  # NEW: Pass template for document type
    )

    return extractor.extract(pdf_path)
