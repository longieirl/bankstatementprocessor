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
        enable_page_validation: Whether to validate page structure before extraction
        enable_header_check: Whether to check for table headers in extracted data
        min_section_gap: Minimum gap in pixels to consider a section boundary (for dynamic detection)
        structure_breakdown_threshold: Number of empty columns to consider structure broken
        dynamic_boundary_threshold: Consecutive non-transaction rows before ending extraction
    """

    table_top_y: int = 300
    table_bottom_y: int = 720
    columns: dict[str, tuple[int | float, int | float]] | None = None
    enable_dynamic_boundary: bool = False
    enable_page_validation: bool = True
    enable_header_check: bool = True
    min_section_gap: int = 50
    structure_breakdown_threshold: int = 8
    dynamic_boundary_threshold: int = 15


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
    recursive_scan: bool = False


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
