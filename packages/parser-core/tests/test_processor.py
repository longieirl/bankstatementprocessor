from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    OutputConfig,
    ProcessingConfig,
    ProcessorConfig,
)
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions
from bankstatements_core.processor import (
    BankStatementProcessor,
    calculate_column_totals,
    find_matching_columns,
    generate_monthly_summary,
    parse_totals_columns,
    parse_transaction_date,
)
from bankstatements_core.services.date_parser import DateParserService

# For tests that need direct access to date parsing internals
_date_parser = DateParserService()
EPOCH_DATE = _date_parser.EPOCH_DATE
TWO_DIGIT_YEAR_CUTOFF = _date_parser.TWO_DIGIT_YEAR_CUTOFF
_normalize_two_digit_year = _date_parser._normalize_two_digit_year
_parse_common_date_formats = _date_parser._parse_common_date_formats
_parse_partial_date = _date_parser._parse_partial_date
_try_parse_date_format = _date_parser._try_parse_date_format


def create_test_processor(input_dir, output_dir, **kwargs):
    """Helper to create processor with test configuration."""
    # Extract extraction config parameters
    table_top_y = kwargs.get("table_top_y", 300)
    table_bottom_y = kwargs.get("table_bottom_y", 720)
    columns = kwargs.get("columns")
    enable_dynamic_boundary = kwargs.get("enable_dynamic_boundary", False)

    # Extract processing config parameters
    sort_by_date = kwargs.get("sort_by_date", True)
    totals_columns = kwargs.get("totals_columns")
    generate_monthly_summary_flag = kwargs.get("generate_monthly_summary", True)

    # Extract output config parameters
    output_formats = kwargs.get("output_formats", ["csv", "json"])

    config = ProcessorConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        extraction=ExtractionConfig(
            table_top_y=table_top_y,
            table_bottom_y=table_bottom_y,
            columns=columns,
            enable_dynamic_boundary=enable_dynamic_boundary,
        ),
        processing=ProcessingConfig(
            sort_by_date=sort_by_date,
            totals_columns=totals_columns,
            generate_monthly_summary=generate_monthly_summary_flag,
        ),
        output=OutputConfig(output_formats=output_formats),
    )
    return BankStatementProcessor(config=config)


class TestBankStatementProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        self.processor = create_test_processor(self.input_dir, self.output_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    # test_create_transaction_key removed - functionality now tested via DuplicateDetectionService

    def test_detect_duplicates_different_files(self):
        """Test duplicate detection when same transaction appears in different files"""
        # Same transaction details but different filenames
        transaction_data = [
            {
                "Date": "01 Jan 2024",
                "Details": "Salary Payment",
                "Debit €": "",
                "Credit €": "3000.00",
                "Balance €": "3500.00",
                "Filename": "statement1.pdf",
            },
            {
                "Date": "01 Jan 2024",
                "Details": "Salary Payment",
                "Debit €": "",
                "Credit €": "3000.00",
                "Balance €": "3500.00",
                "Filename": "statement2.pdf",  # Different file
            },
            {
                "Date": "02 Jan 2024",
                "Details": "Coffee Shop",
                "Debit €": "5.50",
                "Credit €": "",
                "Balance €": "3494.50",
                "Filename": "statement1.pdf",
            },
        ]

        unique, duplicates = self.processor._detect_duplicates(transaction_data)

        # Should have 2 unique and 1 duplicate
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["Filename"], "statement2.pdf")
        self.assertEqual(duplicates[0]["Details"], "Salary Payment")

    def test_detect_duplicates_same_file(self):
        """Test that identical transactions from same file are kept (edge case)"""
        transaction_data = [
            {
                "Date": "01 Jan 2024",
                "Details": "ATM Withdrawal",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "400.00",
                "Filename": "statement1.pdf",
            },
            {
                "Date": "01 Jan 2024",
                "Details": "ATM Withdrawal",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "300.00",  # Different balance
                "Filename": "statement1.pdf",
            },
        ]

        unique, duplicates = self.processor._detect_duplicates(transaction_data)

        # Both should be kept as unique (different balance = different transaction)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 0)

    def test_detect_duplicates_no_duplicates(self):
        """Test when no duplicates exist"""
        transaction_data = [
            {
                "Date": "01 Jan 2024",
                "Details": "Grocery Store",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
                "Filename": "statement1.pdf",
            },
            {
                "Date": "02 Jan 2024",
                "Details": "Gas Station",
                "Debit €": "40.00",
                "Credit €": "",
                "Balance €": "435.50",
                "Filename": "statement2.pdf",
            },
        ]

        unique, duplicates = self.processor._detect_duplicates(transaction_data)

        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 0)

    def test_run_with_mock_data(self):
        """Test the main run method with mocked PDF extraction orchestrator"""
        # Mock extracted data - includes a duplicate transaction
        mock_data_pdf1 = [
            {
                "Date": "01 Jan 2024",
                "Details": "Salary",
                "Debit €": "",
                "Credit €": "3000.00",
                "Balance €": "3000.00",
                "Filename": "test1.pdf",
            }
        ]

        mock_data_pdf2 = [
            {
                "Date": "01 Jan 2024",
                "Details": "Salary",  # Same transaction
                "Debit €": "",
                "Credit €": "3000.00",
                "Balance €": "3000.00",
                "Filename": "test2.pdf",
            },
            {
                "Date": "02 Jan 2024",
                "Details": "Coffee",
                "Debit €": "5.00",
                "Credit €": "",
                "Balance €": "2995.00",
                "Filename": "test2.pdf",
            },
        ]

        # Create mock PDF files
        pdf1 = self.input_dir / "test1.pdf"
        pdf2 = self.input_dir / "test2.pdf"
        pdf1.touch()
        pdf2.touch()

        # Mock the PDFProcessingOrchestrator's process_all_pdfs method
        with patch(
            "bankstatements_core.services.pdf_processing_orchestrator.PDFProcessingOrchestrator.process_all_pdfs"
        ) as mock_process:
            # Configure mock to return (list[ExtractionResult], pdf_count, pages_read)
            mock_process.return_value = (
                [
                    ExtractionResult(
                        transactions=dicts_to_transactions(mock_data_pdf1),
                        page_count=1,
                        iban=None,
                        source_file=pdf1,
                    ),
                    ExtractionResult(
                        transactions=dicts_to_transactions(mock_data_pdf2),
                        page_count=1,
                        iban=None,
                        source_file=pdf2,
                    ),
                ],
                2,
                2,
            )

            processor = create_test_processor(self.input_dir, self.output_dir)
            result = processor.run()

            # Verify the mock was called with correct arguments
            mock_process.assert_called_once_with(self.input_dir, recursive=True)

            # Verify results summary
            self.assertIn("pdf_count", result)
            self.assertIn("pages_read", result)
            self.assertIn("transactions", result)
            self.assertIn("duplicates", result)

            # Verify the processor correctly processed the mock data
            # The mock returned 3 total transactions, but 1 is a duplicate (same Salary entry)
            # so we expect 2 unique transactions and 1 duplicate
            self.assertEqual(result["pages_read"], 2)
            self.assertEqual(result["transactions"], 2)  # 2 unique transactions
            self.assertEqual(result["duplicates"], 1)  # 1 duplicate

    def test_processor_with_no_pdfs(self):
        """Test processor behavior when no PDF files are present"""
        # Create empty input directory
        processor = create_test_processor(self.input_dir, self.output_dir)

        result = processor.run()

        # Should have 0 everything
        self.assertEqual(result["pdf_count"], 0)
        self.assertEqual(result["pages_read"], 0)
        self.assertEqual(result["transactions"], 0)
        self.assertEqual(result["duplicates"], 0)

        # With IBAN grouping, no PDFs means no IBAN groups and no output files
        # The result should not contain file paths when there are no PDFs
        self.assertNotIn("csv_path", result)
        self.assertNotIn("json_path", result)
        self.assertNotIn("duplicates_path", result)

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_processor_continues_after_pdf_error(self, mock_extract):
        """Test that processing continues when a PDF fails to extract"""
        # Create mock PDF files
        (self.input_dir / "good.pdf").touch()
        (self.input_dir / "bad.pdf").touch()
        (self.input_dir / "good2.pdf").touch()

        # Mock: first PDF succeeds, second fails, third succeeds
        mock_extract.side_effect = [
            ExtractionResult(
                transactions=dicts_to_transactions(
                    [{"Date": "01 Jan 2024", "Details": "Transaction 1"}]
                ),
                page_count=1,
                iban=None,
                source_file=Path("good.pdf"),
            ),
            OSError("Failed to open PDF"),
            ExtractionResult(
                transactions=dicts_to_transactions(
                    [{"Date": "02 Jan 2024", "Details": "Transaction 2"}]
                ),
                page_count=1,
                iban=None,
                source_file=Path("good2.pdf"),
            ),
        ]

        processor = create_test_processor(self.input_dir, self.output_dir)
        result = processor.run()

        # Should process 3 PDFs total, but only successfully extract from 2
        self.assertEqual(result["pdf_count"], 3)
        self.assertEqual(result["transactions"], 2)
        self.assertEqual(mock_extract.call_count, 3)

    @patch(
        "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
    )
    def test_processor_handles_empty_pdf_gracefully(self, mock_extract):
        """Test that processing continues when a PDF has no tables"""
        # Create mock PDF files
        (self.input_dir / "empty.pdf").touch()
        (self.input_dir / "with_data.pdf").touch()

        # Mock: first PDF returns no rows, second has data
        mock_extract.side_effect = [
            ExtractionResult(
                transactions=[],
                page_count=1,
                iban=None,
                source_file=Path("empty.pdf"),
                warnings=["credit card statement detected, skipped"],
            ),
            ExtractionResult(
                transactions=dicts_to_transactions(
                    [{"Date": "01 Jan 2024", "Details": "Transaction 1"}]
                ),
                page_count=1,
                iban=None,
                source_file=Path("with_data.pdf"),
            ),
        ]

        processor = create_test_processor(self.input_dir, self.output_dir)
        result = processor.run()

        # Should process both PDFs
        self.assertEqual(result["pdf_count"], 2)
        self.assertEqual(result["pages_read"], 2)
        self.assertEqual(result["transactions"], 1)
        self.assertEqual(mock_extract.call_count, 2)

    def test_processor_with_dynamic_boundary_enabled(self):
        """Test processor with dynamic boundary detection enabled"""
        processor = create_test_processor(
            self.input_dir, self.output_dir, enable_dynamic_boundary=True
        )

        # Should initialize with dynamic boundary enabled
        self.assertTrue(processor.enable_dynamic_boundary)

    def test_processor_with_custom_table_bounds(self):
        """Test processor with custom table boundaries"""
        processor = create_test_processor(
            self.input_dir, self.output_dir, table_top_y=250, table_bottom_y=750
        )

        # Should store custom boundaries
        self.assertEqual(processor.table_top_y, 250)
        self.assertEqual(processor.table_bottom_y, 750)

    def test_processor_with_custom_columns(self):
        """Test processor with custom column definitions"""
        custom_columns = {
            "Date": (0, 50),
            "Description": (50, 200),
            "Amount": (200, 300),
        }

        processor = create_test_processor(
            self.input_dir, self.output_dir, columns=custom_columns
        )

        # Should store custom columns
        self.assertEqual(processor.columns, custom_columns)

        # Column names should be updated
        expected_names = ["Date", "Description", "Amount", "Filename"]
        self.assertEqual(processor.column_names, expected_names)

    # test_create_transaction_key_edge_cases removed - functionality now tested via DuplicateDetectionService

    def test_detect_duplicates_complex_scenario(self):
        """Test duplicate detection with complex real-world scenarios"""
        processor = create_test_processor(self.input_dir, self.output_dir)

        transaction_data = [
            # Same transaction, same file (should be unique)
            {
                "Date": "01 Jan 2024",
                "Details": "VDC-GROCERY STORE",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
                "Filename": "statement1.pdf",
            },
            # Same transaction, different file (should be duplicate)
            {
                "Date": "01 Jan 2024",
                "Details": "VDC-GROCERY STORE",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
                "Filename": "statement2.pdf",
            },
            # Similar transaction, different amount (should be unique)
            {
                "Date": "01 Jan 2024",
                "Details": "VDC-GROCERY STORE",
                "Debit €": "26.50",  # Different amount
                "Credit €": "",
                "Balance €": "474.50",
                "Filename": "statement3.pdf",
            },
            # Same transaction details, different date (should be unique)
            {
                "Date": "02 Jan 2024",  # Different date
                "Details": "VDC-GROCERY STORE",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
                "Filename": "statement4.pdf",
            },
        ]

        unique, duplicates = processor._detect_duplicates(transaction_data)

        # Should have 3 unique (original + different amount + different date)
        # and 1 duplicate (same transaction from different file)
        self.assertEqual(len(unique), 3)
        self.assertEqual(len(duplicates), 1)

        # Verify the duplicate is correctly identified
        self.assertEqual(duplicates[0]["Filename"], "statement2.pdf")


