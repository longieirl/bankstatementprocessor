"""Tests for template data models."""

from __future__ import annotations

import pytest

from bankstatements_core.templates.template_model import (
    BankTemplate,
    PerPageBoundaries,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
    TemplateProcessingConfig,
)


class TestPerPageBoundaries:
    """Tests for PerPageBoundaries dataclass."""

    def test_create_empty_boundaries(self):
        """Test creating empty per-page boundaries."""
        boundaries = PerPageBoundaries()

        assert boundaries.table_top_y is None
        assert boundaries.table_bottom_y is None
        assert boundaries.header_check_top_y is None

    def test_create_with_table_top_y_only(self):
        """Test creating boundaries with only table_top_y."""
        boundaries = PerPageBoundaries(table_top_y=490)

        assert boundaries.table_top_y == 490
        assert boundaries.table_bottom_y is None
        assert boundaries.header_check_top_y is None

    def test_create_with_all_boundaries(self):
        """Test creating boundaries with all fields."""
        boundaries = PerPageBoundaries(
            table_top_y=490, table_bottom_y=735, header_check_top_y=450
        )

        assert boundaries.table_top_y == 490
        assert boundaries.table_bottom_y == 735
        assert boundaries.header_check_top_y == 450


class TestTemplateExtractionConfig:
    """Tests for TemplateExtractionConfig."""

    def test_valid_config(self):
        """Test creating valid extraction config."""
        config = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={
                "Date": (26, 78),
                "Details": (78, 255),
            },
        )

        assert config.table_top_y == 300
        assert config.table_bottom_y == 720
        assert len(config.columns) == 2

    def test_invalid_y_bounds(self):
        """Test that invalid Y bounds raise ValueError."""
        with pytest.raises(
            ValueError, match="table_top_y.*must be less than.*table_bottom_y"
        ):
            TemplateExtractionConfig(
                table_top_y=720,
                table_bottom_y=300,
                columns={"Date": (26, 78)},
            )

    def test_equal_y_bounds(self):
        """Test that equal Y bounds raise ValueError."""
        with pytest.raises(
            ValueError, match="table_top_y.*must be less than.*table_bottom_y"
        ):
            TemplateExtractionConfig(
                table_top_y=500,
                table_bottom_y=500,
                columns={"Date": (26, 78)},
            )

    def test_empty_columns(self):
        """Test that empty columns dict raises ValueError."""
        with pytest.raises(ValueError, match="columns dictionary cannot be empty"):
            TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={},
            )

    def test_invalid_column_bounds(self):
        """Test that invalid column X bounds raise ValueError."""
        with pytest.raises(ValueError, match="x_start.*must be less than.*x_end"):
            TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (78, 26)},
            )

    def test_get_table_top_y_no_overrides(self):
        """Test get_table_top_y returns default when no overrides exist."""
        config = TemplateExtractionConfig(
            table_top_y=300, table_bottom_y=720, columns={"Date": (26, 78)}
        )

        assert config.get_table_top_y(1) == 300
        assert config.get_table_top_y(2) == 300
        assert config.get_table_top_y(10) == 300

    def test_get_table_top_y_with_override(self):
        """Test get_table_top_y returns override for specific page."""
        config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (26, 78)},
            per_page_overrides={1: PerPageBoundaries(table_top_y=490)},
        )

        assert config.get_table_top_y(1) == 490  # Override for page 1
        assert config.get_table_top_y(2) == 140  # Default for other pages

    def test_get_table_bottom_y_no_overrides(self):
        """Test get_table_bottom_y returns default when no overrides exist."""
        config = TemplateExtractionConfig(
            table_top_y=300, table_bottom_y=720, columns={"Date": (26, 78)}
        )

        assert config.get_table_bottom_y(1) == 720
        assert config.get_table_bottom_y(2) == 720

    def test_get_table_bottom_y_with_override(self):
        """Test get_table_bottom_y returns override for specific page."""
        config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (26, 78)},
            per_page_overrides={1: PerPageBoundaries(table_bottom_y=800)},
        )

        assert config.get_table_bottom_y(1) == 800  # Override for page 1
        assert config.get_table_bottom_y(2) == 735  # Default for other pages

    def test_get_header_check_top_y_no_overrides(self):
        """Test get_header_check_top_y returns default when no overrides exist."""
        config = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
            header_check_top_y=250,
        )

        assert config.get_header_check_top_y(1) == 250
        assert config.get_header_check_top_y(2) == 250

    def test_get_header_check_top_y_with_override(self):
        """Test get_header_check_top_y returns override for specific page."""
        config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (26, 78)},
            header_check_top_y=100,
            per_page_overrides={1: PerPageBoundaries(header_check_top_y=450)},
        )

        assert config.get_header_check_top_y(1) == 450  # Override for page 1
        assert config.get_header_check_top_y(2) == 100  # Default for other pages

    def test_get_header_check_top_y_returns_none_when_no_default(self):
        """Test get_header_check_top_y returns None when no default is set."""
        config = TemplateExtractionConfig(
            table_top_y=300, table_bottom_y=720, columns={"Date": (26, 78)}
        )

        assert config.get_header_check_top_y(1) is None
        assert config.get_header_check_top_y(2) is None

    def test_per_page_overrides_with_multiple_pages(self):
        """Test per-page overrides for multiple pages."""
        config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (26, 78)},
            per_page_overrides={
                1: PerPageBoundaries(table_top_y=490, header_check_top_y=450),
                3: PerPageBoundaries(table_top_y=200),
            },
        )

        # Page 1 has overrides
        assert config.get_table_top_y(1) == 490
        assert config.get_header_check_top_y(1) == 450

        # Page 2 uses defaults
        assert config.get_table_top_y(2) == 140
        assert config.get_table_bottom_y(2) == 735

        # Page 3 has partial override
        assert config.get_table_top_y(3) == 200
        assert config.get_table_bottom_y(3) == 735  # Uses default

    def test_per_page_override_validation_invalid_bounds(self):
        """Test that invalid per-page override bounds raise ValueError."""
        with pytest.raises(
            ValueError, match="Page 1.*table_top_y.*must be less than.*table_bottom_y"
        ):
            TemplateExtractionConfig(
                table_top_y=140,
                table_bottom_y=735,
                columns={"Date": (26, 78)},
                per_page_overrides={
                    1: PerPageBoundaries(table_top_y=800, table_bottom_y=400)
                },
            )

    def test_per_page_override_partial_boundaries_allowed(self):
        """Test that partial per-page overrides are allowed (no validation error)."""
        # Should NOT raise error when only one boundary is overridden
        config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns={"Date": (26, 78)},
            per_page_overrides={1: PerPageBoundaries(table_top_y=490)},
        )

        assert config.get_table_top_y(1) == 490
        assert config.get_table_bottom_y(1) == 735  # Uses default


