from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from bankstatements_core.config.column_config import DEFAULT_COLUMNS, get_column_names
from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.config.totals_config import (  # noqa: F401 — re-exported for backward compat
    parse_totals_columns,
)
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import transactions_to_dicts
from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.column_analysis import ColumnAnalysisService
from bankstatements_core.services.date_parser import DateParserService
from bankstatements_core.services.duplicate_detector import DuplicateDetectionService
from bankstatements_core.services.expense_analysis import ExpenseAnalysisService
from bankstatements_core.services.monthly_summary import MonthlySummaryService
from bankstatements_core.services.output_orchestrator import OutputOrchestrator
from bankstatements_core.services.pdf_processing_orchestrator import (
    PDFProcessingOrchestrator,
)
from bankstatements_core.services.service_registry import ServiceRegistry
from bankstatements_core.services.sorting_service import (
    ChronologicalSortingStrategy,
    NoSortingStrategy,
    TransactionSortingService,
)
from bankstatements_core.services.transaction_filter import TransactionFilterService
from bankstatements_core.utils import (  # noqa: F401 — re-exported for backward compat
    is_date_column,
    to_float,
)

logger = logging.getLogger(__name__)


# Backward compatibility wrappers - delegate to ColumnAnalysisService
_column_analysis_service = ColumnAnalysisService()


# Keep the delegation wrappers for other column analysis functions


def find_matching_columns(column_names: list[str], patterns: list[str]) -> list[str]:
    """
    Find column names that match the given patterns.

    This is a backward compatibility wrapper around ColumnAnalysisService.

    Args:
        column_names: List of actual column names from CSV
        patterns: List of patterns to match (case-insensitive partial matching)

    Returns:
        List of matching column names
    """
    return _column_analysis_service.find_matching_columns(column_names, patterns)


def calculate_column_totals(
    df: pd.DataFrame, columns_to_total: list[str]
) -> dict[str, float]:
    """
    Calculate totals for specified columns using vectorized operations.

    This is a backward compatibility wrapper around ColumnAnalysisService.

    Args:
        df: DataFrame containing transaction data
        columns_to_total: List of column names to calculate totals for

    Returns:
        Dictionary mapping column names to their totals
    """
    return _column_analysis_service.calculate_column_totals(df, columns_to_total)


def generate_monthly_summary(transactions: list[dict], column_names: list[str]) -> dict:
    """
    Generate monthly summary statistics from transactions.

    This is a backward compatibility wrapper around ColumnAnalysisService.

    Args:
        transactions: List of transaction dictionaries
        column_names: List of all column names to identify debit/credit columns

    Returns:
        Dictionary with monthly summaries
    """
    return _column_analysis_service.generate_monthly_summary(transactions, column_names)


# Backward compatibility wrapper - delegates to DateParserService
_date_parser_service = DateParserService()


def parse_transaction_date(date_str: str) -> datetime:
    """
    Parse bank statement date string into datetime object for sorting.

    This is a backward compatibility wrapper around DateParserService.

    Args:
        date_str: Date string from bank statement

    Returns:
        datetime object for sorting, or epoch (1970-01-01) if unparseable
    """
    return _date_parser_service.parse_transaction_date(date_str)


