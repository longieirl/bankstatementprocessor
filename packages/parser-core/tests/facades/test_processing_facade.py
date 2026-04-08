"""Tests for BankStatementProcessingFacade."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.facades import BankStatementProcessingFacade


class TestBankStatementProcessingFacade:
    """Tests for BankStatementProcessingFacade."""

    def test_initialization_with_config(self):
        """Test facade initialization with provided config."""
        config = MagicMock(spec=AppConfig)
        facade = BankStatementProcessingFacade(
            config, entitlements=Entitlements.paid_tier()
        )

        assert facade.config == config
        assert facade._processor is None

    def test_initialization_without_config(self):
        """Test facade initialization without config."""
        facade = BankStatementProcessingFacade()

        assert facade.config is None
        assert facade._processor is None

    @patch("bankstatements_core.patterns.repositories.get_config_singleton")
    def test_from_environment(self, mock_get_config):
        """Test creating facade from environment variables."""
        mock_config = MagicMock(spec=AppConfig)
        mock_get_config.return_value = mock_config

        facade = BankStatementProcessingFacade.from_environment()

        mock_get_config.assert_called_once()
        assert facade.config == mock_config

    def test_process_all_without_config_raises_error(self):
        """Test that process_all raises error if config is None."""
        facade = BankStatementProcessingFacade()

        with pytest.raises(ConfigurationError, match="Configuration not loaded"):
            facade.process_all()

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_process_all_success(self, mock_factory, mock_get_columns):
        """Test successful processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit", "credit"],
                generate_monthly_summary=True,
                output_formats=["csv", "json"],
            )

            # Use PAID tier entitlements for tests with PAID features
            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock column config
            mock_get_columns.return_value = {"Date": (0, 100)}

            # Mock processor
            mock_processor = MagicMock()
            mock_processor.run.return_value = {
                "pdf_count": 1,
                "transactions": 10,
                "duplicates": 2,
            }
            mock_factory.create_from_config.return_value = mock_processor

            summary = facade.process_all()

            # Verify output directory was created
            assert output_dir.exists()

            # Verify methods were called
            mock_get_columns.assert_called_once()
            mock_factory.create_from_config.assert_called_once_with(
                config, activity_log=ANY, entitlements=ANY
            )
            mock_processor.run.assert_called_once()

            # Verify summary returned
            assert summary["pdf_count"] == 1
            assert summary["transactions"] == 10
            assert summary["duplicates"] == 2

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    def test_process_all_column_config_error(self, mock_get_columns):
        """Test that column config errors are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Simulate column config error
            mock_get_columns.side_effect = ValueError("Column config failed")

            with pytest.raises(ConfigurationError, match="Column configuration error"):
                facade.process_all()

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    @patch("bankstatements_core.utils.log_summary")
    def test_process_with_error_handling_success(
        self, mock_log_summary, mock_factory, mock_get_columns
    ):
        """Test error handling wrapper with successful processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock successful processing
            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.return_value = {"pdf_count": 1}
            mock_factory.create_from_config.return_value = mock_processor

            exit_code = facade.process_with_error_handling()

            assert exit_code == 0

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    def test_process_with_error_handling_config_error(self, mock_get_columns):
        """Test error handling for configuration errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Simulate configuration error
            mock_get_columns.side_effect = ValueError("Config error")

            exit_code = facade.process_with_error_handling()

            assert exit_code == 1  # Configuration error exit code

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_process_with_error_handling_file_not_found(
        self, mock_factory, mock_get_columns
    ):
        """Test error handling for file not found errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock file not found error
            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.side_effect = FileNotFoundError("File not found")
            mock_factory.create_from_config.return_value = mock_processor

            exit_code = facade.process_with_error_handling()

            assert exit_code == 2  # File not found exit code

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_process_with_error_handling_permission_error(
        self, mock_factory, mock_get_columns
    ):
        """Test error handling for permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock permission error
            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.side_effect = PermissionError("Permission denied")
            mock_factory.create_from_config.return_value = mock_processor

            exit_code = facade.process_with_error_handling()

            assert exit_code == 3  # Permission error exit code

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_process_with_error_handling_keyboard_interrupt(
        self, mock_factory, mock_get_columns
    ):
        """Test error handling for keyboard interrupt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock keyboard interrupt
            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.side_effect = KeyboardInterrupt()
            mock_factory.create_from_config.return_value = mock_processor

            exit_code = facade.process_with_error_handling()

            assert exit_code == 130  # SIGINT exit code

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_process_with_error_handling_unexpected_error(
        self, mock_factory, mock_get_columns
    ):
        """Test error handling for unexpected errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(
                input_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "output",
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            # Mock unexpected error
            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.side_effect = RuntimeError("Unexpected error")
            mock_factory.create_from_config.return_value = mock_processor

            exit_code = facade.process_with_error_handling()

            assert exit_code == 4  # Unexpected error exit code

    @patch("bankstatements_core.facades.processing_facade.get_columns_config")
    @patch("bankstatements_core.patterns.factories.ProcessorFactory")
    def test_auto_cleanup_forwards_data_retention_days(
        self, mock_factory, mock_get_columns
    ):
        """DataRetentionService must receive data_retention_days from config, not a hardcoded 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                table_top_y=300,
                table_bottom_y=720,
                enable_dynamic_boundary=False,
                sort_by_date=True,
                totals_columns=["debit"],
                generate_monthly_summary=True,
                output_formats=["csv"],
                auto_cleanup_on_exit=True,
                data_retention_days=30,
            )

            facade = BankStatementProcessingFacade(
                config, entitlements=Entitlements.paid_tier()
            )

            mock_get_columns.return_value = {"Date": (0, 100)}
            mock_processor = MagicMock()
            mock_processor.run.return_value = {"pdf_count": 0}
            mock_factory.create_from_config.return_value = mock_processor

            with patch(
                "bankstatements_core.services.data_retention.DataRetentionService"
            ) as mock_drs:
                mock_drs.return_value.cleanup_all_files.return_value = 0
                facade.process_all()

            mock_drs.assert_called_once_with(30, output_dir)
