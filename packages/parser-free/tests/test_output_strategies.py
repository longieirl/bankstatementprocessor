"""
Tests for output format strategies.

Tests the Strategy pattern implementation for different output formats,
including Excel, and the configuration integration.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from bankstatements_core.patterns.factories import ProcessorFactory
from bankstatements_core.patterns.strategies import (
    CSVOutputStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
)
from bankstatements_free.app import AppConfig, ConfigurationError

# Check if openpyxl is available (PAID tier dependency)
try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


@pytest.mark.skipif(
    not OPENPYXL_AVAILABLE, reason="openpyxl not installed (PAID tier dependency)"
)
class TestExcelOutputStrategy(unittest.TestCase):
    """Test the ExcelOutputStrategy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = ExcelOutputStrategy()
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Sample transaction data
        self.transactions = [
            {
                "Date": "01/01/2024",
                "Details": "Purchase 1",
                "Debit": "€100.00",
                "Credit": "",
            },
            {
                "Date": "02/01/2024",
                "Details": "Purchase 2",
                "Debit": "€50.00",
                "Credit": "",
            },
            {
                "Date": "03/01/2024",
                "Details": "Refund",
                "Debit": "",
                "Credit": "€25.00",
            },
        ]
        self.column_names = ["Date", "Details", "Debit", "Credit"]

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_write_excel_basic(self):
        """Test basic Excel writing without totals."""
        file_path = self.temp_path / "test.xlsx"

        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
            include_totals=False,
        )

        # Verify file was created
        self.assertTrue(file_path.exists())

        # Read back and verify content
        df = pd.read_excel(file_path, sheet_name="Transactions")
        self.assertEqual(len(df), 3)
        self.assertListEqual(list(df.columns), self.column_names)

    def test_write_excel_with_totals(self):
        """Test Excel writing with totals row."""
        file_path = self.temp_path / "test_totals.xlsx"

        # Calculate totals (Phase 3 refactoring: calculation moved to service layer)
        from bankstatements_core.services.totals_calculator import ColumnTotalsService

        df = pd.DataFrame(self.transactions)
        totals_service = ColumnTotalsService(["debit", "credit"])
        totals = totals_service.calculate(df)
        totals_row = totals_service.format_totals_row(totals, self.column_names)

        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
            include_totals=True,
            totals_columns=["debit", "credit"],
            totals_row=totals_row,
        )

        # Verify file was created
        self.assertTrue(file_path.exists())

        # Read back and verify content
        df = pd.read_excel(file_path, sheet_name="Transactions")
        # Note: Excel includes the empty row and totals row, so we have 5 rows total
        # (3 transactions + 1 empty + 1 totals)
        self.assertEqual(len(df), 5)

        # Verify the first 3 rows are the transactions
        self.assertEqual(df.iloc[0]["Date"], "01/01/2024")
        self.assertEqual(df.iloc[1]["Date"], "02/01/2024")
        self.assertEqual(df.iloc[2]["Date"], "03/01/2024")

        # Verify the totals row has "TOTAL" in Date column
        self.assertEqual(df.iloc[4]["Date"], "TOTAL")

    def test_excel_file_extension(self):
        """Test that Excel strategy works with .xlsx extension."""
        file_path = self.temp_path / "bank_statements.xlsx"

        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
        )

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.suffix, ".xlsx")

    def test_numeric_columns_written_as_numbers(self):
        """Test that numeric columns are written as actual numbers, not text."""
        file_path = self.temp_path / "test_numeric.xlsx"

        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
        )

        # Read the Excel file directly with openpyxl to check cell types
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]

        # Check that Debit column (column C) contains numbers
        # Row 2 should have 100.0 (from "€100.00")
        debit_cell = worksheet["C2"]
        self.assertIsInstance(
            debit_cell.value,
            (int, float),
            "Debit column should contain numbers, not text",
        )
        self.assertAlmostEqual(debit_cell.value, 100.0, places=2)

        # Row 3 should have 50.0 (from "€50.00")
        debit_cell2 = worksheet["C3"]
        self.assertIsInstance(
            debit_cell2.value,
            (int, float),
            "Debit column should contain numbers, not text",
        )
        self.assertAlmostEqual(debit_cell2.value, 50.0, places=2)

        # Check that Credit column (column D) contains numbers
        # Row 4 should have 25.0 (from "€25.00")
        credit_cell = worksheet["D4"]
        self.assertIsInstance(
            credit_cell.value,
            (int, float),
            "Credit column should contain numbers, not text",
        )
        self.assertAlmostEqual(credit_cell.value, 25.0, places=2)

        # Check that empty cells are None (not empty strings)
        empty_credit = worksheet["D2"]  # Credit for first transaction
        self.assertIsNone(empty_credit.value, "Empty numeric cells should be None")

        # Check that non-numeric columns remain as text
        date_cell = worksheet["A2"]
        self.assertIsInstance(date_cell.value, str, "Date column should remain as text")

        workbook.close()

    def test_number_formatting_applied(self):
        """Test that numeric columns have proper Excel number formatting."""
        file_path = self.temp_path / "test_formatting.xlsx"

        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
        )

        # Read the Excel file with openpyxl to check cell formatting
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]

        # Check that numeric cells have number format applied
        # Debit column (C2)
        debit_cell = worksheet["C2"]
        self.assertIn(
            "#,##0",
            debit_cell.number_format,
            "Numeric cells should have comma-separated number format",
        )

        # Credit column (D4)
        credit_cell = worksheet["D4"]
        self.assertIn(
            "#,##0",
            credit_cell.number_format,
            "Numeric cells should have comma-separated number format",
        )

        workbook.close()