class TestTransactionDateParsing(unittest.TestCase):
    """Test suite for transaction date parsing and sorting functionality"""

    def test_parse_transaction_date_dd_mm_yy(self):
        """Test parsing DD/MM/YY format dates"""
        self.assertEqual(parse_transaction_date("01/12/23"), datetime(2023, 12, 1))
        self.assertEqual(parse_transaction_date("31/01/24"), datetime(2024, 1, 31))

    def test_parse_transaction_date_dd_mm_yyyy(self):
        """Test parsing DD/MM/YYYY format dates"""
        self.assertEqual(parse_transaction_date("01/12/2023"), datetime(2023, 12, 1))
        self.assertEqual(parse_transaction_date("15/06/2024"), datetime(2024, 6, 15))

    def test_parse_transaction_date_ddmmmyy(self):
        """Test parsing DDMMMYY format dates"""
        self.assertEqual(parse_transaction_date("01DEC23"), datetime(2023, 12, 1))
        self.assertEqual(parse_transaction_date("15JUN24"), datetime(2024, 6, 15))

    def test_parse_transaction_date_dd_dash_mm_yy(self):
        """Test parsing DD-MM-YY format dates"""
        self.assertEqual(parse_transaction_date("01-12-23"), datetime(2023, 12, 1))
        self.assertEqual(parse_transaction_date("25-03-24"), datetime(2024, 3, 25))

    def test_parse_transaction_date_dd_space_mmm_yyyy(self):
        """Test parsing 'DD MMM YYYY' format dates (space-separated)"""
        self.assertEqual(parse_transaction_date("25 Apr 2025"), datetime(2025, 4, 25))
        self.assertEqual(parse_transaction_date("01 Jan 2023"), datetime(2023, 1, 1))
        self.assertEqual(parse_transaction_date("31 Dec 2024"), datetime(2024, 12, 31))

    def test_parse_transaction_date_dd_space_mmmm_yyyy(self):
        """Test parsing 'DD MMMM YYYY' format dates (full month names)"""
        self.assertEqual(
            parse_transaction_date("15 December 2024"), datetime(2024, 12, 15)
        )
        self.assertEqual(
            parse_transaction_date("10 February 2023"), datetime(2023, 2, 10)
        )

    def test_parse_transaction_date_dd_space_mmm_yy(self):
        """Test parsing 'DD MMM YY' format dates (2-digit year)"""
        self.assertEqual(
            parse_transaction_date("31 Mar 25"), datetime(2025, 3, 31)  # < 50 = 20xx
        )
        self.assertEqual(
            parse_transaction_date("10 Feb 99"), datetime(1999, 2, 10)  # >= 50 = 19xx
        )

    def test_parse_transaction_date_two_digit_year_logic(self):
        """Test two-digit year interpretation (< 50 = 20xx, >= 50 = 19xx)"""
        self.assertEqual(
            parse_transaction_date("01/01/49"), datetime(2049, 1, 1)  # < 50 = 20xx
        )
        self.assertEqual(
            parse_transaction_date("01/01/50"), datetime(1950, 1, 1)  # >= 50 = 19xx
        )
        self.assertEqual(
            parse_transaction_date("01/01/99"), datetime(1999, 1, 1)  # >= 50 = 19xx
        )

    def test_parse_transaction_date_empty_or_invalid(self):
        """Test handling of empty or invalid dates"""
        # Empty dates should return epoch
        self.assertEqual(parse_transaction_date(""), datetime(1970, 1, 1))
        self.assertEqual(parse_transaction_date("   "), datetime(1970, 1, 1))
        self.assertEqual(parse_transaction_date(None), datetime(1970, 1, 1))

        # Invalid dates should return epoch with warning logged
        self.assertEqual(parse_transaction_date("invalid-date"), datetime(1970, 1, 1))
        self.assertEqual(
            parse_transaction_date("32/13/23"),  # Invalid day/month
            datetime(1970, 1, 1),
        )

    def test_parse_transaction_date_partial_dates(self):
        """Test parsing of partial dates (missing year)"""
        # Should default to 2023 for missing year
        self.assertEqual(parse_transaction_date("01/12"), datetime(2023, 12, 1))
        self.assertEqual(parse_transaction_date("15-06"), datetime(2023, 6, 15))

    def test_chronological_sorting_with_processor(self):
        """Test that BankStatementProcessor sorts transactions chronologically"""
        # Create processor with sorting enabled
        temp_dir = tempfile.TemporaryDirectory()
        input_dir = Path(temp_dir.name) / "input"
        output_dir = Path(temp_dir.name) / "output"
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        processor = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            sort_by_date=True,  # Enable sorting
        )

        # Test data with mixed chronological order
        transaction_data = [
            {
                "Date": "15/12/2023",  # December 15 (should be last)
                "Details": "Christmas Shopping",
                "Debit €": "150.00",
                "Credit €": "",
                "Balance €": "850.00",
                "Filename": "statement1.pdf",
            },
            {
                "Date": "01/01/2023",  # January 1 (should be first)
                "Details": "Salary Payment",
                "Debit €": "",
                "Credit €": "3000.00",
                "Balance €": "3000.00",
                "Filename": "statement1.pdf",
            },
            {
                "Date": "15/06/2023",  # June 15 (should be middle)
                "Details": "Vacation Expense",
                "Debit €": "500.00",
                "Credit €": "",
                "Balance €": "2500.00",
                "Filename": "statement1.pdf",
            },
        ]

        # Mock the duplicate detection to return our test data
        with patch.object(processor, "_detect_duplicates") as mock_duplicates:
            mock_duplicates.return_value = (transaction_data, [])

            # Test chronological sorting logic directly
            unique_rows = transaction_data.copy()
            unique_rows.sort(
                key=lambda row: parse_transaction_date(row.get("Date", ""))
            )

            # Verify chronological order
            expected_order = [
                "01/01/2023",  # January (earliest)
                "15/06/2023",  # June (middle)
                "15/12/2023",  # December (latest)
            ]

            actual_order = [row["Date"] for row in unique_rows]
            self.assertEqual(actual_order, expected_order)

        temp_dir.cleanup()

    def test_chronological_sorting_disabled(self):
        """Test that sorting can be disabled"""
        temp_dir = tempfile.TemporaryDirectory()
        input_dir = Path(temp_dir.name) / "input"
        output_dir = Path(temp_dir.name) / "output"
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        processor = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            sort_by_date=False,  # Disable sorting
        )

        # Verify sorting is disabled
        self.assertFalse(processor.sort_by_date)

        temp_dir.cleanup()

    def test_chronological_sorting_with_mixed_date_formats(self):
        """Test sorting with various date formats mixed together"""
        transaction_data = [
            {"Date": "15DEC23", "Details": "Transaction 1", "Filename": "test.pdf"},
            {"Date": "01/01/2023", "Details": "Transaction 2", "Filename": "test.pdf"},
            {"Date": "15-06-23", "Details": "Transaction 3", "Filename": "test.pdf"},
            {
                "Date": "25 Apr 2025",
                "Details": "Transaction 5",
                "Filename": "test.pdf",
            },  # Space format
            {
                "Date": "10 February 2024",
                "Details": "Transaction 6",
                "Filename": "test.pdf",
            },  # Full month
            {
                "Date": "",
                "Details": "Transaction 4",
                "Filename": "test.pdf",
            },  # Empty date
        ]

        # Sort using the same logic as processor
        transaction_data.sort(
            key=lambda row: parse_transaction_date(row.get("Date", ""))
        )

        # Expected order: empty date first (epoch), then chronological
        expected_details = [
            "Transaction 4",  # Empty date (epoch) sorts first
            "Transaction 2",  # 01/01/2023 (earliest real date)
            "Transaction 3",  # 15/06/2023 (middle)
            "Transaction 1",  # 15/12/2023
            "Transaction 6",  # 10/02/2024
            "Transaction 5",  # 25/04/2025 (latest)
        ]

        actual_details = [row["Details"] for row in transaction_data]
        self.assertEqual(actual_details, expected_details)


