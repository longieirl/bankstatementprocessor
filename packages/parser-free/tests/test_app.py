from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.patterns.repositories import reset_config_singleton
from bankstatements_free.app import AppConfig, ConfigurationError, main


class TestApp(unittest.TestCase):
    def tearDown(self):
        """Reset configuration singleton after each test for isolation."""
        reset_config_singleton()

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_function_integration(self, mock_factory):
        """Test the main function integration flow"""
        # Mock processor instance
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor

        # Mock processor.run() return value
        mock_summary = {
            "pdf_count": 2,
            "pages_read": 4,
            "transactions": 15,
            "duplicates": 3,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "duplicates_path": "/app/output/duplicates.json",
            "monthly_summary_path": "/app/output/monthly_summary.json",
        }
        mock_processor.run.return_value = mock_summary

        # Call main function
        with patch("bankstatements_core.utils.logger") as mock_logger:
            main([])

        # Verify factory was called with config
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        config = call_args[0][0]  # First positional argument is the config

        # With PROJECT_ROOT support, paths resolve relative to CWD
        # Check that paths end with expected directory names
        self.assertTrue(str(config.input_dir).endswith("input"))
        self.assertTrue(str(config.output_dir).endswith("output"))
        self.assertEqual(config.table_top_y, 300)
        self.assertEqual(config.table_bottom_y, 720)
        self.assertFalse(config.enable_dynamic_boundary)
        self.assertTrue(config.sort_by_date)
        self.assertEqual(config.totals_columns, ["debit", "credit"])
        self.assertTrue(
            config.generate_monthly_summary
        )  # Available for both FREE and PAID tiers

        # Verify processor.run() was called
        mock_processor.run.assert_called_once()

        # Verify summary logging
        mock_logger.info.assert_any_call("========== SUMMARY ==========")
        mock_logger.info.assert_any_call("PDFs read: %d", 2)
        mock_logger.info.assert_any_call("PDFs extracted: %d", 2)
        mock_logger.info.assert_any_call("Pages read: %d", 4)
        mock_logger.info.assert_any_call("Unique transactions: %d", 15)
        mock_logger.info.assert_any_call("Duplicate transactions: %d", 3)
        mock_logger.info.assert_any_call(
            "Monthly summary output: %s", "/app/output/monthly_summary.json"
        )

    @patch.dict("os.environ", {"ENABLE_DYNAMIC_BOUNDARY": "true"})
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_function_with_dynamic_boundary_enabled(self, mock_factory):
        """Test the main function with dynamic boundary detection enabled via env var"""
        # Mock processor instance
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.return_value = {
            "pdf_count": 1,
            "pages_read": 2,
            "transactions": 10,
            "duplicates": 0,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "duplicates_path": "/app/output/duplicates.json",
        }

        # Call main function - patch config logger since log_configuration is in config module now
        with (
            patch("bankstatements_core.config.app_config.logger") as mock_config_logger,
            patch("bankstatements_free.app.logger"),
        ):
            main([])

        # Verify factory was called with config with dynamic boundary enabled
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        config = call_args[0][0]

        # With PROJECT_ROOT support, paths resolve relative to CWD
        # Check that paths end with expected directory names
        self.assertTrue(str(config.input_dir).endswith("input"))
        self.assertTrue(str(config.output_dir).endswith("output"))
        self.assertTrue(config.enable_dynamic_boundary)  # Should be True from env var
        self.assertTrue(config.sort_by_date)
        self.assertEqual(config.totals_columns, ["debit", "credit"])
        self.assertTrue(config.generate_monthly_summary)  # Available to FREE tier

        # Verify logging includes dynamic boundary status (from config module logger)
        mock_config_logger.info.assert_any_call(
            "Dynamic boundary detection: %s", "ENABLED"
        )
        # Verify logging includes chronological sorting status (default enabled)
        mock_config_logger.info.assert_any_call(
            "Chronological date sorting: %s", "ENABLED"
        )

    @patch.dict("os.environ", {"TABLE_TOP_Y": "250", "TABLE_BOTTOM_Y": "750"})
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_function_with_custom_table_bounds(self, mock_factory):
        """Test the main function with custom table boundaries from env vars"""
        # Mock processor instance
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.return_value = {
            "pdf_count": 1,
            "pages_read": 2,
            "transactions": 10,
            "duplicates": 0,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "duplicates_path": "/app/output/duplicates.json",
        }

        # Call main function - patch config logger since log_configuration is in config module now
        with (
            patch("bankstatements_core.config.app_config.logger") as mock_config_logger,
            patch("bankstatements_free.app.logger"),
        ):
            main([])

        # Verify factory was called with custom boundaries
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        config = call_args[0][0]

        # With PROJECT_ROOT support, paths resolve relative to CWD
        # Check that paths end with expected directory names
        self.assertTrue(str(config.input_dir).endswith("input"))
        self.assertTrue(str(config.output_dir).endswith("output"))
        self.assertEqual(config.table_top_y, 250)  # Custom value
        self.assertEqual(config.table_bottom_y, 750)  # Custom value
        self.assertFalse(config.enable_dynamic_boundary)
        self.assertTrue(config.sort_by_date)
        self.assertEqual(config.totals_columns, ["debit", "credit"])
        self.assertTrue(config.generate_monthly_summary)  # Available to FREE tier

        # Verify logging of custom boundaries (from AppConfig.log_configuration in config module)
        mock_config_logger.info.assert_any_call("Table bounds: Y=%d to %d", 250, 750)

    @patch.dict("os.environ", {"SORT_BY_DATE": "false"})
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_function_with_sorting_disabled(self, mock_factory):
        """Test the main function with chronological sorting disabled via env var"""
        # Mock processor instance
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.return_value = {
            "pdf_count": 1,
            "pages_read": 2,
            "transactions": 10,
            "duplicates": 0,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "duplicates_path": "/app/output/duplicates.json",
        }

        # Call main function - patch config logger since log_configuration is in config module now
        with (
            patch("bankstatements_core.config.app_config.logger") as mock_config_logger,
            patch("bankstatements_free.app.logger"),
        ):
            main([])

        # Verify factory was called with sorting disabled
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        config = call_args[0][0]

        # With PROJECT_ROOT support, paths resolve relative to CWD
        # Check that paths end with expected directory names
        self.assertTrue(str(config.input_dir).endswith("input"))
        self.assertTrue(str(config.output_dir).endswith("output"))
        self.assertFalse(config.enable_dynamic_boundary)
        self.assertFalse(config.sort_by_date)  # Should be False from env var
        self.assertEqual(config.totals_columns, ["debit", "credit"])
        self.assertTrue(config.generate_monthly_summary)  # Available to FREE tier

        # Verify logging includes chronological sorting status (from config module logger)
        mock_config_logger.info.assert_any_call(
            "Chronological date sorting: %s", "DISABLED"
        )

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_output_directory_creation(self, mock_factory):
        """Test that output directory is created if it doesn't exist"""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"

            # Mock processor
            mock_processor = MagicMock()
            mock_processor.run.return_value = {
                "pdf_count": 0,
                "pages_read": 0,
                "transactions": 0,
                "duplicates": 0,
                "csv_path": "",
                "json_path": "",
                "duplicates_path": "",
            }
            mock_factory.return_value = mock_processor

            # Use environment variable to set output directory
            with patch.dict("os.environ", {"OUTPUT_DIR": str(output_dir)}):
                main([])

            # Verify directory was created
            self.assertTrue(output_dir.exists())

    @patch.dict(
        "os.environ",
        {"TOTALS_COLUMNS": "debit,credit,balance", "GENERATE_MONTHLY_SUMMARY": "false"},
    )
    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_main_function_with_new_features_configured(self, mock_factory):
        """Test the main function with new totals and monthly summary features configured"""
        # Mock processor instance
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor
        mock_processor.run.return_value = {
            "pdf_count": 1,
            "pages_read": 2,
            "transactions": 10,
            "duplicates": 0,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "duplicates_path": "/app/output/duplicates.json",
            # Note: no monthly_summary_path since it's disabled
        }

        # Call main function - patch config logger since log_configuration is in config module now
        with (
            patch("bankstatements_core.config.app_config.logger") as mock_config_logger,
            patch("bankstatements_free.app.logger"),
        ):
            main([])

        # Verify factory was called with custom configuration
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args
        config = call_args[0][0]

        # With PROJECT_ROOT support, paths resolve relative to CWD
        # Check that paths end with expected directory names
        self.assertTrue(str(config.input_dir).endswith("input"))
        self.assertTrue(str(config.output_dir).endswith("output"))
        self.assertFalse(config.enable_dynamic_boundary)
        self.assertTrue(config.sort_by_date)
        self.assertEqual(
            config.totals_columns, ["debit", "credit", "balance"]
        )  # Custom from env var
        self.assertFalse(config.generate_monthly_summary)  # Disabled from env var

        # Verify logging includes new feature status (from config module logger)
        mock_config_logger.info.assert_any_call(
            "Column totals: %s", "debit, credit, balance"
        )
        mock_config_logger.info.assert_any_call(
            "Monthly summary generation: %s", "DISABLED"
        )


