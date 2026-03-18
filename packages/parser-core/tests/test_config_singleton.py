"""Tests for configuration singleton pattern."""

from __future__ import annotations

import os

import pytest

from bankstatements_core.config.app_config import AppConfig
from bankstatements_core.patterns.repositories import get_config_singleton, reset_config_singleton


class TestConfigSingleton:
    """Tests for configuration singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test for isolation."""
        reset_config_singleton()

    def test_get_config_singleton_returns_appconfig(self, monkeypatch):
        """Test that get_config_singleton returns AppConfig instance."""
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        config = get_config_singleton()

        assert isinstance(config, AppConfig)

    def test_get_config_singleton_returns_same_instance(self, monkeypatch):
        """Test that subsequent calls return the same instance."""
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        config1 = get_config_singleton()
        config2 = get_config_singleton()

        assert config1 is config2

    def test_reset_config_singleton_clears_instance(self, monkeypatch):
        """Test that reset_config_singleton allows reloading configuration."""
        monkeypatch.setenv("INPUT_DIR", "test_input_1")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_1")

        config1 = get_config_singleton()
        assert str(config1.input_dir).endswith("test_input_1")

        reset_config_singleton()
        monkeypatch.setenv("INPUT_DIR", "test_input_2")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_2")

        config2 = get_config_singleton()
        assert str(config2.input_dir).endswith("test_input_2")

        assert config1 is not config2

    def test_singleton_with_different_env_vars(self, monkeypatch):
        """Test that singleton caches first configuration."""
        monkeypatch.setenv("INPUT_DIR", "test_input_1")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_1")
        monkeypatch.setenv("TABLE_TOP_Y", "100")

        config1 = get_config_singleton()
        assert str(config1.input_dir).endswith("test_input_1")
        assert config1.table_top_y == 100

        # Change environment without resetting singleton
        monkeypatch.setenv("INPUT_DIR", "test_input_2")
        monkeypatch.setenv("TABLE_TOP_Y", "200")

        config2 = get_config_singleton()

        # Should still return the cached first instance
        assert config2 is config1
        assert str(config2.input_dir).endswith("test_input_1")
        assert config2.table_top_y == 100

    def test_singleton_consistency_across_modules(self, monkeypatch):
        """Test that singleton provides consistency across the application."""
        monkeypatch.setenv("INPUT_DIR", "shared_input")
        monkeypatch.setenv("OUTPUT_DIR", "shared_output")
        monkeypatch.setenv("SORT_BY_DATE", "false")

        from bankstatements_core.patterns.repositories import get_config_singleton as get_config_1

        config1 = get_config_1()

        from bankstatements_core.patterns.repositories import get_config_singleton as get_config_2

        config2 = get_config_2()

        assert config1 is config2
        assert config1.sort_by_date == config2.sort_by_date


class TestSingletonPerformance:
    """Test singleton performance benefits."""

    def teardown_method(self):
        """Reset singleton after each test for isolation."""
        reset_config_singleton()

    def test_singleton_avoids_redundant_parsing(self, monkeypatch):
        """Test that singleton prevents redundant environment variable parsing."""
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        configs = [get_config_singleton() for _ in range(100)]

        assert all(c is configs[0] for c in configs)
        assert len({id(c) for c in configs}) == 1
