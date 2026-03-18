"""Output Orchestrator for bank statement results.

This module orchestrates output generation including:
- Writing files in multiple formats (CSV, JSON, Excel)
- Generating totals and monthly summaries
- Building processing summary results
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.file_io import IJsonWriter
    from bankstatements_core.domain.protocols.services import (
        IColumnTotals,
        IExpenseAnalysis,
        IMonthlySummary,
    )

logger = logging.getLogger(__name__)


class OutputOrchestrator:
    """Orchestrates output file generation.

    Handles:
    - Writing transactions in multiple formats using strategies
    - Writing duplicates JSON
    - Generating and writing monthly summary JSON
    - Generating and writing expense analysis JSON
    - Building summary result dictionary
    """

    def __init__(
        self,
        output_dir: Path,
        output_strategies: dict[str, Any],
        monthly_summary_service: "IMonthlySummary",
        column_names: list[str],
        totals_columns: list[str] | None,
        generate_monthly_summary: bool,
        totals_service: "IColumnTotals | None" = None,
        file_writer: "IJsonWriter | None" = None,
        expense_analysis_service: "IExpenseAnalysis | None" = None,
        generate_expense_analysis: bool = False,
    ):
        """Initialize output orchestrator.

        Args:
            output_dir: Directory to write output files
            output_strategies: Dict mapping format names to output strategies
            monthly_summary_service: Service for generating monthly summaries
            column_names: List of column names for output
            totals_columns: List of column patterns for totals calculation
            generate_monthly_summary: Whether to generate monthly summary
            totals_service: Service for calculating column totals (optional, creates default if None)
            file_writer: Optional file writer for dependency injection (default: use direct file I/O)
            expense_analysis_service: Optional service for generating expense analysis
            generate_expense_analysis: Whether to generate expense analysis (default: False)
        """
        from bankstatements_core.services.totals_calculator import ColumnTotalsService

        self.output_dir = output_dir
        self.output_strategies = output_strategies
        self.monthly_summary_service = monthly_summary_service
        self.column_names = column_names
        self.totals_columns = totals_columns or []
        self.generate_monthly_summary = generate_monthly_summary
        self.expense_analysis_service = expense_analysis_service
        self.generate_expense_analysis = generate_expense_analysis
        self._file_writer = file_writer
        # Create totals service if totals are configured
        self.totals_service = (
            totals_service
            if totals_service
            else (
                ColumnTotalsService(self.totals_columns)
                if self.totals_columns
                else None
            )
        )

    def write_output_files(
        self,
        unique_rows: list[dict],
        duplicate_rows: list[dict],
        df_unique: pd.DataFrame,
        iban_suffix: str | None = None,
    ) -> dict[str, str]:
        """Write all output files using configured output format strategies.

        Args:
            unique_rows: List of unique transaction dictionaries
            duplicate_rows: List of duplicate transaction dictionaries
            df_unique: DataFrame of unique transactions
            iban_suffix: Optional IBAN suffix (last 4 digits) for filename

        Returns:
            Dictionary mapping output types to file paths

        Examples:
            >>> orchestrator = OutputOrchestrator(output_dir, strategies, ...)
            >>> paths = orchestrator.write_output_files(unique, dupes, df)
            >>> print(f"CSV saved to: {paths['csv_path']}")
        """
        output_paths = {}

        # Build filename suffix if IBAN provided
        filename_suffix = f"_{iban_suffix}" if iban_suffix else ""

        # Pre-calculate totals if needed (moved from strategy to service layer)
        totals_row = []
        if self.totals_service:
            totals = self.totals_service.calculate(df_unique)
            totals_row = self.totals_service.format_totals_row(
                totals, self.column_names
            )

        # Write unique transactions in all configured formats using strategies
        for format_name, strategy in self.output_strategies.items():
            # Determine file extension based on format
            if format_name == "excel":
                file_path = self.output_dir / f"bank_statements{filename_suffix}.xlsx"
            else:
                file_path = (
                    self.output_dir / f"bank_statements{filename_suffix}.{format_name}"
                )

            logger.info("Writing %s output: %s", format_name.upper(), file_path)

            strategy.write(
                unique_rows,
                file_path,
                self.column_names,
                include_totals=bool(self.totals_columns),
                totals_columns=self.totals_columns,
                totals_row=totals_row,  # Pass pre-calculated totals
            )

            output_paths[f"{format_name}_path"] = str(file_path)

        # Write duplicates (always JSON, regardless of OUTPUT_FORMATS)
        duplicates_path = self.output_dir / f"duplicates{filename_suffix}.json"
        self._write_json_file(duplicates_path, duplicate_rows)
        output_paths["duplicates_path"] = str(duplicates_path)

        # Generate monthly summary (always JSON, regardless of OUTPUT_FORMATS)
        # Only generate if enabled via generate_monthly_summary flag
        if self.generate_monthly_summary and unique_rows:
            logger.info("Generating monthly summary JSON")
            monthly_summary = self.monthly_summary_service.generate(unique_rows)
            monthly_summary_path = (
                self.output_dir / f"monthly_summary{filename_suffix}.json"
            )
            self._write_json_file(monthly_summary_path, monthly_summary)
            output_paths["monthly_summary_path"] = str(monthly_summary_path)
            logger.info("Monthly summary saved to: %s", monthly_summary_path)

        # Generate expense analysis (always JSON, regardless of OUTPUT_FORMATS)
        # Only generate if enabled via generate_expense_analysis flag
        if (
            self.generate_expense_analysis
            and self.expense_analysis_service
            and unique_rows
        ):
            logger.info("Generating expense analysis JSON")
            expense_analysis = self.expense_analysis_service.analyze(unique_rows)
            expense_analysis_path = (
                self.output_dir / f"expense_analysis{filename_suffix}.json"
            )
            self._write_json_file(expense_analysis_path, expense_analysis)
            output_paths["expense_analysis_path"] = str(expense_analysis_path)
            logger.info("Expense analysis saved to: %s", expense_analysis_path)

        return output_paths

    def build_summary_result(
        self,
        pdf_count: int,
        pages_read: int,
        unique_count: int,
        duplicate_count: int,
        output_paths: dict[str, str],
    ) -> dict:
        """Build the final summary result dictionary.

        Args:
            pdf_count: Number of PDFs processed
            pages_read: Total pages read
            unique_count: Number of unique transactions
            duplicate_count: Number of duplicate transactions
            output_paths: Dictionary of output file paths

        Returns:
            Summary dictionary with processing results

        Examples:
            >>> orchestrator = OutputOrchestrator(...)
            >>> summary = orchestrator.build_summary_result(5, 25, 100, 5, paths)
            >>> print(f"Processed {summary['transactions']} transactions")
        """
        summary_result: dict[str, Any] = {
            "pdf_count": pdf_count,
            "pages_read": pages_read,
            "transactions": unique_count,
            "duplicates": duplicate_count,
        }

        # Add output file paths
        summary_result.update(output_paths)

        return summary_result

    def _write_json_file(self, path: Path, data: Any) -> None:
        """Write data to JSON file.

        Args:
            path: Path to write JSON file
            data: Data to serialize to JSON
        """
        if self._file_writer:
            self._file_writer.write_json(path, data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