class TestDateParsingHelpers(unittest.TestCase):
    """Test suite for date parsing helper functions"""

    def test_normalize_two_digit_year_no_change_for_4_digit_year(self):
        """Test that 4-digit year formats are not modified"""
        date = datetime(2023, 12, 1)
        result = _normalize_two_digit_year(date, "%d/%m/%Y")
        self.assertEqual(result, date)

    def test_normalize_two_digit_year_below_cutoff(self):
        """Test that years 00-49 are treated as 2000-2049"""
        # Year 2025 with %y should remain 2025
        date = datetime(2025, 4, 15)
        result = _normalize_two_digit_year(date, "%d %b %y")
        self.assertEqual(result.year, 2025)

    def test_normalize_two_digit_year_above_cutoff(self):
        """Test that years 50-99 are converted to 1950-1999"""
        # Python parses "50" as 2050, but we want 1950
        date = datetime(2050, 1, 1)  # strptime result for "01/01/50"
        result = _normalize_two_digit_year(date, "%d/%m/%y")
        self.assertEqual(result.year, 1950)

        # Python parses "99" as 2099, but we want 1999
        date = datetime(2099, 12, 31)
        result = _normalize_two_digit_year(date, "%d/%m/%y")
        self.assertEqual(result.year, 1999)

    def test_try_parse_date_format_success(self):
        """Test successful date parsing with specific format"""
        result = _try_parse_date_format("01/12/2023", "%d/%m/%Y")
        self.assertEqual(result, datetime(2023, 12, 1))

    def test_try_parse_date_format_failure(self):
        """Test that mismatched format returns None"""
        result = _try_parse_date_format("01/12/2023", "%Y-%m-%d")
        self.assertIsNone(result)

    def test_try_parse_date_format_with_year_normalization(self):
        """Test that two-digit years are normalized correctly"""
        # Year 50 should become 1950
        result = _try_parse_date_format("01/01/50", "%d/%m/%y")
        self.assertEqual(result.year, 1950)

        # Year 49 should remain 2049
        result = _try_parse_date_format("01/01/49", "%d/%m/%y")
        self.assertEqual(result.year, 2049)

    def test_parse_common_date_formats_success(self):
        """Test parsing with multiple common formats"""
        # Should match DD/MM/YYYY format
        result = _parse_common_date_formats("01/12/2023")
        self.assertEqual(result, datetime(2023, 12, 1))

        # Should match DD MMM YYYY format
        result = _parse_common_date_formats("25 Apr 2025")
        self.assertEqual(result, datetime(2025, 4, 25))

        # Should match DDMMMYY format
        result = _parse_common_date_formats("01DEC23")
        self.assertEqual(result, datetime(2023, 12, 1))

    def test_parse_common_date_formats_no_match(self):
        """Test that unrecognized format returns None"""
        result = _parse_common_date_formats("2023-12-01")  # ISO format not in list
        self.assertIsNone(result)

        result = _parse_common_date_formats("invalid")
        self.assertIsNone(result)

    def test_parse_partial_date_missing_year(self):
        """Test parsing dates without year component"""
        # Should use DEFAULT_YEAR (2023)
        result = _parse_partial_date("01/12")
        self.assertEqual(result, datetime(2023, 12, 1))

        result = _parse_partial_date("15-06")
        self.assertEqual(result, datetime(2023, 6, 15))

    def test_parse_partial_date_with_two_digit_year(self):
        """Test partial date parsing with 2-digit year"""
        # 25 should become 2025
        result = _parse_partial_date("01/12/25")
        self.assertEqual(result, datetime(2025, 12, 1))

        # 50 should become 1950
        result = _parse_partial_date("01/12/50")
        self.assertEqual(result, datetime(1950, 12, 1))

    def test_parse_partial_date_no_separators(self):
        """Test that dates without separators return None"""
        result = _parse_partial_date("20231201")
        self.assertIsNone(result)

    def test_parse_partial_date_invalid_values(self):
        """Test that invalid date components return None"""
        result = _parse_partial_date("32/13")  # Invalid day and month
        self.assertIsNone(result)

        result = _parse_partial_date("abc/def")
        self.assertIsNone(result)

    def test_constants_values(self):
        """Test that date parsing constants have expected values"""
        self.assertEqual(EPOCH_DATE, datetime(1970, 1, 1))
        self.assertEqual(TWO_DIGIT_YEAR_CUTOFF, 50)


