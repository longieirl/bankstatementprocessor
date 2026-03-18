"""Tests for template registry."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry


@pytest.fixture
def sample_template_config():
    """Create sample template configuration."""
    return {
        "version": "1.0",
        "templates": {
            "aib": {
                "name": "Allied Irish Banks",
                "enabled": True,
                "detection": {
                    "iban_patterns": ["IE[0-9]{2}AIBK.*"],
                    "filename_patterns": ["Statement*.pdf"],
                    "header_keywords": ["AIB"],
                    "column_headers": ["Date", "Details"],
                },
                "extraction": {
                    "table_top_y": 300,
                    "table_bottom_y": 720,
                    "columns": {
                        "Date": [26, 78],
                        "Details": [78, 255],
                    },
                },
            },
            "revolut": {
                "name": "Revolut",
                "enabled": False,
                "detection": {
                    "iban_patterns": ["IE[0-9]{2}REVO.*"],
                },
                "extraction": {
                    "table_top_y": 504,
                    "table_bottom_y": 810,
                    "columns": {
                        "Date": [42, 120],
                    },
                },
            },
        },
        "default_template": "aib",
    }


@pytest.fixture
def temp_config_file(sample_template_config):
    """Create temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_template_config, f)
        temp_path = Path(f.name)

    yield temp_path

    temp_path.unlink()


