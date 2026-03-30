"""Tests for excluded files logging functionality."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions


def create_test_processor(input_dir, output_dir):
    """Helper to create processor with test configuration."""
    from bankstatements_core.processor import BankStatementProcessor

    config = ProcessorConfig(input_dir=input_dir, output_dir=output_dir)
    return BankStatementProcessor(config=config)


class TestExcludedFilesLogging:
    """Tests for logging excluded credit card statements to JSON."""

    def test_excluded_files_json_created(self):
        """Test that excluded_files.json is created when credit card statements are detected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a test PDF file
            test_pdf = input_dir / "credit_card.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock PDFTableExtractor to return empty results (credit card detected)
            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=[],
                    page_count=1,
                    iban=None,
                    source_file=Path("credit_card.pdf"),
                    warnings=["credit card statement detected, skipped"],
                )

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Check that excluded_files.json was created
                excluded_path = output_dir / "excluded_files.json"
                assert excluded_path.exists()

                # Verify content
                with open(excluded_path) as f:
                    data = json.load(f)

                assert "summary" in data
                assert "excluded_files" in data
                assert data["summary"]["total_excluded"] == 1
                assert len(data["excluded_files"]) == 1
                assert data["excluded_files"][0]["filename"] == "credit_card.pdf"
                assert "Could not be processed" in data["excluded_files"][0]["reason"]
                assert data["excluded_files"][0]["pages"] == 1

    def test_excluded_files_json_not_created_when_no_exclusions(self):
        """Test that excluded_files.json is not created when all PDFs are processed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a test PDF file
            test_pdf = input_dir / "bank_statement.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock PDFTableExtractor to return transactions (not credit card)
            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=dicts_to_transactions(
                        [{"Date": "01/12/23", "Details": "Test", "Debit €": "100"}]
                    ),
                    page_count=1,
                    iban="IE29AIBK93115212345678",
                    source_file=Path("bank_statement.pdf"),
                )

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Check that excluded_files.json was NOT created
                excluded_path = output_dir / "excluded_files.json"
                assert not excluded_path.exists()

    def test_excluded_files_multiple_exclusions(self):
        """Test logging multiple excluded files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create multiple test PDF files
            for i in range(3):
                test_pdf = input_dir / f"credit_card_{i}.pdf"
                test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock PDFTableExtractor to return empty results for all
            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=[],
                    page_count=2,
                    iban=None,
                    source_file=Path("credit_card.pdf"),
                    warnings=["credit card statement detected, skipped"],
                )

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Check excluded_files.json
                excluded_path = output_dir / "excluded_files.json"
                assert excluded_path.exists()

                with open(excluded_path) as f:
                    data = json.load(f)

                assert data["summary"]["total_excluded"] == 3
                assert len(data["excluded_files"]) == 3

                # Verify all files are logged
                filenames = [f["filename"] for f in data["excluded_files"]]
                assert "credit_card_0.pdf" in filenames
                assert "credit_card_1.pdf" in filenames
                assert "credit_card_2.pdf" in filenames

    def test_excluded_files_mixed_scenarios(self):
        """Test logging with mix of excluded and processed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create test PDF files
            credit_card_pdf = input_dir / "credit_card.pdf"
            credit_card_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            bank_pdf = input_dir / "bank_statement.pdf"
            bank_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock PDFTableExtractor to return different results
            def mock_extract_side_effect(pdf_path, *args, **kwargs):
                if "credit_card" in str(pdf_path):
                    return ExtractionResult(
                        transactions=[],
                        page_count=1,
                        iban=None,
                        source_file=pdf_path,
                        warnings=["credit card statement detected, skipped"],
                    )
                else:
                    return ExtractionResult(
                        transactions=dicts_to_transactions(
                            [{"Date": "01/12/23", "Details": "Test", "Debit €": "100"}]
                        ),
                        page_count=1,
                        iban="IE29AIBK93115212345678",
                        source_file=pdf_path,
                    )

            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.side_effect = mock_extract_side_effect

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Check excluded_files.json
                excluded_path = output_dir / "excluded_files.json"
                assert excluded_path.exists()

                with open(excluded_path) as f:
                    data = json.load(f)

                # Only credit card should be excluded
                assert data["summary"]["total_excluded"] == 1
                assert data["excluded_files"][0]["filename"] == "credit_card.pdf"

    def test_excluded_files_json_structure(self):
        """Test the structure of excluded_files.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            test_pdf = input_dir / "test.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=[],
                    page_count=3,
                    iban=None,
                    source_file=Path("test.pdf"),
                    warnings=["credit card statement detected, skipped"],
                )

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                excluded_path = output_dir / "excluded_files.json"
                with open(excluded_path) as f:
                    data = json.load(f)

                # Verify structure
                assert "summary" in data
                assert "total_excluded" in data["summary"]
                assert "generated_at" in data["summary"]
                assert "excluded_files" in data

                # Verify excluded file entry structure
                entry = data["excluded_files"][0]
                assert "filename" in entry
                assert "path" in entry
                assert "reason" in entry
                assert "timestamp" in entry
                assert "pages" in entry

                # Verify values
                assert entry["filename"] == "test.pdf"
                assert "Could not be processed" in entry["reason"]
                assert entry["pages"] == 3

    def test_excluded_files_logging_with_exception(self):
        """Test that excluded files logging doesn't break when there's an exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            test_pdf = input_dir / "test.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.side_effect = ValueError("Processing error")

                processor = create_test_processor(input_dir, output_dir)
                result = processor.run()

                # Should complete without crashing
                assert "pdf_count" in result

                # No excluded_files.json should be created (exception case)
                excluded_path = output_dir / "excluded_files.json"
                assert not excluded_path.exists()

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_credit_card_detection_integration(self, mock_pdfplumber):
        """Test end-to-end credit card detection and exclusion logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a real PDF file (content doesn't matter, mocked)
            test_pdf = input_dir / "credit_card_statement.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock PDF with credit card indicator
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.return_value = mock_pdf

            # Page contains "Card Number"
            mock_page.extract_text.return_value = (
                "Credit Card Statement\nCard Number: 1234"
            )

            # Need to mock crop and extract_words/extract_text since those are also called
            mock_cropped = MagicMock()
            mock_page.crop.return_value = mock_cropped
            mock_cropped.extract_text.return_value = "Credit Card Statement\nCard Number: 1234"  # Phase 2: document classification uses cropped text
            mock_cropped.extract_words.return_value = []

            processor = create_test_processor(input_dir, output_dir)
            result = processor.run()

            # Check that file was excluded
            excluded_path = output_dir / "excluded_files.json"
            assert excluded_path.exists()

            with open(excluded_path) as f:
                data = json.load(f)

            assert data["summary"]["total_excluded"] == 1
            assert data["excluded_files"][0]["filename"] == "credit_card_statement.pdf"
            assert "Could not be processed" in data["excluded_files"][0]["reason"]
            assert result["transactions"] == 0

    def test_pdf_with_iban_not_excluded(self):
        """Test that PDFs with IBAN are NOT excluded even if no rows extracted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a test PDF
            test_pdf = input_dir / "bank_statement.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock: PDF has IBAN but no rows (extraction issue, not credit card)
            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=[],
                    page_count=2,
                    iban="IE29AIBK93115212345678",
                    source_file=Path("bank_statement.pdf"),
                )

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Should NOT be excluded (has IBAN)
                excluded_path = output_dir / "excluded_files.json"
                assert not excluded_path.exists()

                # IBAN should be saved
                iban_path = output_dir / "ibans.json"
                assert iban_path.exists()

    def test_mixed_with_iban_and_without_iban(self):
        """Test that only PDFs without IBAN are excluded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create test PDFs
            pdf1 = input_dir / "bank_with_iban.pdf"
            pdf1.write_bytes(b"%PDF-1.4\nTest PDF")

            pdf2 = input_dir / "credit_card_no_iban.pdf"
            pdf2.write_bytes(b"%PDF-1.4\nTest PDF")

            def mock_extract_side_effect(pdf_path, *args, **kwargs):
                if "bank_with_iban" in str(pdf_path):
                    # Has IBAN, empty rows (should NOT be excluded)
                    return ExtractionResult(
                        transactions=[],
                        page_count=2,
                        iban="IE29AIBK93115212345678",
                        source_file=pdf_path,
                    )
                else:
                    # No IBAN, empty rows (SHOULD be excluded)
                    return ExtractionResult(
                        transactions=[],
                        page_count=1,
                        iban=None,
                        source_file=pdf_path,
                        warnings=["credit card statement detected, skipped"],
                    )

            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.side_effect = mock_extract_side_effect

                processor = create_test_processor(input_dir, output_dir)
                processor.run()

                # Only PDF without IBAN should be excluded
                excluded_path = output_dir / "excluded_files.json"
                assert excluded_path.exists()

                with open(excluded_path) as f:
                    data = json.load(f)

                assert data["summary"]["total_excluded"] == 1
                assert (
                    data["excluded_files"][0]["filename"] == "credit_card_no_iban.pdf"
                )

                # PDF with IBAN should have IBAN saved
                iban_path = output_dir / "ibans.json"
                assert iban_path.exists()

                with open(iban_path) as f:
                    iban_data = json.load(f)

                assert len(iban_data) == 1
                assert iban_data[0]["pdf_filename"] == "bank_with_iban.pdf"
