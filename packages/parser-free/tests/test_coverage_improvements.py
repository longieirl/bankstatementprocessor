"""
Additional tests to improve coverage for uncovered error handling paths.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from bankstatements_core.patterns.repositories import reset_config_singleton
from bankstatements_core.processor import calculate_column_totals
from bankstatements_free.app import main


class TestAppErrorHandling(unittest.TestCase):
    """Tests for uncovered error handling paths in app.py"""

    def tearDown(self):
        """Reset configuration singleton after each test for isolation."""
        reset_config_singleton()

    @patch("bankstatements_core.patterns.repositories.get_config_singleton")
    def test_main_configuration_error(self, mock_get_config):
        """Test main handles ConfigurationError"""
        from bankstatements_free.app import ConfigurationError

        mock_get_config.side_effect = ConfigurationError("Invalid configuration")

        exit_code = main([])
        self.assertEqual(exit_code, 1)

    @patch("bankstatements_free.app.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_file_not_found_error(self, mock_factory, mock_get_columns):
        """Test main handles FileNotFoundError"""
        mock_get_columns.return_value = {}
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.side_effect = FileNotFoundError("File not found")

        exit_code = main([])
        self.assertEqual(exit_code, 2)

    @patch("bankstatements_free.app.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_permission_error(self, mock_factory, mock_get_columns):
        """Test main handles PermissionError"""
        mock_get_columns.return_value = {}
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.side_effect = PermissionError("Permission denied")

        exit_code = main([])
        self.assertEqual(exit_code, 3)

    @patch("bankstatements_free.app.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_keyboard_interrupt(self, mock_factory, mock_get_columns):
        """Test main handles KeyboardInterrupt"""
        mock_get_columns.return_value = {}
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.side_effect = KeyboardInterrupt()

        exit_code = main([])
        self.assertEqual(exit_code, 130)

    @patch("bankstatements_core.config.app_config.Path")
    @patch.dict("os.environ", {"INPUT_DIR": "input", "OUTPUT_DIR": "output"})
    def test_appconfig_from_env_generic_exception(self, mock_path):
        """Test AppConfig.from_env handles generic exceptions"""
        from bankstatements_free.app import AppConfig, ConfigurationError

        # Make Path() raise a generic exception
        mock_path.side_effect = RuntimeError("Unexpected error")

        with self.assertRaises(ConfigurationError) as cm:
            AppConfig.from_env()

        self.assertIn("Failed to load configuration", str(cm.exception))


class TestProcessorErrorHandling(unittest.TestCase):
    """Tests for uncovered error handling paths in processor.py"""

    def test_calculate_column_totals_exception_handling(self):
        """Test calculate_column_totals handles exceptions gracefully"""
        # Create a DataFrame with a column that will cause an error
        df = pd.DataFrame({"BadColumn": [object(), object(), object()]})

        # Mock to_float to raise an exception
        with patch(
            "bankstatements_core.processor.to_float",
            side_effect=Exception("Parse error"),
        ):
            result = calculate_column_totals(df, ["BadColumn"])

            # Should return 0.0 for the column that caused an error
            self.assertEqual(result.get("BadColumn"), 0.0)

    def test_calculate_column_totals_with_complex_exception(self):
        """Test calculate_column_totals with DataFrame operation failure"""
        df = pd.DataFrame({"Amount": ["100", "200", "300"]})

        # Mock pandas apply to raise an exception
        with patch.object(pd.Series, "apply", side_effect=ValueError("Apply failed")):
            result = calculate_column_totals(df, ["Amount"])

            # Should handle the error and return 0.0
            self.assertEqual(result.get("Amount"), 0.0)


class TestProcessorHelperFunctions(unittest.TestCase):
    """Tests for processor helper functions to increase coverage"""

    def test_detect_duplicates_same_file_same_transaction(self):
        """Test _detect_duplicates handles same transaction in same file"""
        from bankstatements_core.config.processor_config import (
            ExtractionConfig,
            ProcessorConfig,
        )
        from bankstatements_core.processor import BankStatementProcessor

        config = ProcessorConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            extraction=ExtractionConfig(
                table_top_y=100,
                table_bottom_y=700,
            ),
        )
        processor = BankStatementProcessor(config=config)

        # Same transaction appearing twice in the same file
        all_rows = [
            {
                "Date": "01/12/23",
                "Details": "Test",
                "Debit €": "100",
                "Filename": "file1.pdf",
            },
            {
                "Date": "01/12/23",
                "Details": "Test",
                "Debit €": "100",
                "Filename": "file1.pdf",
            },
        ]

        unique_rows, duplicate_rows = processor._detect_duplicates(all_rows)

        # Both should be kept since they're from the same file
        self.assertEqual(len(unique_rows), 2)
        self.assertEqual(len(duplicate_rows), 0)

    def test_parse_totals_columns_empty_string(self):
        """Test parse_totals_columns with empty string"""
        from bankstatements_core.processor import parse_totals_columns

        result = parse_totals_columns("")
        self.assertEqual(result, [])

    def test_parse_totals_columns_with_spaces(self):
        """Test parse_totals_columns handles spaces correctly"""
        from bankstatements_core.processor import parse_totals_columns

        result = parse_totals_columns("  debit  ,  credit  ,  balance  ")
        self.assertEqual(result, ["debit", "credit", "balance"])

    def test_find_matching_columns_no_matches(self):
        """Test find_matching_columns when no columns match"""
        from bankstatements_core.processor import find_matching_columns

        column_names = ["Date", "Description", "Amount"]
        patterns = ["debit", "credit"]

        result = find_matching_columns(column_names, patterns)
        self.assertEqual(result, [])

    def test_find_matching_columns_case_insensitive(self):
        """Test find_matching_columns is case-insensitive"""
        from bankstatements_core.processor import find_matching_columns

        column_names = ["Date", "DEBIT Amount", "credit_total"]
        patterns = ["debit", "credit"]

        result = find_matching_columns(column_names, patterns)
        self.assertEqual(len(result), 2)
        self.assertIn("DEBIT Amount", result)
        self.assertIn("credit_total", result)

    def test_generate_monthly_summary_with_no_transactions(self):
        """Test generate_monthly_summary with empty transactions"""
        from bankstatements_core.processor import generate_monthly_summary

        result = generate_monthly_summary([], ["Date", "Debit €", "Credit €"])

        self.assertEqual(result["total_months"], 0)
        self.assertEqual(len(result["monthly_data"]), 0)

    def test_generate_monthly_summary_with_invalid_dates(self):
        """Test generate_monthly_summary handles invalid dates"""
        from bankstatements_core.processor import generate_monthly_summary

        transactions = [
            {"Date": "invalid", "Debit €": "100", "Credit €": ""},
            {"Date": "", "Debit €": "", "Credit €": "50"},
        ]

        result = generate_monthly_summary(transactions, ["Date", "Debit €", "Credit €"])

        # Should have Unknown month for invalid dates
        self.assertIn("Unknown", [m["Month"] for m in result["monthly_data"]])


class TestDateParsingHelperCoverage(unittest.TestCase):
    """Additional tests for date parsing helper functions"""

    def test_normalize_two_digit_year_with_1900s(self):
        """Test _normalize_two_digit_year with years in 1900s"""
        from datetime import datetime

        from bankstatements_core.services.date_parser import DateParserService

        _date_parser = DateParserService()
        _normalize_two_digit_year = _date_parser._normalize_two_digit_year

        # Test year that's already in 1900s
        date = datetime(1999, 12, 31)
        result = _normalize_two_digit_year(date, "%d/%m/%y")
        self.assertEqual(result.year, 1999)

    def test_parse_partial_date_with_four_digit_year(self):
        """Test _parse_partial_date with 4-digit year"""
        from bankstatements_core.services.date_parser import DateParserService

        _date_parser = DateParserService()
        _parse_partial_date = _date_parser._parse_partial_date

        result = _parse_partial_date("01/12/2023")
        self.assertIsNotNone(result)
        if result:  # Type narrowing for mypy
            self.assertEqual(result.year, 2023)
            self.assertEqual(result.month, 12)
            self.assertEqual(result.day, 1)

    def test_parse_partial_date_no_separators(self):
        """Test _parse_partial_date without separators returns None"""
        from bankstatements_core.services.date_parser import DateParserService

        _date_parser = DateParserService()
        _parse_partial_date = _date_parser._parse_partial_date

        result = _parse_partial_date("20231201")
        self.assertIsNone(result)

    def test_parse_common_date_formats_iso_format(self):
        """Test _parse_common_date_formats with unsupported ISO format"""
        from bankstatements_core.services.date_parser import DateParserService

        _date_parser = DateParserService()
        _parse_common_date_formats = _date_parser._parse_common_date_formats

        # ISO format is not in our supported formats
        result = _parse_common_date_formats("2023-12-01")
        self.assertIsNone(result)


class TestProcessorStrategySetters(unittest.TestCase):
    """Tests for processor strategy setter methods to improve coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.output_dir = Path(self.temp_dir) / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def test_set_duplicate_strategy(self):
        """Test set_duplicate_strategy setter method."""
        from bankstatements_core.config.processor_config import ProcessorConfig
        from bankstatements_core.processor import BankStatementProcessor

        config = ProcessorConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
        )
        processor = BankStatementProcessor(config=config)

        # Create a mock strategy
        mock_strategy = MagicMock()

        # Set the strategy
        processor.set_duplicate_strategy(mock_strategy)

        # Verify it was set
        self.assertEqual(processor._duplicate_strategy, mock_strategy)


class TestUtilityFunctions(unittest.TestCase):
    """Tests for utility functions to improve coverage."""

    def test_parse_int_env_with_invalid_value(self):
        """Test parse_int_env with non-integer value raises ValueError."""
        from bankstatements_core.utils import parse_int_env

        with patch.dict("os.environ", {"TEST_VAR": "not_an_integer"}):
            with self.assertRaises(ValueError) as context:
                parse_int_env("TEST_VAR", 100)

            self.assertIn("TEST_VAR must be an integer", str(context.exception))

    def test_parse_bool_env_with_false_value(self):
        """Test parse_bool_env returns False for non-'true' values."""
        from bankstatements_core.utils import parse_bool_env

        with patch.dict("os.environ", {"TEST_BOOL": "false"}):
            result = parse_bool_env("TEST_BOOL", True)
            self.assertFalse(result)

    def test_parse_bool_env_with_missing_var(self):
        """Test parse_bool_env with missing environment variable."""
        from bankstatements_core.utils import parse_bool_env

        # Use a variable name that doesn't exist
        result = parse_bool_env("NONEXISTENT_BOOL_VAR", False)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