class TestTemplateRegistry:
    """Tests for TemplateRegistry."""

    def test_from_json_valid_config(self, temp_config_file):
        """Test loading valid config from JSON."""
        registry = TemplateRegistry.from_json(temp_config_file)

        assert len(registry.get_template_ids()) == 2
        assert "aib" in registry.get_template_ids()
        assert "revolut" in registry.get_template_ids()

    def test_from_json_missing_file(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            TemplateRegistry.from_json(Path("/nonexistent/config.json"))

    def test_from_json_missing_templates_key(self):
        """Test loading config without templates key raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "1.0"}, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Config must contain 'templates' key"):
                TemplateRegistry.from_json(temp_path)
        finally:
            temp_path.unlink()

    def test_from_json_missing_default_template(self):
        """Test loading config without default_template key raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"templates": {}}, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(
                ValueError, match="Config must contain 'default_template' key"
            ):
                TemplateRegistry.from_json(temp_path)
        finally:
            temp_path.unlink()

    def test_get_template_enabled(self, temp_config_file):
        """Test getting enabled template."""
        registry = TemplateRegistry.from_json(temp_config_file)
        template = registry.get_template("aib")

        assert template is not None
        assert template.id == "aib"
        assert template.name == "Allied Irish Banks"

    def test_get_template_disabled(self, temp_config_file):
        """Test getting disabled template returns None."""
        registry = TemplateRegistry.from_json(temp_config_file)
        template = registry.get_template("revolut")

        assert template is None

    def test_get_template_nonexistent(self, temp_config_file):
        """Test getting non-existent template returns None."""
        registry = TemplateRegistry.from_json(temp_config_file)
        template = registry.get_template("nonexistent")

        assert template is None

    def test_get_default_template(self, temp_config_file):
        """Test getting default template."""
        registry = TemplateRegistry.from_json(temp_config_file)
        default = registry.get_default_template()

        assert default.id == "aib"
        assert default.name == "Allied Irish Banks"

    def test_get_all_templates_only_enabled(self, temp_config_file):
        """Test get_all_templates returns only enabled templates."""
        registry = TemplateRegistry.from_json(temp_config_file)
        templates = registry.get_all_templates()

        assert len(templates) == 1
        assert templates[0].id == "aib"

    def test_parse_template_column_coords(self, temp_config_file):
        """Test that column coordinates are parsed as tuples."""
        registry = TemplateRegistry.from_json(temp_config_file)
        template = registry.get_template("aib")

        assert template is not None
        assert isinstance(template.extraction.columns["Date"], tuple)
        assert template.extraction.columns["Date"] == (26, 78)

    def test_invalid_default_template_id(self):
        """Test that invalid default template ID raises error."""
        detection = TemplateDetectionConfig(iban_patterns=["IE.*"])
        extraction = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        )
        template = BankTemplate(
            id="test",
            name="Test",
            enabled=True,
            detection=detection,
            extraction=extraction,
        )

        with pytest.raises(ValueError, match="Default template.*not found"):
            TemplateRegistry(
                templates={"test": template},
                default_template_id="nonexistent",
            )

    def test_from_default_config(self):
        """Test loading from default config file."""
        registry = TemplateRegistry.from_default_config()

        assert registry is not None
        assert len(registry.get_template_ids()) >= 2
        assert registry.get_default_template() is not None

    def test_from_directory_loads_individual_files(self, tmp_path):
        """Test loading templates from directory with individual JSON files."""
        # Create individual template files
        aib_data = {
            "id": "aib",
            "name": "Allied Irish Banks",
            "enabled": True,
            "detection": {
                "iban_patterns": ["IE[0-9]{2}AIBK.*"],
                "header_keywords": ["AIB"],
            },
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        revolut_data = {
            "id": "revolut",
            "name": "Revolut",
            "enabled": True,
            "detection": {
                "iban_patterns": ["IE[0-9]{2}REVO.*"],
            },
            "extraction": {
                "table_top_y": 140,
                "table_bottom_y": 735,
                "columns": {"Date": [42, 120]},
            },
        }

        # Write template files
        (tmp_path / "aib.json").write_text(json.dumps(aib_data))
        (tmp_path / "revolut.json").write_text(json.dumps(revolut_data))

        # Load from directory
        registry = TemplateRegistry.from_directory(tmp_path)

        assert len(registry.get_template_ids()) == 2
        assert "aib" in registry.get_template_ids()
        assert "revolut" in registry.get_template_ids()

        # Verify templates loaded correctly
        aib = registry.get_template("aib")
        assert aib is not None
        assert aib.name == "Allied Irish Banks"

        revolut = registry.get_template("revolut")
        assert revolut is not None
        assert revolut.name == "Revolut"

    def test_from_directory_missing_directory(self):
        """Test loading from non-existent directory raises error."""
        with pytest.raises(FileNotFoundError, match="Templates directory not found"):
            TemplateRegistry.from_directory(Path("/nonexistent/templates"))

    def test_from_directory_no_json_files(self, tmp_path):
        """Test loading from directory with no JSON files raises error."""
        with pytest.raises(ValueError, match="No template files found"):
            TemplateRegistry.from_directory(tmp_path)

    def test_from_directory_invalid_json_skipped(self, tmp_path):
        """Test that invalid JSON files are skipped with warning."""
        # Create one valid and one invalid template
        valid_data = {
            "id": "valid",
            "name": "Valid Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "valid.json").write_text(json.dumps(valid_data))
        (tmp_path / "invalid.json").write_text("{ invalid json }")

        # Should load successfully, skipping invalid file
        registry = TemplateRegistry.from_directory(tmp_path)

        assert len(registry.get_template_ids()) == 1
        assert "valid" in registry.get_template_ids()

    def test_from_directory_sets_default_to_first_enabled(self, tmp_path):
        """Test that first enabled template becomes default."""
        bank1_data = {
            "id": "bank1",
            "name": "Bank 1",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        bank2_data = {
            "id": "bank2",
            "name": "Bank 2",
            "enabled": True,
            "detection": {"iban_patterns": ["GB.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "bank1.json").write_text(json.dumps(bank1_data))
        (tmp_path / "bank2.json").write_text(json.dumps(bank2_data))

        registry = TemplateRegistry.from_directory(tmp_path)

        # Default should be one of the enabled templates
        default = registry.get_default()
        assert default.id in ["bank1", "bank2"]
        assert default.enabled is True

    def test_from_directory_env_var_default_template(self, tmp_path, monkeypatch):
        """Test DEFAULT_TEMPLATE environment variable sets default."""
        bank1_data = {
            "id": "bank1",
            "name": "Bank 1",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        bank2_data = {
            "id": "bank2",
            "name": "Bank 2",
            "enabled": True,
            "detection": {"iban_patterns": ["GB.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "bank1.json").write_text(json.dumps(bank1_data))
        (tmp_path / "bank2.json").write_text(json.dumps(bank2_data))

        # Set DEFAULT_TEMPLATE env var
        monkeypatch.setenv("DEFAULT_TEMPLATE", "bank2")

        registry = TemplateRegistry.from_directory(tmp_path)

        # Default should be bank2 as specified
        default = registry.get_default()
        assert default.id == "bank2"

    def test_from_directory_invalid_default_template_fallback(
        self, tmp_path, monkeypatch
    ):
        """Test fallback when DEFAULT_TEMPLATE is invalid."""
        bank1_data = {
            "id": "bank1",
            "name": "Bank 1",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "bank1.json").write_text(json.dumps(bank1_data))

        # Set invalid DEFAULT_TEMPLATE env var
        monkeypatch.setenv("DEFAULT_TEMPLATE", "nonexistent")

        registry = TemplateRegistry.from_directory(tmp_path)

        # Should fall back to first enabled template
        default = registry.get_default()
        assert default.id == "bank1"

    def test_load_single_template_new_format(self, tmp_path):
        """Test loading single template with new format (id at root)."""
        template_data = {
            "id": "mybank",
            "name": "My Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        template_file = tmp_path / "mybank.json"
        template_file.write_text(json.dumps(template_data))

        template = TemplateRegistry._load_single_template(template_file)

        assert template is not None
        assert template.id == "mybank"
        assert template.name == "My Bank"

    def test_load_single_template_legacy_format(self, tmp_path):
        """Test loading single template with legacy format (templates dict)."""
        template_data = {
            "templates": {
                "mybank": {
                    "name": "My Bank",
                    "enabled": True,
                    "detection": {"iban_patterns": ["IE.*"]},
                    "extraction": {
                        "table_top_y": 300,
                        "table_bottom_y": 720,
                        "columns": {"Date": [26, 78]},
                    },
                }
            }
        }

        template_file = tmp_path / "mybank.json"
        template_file.write_text(json.dumps(template_data))

        template = TemplateRegistry._load_single_template(template_file)

        assert template is not None
        assert template.id == "mybank"
        assert template.name == "My Bank"

    def test_list_enabled_returns_enabled_only(self, tmp_path):
        """Test list_enabled returns only enabled templates."""
        enabled_data = {
            "id": "enabled",
            "name": "Enabled Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        disabled_data = {
            "id": "disabled",
            "name": "Disabled Bank",
            "enabled": False,
            "detection": {"iban_patterns": ["GB.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "enabled.json").write_text(json.dumps(enabled_data))
        (tmp_path / "disabled.json").write_text(json.dumps(disabled_data))

        registry = TemplateRegistry.from_directory(tmp_path)

        enabled_templates = registry.list_enabled()
        assert len(enabled_templates) == 1
        assert enabled_templates[0].id == "enabled"

    def test_list_all_returns_all_templates(self, tmp_path):
        """Test list_all returns all templates regardless of enabled status."""
        enabled_data = {
            "id": "enabled",
            "name": "Enabled Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        disabled_data = {
            "id": "disabled",
            "name": "Disabled Bank",
            "enabled": False,
            "detection": {"iban_patterns": ["GB.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "enabled.json").write_text(json.dumps(enabled_data))
        (tmp_path / "disabled.json").write_text(json.dumps(disabled_data))

        registry = TemplateRegistry.from_directory(tmp_path)

        all_templates = registry.list_all()
        assert len(all_templates) == 2
        assert {t.id for t in all_templates} == {"enabled", "disabled"}

    def test_from_default_config_uses_env_var(self, tmp_path, monkeypatch):
        """Test from_default_config uses BANK_TEMPLATES_DIR env var."""
        template_data = {
            "id": "custom",
            "name": "Custom Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "custom.json").write_text(json.dumps(template_data))

        # Set BANK_TEMPLATES_DIR env var
        monkeypatch.setenv("BANK_TEMPLATES_DIR", str(tmp_path))

        registry = TemplateRegistry.from_default_config()

        assert "custom" in registry.get_template_ids()
        custom = registry.get_template("custom")
        assert custom is not None
        assert custom.name == "Custom Bank"

    def test_filename_patterns_defaults_to_all_pdfs(self, tmp_path):
        """Test that omitting filename_patterns defaults to *.pdf."""
        template_data = {
            "id": "testbank",
            "name": "Test Bank",
            "enabled": True,
            "detection": {
                "iban_patterns": ["IE[0-9]{2}TEST.*"],
                # Note: filename_patterns omitted
            },
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "testbank.json").write_text(json.dumps(template_data))

        registry = TemplateRegistry.from_directory(tmp_path)
        testbank = registry.get_template("testbank")

        assert testbank is not None
        # Should have empty filename_patterns list in the config
        assert testbank.detection.filename_patterns == []
        # But get_filename_patterns() should return default ["*.pdf"]
        assert testbank.detection.get_filename_patterns() == ["*.pdf"]

    def test_parse_template_with_per_page_overrides(self, tmp_path):
        """Test parsing template with per-page boundary overrides."""
        template_data = {
            "id": "revolut",
            "name": "Revolut Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE[0-9]{2}REVO.*"]},
            "extraction": {
                "table_top_y": 140,
                "table_bottom_y": 735,
                "columns": {"Date": [42, 120]},
                "per_page_overrides": {
                    "1": {"table_top_y": 490, "header_check_top_y": 450},
                    "3": {"table_bottom_y": 800},
                },
            },
        }

        (tmp_path / "revolut.json").write_text(json.dumps(template_data))

        registry = TemplateRegistry.from_directory(tmp_path)
        revolut = registry.get_template("revolut")

        assert revolut is not None
        assert revolut.extraction.per_page_overrides is not None
        assert len(revolut.extraction.per_page_overrides) == 2

        # Check page 1 overrides
        assert 1 in revolut.extraction.per_page_overrides
        page1_override = revolut.extraction.per_page_overrides[1]
        assert page1_override.table_top_y == 490
        assert page1_override.header_check_top_y == 450
        assert page1_override.table_bottom_y is None

        # Check page 3 overrides
        assert 3 in revolut.extraction.per_page_overrides
        page3_override = revolut.extraction.per_page_overrides[3]
        assert page3_override.table_bottom_y == 800
        assert page3_override.table_top_y is None

    def test_parse_template_without_per_page_overrides(self, tmp_path):
        """Test parsing template without per-page overrides."""
        template_data = {
            "id": "standard",
            "name": "Standard Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 300,
                "table_bottom_y": 720,
                "columns": {"Date": [26, 78]},
            },
        }

        (tmp_path / "standard.json").write_text(json.dumps(template_data))

        registry = TemplateRegistry.from_directory(tmp_path)
        standard = registry.get_template("standard")

        assert standard is not None
        assert standard.extraction.per_page_overrides == {}

    def test_per_page_overrides_methods_work_correctly(self, tmp_path):
        """Test that per-page override accessor methods work correctly."""
        template_data = {
            "id": "test",
            "name": "Test Bank",
            "enabled": True,
            "detection": {"iban_patterns": ["IE.*"]},
            "extraction": {
                "table_top_y": 140,
                "table_bottom_y": 735,
                "columns": {"Date": [26, 78]},
                "per_page_overrides": {"1": {"table_top_y": 490}},
            },
        }

        (tmp_path / "test.json").write_text(json.dumps(template_data))

        registry = TemplateRegistry.from_directory(tmp_path)
        test_template = registry.get_template("test")

        assert test_template is not None

        # Page 1 should use override
        assert test_template.extraction.get_table_top_y(1) == 490
        assert test_template.extraction.get_table_bottom_y(1) == 735  # Default

        # Page 2 should use defaults
        assert test_template.extraction.get_table_top_y(2) == 140
        assert test_template.extraction.get_table_bottom_y(2) == 735