class TestAppConfig(unittest.TestCase):
    """Test cases for AppConfig validation"""

    def test_appconfig_from_env_defaults(self):
        """Test AppConfig loads default values correctly"""
        with patch.dict("os.environ", {}, clear=False):
            config = AppConfig.from_env()

            # With PROJECT_ROOT support, paths resolve to absolute paths
            # Check that paths end with expected directory names
            self.assertTrue(str(config.input_dir).endswith("input"))
            self.assertTrue(str(config.output_dir).endswith("output"))
            self.assertEqual(config.table_top_y, 300)
            self.assertEqual(config.table_bottom_y, 720)
            self.assertFalse(config.enable_dynamic_boundary)
            self.assertTrue(config.sort_by_date)
            self.assertEqual(config.totals_columns, ["debit", "credit"])
            self.assertTrue(config.generate_monthly_summary)  # Available to FREE tier

    def test_appconfig_from_env_custom_values(self):
        """Test AppConfig loads custom environment variables correctly"""
        with patch.dict(
            "os.environ",
            {
                "INPUT_DIR": "/custom/input",
                "OUTPUT_DIR": "/custom/output",
                "TABLE_TOP_Y": "250",
                "TABLE_BOTTOM_Y": "750",
                "ENABLE_DYNAMIC_BOUNDARY": "true",
                "SORT_BY_DATE": "false",
                "TOTALS_COLUMNS": "debit,credit,balance",
                "GENERATE_MONTHLY_SUMMARY": "false",
            },
        ):
            config = AppConfig.from_env()

            self.assertEqual(config.input_dir, Path("/custom/input"))
            self.assertEqual(config.output_dir, Path("/custom/output"))
            self.assertEqual(config.table_top_y, 250)
            self.assertEqual(config.table_bottom_y, 750)
            self.assertTrue(config.enable_dynamic_boundary)
            self.assertFalse(config.sort_by_date)
            self.assertEqual(config.totals_columns, ["debit", "credit", "balance"])
            self.assertFalse(config.generate_monthly_summary)

    def test_appconfig_validation_negative_table_top_y(self):
        """Test AppConfig rejects negative TABLE_TOP_Y"""
        with patch.dict("os.environ", {"TABLE_TOP_Y": "-10"}):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()

            self.assertIn("TABLE_TOP_Y must be non-negative", str(cm.exception))

    def test_appconfig_validation_negative_table_bottom_y(self):
        """Test AppConfig rejects negative TABLE_BOTTOM_Y"""
        with patch.dict("os.environ", {"TABLE_BOTTOM_Y": "-10"}):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()

            self.assertIn("TABLE_BOTTOM_Y must be non-negative", str(cm.exception))

    def test_appconfig_validation_top_greater_than_bottom(self):
        """Test AppConfig rejects TABLE_TOP_Y >= TABLE_BOTTOM_Y"""
        with patch.dict("os.environ", {"TABLE_TOP_Y": "700", "TABLE_BOTTOM_Y": "600"}):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()

            self.assertIn(
                "TABLE_TOP_Y (700) must be less than TABLE_BOTTOM_Y (600)",
                str(cm.exception),
            )

    def test_appconfig_validation_invalid_table_top_y_format(self):
        """Test AppConfig rejects non-integer TABLE_TOP_Y"""
        with patch.dict("os.environ", {"TABLE_TOP_Y": "invalid"}):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()

            self.assertIn("TABLE_TOP_Y must be an integer", str(cm.exception))

    def test_appconfig_validation_invalid_table_bottom_y_format(self):
        """Test AppConfig rejects non-integer TABLE_BOTTOM_Y"""
        with patch.dict("os.environ", {"TABLE_BOTTOM_Y": "invalid"}):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()

            self.assertIn("TABLE_BOTTOM_Y must be an integer", str(cm.exception))

    def test_appconfig_log_configuration(self):
        """Test AppConfig logs configuration correctly"""
        config = AppConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            table_top_y=300,
            table_bottom_y=720,
            enable_dynamic_boundary=False,
            sort_by_date=True,
            totals_columns=["debit", "credit"],
            generate_monthly_summary=True,
        )

        with patch("bankstatements_core.config.app_config.logger") as mock_logger:
            config.log_configuration()

            mock_logger.info.assert_any_call("========== CONFIGURATION ==========")
            mock_logger.info.assert_any_call("Input directory: %s", Path("input"))
            mock_logger.info.assert_any_call("Output directory: %s", Path("output"))
            mock_logger.info.assert_any_call("Table bounds: Y=%d to %d", 300, 720)
            mock_logger.info.assert_any_call(
                "Dynamic boundary detection: %s", "DISABLED"
            )
            mock_logger.info.assert_any_call(
                "Chronological date sorting: %s", "ENABLED"
            )
            mock_logger.info.assert_any_call("Column totals: %s", "debit, credit")
            mock_logger.info.assert_any_call(
                "Monthly summary generation: %s", "ENABLED"
            )
            mock_logger.info.assert_any_call("===================================")

    def test_appconfig_validation_large_table_bottom_y_warning(self):
        """Test AppConfig logs warning for unusually large TABLE_BOTTOM_Y"""
        with (
            patch("bankstatements_core.config.app_config.logger") as mock_logger,
            patch.dict("os.environ", {"TABLE_BOTTOM_Y": "1500"}),
        ):
            AppConfig.from_env()
            mock_logger.warning.assert_called_once()
            self.assertIn("unusually large", str(mock_logger.warning.call_args))

    def test_appconfig_invalid_totals_columns_format(self):
        """Test AppConfig rejects invalid TOTALS_COLUMNS format"""
        with (
            patch.dict("os.environ", {"TOTALS_COLUMNS": "debit"}),
            patch(
                "bankstatements_core.config.totals_config.parse_totals_columns",
                side_effect=ValueError("Parse error"),
            ),
        ):
            with self.assertRaises(ConfigurationError) as cm:
                AppConfig.from_env()
            self.assertIn("Invalid TOTALS_COLUMNS", str(cm.exception))

    def test_setup_logging_with_invalid_level(self):
        """Test setup_logging handles invalid LOG_LEVEL"""
        from bankstatements_free.app import setup_logging

        with (
            patch.dict("os.environ", {"LOG_LEVEL": "INVALID"}),
            patch("bankstatements_free.app.logger") as mock_logger,
        ):
            setup_logging()
            mock_logger.warning.assert_called_once()
            self.assertIn("Invalid LOG_LEVEL", str(mock_logger.warning.call_args))

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    def test_main_with_columns_config_error(self, mock_get_columns):
        """Test main handles get_columns_config errors"""
        mock_get_columns.side_effect = ValueError("Column config error")

        exit_code = main([])

        # Column config errors now wrapped in ConfigurationError (exit code 1)
        self.assertEqual(exit_code, 1)

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    def test_main_with_generic_exception(self, mock_get_columns, mock_factory):
        """Test main handles generic exceptions"""
        mock_get_columns.return_value = {}
        mock_factory.side_effect = RuntimeError("Unexpected error")

        exit_code = main([])

        self.assertEqual(exit_code, 4)

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_log_summary_with_csv_only(self, mock_factory):
        """Test log_summary handles missing json_path when OUTPUT_FORMATS=csv"""
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor

        # Summary with only CSV output (no json_path)
        mock_summary = {
            "pdf_count": 11,
            "pages_read": 62,
            "transactions": 1357,
            "duplicates": 0,
            "csv_path": "/app/output/bank_statements.csv",
            "duplicates_path": "/app/output/duplicates.json",
            "monthly_summary_path": "/app/output/monthly_summary.json",
        }
        mock_processor.run.return_value = mock_summary

        # Call main function - should not raise KeyError
        with patch("bankstatements_core.utils.logger") as mock_logger:
            exit_code = main([])

        # Verify no error occurred
        self.assertEqual(exit_code, 0)

        # Verify CSV path was logged
        mock_logger.info.assert_any_call(
            "CSV output: %s", "/app/output/bank_statements.csv"
        )

        # Verify JSON path was NOT logged (since it doesn't exist)
        json_calls = [
            call
            for call in mock_logger.info.call_args_list
            if len(call[0]) > 0 and "JSON output" in str(call[0][0])
        ]
        self.assertEqual(
            len(json_calls),
            0,
            "JSON output should not be logged when json_path is missing",
        )

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_log_summary_with_excel_only(self, mock_factory):
        """Test log_summary handles Excel-only output"""
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor

        # Summary with only Excel output
        mock_summary = {
            "pdf_count": 5,
            "pages_read": 20,
            "transactions": 100,
            "duplicates": 2,
            "excel_path": "/app/output/bank_statements.xlsx",
            "duplicates_path": "/app/output/duplicates.json",
            "monthly_summary_path": "/app/output/monthly_summary.json",
        }
        mock_processor.run.return_value = mock_summary

        # Call main function
        with patch("bankstatements_core.utils.logger") as mock_logger:
            exit_code = main([])

        # Verify no error occurred
        self.assertEqual(exit_code, 0)

        # Verify Excel path was logged
        mock_logger.info.assert_any_call(
            "Excel output: %s", "/app/output/bank_statements.xlsx"
        )

    @patch("bankstatements_core.patterns.factories.ProcessorFactory.create_from_config")
    def test_log_summary_with_all_formats(self, mock_factory):
        """Test log_summary handles all output formats"""
        mock_processor = MagicMock()
        mock_factory.return_value = mock_processor

        # Summary with all formats
        mock_summary = {
            "pdf_count": 3,
            "pages_read": 10,
            "transactions": 50,
            "duplicates": 1,
            "csv_path": "/app/output/bank_statements.csv",
            "json_path": "/app/output/bank_statements.json",
            "excel_path": "/app/output/bank_statements.xlsx",
            "duplicates_path": "/app/output/duplicates.json",
            "monthly_summary_path": "/app/output/monthly_summary.json",
        }
        mock_processor.run.return_value = mock_summary

        # Call main function
        with patch("bankstatements_core.utils.logger") as mock_logger:
            exit_code = main([])

        # Verify no error occurred
        self.assertEqual(exit_code, 0)

        # Verify all paths were logged
        mock_logger.info.assert_any_call(
            "CSV output: %s", "/app/output/bank_statements.csv"
        )
        mock_logger.info.assert_any_call(
            "JSON output: %s", "/app/output/bank_statements.json"
        )
        mock_logger.info.assert_any_call(
            "Excel output: %s", "/app/output/bank_statements.xlsx"
        )


if __name__ == "__main__":
    unittest.main([])
