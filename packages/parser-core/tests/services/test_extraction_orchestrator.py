"""Tests for extraction orchestrator service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions
from bankstatements_core.services.extraction_orchestrator import ExtractionOrchestrator


class TestExtractionOrchestrator(unittest.TestCase):
    """Test ExtractionOrchestrator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.extraction_config = ExtractionConfig(
            table_top_y=100,
            table_bottom_y=700,
        )
        self.orchestrator = ExtractionOrchestrator(
            extraction_config=self.extraction_config
        )

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_extract_from_pdf_success(self, mock_extract):
        """Test successful PDF extraction."""
        pdf_path = Path(self.temp_dir) / "test.pdf"
        pdf_path.write_text("fake pdf")

        # Mock successful extraction
        mock_extract.return_value = ExtractionResult(
            transactions=dicts_to_transactions(
                [{"Date": "01/01/23", "Details": "Test"}]
            ),
            page_count=5,
            iban="IE12BOFI90000112345",
            source_file=pdf_path,
        )

        result = self.orchestrator.extract_from_pdf(pdf_path)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(len(result.transactions), 1)
        self.assertEqual(result.page_count, 5)
        self.assertEqual(result.iban, "IE12BOFI90000112345")
        mock_extract.assert_called_once()

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_extract_from_pdf_with_forced_template(self, mock_extract):
        """Test extraction with forced template."""
        pdf_path = Path(self.temp_dir) / "test.pdf"
        pdf_path.write_text("fake pdf")

        # Create mock template
        mock_template = MagicMock()
        mock_template.name = "TestTemplate"

        mock_extract.return_value = ExtractionResult(
            transactions=dicts_to_transactions([{"Date": "01/01/23"}]),
            page_count=3,
            iban=None,
            source_file=pdf_path,
        )

        result = self.orchestrator.extract_from_pdf(
            pdf_path, forced_template=mock_template
        )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(len(result.transactions), 1)
        self.assertEqual(result.page_count, 3)
        # Verify extraction was called with the forced template
        call_args = mock_extract.call_args
        self.assertEqual(call_args[0][0], pdf_path)  # First positional arg

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_extract_from_pdf_no_data(self, mock_extract):
        """Test extraction when PDF has no data."""
        pdf_path = Path(self.temp_dir) / "test.pdf"
        pdf_path.write_text("fake pdf")

        mock_extract.return_value = ExtractionResult(
            transactions=[], page_count=2, iban=None, source_file=pdf_path
        )

        result = self.orchestrator.extract_from_pdf(pdf_path)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(len(result.transactions), 0)
        self.assertEqual(result.page_count, 2)
        self.assertIsNone(result.iban)

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_extract_from_pdf_returns_rows_as_is(self, mock_extract):
        """Test that extracted rows are returned as-is from extract_tables_from_pdf."""
        pdf_path = Path(self.temp_dir) / "test.pdf"
        pdf_path.write_text("fake pdf")

        mock_extract.return_value = ExtractionResult(
            transactions=dicts_to_transactions(
                [
                    {"Date": "01/01/23", "Details": "Test1"},
                    {"Date": "02/01/23", "Details": "Test2"},
                ]
            ),
            page_count=3,
            iban=None,
            source_file=pdf_path,
        )

        result = self.orchestrator.extract_from_pdf(pdf_path)

        self.assertIsInstance(result, ExtractionResult)
        # transactions are Transaction objects; check via to_dict() for field values
        self.assertEqual(len(result.transactions), 2)
        self.assertEqual(result.transactions[0].to_dict()["Details"], "Test1")
        self.assertEqual(result.transactions[1].to_dict()["Details"], "Test2")

    def test_initialization_without_errors(self):
        """Test orchestrator initializes without errors."""
        # Create orchestrator which should initialize template system
        orchestrator = ExtractionOrchestrator(extraction_config=self.extraction_config)

        # Verify config was stored
        self.assertEqual(orchestrator._config.table_top_y, 100)
        self.assertEqual(orchestrator._config.table_bottom_y, 700)

    def test_custom_extraction_config(self):
        """Test orchestrator uses custom extraction config."""
        custom_config = ExtractionConfig(
            table_top_y=200,
            table_bottom_y=800,
        )
        orchestrator = ExtractionOrchestrator(extraction_config=custom_config)

        self.assertEqual(orchestrator._config.table_top_y, 200)
        self.assertEqual(orchestrator._config.table_bottom_y, 800)

    def test_pdf_reader_injection(self):
        """Test that orchestrator accepts pdf_reader dependency injection."""
        mock_pdf_reader = MagicMock()
        orchestrator = ExtractionOrchestrator(
            extraction_config=self.extraction_config, pdf_reader=mock_pdf_reader
        )

        # Verify injected pdf_reader is used
        self.assertEqual(orchestrator._pdf_reader, mock_pdf_reader)

    @patch.dict("os.environ", {"FORCE_TEMPLATE": "aib_personal"})
    @patch("bankstatements_core.services.extraction_orchestrator.TemplateRegistry")
    def test_force_template_from_env(self, mock_registry_class):
        """Test FORCE_TEMPLATE environment variable is respected."""
        mock_registry = MagicMock()
        mock_template = MagicMock()
        mock_template.name = "aib_personal"
        mock_detector = MagicMock()
        mock_detector.force_template.return_value = mock_template

        mock_registry_class.from_default_config.return_value = mock_registry

        # Create orchestrator which should read FORCE_TEMPLATE env var
        with patch(
            "bankstatements_core.services.extraction_orchestrator.TemplateDetector",
            return_value=mock_detector,
        ):
            _ = ExtractionOrchestrator(extraction_config=self.extraction_config)

            # Verify force_template was called with the env var value
            mock_detector.force_template.assert_called_once_with("aib_personal")

    @patch.dict("os.environ", {"FORCE_TEMPLATE": "nonexistent_template"})
    @patch("bankstatements_core.services.extraction_orchestrator.TemplateRegistry")
    def test_force_template_not_found(self, mock_registry_class):
        """Test handling when FORCE_TEMPLATE template doesn't exist."""
        mock_registry = MagicMock()
        mock_detector = MagicMock()
        mock_detector.force_template.return_value = None  # Template not found

        mock_registry_class.from_default_config.return_value = mock_registry

        # Create orchestrator - should handle template not found gracefully
        with patch(
            "bankstatements_core.services.extraction_orchestrator.TemplateDetector",
            return_value=mock_detector,
        ):
            orchestrator = ExtractionOrchestrator(
                extraction_config=self.extraction_config
            )

            # Verify template detection is not forced
            assert orchestrator._forced_template is None

    @patch("bankstatements_core.services.extraction_orchestrator.TemplateRegistry")
    def test_extraction_orchestrator_does_not_mutate_registry_templates(
        self, mock_registry_class
    ):
        """Two orchestrators sharing the same registry — second still sees all templates."""
        from bankstatements_core.entitlements import Entitlements

        # Build two fake templates: one with IBAN patterns, one without
        t_with_iban = MagicMock()
        t_with_iban.id = "with_iban"
        t_with_iban.name = "With IBAN"
        t_with_iban.detection.iban_patterns = ["IE.*"]
        t_with_iban.enabled = True

        t_no_iban = MagicMock()
        t_no_iban.id = "no_iban"
        t_no_iban.name = "No IBAN"
        t_no_iban.detection.iban_patterns = []
        t_no_iban.enabled = True

        # Registry always returns both templates from list_all()
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = [t_with_iban, t_no_iban]
        mock_registry.filtered_by_ids.return_value = mock_registry
        mock_registry_class.from_default_config.return_value = mock_registry

        free = Entitlements.free_tier()

        with patch(
            "bankstatements_core.services.extraction_orchestrator.TemplateDetector"
        ):
            ExtractionOrchestrator(
                extraction_config=self.extraction_config, entitlements=free
            )
            ExtractionOrchestrator(
                extraction_config=self.extraction_config, entitlements=free
            )

        # filtered_by_ids() called, NOT template.enabled = False
        mock_registry.filtered_by_ids.assert_called()
        assert t_with_iban.enabled is True
        assert t_no_iban.enabled is True


if __name__ == "__main__":
    unittest.main()
