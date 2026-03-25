"""
Factory Pattern implementations for object creation.

This module provides factory classes that encapsulate the creation logic
for complex objects, making it easier to instantiate processors with
different configurations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bankstatements_core.config.app_config import AppConfig
from bankstatements_core.config.column_config import get_columns_config
from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    OutputConfig,
    ProcessingConfig,
    ProcessorConfig,
)
from bankstatements_core.patterns.strategies import (
    AllFieldsDuplicateStrategy,
    CSVOutputStrategy,
    DateAmountDuplicateStrategy,
    DuplicateDetectionStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
    OutputFormatStrategy,
)

if TYPE_CHECKING:
    from bankstatements_core.processor import BankStatementProcessor


class ProcessorFactory:
    """
    Factory for creating BankStatementProcessor instances.

    This factory encapsulates the complex instantiation logic and allows
    different processor configurations to be created easily.
    """

    @staticmethod
    def create_from_config(
        config: AppConfig,
        duplicate_strategy: DuplicateDetectionStrategy | None = None,
        output_strategies: dict[str, OutputFormatStrategy] | None = None,
        activity_log: Any | None = None,
        entitlements: Any | None = None,
    ) -> "BankStatementProcessor":
        """
        Create a processor from application configuration using Builder pattern.

        Args:
            config: Application configuration
            duplicate_strategy: Optional custom duplicate detection strategy.
                               Defaults to AllFieldsDuplicateStrategy.
            output_strategies: Optional custom output format strategies.
                              If None, builds strategies from config.output_formats.
            activity_log: Optional ProcessingActivityLog for GDPR audit trail.
            entitlements: Optional Entitlements for tier-based feature access control.

        Returns:
            Configured BankStatementProcessor instance
        """
        from bankstatements_core.builders import BankStatementProcessorBuilder

        # Get column configuration
        columns = get_columns_config()

        # Build output strategies from config if not provided
        if output_strategies is None:
            strategy_map = {
                "csv": CSVOutputStrategy(),
                "json": JSONOutputStrategy(),
                "excel": ExcelOutputStrategy(),
            }
            output_strategies = {
                fmt: strategy_map[fmt]
                for fmt in config.output_formats
                if fmt in strategy_map
            }

        # Use default duplicate strategy if none provided
        if duplicate_strategy is None:
            duplicate_strategy = AllFieldsDuplicateStrategy()

        # Build ProcessorConfig from AppConfig fields
        processor_config = ProcessorConfig(
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            extraction=ExtractionConfig(
                table_top_y=config.table_top_y,
                table_bottom_y=config.table_bottom_y,
                columns=columns,
                enable_dynamic_boundary=config.enable_dynamic_boundary,
            ),
            processing=ProcessingConfig(
                sort_by_date=config.sort_by_date,
                recursive_scan=config.recursive_scan,
                totals_columns=config.totals_columns,
                generate_monthly_summary=config.generate_monthly_summary,
                generate_expense_analysis=config.generate_expense_analysis,
            ),
            output=OutputConfig(
                output_formats=config.output_formats,
            ),
        )

        # Build processor using fluent interface
        builder = (
            BankStatementProcessorBuilder()
            .with_processor_config(processor_config)
            .with_output_strategies(output_strategies)
            .with_duplicate_strategy(duplicate_strategy)
        )

        # Add activity log if provided
        if activity_log is not None:
            builder.with_activity_log(activity_log)

        # Add entitlements if provided
        if entitlements is not None:
            builder.with_entitlements(entitlements)

        return builder.build()

    @staticmethod
    def create_for_bank(bank_type: str, config: AppConfig) -> "BankStatementProcessor":
        """
        Create a processor optimized for a specific bank.

        This method allows bank-specific configurations and strategies
        to be applied automatically.

        Args:
            bank_type: Type of bank ("strict", "lenient", etc.)
            config: Application configuration

        Returns:
            Configured BankStatementProcessor instance

        Examples:
            >>> processor = ProcessorFactory.create_for_bank("lenient", config)
        """
        # Select duplicate detection strategy based on bank
        if bank_type == "lenient":
            # Use lenient matching for banks with varying descriptions
            strategy: DuplicateDetectionStrategy = DateAmountDuplicateStrategy()
        else:
            # Default to strict matching
            strategy = AllFieldsDuplicateStrategy()

        return ProcessorFactory.create_from_config(config, strategy)

    @staticmethod
    def create_custom(
        input_dir: Path,
        output_dir: Path,
        table_top_y: int = 100,
        table_bottom_y: int = 700,
        duplicate_strategy: DuplicateDetectionStrategy | None = None,
        output_strategies: dict[str, OutputFormatStrategy] | None = None,
        entitlements: Any | None = None,
        **kwargs: Any,
    ) -> "BankStatementProcessor":
        """
        Create a processor with custom parameters.

        This provides a convenient way to create processors programmatically
        without needing full AppConfig.

        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output files
            table_top_y: Top Y coordinate for table extraction
            table_bottom_y: Bottom Y coordinate for table extraction
            duplicate_strategy: Custom duplicate detection strategy
            output_strategies: Custom output format strategies (default: CSV and JSON)
            entitlements: Optional Entitlements for tier-based feature access control.
            **kwargs: Additional processor options (sort_by_date, etc.)

        Returns:
            Configured BankStatementProcessor instance
        """
        from bankstatements_core.processor import BankStatementProcessor

        columns = get_columns_config()

        if duplicate_strategy is None:
            duplicate_strategy = AllFieldsDuplicateStrategy()

        # Build default output strategies if not provided
        if output_strategies is None:
            output_strategies = {
                "csv": CSVOutputStrategy(),
                "json": JSONOutputStrategy(),
            }

        # Build configuration object
        config = ProcessorConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            extraction=ExtractionConfig(
                table_top_y=table_top_y,
                table_bottom_y=table_bottom_y,
                columns=columns,
                enable_dynamic_boundary=kwargs.get("enable_dynamic_boundary", False),
            ),
            processing=ProcessingConfig(
                sort_by_date=kwargs.get("sort_by_date", True),
                totals_columns=kwargs.get("totals_columns", ["debit", "credit"]),
                generate_monthly_summary=kwargs.get("generate_monthly_summary", True),
                generate_expense_analysis=kwargs.get("generate_expense_analysis", True),
            ),
            output=OutputConfig(
                output_formats=(
                    list(output_strategies.keys())
                    if output_strategies
                    else ["csv", "json"]
                ),
            ),
        )

        from bankstatements_core.services.service_registry import ServiceRegistry

        registry = ServiceRegistry.from_config(config, entitlements=entitlements)

        processor = BankStatementProcessor(
            config=config,
            output_strategies=output_strategies,
            duplicate_strategy=duplicate_strategy,
            entitlements=entitlements,
            registry=registry,
        )

        return processor
