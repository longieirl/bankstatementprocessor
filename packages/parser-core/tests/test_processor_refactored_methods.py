"""
Tests for refactored processor methods to improve testability and coverage.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pandas as pd

from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    ProcessorConfig,
)
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions
from bankstatements_core.processor import BankStatementProcessor

# Module-level defaults to avoid B008 (function call in defaults)
_DEFAULT_INPUT_DIR = Path("input")
_DEFAULT_OUTPUT_DIR = Path("output")


def create_test_processor(input_dir=None, output_dir=None, **kwargs):
    """Helper to create processor with test configuration."""
    if input_dir is None:
        input_dir = _DEFAULT_INPUT_DIR
    if output_dir is None:
        output_dir = _DEFAULT_OUTPUT_DIR
    table_top_y = kwargs.get("table_top_y", 100)
    table_bottom_y = kwargs.get("table_bottom_y", 700)

    extraction_config = ExtractionConfig(
        table_top_y=table_top_y,
        table_bottom_y=table_bottom_y,
    )
    config = ProcessorConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        extraction=extraction_config,
    )
    return BankStatementProcessor(config=config)


class TestProcessorRefactoredMethods(unittest.TestCase):
    """Tests for newly extracted processor methods"""

    def setUp(self):
        """Set up test processor instance"""
        self.processor = create_test_processor()

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_process_all_pdfs_multiple_files(self, mock_extract):
        """Test _process_all_pdfs with multiple PDF files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = create_test_processor(
                input_dir=input_dir, output_dir=output_dir
            )

            # Mock glob to return multiple PDFs
            with patch.object(Path, "glob") as mock_glob:
                mock_glob.return_value = [
                    Path("input/file1.pdf"),
                    Path("input/file2.pdf"),
                ]

                # Mock extract_tables_from_pdf to return different data
                mock_extract.side_effect = [
                    ExtractionResult(
                        transactions=dicts_to_transactions(
                            [{"Date": "01/01/23", "Details": "Test1"}]
                        ),
                        page_count=5,
                        iban=None,
                        source_file=Path("file1.pdf"),
                    ),
                    ExtractionResult(
                        transactions=dicts_to_transactions(
                            [{"Date": "02/01/23", "Details": "Test2"}]
                        ),
                        page_count=3,
                        iban=None,
                        source_file=Path("file2.pdf"),
                    ),
                ]

                results, pdf_count, pages_read = processor._process_all_pdfs()

                # Verify results
                self.assertEqual(pdf_count, 2)
                self.assertEqual(len(results), 2)
                self.assertEqual(pages_read, 8)
                self.assertEqual(results[0].page_count, 5)
                self.assertEqual(results[1].page_count, 3)
                self.assertEqual(
                    results[0].transactions[0].to_dict()["Details"], "Test1"
                )
                self.assertEqual(
                    results[1].transactions[0].to_dict()["Details"], "Test2"
                )
                self.assertIsNone(results[0].iban)
                self.assertIsNone(results[1].iban)

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_process_all_pdfs_no_files(self, mock_extract):
        """Test _process_all_pdfs with no PDF files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = create_test_processor(
                input_dir=input_dir, output_dir=output_dir
            )

            with patch.object(Path, "glob") as mock_glob:
                mock_glob.return_value = []

                results, pdf_count, pages_read = processor._process_all_pdfs()

                # Should return empty results
                self.assertEqual(pdf_count, 0)
                self.assertEqual(len(results), 0)
                self.assertEqual(pages_read, 0)
                mock_extract.assert_not_called()

    def test_sort_transactions_by_date_mixed_dates(self):
        """Test _sort_transactions_by_date with various date formats"""
        from bankstatements_core.domain.converters import dicts_to_transactions

        rows = dicts_to_transactions(
            [
                {"Date": "15/06/23", "Details": "Third"},
                {"Date": "01/01/23", "Details": "First"},
                {"Date": "10/03/23", "Details": "Second"},
            ]
        )

        sorted_rows = self.processor._sort_transactions_by_date(rows)

        # Verify chronological order
        self.assertEqual(sorted_rows[0].details, "First")
        self.assertEqual(sorted_rows[1].details, "Second")
        self.assertEqual(sorted_rows[2].details, "Third")

    def test_sort_transactions_by_date_empty_list(self):
        """Test _sort_transactions_by_date with empty list"""
        sorted_rows = self.processor._sort_transactions_by_date([])

        self.assertEqual(sorted_rows, [])

    def test_sort_transactions_by_date_single_item(self):
        """Test _sort_transactions_by_date with single transaction"""
        from bankstatements_core.domain.converters import dicts_to_transactions

        rows = dicts_to_transactions([{"Date": "01/01/23", "Details": "Only"}])

        sorted_rows = self.processor._sort_transactions_by_date(rows)

        self.assertEqual(len(sorted_rows), 1)
        self.assertEqual(sorted_rows[0].details, "Only")

    def test_write_json_file(self):
        """Test JSON writing through repository"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"
            test_data = {"key": "value", "number": 123}

            # Use repository directly since _write_json_file was moved
            self.processor.repository.save_as_json(test_data, test_path)

            # Verify file was created and contains correct data
            self.assertTrue(test_path.exists())
            content = test_path.read_text(encoding="utf-8")
            loaded_data = json.loads(content)
            self.assertEqual(loaded_data, test_data)
            # Verify it's indented (formatted)
            self.assertIn("\n", content)

    def test_write_output_files_with_monthly_summary(self):
        """Test _write_output_files when monthly summary is enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.processor.output_dir = Path(tmpdir)
            self.processor._output_orchestrator.output_dir = Path(tmpdir)
            self.processor.generate_monthly_summary = True

            unique_rows = [{"Date": "01/01/23", "Debit €": "100", "Credit €": "50"}]
            duplicate_rows = []
            df_unique = pd.DataFrame(unique_rows)

            with patch.object(
                self.processor._monthly_summary_service, "generate"
            ) as mock_gen_summary:
                mock_gen_summary.return_value = {
                    "summary": "Monthly Transaction Summary",
                    "generated_at": "2023-01-01T00:00:00",
                    "total_months": 1,
                    "monthly_data": [{"Month": "2023-01"}],
                }

                output_paths = self.processor._output_orchestrator.write_output_files(
                    unique_rows, duplicate_rows, df_unique
                )

                # Verify all expected paths are returned
                self.assertIn("csv_path", output_paths)
                self.assertIn("json_path", output_paths)
                self.assertIn("duplicates_path", output_paths)
                self.assertIn("monthly_summary_path", output_paths)

                # Verify monthly summary was generated
                mock_gen_summary.assert_called_once()

    def test_write_output_files_always_generates_monthly_summary(self):
        """Test _write_output_files always generates monthly summary when there are transactions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.processor.output_dir = Path(tmpdir)
            self.processor._output_orchestrator.output_dir = Path(tmpdir)
            # Note: generate_monthly_summary flag is no longer used - always generates

            unique_rows = [{"Date": "01/01/23", "Debit €": "100"}]
            duplicate_rows = []
            df_unique = pd.DataFrame(unique_rows)

            with patch.object(
                self.processor._monthly_summary_service, "generate"
            ) as mock_gen_summary:
                mock_gen_summary.return_value = {
                    "summary": "Monthly Transaction Summary",
                    "generated_at": "2023-01-01T00:00:00",
                    "total_months": 1,
                    "monthly_data": [{"Month": "2023-01", "total": 100}],
                }

                output_paths = self.processor._output_orchestrator.write_output_files(
                    unique_rows, duplicate_rows, df_unique
                )

                # Verify monthly_summary_path is always included (when there are transactions)
                self.assertIn("monthly_summary_path", output_paths)

                # Verify monthly summary was generated
                mock_gen_summary.assert_called_once()

    def test_write_output_files_with_empty_rows(self):
        """Test _write_output_files with empty unique rows and monthly summary enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.processor.output_dir = Path(tmpdir)
            self.processor._output_orchestrator.output_dir = Path(tmpdir)
            self.processor.generate_monthly_summary = True

            unique_rows = []
            duplicate_rows = []
            df_unique = pd.DataFrame()

            with patch(
                "bankstatements_core.processor.generate_monthly_summary"
            ) as mock_gen_summary:
                output_paths = self.processor._output_orchestrator.write_output_files(
                    unique_rows, duplicate_rows, df_unique
                )

                # Monthly summary should not be generated for empty rows
                self.assertNotIn("monthly_summary_path", output_paths)
                mock_gen_summary.assert_not_called()

    def test_build_summary_result_with_all_paths(self):
        """Test _build_summary_result includes all provided paths"""
        output_paths = {
            "csv_path": "/output/bank_statements.csv",
            "json_path": "/output/bank_statements.json",
            "duplicates_path": "/output/duplicates.json",
            "monthly_summary_path": "/output/monthly_summary.json",
        }

        result = self.processor._output_orchestrator.build_summary_result(
            pdf_count=3,
            pdfs_extracted=3,
            pages_read=10,
            unique_count=50,
            duplicate_count=5,
            output_paths=output_paths,
        )

        # Verify all fields are present
        self.assertEqual(result["pdf_count"], 3)
        self.assertEqual(result["pages_read"], 10)
        self.assertEqual(result["transactions"], 50)
        self.assertEqual(result["duplicates"], 5)
        self.assertEqual(result["csv_path"], "/output/bank_statements.csv")
        self.assertEqual(result["json_path"], "/output/bank_statements.json")
        self.assertEqual(result["duplicates_path"], "/output/duplicates.json")
        self.assertEqual(result["monthly_summary_path"], "/output/monthly_summary.json")

    def test_build_summary_result_without_monthly_summary(self):
        """Test _build_summary_result without monthly summary path"""
        output_paths = {
            "csv_path": "/output/bank_statements.csv",
            "json_path": "/output/bank_statements.json",
            "duplicates_path": "/output/duplicates.json",
        }

        result = self.processor._output_orchestrator.build_summary_result(
            pdf_count=2,
            pdfs_extracted=2,
            pages_read=5,
            unique_count=25,
            duplicate_count=2,
            output_paths=output_paths,
        )

        # Verify monthly_summary_path is not in result
        self.assertNotIn("monthly_summary_path", result)
        self.assertEqual(result["pdf_count"], 2)
        self.assertEqual(result["transactions"], 25)


class TestProcessorRefactoredIntegration(unittest.TestCase):
    """Integration tests for refactored run() method"""

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_run_uses_refactored_methods(self, mock_extract):
        """Test that run() correctly orchestrates refactored methods"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create a fake PDF file
            pdf_file = input_dir / "test.pdf"
            pdf_file.write_text("fake pdf", encoding="utf-8")

            processor = create_test_processor(
                input_dir=input_dir,
                output_dir=output_dir,
                table_top_y=100,
                table_bottom_y=700,
            )

            # Mock extract_tables_from_pdf
            mock_extract.return_value = ExtractionResult(
                transactions=dicts_to_transactions(
                    [
                        {"Date": "15/06/23", "Details": "Second", "Debit €": "200"},
                        {"Date": "01/01/23", "Details": "First", "Debit €": "100"},
                    ]
                ),
                page_count=2,
                iban=None,
                source_file=Path("test.pdf"),
            )

            result = processor.run()

            # Verify result structure
            self.assertEqual(result["pdf_count"], 1)
            self.assertEqual(result["pages_read"], 2)
            self.assertEqual(result["transactions"], 2)
            self.assertEqual(result["duplicates"], 0)
            # With IBAN grouping, the keys are now prefixed with IBAN suffix (or "unknown")
            self.assertIn("unknown_csv_path", result)
            self.assertIn("unknown_monthly_summary_path", result)

            # Verify CSV was written and sorted
            csv_path = Path(result["unknown_csv_path"])
            self.assertTrue(csv_path.exists())


if __name__ == "__main__":
    unittest.main()
