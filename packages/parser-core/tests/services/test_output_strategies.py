# packages/parser-core/tests/services/test_output_strategies.py
"""Tests for output format strategies — concrete write behaviour."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.patterns.factories import ProcessorFactory
from bankstatements_core.patterns.strategies import (
    CSVOutputStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
)

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


@pytest.mark.skipif(
    not OPENPYXL_AVAILABLE, reason="openpyxl not installed (PAID tier dependency)"
)
class TestExcelOutputStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = ExcelOutputStrategy()
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.transactions = [
            {"Date": "01/01/2024", "Details": "Purchase 1", "Debit": "€100.00", "Credit": ""},
            {"Date": "02/01/2024", "Details": "Purchase 2", "Debit": "€50.00", "Credit": ""},
            {"Date": "03/01/2024", "Details": "Refund", "Debit": "", "Credit": "€25.00"},
        ]
        self.column_names = ["Date", "Details", "Debit", "Credit"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_excel_basic(self):
        file_path = self.temp_path / "test.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names, include_totals=False)
        self.assertTrue(file_path.exists())
        df = pd.read_excel(file_path, sheet_name="Transactions")
        self.assertEqual(len(df), 3)
        self.assertListEqual(list(df.columns), self.column_names)

    def test_write_excel_with_totals(self):
        file_path = self.temp_path / "test_totals.xlsx"
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
        self.assertTrue(file_path.exists())
        df = pd.read_excel(file_path, sheet_name="Transactions")
        # 3 transactions + 1 empty row + 1 totals row = 5
        self.assertEqual(len(df), 5)
        self.assertEqual(df.iloc[0]["Date"], "01/01/2024")
        self.assertEqual(df.iloc[4]["Date"], "TOTAL")

    def test_excel_file_extension(self):
        file_path = self.temp_path / "bank_statements.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.suffix, ".xlsx")

    def test_numeric_columns_written_as_numbers(self):
        file_path = self.temp_path / "test_numeric.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]
        debit_cell = worksheet["C2"]
        self.assertIsInstance(debit_cell.value, (int, float))
        self.assertAlmostEqual(debit_cell.value, 100.0, places=2)
        debit_cell2 = worksheet["C3"]
        self.assertIsInstance(debit_cell2.value, (int, float))
        self.assertAlmostEqual(debit_cell2.value, 50.0, places=2)
        credit_cell = worksheet["D4"]
        self.assertIsInstance(credit_cell.value, (int, float))
        self.assertAlmostEqual(credit_cell.value, 25.0, places=2)
        empty_credit = worksheet["D2"]
        self.assertIsNone(empty_credit.value)
        date_cell = worksheet["A2"]
        self.assertIsInstance(date_cell.value, str)
        workbook.close()

    def test_number_formatting_applied(self):
        file_path = self.temp_path / "test_formatting.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]
        self.assertIn("#,##0", worksheet["C2"].number_format)
        self.assertIn("#,##0", worksheet["D4"].number_format)
        workbook.close()


class TestOutputFormatConfiguration(unittest.TestCase):
    def test_single_format_csv(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["csv"])

    def test_single_format_excel(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "excel"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["excel"])

    def test_multiple_formats(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,excel"}):
            config = AppConfig.from_env()
            self.assertIn("csv", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_all_formats(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,json,excel"}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            self.assertIn("csv", config.output_formats)
            self.assertIn("json", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_invalid_format_raises_error(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,invalid"}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("Invalid output format", str(context.exception))
            self.assertIn("invalid", str(context.exception))

    def test_empty_format_raises_error(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": ""}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("At least one output format", str(context.exception))

    def test_default_formats(self):
        with patch.dict("os.environ", {}, clear=True):
            config = AppConfig.from_env()
            self.assertIn("csv", config.output_formats)
            self.assertEqual(len(config.output_formats), 1)

    def test_formats_with_whitespace(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": " csv , excel , json "}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            for fmt in config.output_formats:
                self.assertEqual(fmt, fmt.strip())


class TestOutputFormatIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_processor_with_multiple_formats(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir), "OUTPUT_FORMATS": "csv,json,excel"},
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("json", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)
            self.assertIsInstance(processor.output_strategies["csv"], CSVOutputStrategy)
            self.assertIsInstance(processor.output_strategies["json"], JSONOutputStrategy)
            self.assertIsInstance(processor.output_strategies["excel"], ExcelOutputStrategy)

    def test_factory_creates_correct_strategies(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir), "OUTPUT_FORMATS": "csv,excel"},
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 2)

    def test_processor_default_strategies(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 1)

    def test_custom_strategies_injection(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
        ):
            config = AppConfig.from_env()
            custom_strategies = {"csv": CSVOutputStrategy(), "excel": ExcelOutputStrategy()}
            processor = ProcessorFactory.create_from_config(config, output_strategies=custom_strategies)
            self.assertEqual(len(processor.output_strategies), 2)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)


class TestStrategyBackwardCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_behavior_unchanged(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertEqual(len(processor.output_strategies), 1)
            self.assertIn("csv", processor.output_strategies)

    def test_processor_direct_instantiation_still_works(self):
        from bankstatements_core.config.processor_config import ExtractionConfig, ProcessorConfig
        from bankstatements_core.pdf_table_extractor import get_columns_config
        from bankstatements_core.processor import BankStatementProcessor

        columns = get_columns_config()
        config = ProcessorConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            extraction=ExtractionConfig(columns=columns),
        )
        processor = BankStatementProcessor(config=config)
        self.assertIn("csv", processor.output_strategies)
        self.assertIn("json", processor.output_strategies)


if __name__ == "__main__":
    unittest.main()
