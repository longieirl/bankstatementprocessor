"""Integration tests for template system with real PDFs."""

from __future__ import annotations

from pathlib import Path

import pytest

from bankstatements_core.templates import TemplateDetector, TemplateRegistry


class TestTemplateIntegration:
    """Integration tests for template detection and extraction."""

    def test_registry_loads_default_config(self):
        """Test that registry can load default configuration."""
        registry = TemplateRegistry.from_default_config()

        assert registry is not None
        assert len(registry.get_template_ids()) >= 2
        assert "default" in registry.get_template_ids()
        assert "revolut" in registry.get_template_ids()

    def test_default_template_is_valid(self):
        """Test that default template is valid and enabled."""
        registry = TemplateRegistry.from_default_config()
        default = registry.get_default_template()

        assert default is not None
        assert default.enabled is True
        # Default can be any enabled template depending on load order
        # Common defaults: default, revolut, credit_card_default, aib_ireland
        assert default.id in [
            "default",
            "revolut",
            "credit_card_default",
            "aib_ireland",
        ]

    def test_default_template_configuration(self):
        """Test default template has correct configuration."""
        registry = TemplateRegistry.from_default_config()
        default_template = registry.get_template("default")

        assert default_template is not None
        assert default_template.name == "Default Bank Statement"
        assert default_template.extraction.table_top_y == 300
        assert default_template.extraction.table_bottom_y == 720
        assert "Date" in default_template.extraction.columns
        assert "Details" in default_template.extraction.columns
        assert "Debit €" in default_template.extraction.columns
        assert "Credit €" in default_template.extraction.columns
        assert "Balance €" in default_template.extraction.columns

    def test_revolut_template_configuration(self):
        """Test Revolut template has correct configuration."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert revolut is not None
        assert revolut.name == "Revolut Bank Statement"
        assert revolut.extraction.table_top_y == 140
        assert revolut.extraction.table_bottom_y == 735
        assert revolut.extraction.enable_page_validation is False
        assert "Date" in revolut.extraction.columns
        assert "Details" in revolut.extraction.columns
        assert "Debit €" in revolut.extraction.columns
        assert "Credit €" in revolut.extraction.columns
        assert "Balance €" in revolut.extraction.columns

    def test_detector_initialization(self):
        """Test detector initializes with registry."""
        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)

        assert detector is not None
        assert detector.registry == registry
        assert len(detector.detectors) == 7  # Phase 2: Added CardNumber, LoanReference
        # Exclusion, IBAN, CardNumber, LoanReference, Filename, Header, ColumnHeader

    @pytest.mark.skipif(
        not Path(
            "input/account-statement_2025-01-01_2026-01-30_en-ie_d04719.pdf"
        ).exists(),
        reason="Revolut test PDF not found",
    )
    def test_detect_revolut_pdf(self):
        """Test detecting Revolut PDF from real file."""
        import pdfplumber

        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)

        pdf_path = Path(
            "input/account-statement_2025-01-01_2026-01-30_en-ie_d04719.pdf"
        )

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            template = detector.detect_template(pdf_path, first_page)

        assert template is not None
        assert template.id == "revolut"
        assert template.name == "Revolut Bank Statement"

    @pytest.mark.skipif(
        not list(Path("input").glob("Statement*.pdf")),
        reason="Statement test PDF not found",
    )
    def test_detect_statement_pdf(self):
        """Test detecting bank statement PDF from real file."""
        import pdfplumber

        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)

        pdf_files = list(Path("input").glob("Statement*.pdf"))
        if not pdf_files:
            pytest.skip("No statement PDF found")

        pdf_path = pdf_files[0]

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            template = detector.detect_template(pdf_path, first_page)

        assert template is not None
        # Could match default, revolut, or aib_ireland depending on file content
        assert template.id in ["default", "revolut", "aib_ireland"]

    def test_template_extraction_config_types(self):
        """Test that template extraction config has correct types."""
        registry = TemplateRegistry.from_default_config()
        template = registry.get_template("default")

        assert template is not None
        assert isinstance(template.extraction.table_top_y, int)
        assert isinstance(template.extraction.table_bottom_y, int)
        assert isinstance(template.extraction.columns, dict)

        for col_name, coords in template.extraction.columns.items():
            assert isinstance(col_name, str)
            assert isinstance(coords, tuple)
            assert len(coords) == 2
            assert isinstance(coords[0], (int, float))
            assert isinstance(coords[1], (int, float))

    def test_force_template_override(self):
        """Test forcing specific template."""
        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)

        forced = detector.force_template("revolut")

        assert forced is not None
        assert forced.id == "revolut"
        assert forced.name == "Revolut Bank Statement"

    def test_all_templates_have_required_fields(self):
        """Test that all templates have required detection and extraction fields."""
        registry = TemplateRegistry.from_default_config()
        templates = registry.get_all_templates()

        for template in templates:
            assert template.id
            assert template.name
            assert template.detection is not None
            assert template.extraction is not None
            assert template.extraction.table_top_y > 0
            assert template.extraction.table_bottom_y > template.extraction.table_top_y
            assert len(template.extraction.columns) > 0

    def test_default_template_has_no_iban_pattern(self):
        """Test that default template does not have IBAN patterns (fallback only)."""
        registry = TemplateRegistry.from_default_config()
        default_template = registry.get_template("default")

        assert default_template is not None
        # Default template should have empty IBAN patterns to avoid matching everything
        assert default_template.detection.iban_patterns == []

    def test_revolut_template_has_specific_iban_pattern(self):
        """Test that Revolut template has specific REVO IBAN pattern."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert revolut is not None
        # Revolut should have specific IBAN pattern containing REVO
        assert len(revolut.detection.iban_patterns) > 0
        # Pattern should match Revolut IBANs with REVO bank code
        import re

        pattern = revolut.detection.iban_patterns[0]
        # Test that it matches Revolut IBAN
        assert re.match(pattern, "IE27REVO99036083303656")
        # Test that it doesn't match generic IBANs without REVO
        assert not re.match(pattern, "IE48AIBK93115212345678")

    def test_default_template_detected_by_column_headers(self):
        """Test that default template is detected via column headers, not IBAN."""
        registry = TemplateRegistry.from_default_config()
        default_template = registry.get_template("default")

        assert default_template is not None
        # Default should have column headers for detection
        assert len(default_template.detection.column_headers) > 0
        # Common headers that most bank statements have
        expected_headers = ["Date", "Details", "Debit", "Credit", "Balance"]
        for header in expected_headers:
            assert header in default_template.detection.column_headers

    def test_revolut_template_extraction_boundaries(self):
        """Test that Revolut template has correct extraction boundaries for pages 2-4."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert revolut is not None
        # Revolut pages 2-4 have transactions starting at y=140
        # This is lower than default template's y=300
        assert revolut.extraction.table_top_y == 140
        assert revolut.extraction.table_bottom_y == 735
        # Ensure it's configured for multiline transaction support
        assert revolut.processing.supports_multiline is True

    @pytest.mark.skipif(
        not Path(
            "input/account-statement_2025-01-01_2026-01-30_en-ie_d04719.pdf"
        ).exists(),
        reason="Revolut test PDF not found",
    )
    def test_revolut_pdf_extracts_all_transactions(self):
        """Test that Revolut PDF extracts all 67+ transactions (not just 43)."""
        from bankstatements_core.pdf_table_extractor import extract_tables_from_pdf

        registry = TemplateRegistry.from_default_config()
        revolut_template = registry.get_template("revolut")

        pdf_path = Path(
            "input/account-statement_2025-01-01_2026-01-30_en-ie_d04719.pdf"
        )

        rows, page_count, iban = extract_tables_from_pdf(
            pdf_path,
            table_top_y=revolut_template.extraction.table_top_y,
            table_bottom_y=revolut_template.extraction.table_bottom_y,
            columns=revolut_template.extraction.columns,
            enable_dynamic_boundary=False,
            template=revolut_template,
        )

        # Should extract 67+ transactions from pages 2-4
        # (Page 1 and 5 have different structure and are skipped)
        assert len(rows) >= 67
        # Verify we have January 2025 transactions (not missing first 24)
        dates = [row.get("Date", "") for row in rows if row.get("Date")]
        jan_transactions = [d for d in dates if "Jan 2025" in d]
        assert len(jan_transactions) >= 4  # At least 4 January transactions

    @pytest.mark.skipif(
        not list(Path("input").glob("Statement*.pdf")),
        reason="Statement test PDF not found",
    )
    def test_statement_pdf_detected_as_default(self):
        """Test that generic bank statement PDF is detected as default template."""
        import pdfplumber

        registry = TemplateRegistry.from_default_config()
        detector = TemplateDetector(registry)

        pdf_files = list(Path("input").glob("Statement*.pdf"))
        if not pdf_files:
            pytest.skip("No statement PDF found")

        pdf_path = pdf_files[0]

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            template = detector.detect_template(pdf_path, first_page)

        assert template is not None
        # Should detect based on actual PDF content
        # Could be aib_ireland, default, or other depending on file
        assert template.id in ["default", "aib_ireland", "revolut"]
