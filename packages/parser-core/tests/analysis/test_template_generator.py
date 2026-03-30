"""Tests for template generator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from bankstatements_core.analysis.template_generator import TemplateGenerator


class TestTemplateGenerator:
    """Tests for TemplateGenerator class."""

    def test_init_default_base_template(self):
        """Test initialization with default base template path."""
        generator = TemplateGenerator()
        assert generator.base_template_path is not None
        assert generator.base_template_path.name == "default.json"

    def test_init_custom_base_template(self):
        """Test initialization with custom base template path."""
        custom_path = Path("/tmp/custom_template.json")
        generator = TemplateGenerator(base_template_path=custom_path)
        assert generator.base_template_path == custom_path

    def test_generate_template_basic(self):
        """Test generating template with basic inputs."""
        # Create temporary base template
        base_template = {
            "id": "base",
            "name": "Base Template",
            "enabled": True,
            "detection": {"iban_patterns": [], "column_headers": []},
            "extraction": {"table_top_y": 0, "table_bottom_y": 0, "columns": {}},
            "processing": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {
                "Date": (50.0, 100.0),
                "Details": (100.0, 300.0),
                "Amount": (300.0, 400.0),
            }

            template = generator.generate_template(
                columns=columns,
                iban="IE29AIBK93115212345678",
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )

            # Check basic structure
            assert template["id"] == "custom_generated"
            assert template["name"] == "Custom Template - Generated"

            # Check extraction config
            assert template["extraction"]["table_top_y"] == 250.0
            assert template["extraction"]["table_bottom_y"] == 700.0
            assert template["extraction"]["header_check_top_y"] == 240.0  # 250 - 10
            assert template["extraction"]["enable_header_check"] is True

            # Check columns
            assert len(template["extraction"]["columns"]) == 3
            assert template["extraction"]["columns"]["Date"] == [50.0, 100.0]
            assert template["extraction"]["columns"]["Details"] == [100.0, 300.0]
            assert template["extraction"]["columns"]["Amount"] == [300.0, 400.0]

            # Check detection config
            assert template["detection"]["iban_patterns"] == ["^IE\\d{2}.*"]
            assert template["detection"]["column_headers"] == [
                "Date",
                "Details",
                "Amount",
            ]

        finally:
            base_path.unlink()

    def test_generate_template_no_iban(self):
        """Test generating template with no IBAN detected.

        When IBAN is not detected, template should accurately reflect this
        with empty iban_patterns array (not add fake patterns).
        """
        base_template = {
            "id": "base",
            "name": "Base",
            "detection": {},
            "extraction": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,  # No IBAN
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )

            # Should have empty IBAN patterns (accurately reflects no detection)
            assert template["detection"]["iban_patterns"] == []

        finally:
            base_path.unlink()

    def test_generate_template_custom_id_and_name(self):
        """Test generating template with custom ID and name."""
        base_template = {
            "id": "base",
            "name": "Base",
            "detection": {},
            "extraction": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
                template_id="my_bank",
                template_name="My Bank Statement",
            )

            assert template["id"] == "my_bank"
            assert template["name"] == "My Bank Statement"

        finally:
            base_path.unlink()

    def test_generate_template_iban_country_code_extraction(self):
        """Test that IBAN country code is correctly extracted for pattern."""
        base_template = {"id": "base", "detection": {}, "extraction": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            # Test different country codes
            template_ie = generator.generate_template(
                columns=columns,
                iban="IE29AIBK93115212345678",
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )
            assert template_ie["detection"]["iban_patterns"] == ["^IE\\d{2}.*"]

            template_de = generator.generate_template(
                columns=columns,
                iban="DE89370400440532013000",
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )
            assert template_de["detection"]["iban_patterns"] == ["^DE\\d{2}.*"]

        finally:
            base_path.unlink()

    def test_generate_template_header_check_y_calculation(self):
        """Test header_check_top_y calculation."""
        base_template = {"id": "base", "detection": {}, "extraction": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            # Normal case
            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=300.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )
            assert template["extraction"]["header_check_top_y"] == 290.0  # 300 - 10

            # Edge case: table very close to top
            template_edge = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=30.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )
            # Should not go negative
            assert template_edge["extraction"]["header_check_top_y"] >= 0

        finally:
            base_path.unlink()

    def test_generate_template_base_template_not_found(self):
        """Test generation when base template file doesn't exist."""
        non_existent = Path("/tmp/nonexistent_template.json")

        generator = TemplateGenerator(base_template_path=non_existent)

        columns = {"Date": (50.0, 100.0)}

        # Should fall back to minimal template
        template = generator.generate_template(
            columns=columns,
            iban="IE29AIBK93115212345678",
            table_top_y=250.0,
            table_bottom_y=700.0,
            page_height=842.0,
        )

        # Should still produce valid template
        assert "id" in template
        assert "extraction" in template
        assert "detection" in template

    def test_save_template_success(self):
        """Test successfully saving template to file."""
        template = {
            "id": "test",
            "name": "Test Template",
            "extraction": {"columns": {}},
            "detection": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_template.json"

            generator = TemplateGenerator()
            generator.save_template(template, output_path)

            # Verify file was created
            assert output_path.exists()

            # Verify content
            with open(output_path) as f:
                loaded = json.load(f)
                assert loaded["id"] == "test"
                assert loaded["name"] == "Test Template"

    def test_save_template_creates_parent_dir(self):
        """Test that save_template creates parent directories."""
        template = {"id": "test", "name": "Test Template"}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "test.json"

            generator = TemplateGenerator()
            generator.save_template(template, output_path)

            # Verify file was created in nested directory
            assert output_path.exists()
            assert output_path.parent.exists()

    def test_save_template_overwrites_existing(self):
        """Test that save_template overwrites existing file."""
        template1 = {"id": "template1", "name": "First"}
        template2 = {"id": "template2", "name": "Second"}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.json"

            generator = TemplateGenerator()

            # Save first template
            generator.save_template(template1, output_path)
            with open(output_path) as f:
                loaded1 = json.load(f)
                assert loaded1["name"] == "First"

            # Save second template (should overwrite)
            generator.save_template(template2, output_path)
            with open(output_path) as f:
                loaded2 = json.load(f)
                assert loaded2["name"] == "Second"

    def test_save_template_io_error(self):
        """Test save_template raises IOError on write failure."""
        template = {"id": "test"}

        # Try to save to invalid path (e.g., read-only location)
        output_path = Path("/invalid/path/that/does/not/exist/template.json")

        generator = TemplateGenerator()

        with pytest.raises(IOError):
            generator.save_template(template, output_path)

    def test_save_template_type_error(self):
        """Test save_template raises IOError on JSON serialization failure."""
        # Create un-serializable template (e.g., contains a function)
        template = {"id": "test", "func": lambda x: x}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.json"

            generator = TemplateGenerator()

            with pytest.raises(IOError):
                generator.save_template(template, output_path)

    def test_create_minimal_template(self):
        """Test creating minimal template structure."""
        generator = TemplateGenerator()
        minimal = generator._create_minimal_template()

        # Check required fields exist
        assert "id" in minimal
        assert "name" in minimal
        assert "enabled" in minimal
        assert "detection" in minimal
        assert "extraction" in minimal
        assert "processing" in minimal

        # Check nested structures
        assert "iban_patterns" in minimal["detection"]
        assert "column_headers" in minimal["detection"]
        assert "columns" in minimal["extraction"]
        assert "table_top_y" in minimal["extraction"]

    def test_format_template_for_display(self):
        """Test formatting template as pretty JSON."""
        template = {
            "id": "test",
            "name": "Test",
            "extraction": {"columns": {"Date": [50, 100], "Amount": [100, 200]}},
        }

        generator = TemplateGenerator()
        formatted = generator.format_template_for_display(template)

        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["id"] == "test"

        # Should be pretty-printed (has newlines and indentation)
        assert "\n" in formatted
        assert "  " in formatted

    def test_generate_template_without_extraction_key(self):
        """Test generating template when base template lacks extraction key."""
        base_template = {
            "id": "base",
            "name": "Base",
            "detection": {},
            # Missing "extraction" key
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )

            # Should create extraction section
            assert "extraction" in template
            assert template["extraction"]["table_top_y"] == 250

        finally:
            base_path.unlink()

    def test_generate_template_without_detection_key(self):
        """Test generating template when base template lacks detection key."""
        base_template = {
            "id": "base",
            "name": "Base",
            "extraction": {},
            # Missing "detection" key
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban="IE29AIBK93115212345678",
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )

            # Should create detection section
            assert "detection" in template
            assert template["detection"]["iban_patterns"] == ["^IE\\d{2}.*"]

        finally:
            base_path.unlink()

    def test_generate_template_invalid_json(self):
        """Test generating template when base template has invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            # Should fall back to minimal template
            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
            )

            # Should still work with minimal template
            assert "id" in template
            assert "extraction" in template

        finally:
            base_path.unlink()

    def test_detect_date_grouping_with_page(self):
        """Test date grouping detection with pdfplumber page object."""
        from unittest.mock import Mock

        # Create mock page with date column words
        mock_page = Mock()
        mock_page.within_bbox.return_value.extract_words.return_value = [
            {"text": "01/01/23", "top": 100, "x0": 50},
            {"text": "Description", "top": 120, "x0": 50},
            {"text": "More", "top": 140, "x0": 50},
            {"text": "02/01/23", "top": 160, "x0": 50},
        ]

        base_template = {
            "id": "base",
            "detection": {},
            "extraction": {},
            "processing": {
                "supports_multiline": False,
                "date_format": "%d/%m/%Y",
                "currency_symbol": "€",
                "decimal_separator": ".",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0), "Details": (100.0, 300.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=95.0,
                table_bottom_y=200.0,
                page_height=842.0,
                page=mock_page,
            )

            # Date grouping should be detected (50% of rows have dates < 60%)
            assert template["processing"]["supports_multiline"] is True

        finally:
            base_path.unlink()

    def test_detect_date_grouping_creates_processing_section(self):
        """Test that date grouping detection creates processing section if missing."""
        from unittest.mock import Mock

        mock_page = Mock()
        mock_page.within_bbox.return_value.extract_words.return_value = [
            {"text": "01/01/23", "top": 100, "x0": 50},
            {"text": "Description", "top": 120, "x0": 50},
            {"text": "More", "top": 140, "x0": 50},
            {"text": "02/01/23", "top": 160, "x0": 50},
        ]

        # Base template WITHOUT processing section
        base_template = {
            "id": "base",
            "detection": {},
            "extraction": {},
            # No processing section
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0), "Details": (100.0, 300.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=95.0,
                table_bottom_y=200.0,
                page_height=842.0,
                page=mock_page,
            )

            # Processing section should be created with date grouping enabled
            assert "processing" in template
            assert template["processing"]["supports_multiline"] is True
            assert template["processing"]["date_format"] == "%d/%m/%Y"
            assert template["processing"]["currency_symbol"] == ""

        finally:
            base_path.unlink()

    def test_detect_date_grouping_no_date_column(self):
        """Test date grouping detection when no Date column exists."""
        from unittest.mock import Mock

        mock_page = Mock()

        base_template = {
            "id": "base",
            "detection": {},
            "extraction": {},
            "processing": {"supports_multiline": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Details": (100.0, 300.0)}  # No Date column

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
                page=mock_page,
            )

            # Should keep processing section from base template
            assert "processing" in template
            # Should not modify supports_multiline (no Date column)
            assert template["processing"]["supports_multiline"] is False

        finally:
            base_path.unlink()

    def test_detect_date_grouping_no_words(self):
        """Test date grouping detection when no words in date column."""
        from unittest.mock import Mock

        mock_page = Mock()
        mock_page.within_bbox.return_value.extract_words.return_value = []

        base_template = {
            "id": "base",
            "detection": {},
            "extraction": {},
            "processing": {"supports_multiline": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=250.0,
                table_bottom_y=700.0,
                page_height=842.0,
                page=mock_page,
            )

            # Should handle empty words gracefully - no date grouping detected
            assert "processing" in template
            assert template["processing"]["supports_multiline"] is False

        finally:
            base_path.unlink()

    def test_detect_date_grouping_insufficient_rows(self):
        """Test date grouping detection with too few rows."""
        from unittest.mock import Mock

        mock_page = Mock()
        mock_page.within_bbox.return_value.extract_words.return_value = [
            {"text": "01/01/23", "top": 100, "x0": 50},
            {"text": "Text", "top": 120, "x0": 50},
        ]

        base_template = {
            "id": "base",
            "detection": {},
            "extraction": {},
            "processing": {"supports_multiline": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(base_template, f)
            base_path = Path(f.name)

        try:
            generator = TemplateGenerator(base_template_path=base_path)

            columns = {"Date": (50.0, 100.0)}

            template = generator.generate_template(
                columns=columns,
                iban=None,
                table_top_y=95.0,
                table_bottom_y=150.0,
                page_height=842.0,
                page=mock_page,
            )

            # Should not detect grouping with < 3 rows
            assert "processing" in template
            assert template["processing"]["supports_multiline"] is False

        finally:
            base_path.unlink()
