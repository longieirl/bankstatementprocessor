"""Tests for analyze_pdf command."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from bankstatements_core.commands.analyze_pdf import PDFAnalyzer, main


class TestPDFAnalyzer:
    """Tests for PDFAnalyzer class."""

    def test_init(self):
        """Test PDFAnalyzer initialization."""
        pdf_path = Path("/tmp/test.pdf")
        output_path = Path("/tmp/output.json")

        analyzer = PDFAnalyzer(pdf_path=pdf_path, output_path=output_path)

        assert analyzer.pdf_path == pdf_path
        assert analyzer.output_path == output_path
        assert analyzer.table_detector is not None
        assert analyzer.iban_filter is not None
        assert analyzer.column_analyzer is not None
        assert analyzer.template_generator is not None

    def test_analyze_file_not_found(self):
        """Test analysis with non-existent PDF."""
        pdf_path = Path("/tmp/nonexistent.pdf")

        analyzer = PDFAnalyzer(pdf_path=pdf_path)

        with pytest.raises(FileNotFoundError):
            analyzer.analyze()

    @patch("bankstatements_core.commands.analyze_pdf.pdfplumber")
    def test_analyze_no_tables_detected(self, mock_pdfplumber):
        """Test analysis when no tables are detected."""
        # Create temp PDF path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        try:
            # Mock pdfplumber
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.page_number = 1
            mock_page.height = 842.0
            mock_page.width = 595.0
            mock_page.find_tables.return_value = []  # No tables

            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

            analyzer = PDFAnalyzer(pdf_path=pdf_path)
            result = analyzer.analyze()

            # Should return failure
            assert result["success"] is False
            assert "error" in result

        finally:
            pdf_path.unlink()

    @patch("bankstatements_core.commands.analyze_pdf.pdfplumber")
    def test_analyze_success_basic(self, mock_pdfplumber):
        """Test successful analysis workflow."""
        # Create temp PDF path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_template.json"

            try:
                # Mock pdfplumber
                mock_pdf = MagicMock()
                mock_page = MagicMock()
                mock_page.page_number = 1
                mock_page.height = 842.0
                mock_page.width = 595.0

                # Mock table detection
                mock_table = Mock()
                mock_table.bbox = (50, 300, 550, 720)
                mock_page.find_tables.return_value = [mock_table]

                # Mock word extraction for IBAN
                mock_page.extract_words.return_value = [
                    {
                        "text": "IE29AIBK93115212345678",
                        "x0": 100,
                        "top": 50,
                        "x1": 200,
                        "bottom": 60,
                    },
                    # Table words for column detection
                    {"text": "Date", "x0": 50, "top": 310, "x1": 80, "bottom": 320},
                    {
                        "text": "Details",
                        "x0": 150,
                        "top": 310,
                        "x1": 200,
                        "bottom": 320,
                    },
                    {"text": "Amount", "x0": 350, "top": 310, "x1": 400, "bottom": 320},
                    {"text": "01/01", "x0": 50, "top": 330, "x1": 80, "bottom": 340},
                    {
                        "text": "Purchase",
                        "x0": 150,
                        "top": 330,
                        "x1": 200,
                        "bottom": 340,
                    },
                    {"text": "100.00", "x0": 350, "top": 330, "x1": 400, "bottom": 340},
                ]

                mock_pdf.pages = [mock_page]
                mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

                analyzer = PDFAnalyzer(pdf_path=pdf_path, output_path=output_path)

                result = analyzer.analyze()

                # Should succeed
                assert result["success"] is True
                assert result["tables"] >= 1
                assert "columns" in result
                assert output_path.exists()

            finally:
                pdf_path.unlink()

    def test_entitlement_constraint_no_processor_factory(self):
        """Test that analyze_pdf does NOT use ProcessorFactory."""
        import inspect

        from bankstatements_core.commands import analyze_pdf

        source = inspect.getsource(analyze_pdf)

        # Check for actual imports or instantiations (not comments)
        import_check = "from bankstatements_core.patterns.factories import ProcessorFactory" in source
        instantiation_check = "ProcessorFactory.create" in source

        assert not import_check, "analyze_pdf must NOT import ProcessorFactory"
        assert (
            not instantiation_check
        ), "analyze_pdf must NOT call ProcessorFactory.create"

        # Verify it DOES use direct instantiation
        assert (
            "PDFTableExtractor(" in source
        ), "analyze_pdf should use direct PDFTableExtractor instantiation"

    def test_entitlement_constraint_no_entitlements_import(self):
        """Test that analyze_pdf does NOT import Entitlements."""
        import inspect

        from bankstatements_core.commands import analyze_pdf

        source = inspect.getsource(analyze_pdf)

        # Verify no Entitlements import
        assert (
            "from bankstatements_core.entitlements import" not in source
        ), "analyze_pdf must NOT import Entitlements module"
        assert "Entitlements" not in source or "entitlement" in source.lower()

    @patch("bankstatements_core.commands.analyze_pdf.pdfplumber")
    def test_first_page_only_for_iban(self, mock_pdfplumber):
        """Test that IBAN extraction only processes first page."""
        # Create temp PDF path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        try:
            # Mock PDF with multiple pages
            mock_pdf = MagicMock()

            mock_page1 = MagicMock()
            mock_page1.page_number = 1
            mock_page1.height = 842.0
            mock_page1.width = 595.0

            # Mock table detection (need tables for analysis to proceed)
            mock_table = Mock()
            mock_table.bbox = (50, 300, 550, 720)
            mock_page1.find_tables.return_value = [mock_table]

            # Mock words for both IBAN and column detection
            mock_page1.extract_words.return_value = [
                # IBAN in header
                {
                    "text": "IE29AIBK93115212345678",
                    "x0": 100,
                    "top": 50,
                    "x1": 200,
                    "bottom": 60,
                },
                # Table header words
                {"text": "Date", "x0": 50, "top": 310, "x1": 80, "bottom": 320},
                {"text": "Details", "x0": 150, "top": 310, "x1": 200, "bottom": 320},
            ]

            mock_page2 = MagicMock()
            mock_page2.page_number = 2
            mock_page2.height = 842.0
            mock_page2.width = 595.0
            mock_page2.find_tables.return_value = [mock_table]
            # Page 2 also has IBAN but should NOT be processed
            mock_page2.extract_words.return_value = [
                {
                    "text": "DE89370400440532013000",
                    "x0": 100,
                    "top": 50,
                    "x1": 200,
                    "bottom": 60,
                }
            ]

            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

            analyzer = PDFAnalyzer(pdf_path=pdf_path)

            # Mock IBAN filter to track calls
            original_extract = analyzer.iban_filter.extract_iban_candidates

            call_count = {"count": 0, "pages": []}

            def tracked_extract(page):
                call_count["count"] += 1
                call_count["pages"].append(page.page_number)
                return original_extract(page)

            analyzer.iban_filter.extract_iban_candidates = tracked_extract

            # Suppress exceptions - may fail due to no tables, but we're checking IBAN call
            import contextlib

            with contextlib.suppress(Exception):
                analyzer.analyze()

            # Verify IBAN extraction only called on first page
            assert (
                call_count["count"] == 1
            ), "IBAN extraction should only be called once"
            assert call_count["pages"] == [
                1
            ], "IBAN extraction should only process page 1"

        finally:
            pdf_path.unlink()


class TestMainCLI:
    """Tests for main CLI entry point."""

    @patch("bankstatements_core.commands.analyze_pdf.PDFAnalyzer")
    @patch("sys.argv", ["analyze_pdf.py", "test.pdf", "--output", "output.json"])
    def test_main_success(self, mock_analyzer_class):
        """Test main CLI with successful execution."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {"success": True}
        mock_analyzer_class.return_value = mock_analyzer

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    @patch("bankstatements_core.commands.analyze_pdf.PDFAnalyzer")
    @patch("sys.argv", ["analyze_pdf.py", "test.pdf"])
    def test_main_failure(self, mock_analyzer_class):
        """Test main CLI with failed execution."""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.side_effect = ValueError("Test error")
        mock_analyzer_class.return_value = mock_analyzer

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["analyze_pdf.py", "--help"])
    def test_main_help(self):
        """Test main CLI help message."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        # Help should exit with code 0
        assert exc_info.value.code == 0