class TestOutputFormatConfiguration(unittest.TestCase):
    """Test output format configuration in AppConfig."""

    def test_single_format_csv(self):
        """Test configuring only CSV format."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["csv"])

    def test_single_format_excel(self):
        """Test configuring only Excel format."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "excel"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["excel"])

    def test_multiple_formats(self):
        """Test configuring CSV and Excel together."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,excel"}):
            config = AppConfig.from_env()
            self.assertIn("csv", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_all_formats(self):
        """Test configuring all available formats."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,json,excel"}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            self.assertIn("csv", config.output_formats)
            self.assertIn("json", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_invalid_format_raises_error(self):
        """Test invalid format raises ConfigurationError."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,invalid"}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("Invalid output format", str(context.exception))
            self.assertIn("invalid", str(context.exception))

    def test_empty_format_raises_error(self):
        """Test empty format list raises ConfigurationError."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": ""}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("At least one output format", str(context.exception))

    def test_default_formats(self):
        """Test default output formats when not configured."""
        with patch.dict("os.environ", {}, clear=True):
            config = AppConfig.from_env()
            # Default should be csv only (FREE tier compatible)
            self.assertIn("csv", config.output_formats)
            self.assertEqual(len(config.output_formats), 1)

    def test_formats_with_whitespace(self):
        """Test formats are trimmed of whitespace."""
        with patch.dict("os.environ", {"OUTPUT_FORMATS": " csv , excel , json "}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            # Verify no whitespace in formats
            for fmt in config.output_formats:
                self.assertEqual(fmt, fmt.strip())


class TestOutputFormatIntegration(unittest.TestCase):
    """Test output format integration with processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create input and output directories
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_processor_with_multiple_formats(self):
        """Test processor writes all configured formats."""
        with patch.dict(
            "os.environ",
            {
                "INPUT_DIR": str(self.input_dir),
                "OUTPUT_DIR": str(self.output_dir),
                "OUTPUT_FORMATS": "csv,json,excel",
            },
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)

            # Verify output_strategies were set correctly
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("json", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)

            # Verify correct strategy types
            self.assertIsInstance(processor.output_strategies["csv"], CSVOutputStrategy)
            self.assertIsInstance(
                processor.output_strategies["json"], JSONOutputStrategy
            )
            self.assertIsInstance(
                processor.output_strategies["excel"], ExcelOutputStrategy
            )

    def test_factory_creates_correct_strategies(self):
        """Test factory injects correct strategies based on config."""
        with patch.dict(
            "os.environ",
            {
                "INPUT_DIR": str(self.input_dir),
                "OUTPUT_DIR": str(self.output_dir),
                "OUTPUT_FORMATS": "csv,excel",
            },
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)

            # Should have CSV and Excel, but not JSON
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 2)

    def test_processor_default_strategies(self):
        """Test processor uses default strategies when none provided."""
        with patch.dict(
            "os.environ",
            {
                "INPUT_DIR": str(self.input_dir),
                "OUTPUT_DIR": str(self.output_dir),
            },
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)

            # Default should be CSV only (FREE tier)
            self.assertIn("csv", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 1)

    def test_custom_strategies_injection(self):
        """Test factory accepts custom strategy instances."""
        with patch.dict(
            "os.environ",
            {
                "INPUT_DIR": str(self.input_dir),
                "OUTPUT_DIR": str(self.output_dir),
            },
        ):
            config = AppConfig.from_env()

            # Create custom strategies
            custom_strategies = {
                "csv": CSVOutputStrategy(),
                "excel": ExcelOutputStrategy(),
            }

            processor = ProcessorFactory.create_from_config(
                config, output_strategies=custom_strategies
            )

            # Verify custom strategies were used
            self.assertEqual(len(processor.output_strategies), 2)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)


class TestStrategyBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility of output strategies."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_default_behavior_unchanged(self):
        """Test that default behavior produces CSV and JSON."""
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)

            # Should have CSV only by default (FREE tier)
            self.assertEqual(len(processor.output_strategies), 1)
            self.assertIn("csv", processor.output_strategies)

    def test_processor_direct_instantiation_still_works(self):
        """Test processor can still be instantiated without factory."""
        from bankstatements_core.config.processor_config import (
            ExtractionConfig,
            ProcessorConfig,
        )
        from bankstatements_core.pdf_table_extractor import get_columns_config
        from bankstatements_core.processor import BankStatementProcessor

        columns = get_columns_config()
        config = ProcessorConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            extraction=ExtractionConfig(columns=columns),
        )
        processor = BankStatementProcessor(config=config)

        # Should have default strategies
        self.assertIn("csv", processor.output_strategies)
        self.assertIn("json", processor.output_strategies)


if __name__ == "__main__":
    unittest.main()
