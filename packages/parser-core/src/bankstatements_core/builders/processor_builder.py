"""Builder for BankStatementProcessor with fluent interface.

This module provides a Builder pattern implementation for constructing
BankStatementProcessor instances with a clean, readable fluent interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    OutputConfig,
    ProcessingConfig,
    ProcessorConfig,
)

if TYPE_CHECKING:
    from bankstatements_core.processor import BankStatementProcessor

logger = logging.getLogger(__name__)


class BankStatementProcessorBuilder:
    """
    Builder for constructing BankStatementProcessor instances.

    Uses fluent interface for readable, self-documenting construction.
    Validates required parameters before building.
    """

    def __init__(self) -> None:
        """Initialize builder with default values."""
        # Required parameters (no defaults)
        self._input_dir: Path | None = None
        self._output_dir: Path | None = None

        # Optional parameters with sensible defaults
        self._table_top_y: int = 300
        self._table_bottom_y: int = 720
        self._columns: dict[str, tuple[int | float, int | float]] | None = None
        self._enable_dynamic_boundary: bool = False
        self._sort_by_date: bool = True
        self._recursive_scan: bool = True
        self._totals_columns: list[str] | None = None
        self._generate_monthly_summary: bool = True
        self._generate_expense_analysis: bool = True
        self._output_strategies: dict[str, Any] | None = None
        self._duplicate_strategy: Any | None = None
        self._repository: Any | None = None
        self._activity_log: Any | None = None
        self._entitlements: Any | None = None

    def with_input_dir(self, path: Path) -> "BankStatementProcessorBuilder":
        """
        Set input directory (required).

        Args:
            path: Path to directory containing PDF files

        Returns:
            Self for method chaining
        """
        self._input_dir = path
        return self

    def with_output_dir(self, path: Path) -> "BankStatementProcessorBuilder":
        """
        Set output directory (required).

        Args:
            path: Path to directory for output files

        Returns:
            Self for method chaining
        """
        self._output_dir = path
        return self

    def with_table_bounds(
        self, top_y: int, bottom_y: int
    ) -> "BankStatementProcessorBuilder":
        """
        Set table boundary coordinates.

        Args:
            top_y: Top Y coordinate for table extraction
            bottom_y: Bottom Y coordinate for table extraction

        Returns:
            Self for method chaining
        """
        self._table_top_y = top_y
        self._table_bottom_y = bottom_y
        return self

    def with_columns(
        self, columns: dict[str, tuple[int | float, int | float]]
    ) -> "BankStatementProcessorBuilder":
        """
        Set column definitions.

        Args:
            columns: Dictionary mapping column names to (x_min, x_max) boundaries

        Returns:
            Self for method chaining
        """
        self._columns = columns
        return self

    def with_dynamic_boundary(
        self, enabled: bool = True
    ) -> "BankStatementProcessorBuilder":
        """
        Enable or disable dynamic boundary detection.

        Args:
            enabled: Whether to use dynamic table end detection

        Returns:
            Self for method chaining
        """
        self._enable_dynamic_boundary = enabled
        return self

    def with_date_sorting(
        self, enabled: bool = True
    ) -> "BankStatementProcessorBuilder":
        """
        Enable or disable chronological date sorting.

        Args:
            enabled: Whether to sort transactions by date

        Returns:
            Self for method chaining
        """
        self._sort_by_date = enabled
        return self

    def with_recursive_scan(
        self, enabled: bool = False
    ) -> "BankStatementProcessorBuilder":
        """
        Enable or disable recursive directory scanning for PDFs.

        Requires PAID tier entitlement.

        Args:
            enabled: Whether to scan subdirectories recursively

        Returns:
            Self for method chaining
        """
        self._recursive_scan = enabled
        return self

    def with_totals(
        self, column_patterns: list[str]
    ) -> "BankStatementProcessorBuilder":
        """
        Set column patterns for totals calculation.

        Args:
            column_patterns: List of column patterns to calculate totals for

        Returns:
            Self for method chaining
        """
        self._totals_columns = column_patterns
        return self

    def with_monthly_summary(
        self, enabled: bool = True
    ) -> "BankStatementProcessorBuilder":
        """
        Enable or disable monthly summary generation.

        Args:
            enabled: Whether to generate monthly summary JSON

        Returns:
            Self for method chaining
        """
        self._generate_monthly_summary = enabled
        return self

    def with_expense_analysis(
        self, enabled: bool = True
    ) -> "BankStatementProcessorBuilder":
        """
        Enable or disable expense analysis generation.

        Args:
            enabled: Whether to generate expense analysis JSON

        Returns:
            Self for method chaining
        """
        self._generate_expense_analysis = enabled
        return self

    def with_output_strategies(
        self, strategies: dict[str, Any]
    ) -> "BankStatementProcessorBuilder":
        """
        Set output format strategies.

        Args:
            strategies: Dictionary mapping format names to OutputFormatStrategy instances

        Returns:
            Self for method chaining
        """
        self._output_strategies = strategies
        return self

    def with_duplicate_strategy(self, strategy: Any) -> "BankStatementProcessorBuilder":
        """
        Set duplicate detection strategy.

        Args:
            strategy: DuplicateDetectionStrategy instance

        Returns:
            Self for method chaining
        """
        self._duplicate_strategy = strategy
        return self

    def with_repository(self, repository: Any) -> "BankStatementProcessorBuilder":
        """
        Set transaction repository.

        Args:
            repository: TransactionRepository instance

        Returns:
            Self for method chaining
        """
        self._repository = repository
        return self

    def with_activity_log(self, activity_log: Any) -> "BankStatementProcessorBuilder":
        """
        Set processing activity log for GDPR audit trail.

        Args:
            activity_log: ProcessingActivityLog instance

        Returns:
            Self for method chaining
        """
        self._activity_log = activity_log
        return self

    def with_entitlements(self, entitlements: Any) -> "BankStatementProcessorBuilder":
        """
        Set entitlements for tier-based feature access control.

        Args:
            entitlements: Entitlements instance (FREE or PAID tier)

        Returns:
            Self for method chaining
        """
        self._entitlements = entitlements
        return self

    def _get_output_formats(self) -> list[str]:
        """
        Determine output formats from configured strategies.

        Returns:
            List of output format names
        """
        if self._output_strategies is not None:
            return list(self._output_strategies.keys())
        # Default to CSV and JSON
        return ["csv", "json"]

    def build_config(self) -> ProcessorConfig:
        """
        Build configuration object from builder settings.

        Returns:
            ProcessorConfig instance

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate required parameters
        if self._input_dir is None:
            raise ValueError("Input directory is required. Use with_input_dir().")
        if self._output_dir is None:
            raise ValueError("Output directory is required. Use with_output_dir().")

        return ProcessorConfig(
            input_dir=self._input_dir,
            output_dir=self._output_dir,
            extraction=ExtractionConfig(
                table_top_y=self._table_top_y,
                table_bottom_y=self._table_bottom_y,
                columns=self._columns,
                enable_dynamic_boundary=self._enable_dynamic_boundary,
            ),
            processing=ProcessingConfig(
                sort_by_date=self._sort_by_date,
                recursive_scan=self._recursive_scan,
                totals_columns=self._totals_columns,
                generate_monthly_summary=self._generate_monthly_summary,
                generate_expense_analysis=self._generate_expense_analysis,
            ),
            output=OutputConfig(
                output_formats=self._get_output_formats(),
            ),
        )

    def build(self) -> "BankStatementProcessor":
        """
        Build and return BankStatementProcessor instance.

        Returns:
            Configured BankStatementProcessor instance

        Raises:
            ValueError: If required parameters are missing
        """
        # Import here to avoid circular dependencies
        from bankstatements_core.processor import BankStatementProcessor

        # Build configuration object
        config = self.build_config()

        logger.info(
            "Building BankStatementProcessor: input=%s, output=%s, dynamic_boundary=%s",
            config.input_dir,
            config.output_dir,
            config.extraction.enable_dynamic_boundary,
        )

        return BankStatementProcessor(
            config=config,
            output_strategies=self._output_strategies,
            duplicate_strategy=self._duplicate_strategy,
            repository=self._repository,
            activity_log=self._activity_log,
            entitlements=self._entitlements,
        )
