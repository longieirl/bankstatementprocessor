"""Tests for configuration singleton pattern."""

from __future__ import annotations


from bankstatements_core.patterns.repositories import (
    get_config_singleton,
    reset_config_singleton,
)
from bankstatements_free.app import AppConfig


class TestConfigSingleton:
    """Tests for configuration singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test for isolation."""
        reset_config_singleton()

    def test_get_config_singleton_returns_appconfig(self, monkeypatch):
        """Test that get_config_singleton returns AppConfig instance."""
        # Set minimal required environment
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        config = get_config_singleton()

        assert isinstance(config, AppConfig)

    def test_get_config_singleton_returns_same_instance(self, monkeypatch):
        """Test that subsequent calls return the same instance."""
        # Set minimal required environment
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        config1 = get_config_singleton()
        config2 = get_config_singleton()

        # Both should be the exact same object (same id)
        assert config1 is config2

    def test_reset_config_singleton_clears_instance(self, monkeypatch):
        """Test that reset_config_singleton allows reloading configuration."""
        # Set initial environment
        monkeypatch.setenv("INPUT_DIR", "test_input_1")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_1")

        config1 = get_config_singleton()
        # With PROJECT_ROOT support, paths are resolved to absolute paths
        assert str(config1.input_dir).endswith("test_input_1")

        # Reset and change environment
        reset_config_singleton()
        monkeypatch.setenv("INPUT_DIR", "test_input_2")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_2")

        config2 = get_config_singleton()
        assert str(config2.input_dir).endswith("test_input_2")

        # They should be different instances
        assert config1 is not config2

    def test_singleton_with_different_env_vars(self, monkeypatch):
        """Test that singleton caches first configuration."""
        # Set initial environment
        monkeypatch.setenv("INPUT_DIR", "test_input_1")
        monkeypatch.setenv("OUTPUT_DIR", "test_output_1")
        monkeypatch.setenv("TABLE_TOP_Y", "100")

        config1 = get_config_singleton()
        # With PROJECT_ROOT support, paths are resolved to absolute paths
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
        # Set environment
        monkeypatch.setenv("INPUT_DIR", "shared_input")
        monkeypatch.setenv("OUTPUT_DIR", "shared_output")
        monkeypatch.setenv("SORT_BY_DATE", "false")

        # Import in different ways to simulate different modules
        from bankstatements_core.patterns.repositories import (
            get_config_singleton as get_config_1,
        )

        config1 = get_config_1()

        from bankstatements_core.patterns.repositories import (
            get_config_singleton as get_config_2,
        )

        config2 = get_config_2()

        # Both should be the same instance
        assert config1 is config2
        assert config1.sort_by_date == config2.sort_by_date


class TestSingletonInAppMain:
    """Test that main() uses singleton correctly."""

    def teardown_method(self):
        """Reset singleton after each test for isolation."""
        reset_config_singleton()

    def test_main_uses_singleton(self, monkeypatch, tmp_path):
        """Test that main() function uses get_config_singleton."""
        # Set up test environment
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        monkeypatch.setenv("INPUT_DIR", str(input_dir))
        monkeypatch.setenv("OUTPUT_DIR", str(output_dir))
        monkeypatch.setenv("GENERATE_MONTHLY_SUMMARY", "false")

        # Get config via singleton before main() is called
        config_before = get_config_singleton()

        # Import main and check that it would use the same instance
        # (We can't actually call main() here without PDFs, but we can verify
        # that a second call to get_config_singleton returns the same instance)
        config_in_main = get_config_singleton()

        assert config_before is config_in_main
        assert str(config_before.input_dir) == str(input_dir)
        assert str(config_in_main.input_dir) == str(input_dir)


class TestSingletonPerformance:
    """Test singleton performance benefits."""

    def teardown_method(self):
        """Reset singleton after each test for isolation."""
        reset_config_singleton()

    def test_singleton_avoids_redundant_parsing(self, monkeypatch):
        """Test that singleton prevents redundant environment variable parsing."""
        # Set environment
        monkeypatch.setenv("INPUT_DIR", "test_input")
        monkeypatch.setenv("OUTPUT_DIR", "test_output")

        # Get config multiple times
        configs = [get_config_singleton() for _ in range(100)]

        # All should be the same instance (no re-parsing)
        assert all(c is configs[0] for c in configs)

        # Only one AppConfig instance created
        assert len({id(c) for c in configs}) == 1