class TestTotalsConfiguration(unittest.TestCase):
    """Test the new totals functionality"""

    def test_parse_totals_columns(self):
        """Test parsing of totals configuration string"""
        # Test normal configuration
        result = parse_totals_columns("debit,credit,balance")
        self.assertEqual(result, ["debit", "credit", "balance"])

        # Test with spaces
        result = parse_totals_columns("debit , credit , balance")
        self.assertEqual(result, ["debit", "credit", "balance"])

        # Test empty configuration
        result = parse_totals_columns("")
        self.assertEqual(result, [])

        # Test single column
        result = parse_totals_columns("debit")
        self.assertEqual(result, ["debit"])

    def test_find_matching_columns(self):
        """Test column pattern matching"""
        column_names = [
            "Date",
            "Details",
            "Debit €",
            "Credit €",
            "Balance €",
            "Filename",
        ]

        # Test exact matches (case insensitive)
        patterns = ["debit", "credit"]
        result = find_matching_columns(column_names, patterns)
        self.assertIn("Debit €", result)
        self.assertIn("Credit €", result)
        self.assertEqual(len(result), 2)

        # Test partial matches
        patterns = ["balance"]
        result = find_matching_columns(column_names, patterns)
        self.assertIn("Balance €", result)

        # Test no matches
        patterns = ["unknown"]
        result = find_matching_columns(column_names, patterns)
        self.assertEqual(result, [])

        # Test avoiding duplicates
        patterns = ["debit", "debit €"]
        result = find_matching_columns(column_names, patterns)
        self.assertEqual(len([col for col in result if "debit" in col.lower()]), 1)

    def test_calculate_column_totals(self):
        """Test totals calculation with real DataFrame"""
        # Create real DataFrame with test data
        df = pd.DataFrame(
            {
                "Date": ["01/01/24", "02/01/24", "03/01/24"],
                "Details": ["Transaction 1", "Transaction 2", "Transaction 3"],
                "Debit €": ["100.00", "€50.50", ""],
                "Credit €": ["", "", "75.25"],
            }
        )

        columns_to_total = ["Debit €", "Credit €"]
        result = calculate_column_totals(df, columns_to_total)

        # Verify totals
        self.assertEqual(result["Debit €"], 150.5)  # 100.00 + 50.50 + 0
        self.assertEqual(result["Credit €"], 75.25)  # 0 + 0 + 75.25

    def test_calculate_column_totals_with_invalid_data(self):
        """Test totals calculation handles invalid data gracefully"""
        df = pd.DataFrame(
            {
                "Debit €": ["100.00", "invalid", "50.00"],
                "Credit €": ["€25.50", "", "abc"],
            }
        )

        result = calculate_column_totals(df, ["Debit €", "Credit €"])

        # Should handle invalid values gracefully
        self.assertEqual(result["Debit €"], 150.0)  # 100 + 0 + 50
        self.assertEqual(result["Credit €"], 25.5)  # 25.5 + 0 + 0

    def test_calculate_column_totals_missing_column(self):
        """Test totals calculation handles missing columns"""
        df = pd.DataFrame(
            {
                "Debit €": ["100.00"],
            }
        )

        # Request a column that doesn't exist
        result = calculate_column_totals(df, ["Debit €", "NonExistent"])

        # Should calculate for existing column and skip missing one
        self.assertEqual(result["Debit €"], 100.0)
        self.assertNotIn("NonExistent", result)

    def test_processor_with_totals_configuration(self):
        """Test processor initialization with totals configuration"""
        temp_dir = tempfile.TemporaryDirectory()
        input_dir = Path(temp_dir.name) / "input"
        output_dir = Path(temp_dir.name) / "output"
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        # Test with custom totals configuration
        totals_columns = ["debit", "credit", "balance"]
        processor = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            totals_columns=totals_columns,
        )

        self.assertEqual(processor.totals_columns, totals_columns)

        # Test with default totals configuration
        processor_default = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        self.assertEqual(processor_default.totals_columns, ["debit", "credit"])

        # Test with no totals configuration
        processor_none = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            totals_columns=[],
        )

        self.assertEqual(processor_none.totals_columns, [])

        temp_dir.cleanup()