class TestTemplateProcessingConfig:
    """Tests for TemplateProcessingConfig."""

    def test_default_config(self):
        """Test default processing config values."""
        config = TemplateProcessingConfig()

        assert config.supports_multiline is False
        assert config.date_format == "%d/%m/%Y"
        assert config.currency_symbol == ""
        assert config.decimal_separator == "."

    def test_custom_config(self):
        """Test creating custom processing config."""
        config = TemplateProcessingConfig(
            supports_multiline=True,
            date_format="%d %b %Y",
            currency_symbol="$",
            decimal_separator=",",
        )

        assert config.supports_multiline is True
        assert config.date_format == "%d %b %Y"
        assert config.currency_symbol == "$"
        assert config.decimal_separator == ","


class TestTemplateDetectionConfig:
    """Tests for TemplateDetectionConfig."""

    def test_empty_config(self):
        """Test creating empty detection config."""
        config = TemplateDetectionConfig()

        assert config.iban_patterns == []
        assert config.filename_patterns == []
        assert config.header_keywords == []
        assert config.column_headers == []

    def test_full_config(self):
        """Test creating full detection config."""
        config = TemplateDetectionConfig(
            iban_patterns=["IE[0-9]{2}AIBK.*"],
            filename_patterns=["Statement*.pdf"],
            header_keywords=["AIB"],
            column_headers=["Date", "Details"],
        )

        assert len(config.iban_patterns) == 1
        assert len(config.filename_patterns) == 1
        assert len(config.header_keywords) == 1
        assert len(config.column_headers) == 2


class TestBankTemplate:
    """Tests for BankTemplate."""

    def test_valid_template(self):
        """Test creating valid bank template."""
        detection = TemplateDetectionConfig(
            iban_patterns=["IE[0-9]{2}AIBK.*"],
        )
        extraction = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        )

        template = BankTemplate(
            id="aib",
            name="Allied Irish Banks",
            enabled=True,
            detection=detection,
            extraction=extraction,
        )

        assert template.id == "aib"
        assert template.name == "Allied Irish Banks"
        assert template.enabled is True
        assert template.detection == detection
        assert template.extraction == extraction

    def test_empty_id(self):
        """Test that empty ID raises ValueError."""
        detection = TemplateDetectionConfig(iban_patterns=["IE.*"])
        extraction = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        )

        with pytest.raises(ValueError, match="Template id cannot be empty"):
            BankTemplate(
                id="",
                name="Test",
                enabled=True,
                detection=detection,
                extraction=extraction,
            )

    def test_empty_name(self):
        """Test that empty name raises ValueError."""
        detection = TemplateDetectionConfig(iban_patterns=["IE.*"])
        extraction = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        )

        with pytest.raises(ValueError, match="Template name cannot be empty"):
            BankTemplate(
                id="test",
                name="",
                enabled=True,
                detection=detection,
                extraction=extraction,
            )

    def test_no_detection_methods(self):
        """Test that template with no detection methods raises ValueError."""
        detection = TemplateDetectionConfig()
        extraction = TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        )

        with pytest.raises(ValueError, match="must have at least one detection method"):
            BankTemplate(
                id="test",
                name="Test",
                enabled=True,
                detection=detection,
                extraction=extraction,
            )


class TestBankTemplateColumnAliases:
    """Tests for BankTemplate.column_aliases field (CC-05)."""

    def test_default_column_aliases_is_empty_dict(self):
        """BankTemplate without column_aliases kwarg defaults to {}."""
        template = BankTemplate(
            id="test",
            name="Test",
            enabled=True,
            detection=TemplateDetectionConfig(header_keywords=["Test"]),
            extraction=TemplateExtractionConfig(
                table_top_y=100, table_bottom_y=500, columns={"Date": (10, 50)}
            ),
        )
        assert template.column_aliases == {}

    def test_column_aliases_set_explicitly(self):
        """BankTemplate with explicit column_aliases stores them correctly."""
        aliases = {"Transaction Details": "Details", "Debit €": "Debit", "Credit €": "Credit"}
        template = BankTemplate(
            id="cc_test",
            name="CC Test",
            enabled=True,
            detection=TemplateDetectionConfig(header_keywords=["CC"]),
            extraction=TemplateExtractionConfig(
                table_top_y=100, table_bottom_y=500, columns={"Date": (10, 50)}
            ),
            column_aliases=aliases,
        )
        assert template.column_aliases == aliases
        assert template.column_aliases["Transaction Details"] == "Details"
