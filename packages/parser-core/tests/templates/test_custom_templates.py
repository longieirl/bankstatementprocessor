"""Tests for custom template loading and merging."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry


@pytest.fixture
def temp_custom_dir(tmp_path):
    """Create temporary custom templates directory."""
    custom_dir = tmp_path / "custom_templates"
    custom_dir.mkdir()
    return custom_dir


@pytest.fixture
def temp_builtin_dir(tmp_path):
    """Create temporary built-in templates directory."""
    builtin_dir = tmp_path / "templates"
    builtin_dir.mkdir()
    return builtin_dir


@pytest.fixture
def sample_custom_template():
    """Sample custom template data."""
    return {
        "id": "custombank",
        "name": "Custom Bank",
        "enabled": True,
        "detection": {
            "iban_patterns": ["IE[0-9]{2}CUST[0-9A-Z]+"],
            "header_keywords": ["Custom Bank"],
            "column_headers": ["Date", "Description", "Amount", "Balance"],
        },
        "extraction": {
            "table_top_y": 200,
            "table_bottom_y": 700,
            "columns": {
                "Date": [20, 80],
                "Details": [80, 250],
                "Debit €": [250, 320],
                "Credit €": [320, 390],
                "Balance €": [390, 460],
            },
        },
        "processing": {
            "supports_multiline": False,
            "date_format": "%d/%m/%Y",
            "currency_symbol": "€",
            "decimal_separator": ".",
        },
    }


@pytest.fixture
def sample_builtin_template():
    """Sample built-in template data."""
    return {
        "id": "default",
        "name": "Default Bank Statement",
        "enabled": True,
        "detection": {
            "iban_patterns": [],
            "column_headers": ["Date", "Details", "Debit", "Credit", "Balance"],
        },
        "extraction": {
            "table_top_y": 300,
            "table_bottom_y": 720,
            "columns": {
                "Date": [26, 78],
                "Details": [78, 255],
                "Debit €": [255, 313],
                "Credit €": [313, 369],
                "Balance €": [369, 434],
            },
        },
        "processing": {
            "supports_multiline": False,
            "date_format": "%d/%m/%Y",
            "currency_symbol": "€",
            "decimal_separator": ".",
        },
    }


class TestCustomTemplateLoading:
    """Tests for loading custom templates."""

    def test_load_from_custom_directory_only(
        self, temp_custom_dir, sample_custom_template
    ):
        """Test loading templates from custom directory only."""
        # Create custom template file
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        # Load templates
        registry = TemplateRegistry.from_directory(temp_custom_dir)

        # Verify custom template loaded
        assert "custombank" in registry.get_template_ids()
        custom_template = registry.get_template("custombank")
        assert custom_template is not None
        assert custom_template.name == "Custom Bank"

    def test_load_from_multiple_directories(
        self,
        temp_custom_dir,
        temp_builtin_dir,
        sample_custom_template,
        sample_builtin_template,
    ):
        """Test loading templates from both custom and built-in directories."""
        # Create custom template
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        # Create built-in template
        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Load from both directories
        registry = TemplateRegistry.from_multiple_directories(
            [temp_custom_dir, temp_builtin_dir]
        )

        # Verify both templates loaded
        assert "custombank" in registry.get_template_ids()
        assert "default" in registry.get_template_ids()
        assert len(registry.get_template_ids()) == 2

    def test_custom_template_overrides_builtin(
        self, temp_custom_dir, temp_builtin_dir, sample_builtin_template
    ):
        """Test that custom template with same ID overrides built-in template."""
        # Create built-in default template
        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Create custom override with same ID but different name (deep copy needed)
        import copy

        custom_override = copy.deepcopy(sample_builtin_template)
        custom_override["name"] = "Custom Default Override"
        custom_override["extraction"]["table_top_y"] = 350  # Different value

        custom_file = temp_custom_dir / "default.json"
        with open(custom_file, "w") as f:
            json.dump(custom_override, f)

        # Load with custom directory first (higher priority)
        registry = TemplateRegistry.from_multiple_directories(
            [temp_custom_dir, temp_builtin_dir]
        )

        # Verify custom version is loaded
        default_template = registry.get_template("default")
        assert default_template is not None
        assert default_template.name == "Custom Default Override"
        assert default_template.extraction.table_top_y == 350  # Custom value

    def test_custom_templates_via_env_var(
        self,
        temp_custom_dir,
        temp_builtin_dir,
        sample_custom_template,
        sample_builtin_template,
    ):
        """Test loading custom templates via CUSTOM_TEMPLATES_DIR env var."""
        # Create templates
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Mock environment variables
        with patch.dict(
            os.environ,
            {
                "CUSTOM_TEMPLATES_DIR": str(temp_custom_dir),
                "BANK_TEMPLATES_DIR": str(temp_builtin_dir),
            },
        ):
            registry = TemplateRegistry.from_default_config()

            # Verify both templates loaded
            assert "custombank" in registry.get_template_ids()
            assert "default" in registry.get_template_ids()

    def test_nonexistent_custom_directory_skipped(
        self, temp_builtin_dir, sample_builtin_template
    ):
        """Test that nonexistent custom directory is gracefully skipped."""
        # Create built-in template
        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Load with nonexistent custom directory
        nonexistent_dir = Path("/nonexistent/custom/templates")
        registry = TemplateRegistry.from_multiple_directories(
            [nonexistent_dir, temp_builtin_dir]
        )

        # Should still load built-in templates
        assert "default" in registry.get_template_ids()
        assert len(registry.get_template_ids()) == 1

    def test_empty_custom_directory_skipped(
        self, temp_custom_dir, temp_builtin_dir, sample_builtin_template
    ):
        """Test that empty custom directory doesn't cause errors."""
        # Create built-in template
        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Custom directory exists but is empty
        registry = TemplateRegistry.from_multiple_directories(
            [temp_custom_dir, temp_builtin_dir]
        )

        # Should still load built-in templates
        assert "default" in registry.get_template_ids()
        assert len(registry.get_template_ids()) == 1

    def test_custom_template_priority_order(
        self,
        temp_custom_dir,
        temp_builtin_dir,
        sample_custom_template,
        sample_builtin_template,
    ):
        """Test that templates are loaded in correct priority order."""
        # Create multiple templates with different priorities
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Load custom first (higher priority)
        registry = TemplateRegistry.from_multiple_directories(
            [temp_custom_dir, temp_builtin_dir]
        )

        # Get all templates
        templates = registry.get_all_templates()

        # Verify custom template exists
        assert any(t.id == "custombank" for t in templates)
        # Verify built-in template exists
        assert any(t.id == "default" for t in templates)

    def test_invalid_custom_template_skipped(
        self, temp_custom_dir, temp_builtin_dir, sample_builtin_template
    ):
        """Test that invalid custom templates are skipped without breaking loading."""
        # Create invalid custom template
        invalid_file = temp_custom_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            json.dump({"invalid": "template"}, f)

        # Create valid built-in template
        builtin_file = temp_builtin_dir / "default.json"
        with open(builtin_file, "w") as f:
            json.dump(sample_builtin_template, f)

        # Should load without error, skipping invalid template
        registry = TemplateRegistry.from_multiple_directories(
            [temp_custom_dir, temp_builtin_dir]
        )

        # Should only have valid template
        assert "default" in registry.get_template_ids()
        assert "invalid" not in registry.get_template_ids()

    def test_custom_template_default_selection(
        self, temp_custom_dir, sample_custom_template
    ):
        """Test that custom template can be selected as default."""
        # Create custom template
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        # Load with custom as default
        with patch.dict(os.environ, {"DEFAULT_TEMPLATE": "custombank"}):
            registry = TemplateRegistry.from_directory(temp_custom_dir)

            # Verify custom template is default
            default = registry.get_default_template()
            assert default.id == "custombank"

    def test_multiple_custom_templates(self, temp_custom_dir, sample_custom_template):
        """Test loading multiple custom templates from same directory."""
        # Create multiple custom templates
        for i in range(3):
            template = sample_custom_template.copy()
            template["id"] = f"custombank{i}"
            template["name"] = f"Custom Bank {i}"

            custom_file = temp_custom_dir / f"custombank{i}.json"
            with open(custom_file, "w") as f:
                json.dump(template, f)

        # Load all custom templates
        registry = TemplateRegistry.from_directory(temp_custom_dir)

        # Verify all templates loaded
        assert len(registry.get_template_ids()) == 3
        for i in range(3):
            assert f"custombank{i}" in registry.get_template_ids()