class BankStatementProcessor:
    # pylint: disable=too-many-instance-attributes
    # Builder/processor class — 27 attributes reflect the full configurable surface
    # area of the processing pipeline. Not reducible without breaking the public API.
    def __init__(  # noqa: PLR0913, PLR0915
        # pylint: disable=too-many-statements
        self,
        config: ProcessorConfig,
        output_strategies: dict[str, Any] | None = None,
        duplicate_strategy: Any | None = None,
        repository: Any | None = None,
        activity_log: Any | None = None,
        entitlements: Any | None = None,
        template_registry: Any | None = None,
        registry: ServiceRegistry | None = None,
    ):
        """
        Initialize the bank statement processor.

        Args:
            config: ProcessorConfig object containing all processor settings
            output_strategies: Dictionary mapping format names to OutputFormatStrategy instances
                (default: None - uses csv and json strategies)
            duplicate_strategy: DuplicateDetectionStrategy instance
                (default: None - uses AllFieldsDuplicateStrategy)
            repository: TransactionRepository instance for file operations
                (default: None - uses FileSystemTransactionRepository)
            activity_log: ProcessingActivityLog instance for GDPR audit trail
                (default: None - no activity logging)
            entitlements: Entitlements instance for tier-based feature access control
                (default: None - allows all features)
            template_registry: TemplateRegistry instance for template lookup
                (default: None - no template-based classification)
        """
        # Store the config object
        self.config = config

        # Map configuration to instance variables
        self.input_dir = config.input_dir
        self.output_dir = config.output_dir
        self.table_top_y = config.extraction.table_top_y
        self.table_bottom_y = config.extraction.table_bottom_y
        self.columns = (
            config.extraction.columns
            if config.extraction.columns is not None
            else DEFAULT_COLUMNS
        )
        self.enable_dynamic_boundary = config.extraction.enable_dynamic_boundary
        self.sort_by_date = config.processing.sort_by_date
        # Default to debit and credit columns if no configuration provided
        default_totals = ["debit", "credit"]
        self.totals_columns = (
            config.processing.totals_columns
            if config.processing.totals_columns is not None
            else default_totals
        )
        self.generate_monthly_summary = config.processing.generate_monthly_summary
        self.generate_expense_analysis = config.processing.generate_expense_analysis
        self.recursive_scan = config.processing.recursive_scan
        self.column_names = get_column_names(self.columns)
        self.entitlements = entitlements

        # Strategy pattern: Output format strategies (defaults based on config)
        if output_strategies is None:
            from bankstatements_core.patterns.strategies import (  # noqa: PLC0415
                CSVOutputStrategy,
                JSONOutputStrategy,
                OutputFormatStrategy,
            )

            # Build strategies based on configured output formats
            self.output_strategies: dict[str, OutputFormatStrategy] = {}
            if "csv" in config.output.output_formats:
                self.output_strategies["csv"] = CSVOutputStrategy()
            if "json" in config.output.output_formats:
                self.output_strategies["json"] = JSONOutputStrategy()
        else:
            self.output_strategies = output_strategies

        # Strategy pattern: Duplicate detection strategy (defaults to AllFieldsStrategy)
        if duplicate_strategy is None:
            from bankstatements_core.patterns.strategies import (  # noqa: PLC0415
                AllFieldsDuplicateStrategy,
            )

            self._duplicate_strategy = AllFieldsDuplicateStrategy()
        else:
            self._duplicate_strategy = duplicate_strategy

        # Service: Duplicate detection service
        self._duplicate_service = DuplicateDetectionService(self._duplicate_strategy)

        # Service: Sorting service (based on sort_by_date flag)
        sorting_strategy = (
            ChronologicalSortingStrategy() if self.sort_by_date else NoSortingStrategy()
        )
        self._sorting_service = TransactionSortingService(sorting_strategy)

        # Service: Monthly summary service
        debit_columns = find_matching_columns(self.column_names, ["debit"])
        credit_columns = find_matching_columns(self.column_names, ["credit"])
        self._monthly_summary_service = MonthlySummaryService(
            debit_columns, credit_columns, entitlements=self.entitlements
        )

        # Service: Expense analysis service
        self._expense_analysis_service = ExpenseAnalysisService(
            entitlements=self.entitlements
        )

        # Service: Transaction filter service
        self._filter_service = TransactionFilterService(self.column_names)

        # Repository pattern: Transaction repository (defaults to FileSystemTransactionRepository)
        if repository is None:
            from bankstatements_core.patterns.repositories import (  # noqa: PLC0415
                FileSystemTransactionRepository,
            )

            self.repository = FileSystemTransactionRepository()
        else:
            self.repository = repository

        # Activity log for GDPR audit trail
        self._activity_log = activity_log

        # Template registry for template lookup
        self._template_registry = template_registry

        # Orchestrators: High-level coordinators for major workflows
        self._pdf_orchestrator = PDFProcessingOrchestrator(
            extraction_config=config.extraction,
            column_names=self.column_names,
            output_dir=self.output_dir,
            repository=self.repository,
            entitlements=self.entitlements,
        )

        # ServiceRegistry: single wiring point for transaction processing
        if registry is not None:
            self._registry = registry
        else:
            self._registry = ServiceRegistry.from_config(
                config,
                entitlements=entitlements,
                duplicate_detector=self._duplicate_service,
                sorting_service=self._sorting_service,
            )

        self._output_orchestrator = OutputOrchestrator(
            output_dir=self.output_dir,
            output_strategies=self.output_strategies,
            monthly_summary_service=self._monthly_summary_service,
            column_names=self.column_names,
            totals_columns=self.totals_columns,
            generate_monthly_summary=self.generate_monthly_summary,
            expense_analysis_service=self._expense_analysis_service,
            generate_expense_analysis=self.generate_expense_analysis,
        )

    def set_duplicate_strategy(self, strategy: Any) -> None:
        """
        Set the duplicate detection strategy.

        Args:
            strategy: DuplicateDetectionStrategy instance
        """
        self._duplicate_strategy = strategy

    def _detect_duplicates(
        self, all_rows: list[Transaction]
    ) -> tuple[list[Transaction], list[Transaction]]:
        """
        Separate unique transactions from duplicates using the configured strategy.

        The strategy determines how transactions are compared for duplication.
        """
        return self._duplicate_service.detect_and_separate(all_rows)

    def _process_all_pdfs(self) -> tuple[list[ExtractionResult], int, int]:
        """Process all PDF files in the input directory and extract transaction data.

        Returns:
            Tuple of (results, pdf_count, pages_read) where pdf_count is total PDFs
            discovered and pages_read covers all PDFs including excluded ones.
        """
        # Delegate to PDF processing orchestrator with recursive_scan setting
        return self._pdf_orchestrator.process_all_pdfs(
            self.input_dir, recursive=self.recursive_scan
        )

    def _sort_transactions_by_date(self, rows: list[Transaction]) -> list[Transaction]:
        """
        Sort transactions using the configured sorting strategy.

        Args:
            rows: List of Transaction objects

        Returns:
            Sorted list of transactions (or original order if sorting disabled)
        """
        return self._sorting_service.sort(rows)

    def run(self) -> dict:
        """Process all bank statement PDFs and generate output files.

        Returns:
            Dictionary containing processing summary with counts and file paths
        """
        start_time = datetime.now()

        # Step 1: Extract transactions from all PDFs (delegated to orchestrator)
        extraction_results, pdf_count, pages_read = (
            self._process_all_pdfs()
        )  # list[ExtractionResult]
        all_transactions: list[Transaction] = []
        pdf_ibans: dict[str, str] = {}
        for extraction in extraction_results:
            if extraction.iban:
                pdf_ibans[extraction.source_file.name] = extraction.iban
            all_transactions.extend(extraction.transactions)

        # Step 2: Group transactions by IBAN (delegated to registry)
        txns_by_iban = self._registry.group_by_iban(all_transactions, pdf_ibans)
        logger.debug(
            "Grouped %s transactions into %s IBAN groups",
            len(all_transactions),
            len(txns_by_iban),
        )

        # Step 3: Process each IBAN group
        all_output_paths = {}
        total_unique = 0
        total_duplicates = 0

        for iban_suffix, iban_txns in txns_by_iban.items():
            result = self._process_transaction_group(iban_suffix, iban_txns)

            logger.debug(
                "IBAN %s: Adding %s unique, %s duplicates to totals",
                iban_suffix,
                result["unique_count"],
                result["duplicate_count"],
            )
            total_unique += result["unique_count"]
            total_duplicates += result["duplicate_count"]
            logger.debug(
                "Running totals: %s unique, %s duplicates",
                total_unique,
                total_duplicates,
            )

            # Merge output paths with IBAN prefix
            for key, value in result["output_paths"].items():
                all_output_paths[f"{iban_suffix}_{key}"] = value

        # Step 4: Log processing activity for GDPR audit trail
        if self._activity_log:
            duration = (datetime.now() - start_time).total_seconds()
            self._activity_log.log_processing(
                pdf_count=pdf_count,
                pages_read=pages_read,
                transaction_count=total_unique,
                duplicate_count=total_duplicates,
                output_formats=list(self.output_strategies.keys()),
                duration_seconds=duration,
            )

        # Step 5: Build and return summary (delegated to orchestrator)
        logger.debug(
            "Building summary: %s PDFs, %s pages, %s unique, %s duplicates",
            pdf_count,
            pages_read,
            total_unique,
            total_duplicates,
        )
        return self._output_orchestrator.build_summary_result(
            pdf_count,
            len(extraction_results),
            pages_read,
            total_unique,
            total_duplicates,
            all_output_paths,
        )

    def _process_transaction_group(
        self, iban_suffix: str | None, iban_txns: list[Transaction]
    ) -> dict:
        """Process a group of transactions for a single IBAN.

        Args:
            iban_suffix: IBAN suffix for this group (or "unknown")
            iban_txns: List of Transaction objects

        Returns:
            Dictionary with unique_count, duplicate_count, and output_paths
        """
        logger.info(
            "Processing %s transactions for IBAN suffix: %s",
            len(iban_txns),
            iban_suffix,
        )

        # Look up template if registry available and transactions have template_id
        template = None
        if self._template_registry and iban_txns:
            template_id = iban_txns[0].additional_fields.get("template_id")
            if template_id:
                template = self._template_registry.get_template(template_id)
                logger.debug(
                    "Using template '%s' for transaction type classification",
                    template_id,
                )

        # Detect duplicates and sort (delegated to registry)
        unique_txns, duplicate_txns = self._registry.process_transaction_group(
            iban_txns, template=template
        )

        # Filter duplicates to remove any empty rows and header rows
        duplicate_txns = self._filter_service.filter_empty_rows(duplicate_txns)
        duplicate_txns = self._filter_service.filter_header_rows(duplicate_txns)

        logger.info(
            "IBAN %s: %s unique transactions, %s duplicates",
            iban_suffix,
            len(unique_txns),
            len(duplicate_txns),
        )

        # Convert to dicts at the output boundary
        unique_rows = transactions_to_dicts(unique_txns)
        duplicate_rows = transactions_to_dicts(duplicate_txns)

        # Create DataFrame for unique transactions
        df_unique = pd.DataFrame(unique_rows, columns=self.column_names)

        # Write output files (delegated to orchestrator)
        output_paths = self._output_orchestrator.write_output_files(
            unique_rows, duplicate_rows, df_unique, iban_suffix
        )

        return {
            "unique_count": len(unique_rows),
            "duplicate_count": len(duplicate_rows),
            "output_paths": output_paths,
        }
