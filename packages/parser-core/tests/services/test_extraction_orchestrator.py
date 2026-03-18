"""Tests for extraction orchestrator service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.config.processor_config import ExtractionConfig
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
        mock_extract.return_value = (
            [{"Date": "01/01/23", "Details": "Test"}],
            5,
            "IE12BOFI90000112345",
        )

        rows, pages, iban = self.orchestrator.extract_from_pdf(pdf_path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(pages, 5)
        self.assertEqual(iban, "IE12BOFI90000112345")
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

        mock_extract.return_value = ([{"Date": "01/01/23"}], 3, None)

        rows, pages, iban = self.orchestrator.extract_from_pdf(
            pdf_path, forced_template=mock_template
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(pages, 3)
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

        mock_extract.return_value = ([], 2, None)

        rows, pages, iban = self.orchestrator.extract_from_pdf(pdf_path)

        self.assertEqual(len(rows), 0)
        self.assertEqual(pages, 2)
        self.assertIsNone(iban)

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_extract_from_pdf_returns_rows_as_is(self, mock_extract):
        """Test that extracted rows are returned as-is from extract_tables_from_pdf."""
        pdf_path = Path(self.temp_dir) / "test.pdf"
        pdf_path.write_text("fake pdf")

        mock_extract.return_value = (
            [
                {"Date": "01/01/23", "Details": "Test1"},
                {"Date": "02/01/23", "Details": "Test2"},
            ],
            3,
            None,
        )

        rows, _, _ = self.orchestrator.extract_from_pdf(pdf_path)

        # Rows should be returned as-is (Filename is added by caller, not orchestrator)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Details"], "Test1")
        self.assertEqual(rows[1]["Details"], "Test2")

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


if __name__ == "__main__":
    unittest.main()
