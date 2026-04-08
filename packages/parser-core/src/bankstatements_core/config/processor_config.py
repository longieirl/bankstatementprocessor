"""Configuration dataclasses for bank statement processor.

This module provides configuration objects to reduce parameter counts
and improve maintainability of the BankStatementProcessor class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractionConfig:
    """Configuration for PDF extraction.

    Attributes:
        table_top_y: Y-coordinate for top boundary of table extraction area
        table_bottom_y: Y-coordinate for bottom boundary of table extraction area
        columns: Optional dictionary mapping column names to (x_start, x_end) tuples
        enable_dynamic_boundary: Whether to enable dynamic boundary detection

    Note:
        enable_page_validation and enable_header_check are template-level settings
        sourced from BankTemplate.extraction (TemplateExtractionConfig), not from
        this config object. Boundary-detection thresholds (min_section_gap,
        structure_breakdown_threshold, dynamic_boundary_threshold) are owned by
        BoundaryDetector and are not operator-configurable via this config.
    """

    table_top_y: int = 300
    table_bottom_y: int = 720
    columns: dict[str, tuple[int | float, int | float]] | None = None
    enable_dynamic_boundary: bool = False


@dataclass
class ProcessingConfig:
    """Configuration for transaction processing.

    Attributes:
        sort_by_date: Whether to sort transactions by date
        totals_columns: Optional list of column names to calculate totals for
        generate_monthly_summary: Whether to generate monthly summary reports
        generate_expense_analysis: Whether to generate expense analysis reports
        recursive_scan: Whether to scan subdirectories recursively for PDF files
    """

    sort_by_date: bool = True
    totals_columns: list[str] | None = None
    generate_monthly_summary: bool = True
    generate_expense_analysis: bool = True
    recursive_scan: bool = True


@dataclass
class OutputConfig:
    """Configuration for output generation.

    Attributes:
        output_formats: List of output format names (e.g., ['csv', 'json', 'excel'])
    """

    output_formats: list[str] = field(
        default_factory=lambda: ["csv", "json", "excel"]
    )  # All formats available in FREE tier


@dataclass
class ProcessorConfig:
    """Complete processor configuration.

    This configuration object groups all processor settings into logical sections,
    reducing the parameter count in BankStatementProcessor.__init__ from 11 to 5.

    Attributes:
        input_dir: Directory containing PDF files to process
        output_dir: Directory where output files will be written
        extraction: Configuration for PDF extraction behavior
        processing: Configuration for transaction processing behavior
        output: Configuration for output generation
    """

    input_dir: Path
    output_dir: Path
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
