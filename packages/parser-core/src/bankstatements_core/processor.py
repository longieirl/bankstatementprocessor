from __future__ import annotations

import json  # noqa: F401 - imported for test mocking
import logging
from collections import defaultdict  # noqa: F401 - imported for test mocking
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from bankstatements_core.config.column_config import DEFAULT_COLUMNS, get_column_names
from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.config.totals_config import parse_totals_columns  # noqa: F401
from bankstatements_core.services.column_analysis import ColumnAnalysisService
from bankstatements_core.services.date_parser import DateParserService
from bankstatements_core.services.duplicate_detector import DuplicateDetectionService
from bankstatements_core.services.expense_analysis import ExpenseAnalysisService
from bankstatements_core.services.monthly_summary import MonthlySummaryService
from bankstatements_core.services.output_orchestrator import OutputOrchestrator
from bankstatements_core.services.pdf_processing_orchestrator import (
    PDFProcessingOrchestrator,
)
from bankstatements_core.services.sorting_service import (
    ChronologicalSortingStrategy,
    NoSortingStrategy,
    TransactionSortingService,
)
from bankstatements_core.services.transaction_filter import TransactionFilterService
from bankstatements_core.services.transaction_processing_orchestrator import (
    TransactionProcessingOrchestrator,
)
from bankstatements_core.utils import is_date_column, to_float  # noqa: F401

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
    def __init__(
        self,
        config: ProcessorConfig,
        output_strategies: dict[str, Any] | None = None,
        duplicate_strategy: Any | None = None,
        repository: Any | None = None,
        activity_log: Any | None = None,
        entitlements: Any | None = None,
        template_registry: Any | None = None,
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
            from bankstatements_core.patterns.strategies import (
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
            from bankstatements_core.patterns.strategies import (
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
            from bankstatements_core.patterns.repositories import (
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

        self._transaction_orchestrator = TransactionProcessingOrchestrator(
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

    def _detect_duplicates(self, all_rows: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Separate unique transactions from duplicates using the configured strategy.

        The strategy determines how transactions are compared for duplication.
        """
        return self._duplicate_service.detect_and_separate(all_rows)

    def _write_csv_with_totals(self, df: pd.DataFrame, csv_path: Path) -> None:
        """
        Write DataFrame to CSV with optional totals rows appended.

        Args:
            df: DataFrame containing transaction data
            csv_path: Path to write the CSV file
        """
        # Write the main transaction data first
        df.to_csv(csv_path, index=False)

        # If totals are configured, append them to the CSV
        if self.totals_columns:
            # Find columns that match the configured patterns
            matching_columns = find_matching_columns(
                list(df.columns), self.totals_columns
            )

            if matching_columns:
                logger.info(
                    "Calculating totals for columns: %s", ", ".join(matching_columns)
                )

                # Calculate totals for matching columns
                totals = calculate_column_totals(df, matching_columns)

                # Create totals rows
                self._append_totals_to_csv(csv_path, list(df.columns), totals)

                logger.info("Totals appended to CSV: %s", csv_path)
            else:
                logger.warning(
                    "No columns found matching totals patterns: %s",
                    ", ".join(self.totals_columns),
                )

    def _append_totals_to_csv(
        self, csv_path: Path, all_columns: list[str], totals: dict[str, float]
    ) -> None:
        """
        Append totals rows to the existing CSV file using repository.

        Args:
            csv_path: Path to the CSV file
            all_columns: All column names in the CSV
            totals: Dictionary mapping column names to their totals
        """
        # Build totals content
        content_parts = ["\n"]  # Empty line for separation

        # Create totals row
        totals_row = []
        for col_name in all_columns:
            if col_name in totals:
                # Format the total value (2 decimal places for currency)
                totals_row.append(f"{totals[col_name]:.2f}")
            elif is_date_column(col_name):
                # Add "TOTAL" label in the first column (usually Date)
                totals_row.append("TOTAL")
            else:
                # Empty value for non-total columns
                totals_row.append("")

        # Build content string
        content_parts.append(",".join(f'"{value}"' for value in totals_row))
        content_parts.append("\n")

        # Use repository to append
        self.repository.append_to_csv(csv_path, "".join(content_parts))

    def _process_all_pdfs(self) -> tuple[list[dict], int, dict[str, str]]:
        """Process all PDF files in the input directory and extract transaction data.

        Returns:
            Tuple of (all_rows, total_pages_read, pdf_ibans)
        """
        # Delegate to PDF processing orchestrator with recursive_scan setting
        return self._pdf_orchestrator.process_all_pdfs(
            self.input_dir, recursive=self.recursive_scan
        )

    def _filter_rows(
        self,
        rows: list[dict],
        predicate: Callable[[dict], bool],
        filter_name: str = "rows",
    ) -> list[dict]:
        """
        Generic row filter that applies a predicate function to each row.

        This method eliminates code duplication across various filtering operations
        by providing a unified filtering pattern.

        Args:
            rows: List of transaction dictionaries to filter
            predicate: Function that returns True if row should be kept, False if filtered
            filter_name: Human-readable name for logging (e.g., "empty rows", "header rows")

        Returns:
            List of transactions that passed the predicate
        """
        filtered_rows = []
        filtered_count = 0

        for row in rows:
            if predicate(row):
                filtered_rows.append(row)
            else:
                filtered_count += 1

        if filtered_count > 0:
            logger.debug(f"Filtered out {filtered_count} {filter_name}")

        return filtered_rows

    def _has_row_data(self, row: dict) -> bool:
        """
        Check if a row has any non-empty data (excluding Filename).

        Args:
            row: Transaction dictionary to check

        Returns:
            True if row has data, False if empty
        """
        for key, value in row.items():
            if key == "Filename":
                continue
            if value and str(value).strip():
                return True
        return False

    def _filter_empty_rows(self, rows: list[dict]) -> list[dict]:
        """
        Filter out empty rows that have no meaningful data.

        A row is considered empty if all its values (excluding 'Filename') are empty,
        whitespace, or None.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of non-empty transactions
        """
        return self._filter_rows(rows, self._has_row_data, "empty rows")

    def _is_header_row(self, row: dict) -> bool:
        """
        Detect if a row is actually a table header row.

        A row is considered a header if its values match the column names.
        For example, if the "Debit €" column contains the value "Debit €",
        that indicates it's a header row, not transaction data.

        Args:
            row: Transaction dictionary to check

        Returns:
            True if the row is a header row, False otherwise
        """
        # Count how many fields have values that match their column names
        matches = 0
        checked_fields = 0

        for column_name, value in row.items():
            # Skip the Filename field
            if column_name == "Filename":
                continue

            # Skip empty values
            if not value or not str(value).strip():
                continue

            checked_fields += 1
            value_str = str(value).strip()
            column_str = column_name.strip()

            # Check for exact match or partial match (case-insensitive)
            if (
                value_str.lower() == column_str.lower()
                or value_str.lower() in column_str.lower()
                or column_str.lower() in value_str.lower()
            ):
                matches += 1

        # If we checked at least 2 fields and more than 50% match, it's a header
        if checked_fields >= 2 and matches / checked_fields > 0.5:
            logger.debug(
                "Detected header row: %d/%d fields matched", matches, checked_fields
            )
            return True

        return False

    def _filter_header_rows(self, rows: list[dict]) -> list[dict]:
        """
        Filter out header rows that were incorrectly extracted as transactions.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of transactions with header rows removed
        """
        return self._filter_rows(
            rows, lambda row: not self._is_header_row(row), "header rows"
        )

    def _has_valid_transaction_date(self, row: dict) -> bool:
        """
        Check if a row has a valid transaction date.

        A valid transaction date matches patterns like:
        - DD/MM/YY or DD/MM/YYYY
        - DD-MM-YY or DD-MM-YYYY
        - DD MMM YYYY (e.g., "12 Jan 2025")
        - DD MMMM YYYY (e.g., "12 January 2025")

        Args:
            row: Transaction dictionary to check

        Returns:
            True if the row has a valid date, False otherwise
        """
        import re

        date_value = row.get("Date", "")
        if not date_value or not str(date_value).strip():
            return False

        date_str = str(date_value).strip()

        # Pattern for common transaction date formats
        patterns = [
            r"^\d{1,2}/\d{1,2}/\d{2,4}$",  # DD/MM/YY or DD/MM/YYYY
            r"^\d{1,2}-\d{1,2}-\d{2,4}$",  # DD-MM-YY or DD-MM-YYYY
            r"^\d{1,2}/\d{1,2}$",  # DD/MM (partial date, no year)
            r"^\d{1,2}-\d{1,2}$",  # DD-MM (partial date, no year)
            r"^\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)$",  # DD MMM (partial, no year)
            r"^\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{4}$",  # DD MMM YYYY
            r"^\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$",  # DD MMMM YYYY
        ]

        return any(re.match(pattern, date_str, re.IGNORECASE) for pattern in patterns)

    def _filter_invalid_date_rows(self, rows: list[dict]) -> list[dict]:
        """
        Filter out rows with invalid or missing transaction dates.

        This removes junk rows like account summaries, headers, and footer text
        that don't have valid transaction dates.

        Args:
            rows: List of transaction dictionaries

        Returns:
            List of transactions with valid dates
        """
        return self._filter_rows(
            rows, self._has_valid_transaction_date, "rows with invalid dates"
        )

    def _sort_transactions_by_date(self, rows: list[dict]) -> list[dict]:
        """
        Sort transactions using the configured sorting strategy.

        Args:
            rows: List of transaction dictionaries

        Returns:
            Sorted list of transactions (or original order if sorting disabled)
        """
        return self._sorting_service.sort(rows)

    def _group_rows_by_iban(
        self, all_rows: list[dict], pdf_ibans: dict[str, str]
    ) -> dict[str, list[dict]]:
        """
        Group transaction rows by IBAN (last 4 digits).

        Args:
            all_rows: All transaction rows from all PDFs
            pdf_ibans: Dictionary mapping PDF filenames to their IBANs

        Returns:
            Dictionary mapping IBAN suffix (last 4 digits) to list of rows
        """
        rows_by_iban: dict[str, list[dict]] = {}

        # Create reverse mapping: filename -> iban last 4 digits
        filename_to_suffix: dict[str, str] = {}
        for pdf_filename, iban in pdf_ibans.items():
            suffix = iban[-4:] if iban else "unknown"
            filename_to_suffix[pdf_filename] = suffix

        # Group rows by IBAN suffix
        for row in all_rows:
            # Get the PDF filename from the row
            pdf_filename = row.get("Filename", "")

            # Look up the IBAN suffix for this PDF
            iban_suffix = filename_to_suffix.get(pdf_filename, "unknown")

            # Add row to the appropriate group
            if iban_suffix not in rows_by_iban:
                rows_by_iban[iban_suffix] = []
            rows_by_iban[iban_suffix].append(row)

        logger.info(
            f"Grouped transactions into {len(rows_by_iban)} IBAN groups: "
            f"{', '.join(sorted(rows_by_iban.keys()))}"
        )

        return rows_by_iban

    def run(self) -> dict:
        """Process all bank statement PDFs and generate output files.

        Returns:
            Dictionary containing processing summary with counts and file paths
        """
        start_time = datetime.now()

        # Step 1: Extract transactions from all PDFs (delegated to orchestrator)
        all_rows, pages_read, pdf_ibans = self._process_all_pdfs()
        pdf_count = len(sorted(self.input_dir.glob("*.pdf")))

        # Step 2: Group transactions by IBAN (delegated to orchestrator)
        rows_by_iban = self._transaction_orchestrator.group_by_iban(all_rows, pdf_ibans)
        logger.debug(
            f"Grouped {len(all_rows)} transactions into {len(rows_by_iban)} IBAN groups"
        )

        # Step 3: Process each IBAN group
        all_output_paths = {}
        total_unique = 0
        total_duplicates = 0

        for iban_suffix, iban_rows in rows_by_iban.items():
            result = self._process_transaction_group(iban_suffix, iban_rows)

            logger.debug(
                f"IBAN {iban_suffix}: Adding {result['unique_count']} unique, "
                f"{result['duplicate_count']} duplicates to totals"
            )
            total_unique += result["unique_count"]
            total_duplicates += result["duplicate_count"]
            logger.debug(
                f"Running totals: {total_unique} unique, {total_duplicates} duplicates"
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
            f"Building summary: {pdf_count} PDFs, {pages_read} pages, "
            f"{total_unique} unique, {total_duplicates} duplicates"
        )
        return self._output_orchestrator.build_summary_result(
            pdf_count, pages_read, total_unique, total_duplicates, all_output_paths
        )

    def _process_transaction_group(
        self, iban_suffix: str | None, iban_rows: list[dict]
    ) -> dict:
        """Process a group of transactions for a single IBAN.

        Args:
            iban_suffix: IBAN suffix for this group (or "unknown")
            iban_rows: List of transaction dictionaries

        Returns:
            Dictionary with unique_count, duplicate_count, and output_paths
        """
        logger.info(
            f"Processing {len(iban_rows)} transactions for IBAN suffix: {iban_suffix}"
        )

        # Look up template if registry available and transactions have template_id
        template = None
        if self._template_registry and iban_rows:
            template_id = iban_rows[0].get("template_id")
            if template_id:
                template = self._template_registry.get_template(template_id)
                logger.debug(
                    f"Using template '{template_id}' for transaction type classification"
                )

        # Detect duplicates and sort (delegated to orchestrator)
        unique_rows, duplicate_rows = (
            self._transaction_orchestrator.process_transaction_group(
                iban_rows, template=template
            )
        )

        # Filter duplicates to remove any empty rows and header rows
        duplicate_rows = self._filter_service.filter_empty_rows(duplicate_rows)
        duplicate_rows = self._filter_service.filter_header_rows(duplicate_rows)

        logger.info(
            f"IBAN {iban_suffix}: {len(unique_rows)} unique transactions, "
            f"{len(duplicate_rows)} duplicates"
        )

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