class TestCustomTemplateDetection:
    """Tests for custom template detection integration."""

    def test_custom_template_detected_by_iban(
        self, temp_custom_dir, sample_custom_template
    ):
        """Test that custom template is detected by IBAN pattern."""
        # Create custom template with specific IBAN pattern
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        registry = TemplateRegistry.from_directory(temp_custom_dir)
        custom_template = registry.get_template("custombank")

        # Verify IBAN pattern is loaded correctly
        assert custom_template is not None
        assert len(custom_template.detection.iban_patterns) > 0
        assert "IE[0-9]{2}CUST[0-9A-Z]+" in custom_template.detection.iban_patterns

    def test_custom_template_extraction_config(
        self, temp_custom_dir, sample_custom_template
    ):
        """Test that custom template extraction config is applied correctly."""
        # Create custom template
        custom_file = temp_custom_dir / "custombank.json"
        with open(custom_file, "w") as f:
            json.dump(sample_custom_template, f)

        registry = TemplateRegistry.from_directory(temp_custom_dir)
        custom_template = registry.get_template("custombank")

        # Verify extraction config
        assert custom_template.extraction.table_top_y == 200
        assert custom_template.extraction.table_bottom_y == 700
        assert "Date" in custom_template.extraction.columns
        assert custom_template.extraction.columns["Date"] == (20, 80)