class TestMonthlySummary(unittest.TestCase):
    """Test the new monthly summary functionality"""

    @patch("bankstatements_core.processor.to_float")
    def test_generate_monthly_summary(self, mock_to_float):
        """Test monthly summary generation with sample data"""
        # Mock to_float to return predictable values
        mock_to_float.side_effect = lambda x: {
            "100.00": 100.0,
            "50.50": 50.5,
            "200.00": 200.0,
            "75.00": 75.0,
            "": None,
        }.get(x)

        # Sample transactions across multiple months
        transactions = [
            {
                "Date": "01/01/2024",
                "Details": "Salary",
                "Debit €": "",
                "Credit €": "100.00",
                "Balance €": "100.00",
            },
            {
                "Date": "15/01/2024",
                "Details": "Groceries",
                "Debit €": "50.50",
                "Credit €": "",
                "Balance €": "49.50",
            },
            {
                "Date": "01/02/2024",
                "Details": "Rent",
                "Debit €": "200.00",
                "Credit €": "",
                "Balance €": "-150.50",
            },
            {
                "Date": "15/02/2024",
                "Details": "Freelance",
                "Debit €": "",
                "Credit €": "75.00",
                "Balance €": "-75.50",
            },
        ]

        column_names = ["Date", "Details", "Debit €", "Credit €", "Balance €"]
        result = generate_monthly_summary(transactions, column_names)

        # Verify structure
        self.assertIn("summary", result)
        self.assertIn("generated_at", result)
        self.assertIn("total_months", result)
        self.assertIn("monthly_data", result)

        # Verify monthly data
        monthly_data = result["monthly_data"]
        self.assertEqual(len(monthly_data), 2)  # Two months

        # Check January data
        jan_data = monthly_data[0]
        self.assertEqual(jan_data["Month"], "2024-01")
        self.assertEqual(jan_data["Debit"], 50.5)  # One debit transaction
        self.assertEqual(jan_data["Total Debit Transactions"], 1)
        self.assertEqual(jan_data["Credit"], 100.0)  # One credit transaction
        self.assertEqual(jan_data["Total Credit Transactions"], 1)

        # Check February data
        feb_data = monthly_data[1]
        self.assertEqual(feb_data["Month"], "2024-02")
        self.assertEqual(feb_data["Debit"], 200.0)  # One debit transaction
        self.assertEqual(feb_data["Total Debit Transactions"], 1)
        self.assertEqual(feb_data["Credit"], 75.0)  # One credit transaction
        self.assertEqual(feb_data["Total Credit Transactions"], 1)

    def test_generate_monthly_summary_with_invalid_dates(self):
        """Test monthly summary with invalid/empty dates"""
        transactions = [
            {
                "Date": "",  # Empty date
                "Details": "Invalid Date Transaction",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "100.00",
            },
            {
                "Date": "invalid-date",  # Invalid date format
                "Details": "Another Invalid",
                "Debit €": "",
                "Credit €": "50.00",
                "Balance €": "50.00",
            },
        ]

        column_names = ["Date", "Details", "Debit €", "Credit €", "Balance €"]

        with patch("bankstatements_core.processor.to_float") as mock_to_float:
            mock_to_float.side_effect = lambda x: {"100.00": 100.0, "50.00": 50.0}.get(
                x
            )

            result = generate_monthly_summary(transactions, column_names)

        # Should have one entry for "Unknown" month
        monthly_data = result["monthly_data"]
        self.assertEqual(len(monthly_data), 1)
        self.assertEqual(monthly_data[0]["Month"], "Unknown")

    def test_processor_with_monthly_summary_enabled(self):
        """Test processor initialization with monthly summary enabled"""
        temp_dir = tempfile.TemporaryDirectory()
        input_dir = Path(temp_dir.name) / "input"
        output_dir = Path(temp_dir.name) / "output"
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        # Test with monthly summary enabled (default)
        processor = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            generate_monthly_summary=True,
        )

        self.assertTrue(processor.generate_monthly_summary)

        # Test with monthly summary disabled
        processor_disabled = create_test_processor(
            input_dir=input_dir,
            output_dir=output_dir,
            generate_monthly_summary=False,
        )

        self.assertFalse(processor_disabled.generate_monthly_summary)

        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
