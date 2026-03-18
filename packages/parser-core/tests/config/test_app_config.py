"""Tests for AppConfig validation and from_env loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError


def _base_config(**kwargs) -> AppConfig:
    """Helper to create a valid AppConfig with overrides."""
    defaults = dict(
        input_dir=Path("/input"),
        output_dir=Path("/output"),
        table_top_y=300,
        table_bottom_y=720,
        enable_dynamic_boundary=False,
        sort_by_date=True,
        totals_columns=["debit", "credit"],
        generate_monthly_summary=True,
        output_formats=["csv"],
    )
    defaults.update(kwargs)
    return AppConfig(**defaults)


class TestAppConfigValidation:
    """Tests for AppConfig field validation."""

    def test_negative_table_top_y_raises(self):
        with pytest.raises(
            ConfigurationError, match="TABLE_TOP_Y must be non-negative"
        ):
            _base_config(table_top_y=-1)

    def test_negative_table_bottom_y_raises(self):
        with pytest.raises(
            ConfigurationError, match="TABLE_BOTTOM_Y must be non-negative"
        ):
            _base_config(table_bottom_y=-1)

    def test_table_top_y_gte_bottom_raises(self):
        with pytest.raises(ConfigurationError, match="must be less than"):
            _base_config(table_top_y=720, table_bottom_y=300)

    def test_table_top_y_equal_bottom_raises(self):
        with pytest.raises(ConfigurationError, match="must be less than"):
            _base_config(table_top_y=300, table_bottom_y=300)

    def test_large_table_bottom_y_logs_warning(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            _base_config(table_top_y=300, table_bottom_y=1001)
        assert any("unusually large" in r.message for r in caplog.records)

    def test_empty_output_formats_raises(self):
        with pytest.raises(ConfigurationError, match="At least one output format"):
            _base_config(output_formats=[])

    def test_invalid_output_format_raises(self):
        with pytest.raises(ConfigurationError, match="Invalid output format"):
            _base_config(output_formats=["pdf"])

    def test_valid_config_creates_without_error(self):
        cfg = _base_config()
        assert cfg.table_top_y == 300
        assert cfg.table_bottom_y == 720


class TestAppConfigFromEnv:
    """Tests for AppConfig.from_env()."""

    def test_from_env_basic(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INPUT_DIR", str(tmp_path / "input"))
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
        cfg = AppConfig.from_env()
        assert cfg.input_dir == tmp_path / "input"
        assert cfg.output_dir == tmp_path / "output"

    def test_from_env_invalid_table_top_y_raises(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INPUT_DIR", str(tmp_path))
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("TABLE_TOP_Y", "not_a_number")
        with pytest.raises(ConfigurationError):
            AppConfig.from_env()

    def test_from_env_generic_exception_wrapped(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INPUT_DIR", str(tmp_path))
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        with patch(
            "bankstatements_core.config.app_config.EnvironmentParser.parse_bool",
            side_effect=RuntimeError("Unexpected"),
        ):
            with pytest.raises(
                ConfigurationError, match="Failed to load configuration"
            ):
                AppConfig.from_env()

    def test_from_env_with_explicit_output_formats(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INPUT_DIR", str(tmp_path))
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("OUTPUT_FORMATS", "csv,json")
        cfg = AppConfig.from_env()
        assert "csv" in cfg.output_formats
        assert "json" in cfg.output_formats


class TestAppConfigLogConfiguration:
    """Tests for AppConfig.log_configuration()."""

    def test_log_configuration_runs(self, caplog):
        import logging

        cfg = _base_config()
        with caplog.at_level(logging.INFO):
            cfg.log_configuration()
        assert any("CONFIGURATION" in r.message for r in caplog.records)
