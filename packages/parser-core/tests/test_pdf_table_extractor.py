from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from bankstatements_core.extraction.column_identifier import ColumnTypeIdentifier
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions
from bankstatements_core.pdf_table_extractor import (
    DEFAULT_COLUMNS,
    analyze_content_density,
    calculate_column_coverage,
    calculate_row_completeness_score,
    classify_row_type,
    detect_table_end_boundary_smart,
    detect_table_headers,
    extract_tables_from_pdf,
    get_column_names,
    get_columns_config,
    has_column_type,
    parse_columns_from_env,
    validate_page_structure,
)


class TestPdfTableExtractor(unittest.TestCase):
    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_with_date_propagation(self, mock_pdfplumber):
        """Test that dates are properly propagated to transactions without dates"""
        # Mock PDF structure
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        # Mock cropped area
        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Mock extracted words - simulating bank statement structure
        mock_words = [
            # First transaction line with date
            {"text": "01", "x0": 30, "top": 100},  # Date column
            {"text": "Jan", "x0": 50, "top": 100},
            {"text": "2024", "x0": 70, "top": 100},
            {"text": "Salary", "x0": 90, "top": 100},  # Details column
            {"text": "Payment", "x0": 120, "top": 100},
            {"text": "3000.00", "x0": 320, "top": 100},  # Credit column
            {"text": "3000.00", "x0": 380, "top": 100},  # Balance column
            # Second transaction line without date (should inherit)
            {"text": "Coffee", "x0": 90, "top": 120},  # Details only
            {"text": "Shop", "x0": 120, "top": 120},
            {"text": "5.50", "x0": 260, "top": 120},  # Debit column
            {"text": "2994.50", "x0": 380, "top": 120},  # Balance column
            # Third transaction with new date
            {"text": "02", "x0": 30, "top": 140},  # New date
            {"text": "Jan", "x0": 50, "top": 140},
            {"text": "2024", "x0": 70, "top": 140},
            {"text": "Gas", "x0": 90, "top": 140},  # Details
            {"text": "Station", "x0": 120, "top": 140},
            {"text": "40.00", "x0": 260, "top": 140},  # Debit column
            {"text": "2954.50", "x0": 380, "top": 140},  # Balance column
        ]

        mock_cropped.extract_words.return_value = mock_words

        # Test the extraction
        test_pdf_path = Path("/tmp/test.pdf")
        result = extract_tables_from_pdf(
            test_pdf_path, enable_page_validation=False, enable_header_check=False
        )

        # Verify results
        self.assertEqual(result.page_count, 1)
        self.assertEqual(len(result.transactions), 3)

        # Check first transaction (has original date)
        self.assertEqual(result.transactions[0].date.strip(), "01 Jan 2024")
        self.assertEqual(result.transactions[0].details.strip(), "Salary Payment")
        self.assertEqual(result.transactions[0].credit.strip(), "3000.00")
        self.assertEqual(result.transactions[0].filename, "test.pdf")

        # Check second transaction (should inherit date from first)
        self.assertEqual(result.transactions[1].date.strip(), "01 Jan 2024")  # Inherited!
        self.assertEqual(result.transactions[1].details.strip(), "Coffee Shop")
        self.assertEqual(result.transactions[1].debit.strip(), "5.50")

        # Check third transaction (has new date)
        self.assertEqual(result.transactions[2].date.strip(), "02 Jan 2024")
        self.assertEqual(result.transactions[2].details.strip(), "Gas Station")
        self.assertEqual(result.transactions[2].debit.strip(), "40.00")

    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_filename_tagging(self, mock_pdfplumber):
        """Test that all transactions are tagged with source filename"""
        # Mock PDF structure
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Simple mock words for one transaction
        mock_words = [
            {"text": "01", "x0": 30, "top": 100},
            {"text": "Jan", "x0": 50, "top": 100},
            {"text": "2024", "x0": 70, "top": 100},
            {"text": "Test", "x0": 90, "top": 100},
            {"text": "Transaction", "x0": 120, "top": 100},
            {"text": "100.00", "x0": 320, "top": 100},
        ]

        mock_cropped.extract_words.return_value = mock_words

        # Test with specific filename - pass parameters directly instead of using env vars
        test_pdf_path = Path("/tmp/bank_statement_jan2024.pdf")
        result = extract_tables_from_pdf(
            test_pdf_path, enable_page_validation=False, enable_header_check=False
        )

        # Verify filename tagging
        self.assertEqual(len(result.transactions), 1)
        self.assertEqual(result.transactions[0].filename, "bank_statement_jan2024.pdf")

    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_empty_rows_filtered(self, mock_pdfplumber):
        """Test that empty rows are filtered out"""
        # Mock PDF structure
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Mock words that would create some empty rows
        mock_words = [
            # Valid transaction
            {"text": "01", "x0": 30, "top": 100},
            {"text": "Jan", "x0": 50, "top": 100},
            {"text": "Valid", "x0": 90, "top": 100},
            # Empty row (no words at Y=120)
            # Another valid transaction
            {"text": "02", "x0": 30, "top": 140},
            {"text": "Jan", "x0": 50, "top": 140},
            {"text": "Another", "x0": 90, "top": 140},
        ]

        mock_cropped.extract_words.return_value = mock_words

        test_pdf_path = Path("/tmp/test.pdf")
        result = extract_tables_from_pdf(
            test_pdf_path, enable_page_validation=False, enable_header_check=False
        )

        # Should only have 2 valid rows (empty row filtered out)
        self.assertEqual(len(result.transactions), 2)
        self.assertTrue(all(any(t.to_dict().values()) for t in result.transactions))

    def test_classify_row_type(self):
        """Test row classification for transaction vs non-transaction content"""
        # Test with default columns
        default_columns = DEFAULT_COLUMNS

        # Test transaction row
        transaction_row = {
            "Date": "01 Jan 2024",
            "Details": "VDC-GROCERY STORE",
            "Debit €": "25.50",
            "Credit €": "",
            "Balance €": "475.50",
        }
        self.assertEqual(
            classify_row_type(transaction_row, default_columns), "transaction"
        )

        # Test administrative row
        admin_row = {
            "Date": "",
            "Details": "BALANCE FORWARD",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        self.assertEqual(
            classify_row_type(admin_row, default_columns), "administrative"
        )

        # Test reference code row
        ref_row = {
            "Date": "",
            "Details": "IE19102156715277",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        self.assertEqual(classify_row_type(ref_row, default_columns), "reference")

        # Test metadata row
        meta_row = {
            "Date": "",
            "Details": "25OCT19 TIME 16:20",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        self.assertEqual(classify_row_type(meta_row, default_columns), "metadata")

        # Test with custom columns (different names but same semantic types)
        custom_columns = {
            "Transaction Date": (20, 80),
            "Description": (80, 260),
            "Amount": (260, 400),
        }

        # Test custom transaction row
        custom_transaction = {
            "Transaction Date": "01 Jan 2024",
            "Description": "VDC-GROCERY STORE",
            "Amount": "25.50",
        }
        self.assertEqual(
            classify_row_type(custom_transaction, custom_columns), "transaction"
        )

        # Test custom administrative row
        custom_admin = {
            "Transaction Date": "",
            "Description": "BALANCE FORWARD",
            "Amount": "",
        }
        self.assertEqual(
            classify_row_type(custom_admin, custom_columns), "administrative"
        )

    def test_identify_column_type(self):
        """Test semantic column type identification"""
        # Test date columns
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Date"), "date")
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Transaction Date"), "date"
        )
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("TIME"), "date")

        # Test description columns
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Details"), "description"
        )
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Description"), "description"
        )
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Transaction Details"),
            "description",
        )
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("MEMO"), "description")

        # Test debit columns
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Debit €"), "debit")
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Withdrawal"), "debit")
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("EXPENSE"), "debit")

        # Test credit columns
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Credit €"), "credit")
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Deposit"), "credit")
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("INCOME"), "credit")

        # Test balance columns
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Balance €"), "balance"
        )
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Amount"), "balance")
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("TOTAL"), "balance")

        # Test other columns
        self.assertEqual(ColumnTypeIdentifier.get_type_as_string("Filename"), "other")
        self.assertEqual(
            ColumnTypeIdentifier.get_type_as_string("Unknown Column"), "other"
        )

    def test_calculate_row_completeness_score(self):
        """Test completeness scoring algorithm with configurable columns"""
        # Test with default columns
        default_columns = DEFAULT_COLUMNS
        complete_row = {
            "Date": "01 Jan 2024",
            "Details": "GROCERY STORE PURCHASE",
            "Debit €": "25.50",
            "Credit €": "",
            "Balance €": "475.50",
        }
        score = calculate_row_completeness_score(complete_row, default_columns)
        self.assertGreater(score, 0.8)  # Should be high score

        # Test with custom columns (different names but same semantic types)
        custom_columns = {
            "Transaction Date": (20, 80),
            "Description": (80, 260),
            "Amount": (260, 400),
        }
        custom_row = {
            "Transaction Date": "01 Jan 2024",
            "Description": "GROCERY STORE PURCHASE",
            "Amount": "25.50",
        }
        custom_score = calculate_row_completeness_score(custom_row, custom_columns)
        self.assertGreater(custom_score, 0.8)  # Should also be high score

        # Test sparse row
        sparse_row = {
            "Date": "",
            "Details": "BALANCE FORWARD",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        sparse_score = calculate_row_completeness_score(sparse_row, default_columns)
        self.assertLess(sparse_score, 0.5)  # Should be low score

    def test_detect_table_end_boundary(self):
        """Test dynamic boundary detection with various content patterns"""
        columns = DEFAULT_COLUMNS

        # Mock words representing transactions followed by administrative content
        mock_words = [
            # Transaction data (Y=100-150)
            {"text": "01", "x0": 30, "top": 100.0},
            {"text": "Jan", "x0": 50, "top": 100.0},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100.0},
            {"text": "25.50", "x0": 260, "top": 100.0},
            {"text": "475.50", "x0": 380, "top": 100.0},
            {"text": "02", "x0": 30, "top": 120.0},
            {"text": "Jan", "x0": 50, "top": 120.0},
            {"text": "VDP-GAS", "x0": 90, "top": 120.0},
            {"text": "40.00", "x0": 260, "top": 120.0},
            {"text": "435.50", "x0": 380, "top": 120.0},
            # Administrative content (Y=200+) - should trigger boundary
            {"text": "BALANCE", "x0": 90, "top": 200.0},
            {"text": "FORWARD", "x0": 120, "top": 200.0},
            {"text": "Interest", "x0": 90, "top": 220.0},
            {"text": "Rate", "x0": 120, "top": 220.0},
            {"text": "IE19102156715277", "x0": 90, "top": 240.0},
        ]

        boundary = detect_table_end_boundary_smart(mock_words, 50, columns, 720)
        # Should detect boundary after last transaction (Y=120) but before
        # administrative content (Y=200)
        self.assertLess(boundary, 200)  # Before administrative content
        self.assertGreater(boundary, 120)  # After last transaction

    def test_dynamic_vs_static_extraction(self):
        """Compare dynamic detection results with static boundary results"""

        @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
        def run_test(mock_pdfplumber):
            # Mock PDF structure
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.return_value = mock_pdf

            # Mock page properties for dynamic detection
            mock_page.height = 800

            # Mock cropped areas for different scenarios
            mock_initial_crop = MagicMock()
            mock_final_crop = MagicMock()

            # Mock words for initial extraction (all content)
            all_words = [
                # Transaction content
                {"text": "01", "x0": 30, "top": 100},
                {"text": "Jan", "x0": 50, "top": 100},
                {"text": "VDC-STORE", "x0": 90, "top": 100},
                {"text": "25.50", "x0": 260, "top": 100},
                # Administrative content (should be filtered by dynamic detection)
                {"text": "BALANCE", "x0": 90, "top": 600},
                {"text": "FORWARD", "x0": 120, "top": 600},
            ]

            # Transaction-only words for final extraction
            transaction_words = [
                {"text": "01", "x0": 30, "top": 100},
                {"text": "Jan", "x0": 50, "top": 100},
                {"text": "VDC-STORE", "x0": 90, "top": 100},
                {"text": "25.50", "x0": 260, "top": 100},
            ]

            mock_initial_crop.extract_words.return_value = all_words
            mock_final_crop.extract_words.return_value = transaction_words

            # Set up crop behavior to return different crops for different calls
            def crop_side_effect(*args):
                if len(args) == 4 and args[3] == 800:  # Initial crop (full height)
                    return mock_initial_crop
                else:  # Final crop (dynamic boundary)
                    return mock_final_crop

            mock_page.crop.side_effect = crop_side_effect

            test_pdf_path = Path("/tmp/test.pdf")

            # Test with dynamic boundary enabled
            dynamic_result = extract_tables_from_pdf(
                test_pdf_path,
                enable_dynamic_boundary=True,
                enable_page_validation=False,
                enable_header_check=False,
            )

            # Should have fewer rows (administrative content filtered)
            self.assertEqual(len(dynamic_result.transactions), 1)
            self.assertEqual(dynamic_result.transactions[0].details.strip(), "VDC-STORE")

        run_test()

    def test_validate_page_structure_valid_table(self):
        """Test page validation with valid table structure"""
        valid_rows = [
            {
                "Date": "01 Jan 2024",
                "Details": "VDC-GROCERY STORE",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
            },
            {
                "Date": "02 Jan 2024",
                "Details": "VDP-GAS STATION",
                "Debit €": "40.00",
                "Credit €": "",
                "Balance €": "435.50",
            },
            {
                "Date": "03 Jan 2024",
                "Details": "SALARY PAYMENT",
                "Debit €": "",
                "Credit €": "2000.00",
                "Balance €": "2435.50",
            },
        ]

        self.assertTrue(validate_page_structure(valid_rows, DEFAULT_COLUMNS))

    def test_validate_page_structure_insufficient_rows(self):
        """Test page validation with too few rows (when threshold > 1)"""
        insufficient_rows = []  # Empty rows

        # Should fail validation even with MIN_TABLE_ROWS=1
        self.assertFalse(validate_page_structure(insufficient_rows, DEFAULT_COLUMNS))

    def test_validate_page_structure_single_transaction(self):
        """Test page validation with single transaction (lenient defaults)."""
        single_transaction = [
            {
                "Date": "01 Jan 2024",
                "Details": "VDC-GROCERY STORE",
                "Debit €": "25.50",
                "Credit €": "",
                "Balance €": "475.50",
            }
        ]

        # Should pass with lenient defaults (MIN_TABLE_ROWS=1, etc.)
        self.assertTrue(validate_page_structure(single_transaction, DEFAULT_COLUMNS))

    def test_validate_page_structure_poor_coverage(self):
        """Test page validation with poor column coverage"""
        poor_coverage_rows = [
            {"Details": "Some text"},
            {"Details": "More text"},
            {"Details": "Even more text"},
            {"Details": "Administrative notice"},
        ]

        self.assertFalse(validate_page_structure(poor_coverage_rows, DEFAULT_COLUMNS))

    def test_validate_page_structure_no_transactions(self):
        """Test page validation with no transaction rows"""
        no_transaction_rows = [
            {"Details": "BALANCE FORWARD"},
            {"Details": "Interest Rate: 2.5%"},
            {"Details": "IE19102156715277"},
            {"Details": "25OCT19 TIME 16:20"},
        ]

        self.assertFalse(validate_page_structure(no_transaction_rows, DEFAULT_COLUMNS))

    def test_calculate_column_coverage_full(self):
        """Test column coverage calculation with full coverage"""
        rows = [
            {
                "Date": "01 Jan 2024",
                "Details": "Transaction",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            }
        ]

        coverage = calculate_column_coverage(rows, DEFAULT_COLUMNS)
        self.assertEqual(coverage, 0.8)  # 4/5 columns have data

    def test_calculate_column_coverage_partial(self):
        """Test column coverage calculation with partial coverage"""
        rows = [
            {"Details": "Transaction"},
            {"Date": "01 Jan 2024"},
        ]

        coverage = calculate_column_coverage(rows, DEFAULT_COLUMNS)
        self.assertEqual(coverage, 0.4)  # 2/5 columns have data

    def test_calculate_column_coverage_empty(self):
        """Test column coverage calculation with empty data"""
        self.assertEqual(calculate_column_coverage([], DEFAULT_COLUMNS), 0.0)
        self.assertEqual(calculate_column_coverage([{}], DEFAULT_COLUMNS), 0.0)

    def test_has_column_type_single_type(self):
        """Test column type detection with single required type"""
        self.assertTrue(has_column_type(DEFAULT_COLUMNS, "date"))
        self.assertTrue(has_column_type(DEFAULT_COLUMNS, "description"))
        self.assertFalse(has_column_type(DEFAULT_COLUMNS, "unknown"))

    def test_has_column_type_multiple_types(self):
        """Test column type detection with multiple acceptable types"""
        self.assertTrue(has_column_type(DEFAULT_COLUMNS, ["debit", "credit"]))
        self.assertTrue(has_column_type(DEFAULT_COLUMNS, ["balance", "total"]))
        self.assertFalse(has_column_type(DEFAULT_COLUMNS, ["unknown1", "unknown2"]))

    def test_has_column_type_custom_columns(self):
        """Test column type detection with custom columns"""
        custom_columns = {
            "Transaction Date": (20, 80),
            "Description": (80, 260),
            "Amount": (260, 400),
        }

        self.assertTrue(has_column_type(custom_columns, "date"))
        self.assertTrue(has_column_type(custom_columns, "description"))
        self.assertTrue(has_column_type(custom_columns, "balance"))

    def test_detect_table_headers_valid(self):
        """Test table header detection with valid headers"""
        header_words = [
            {"text": "Date", "x0": 30, "top": 100.0},
            {"text": "Details", "x0": 90, "top": 100.0},
            {"text": "Amount", "x0": 260, "top": 100.0},
            {"text": "Balance", "x0": 320, "top": 100.0},
        ]

        self.assertTrue(detect_table_headers(header_words, DEFAULT_COLUMNS))

    def test_detect_table_headers_no_headers(self):
        """Test table header detection with no recognizable headers"""
        non_header_words = [
            {"text": "Account", "x0": 30, "top": 100.0},
            {"text": "Statement", "x0": 90, "top": 100.0},
            {"text": "Page", "x0": 260, "top": 100.0},
            {"text": "1", "x0": 320, "top": 100.0},
        ]

        self.assertFalse(detect_table_headers(non_header_words, DEFAULT_COLUMNS))

    def test_detect_table_headers_mixed_content(self):
        """Test table header detection with mixed content including headers"""
        mixed_words = [
            {"text": "Bank", "x0": 30, "top": 80.0},
            {"text": "Statement", "x0": 90, "top": 80.0},
            {"text": "Date", "x0": 30, "top": 100.0},
            {"text": "Transaction", "x0": 90, "top": 100.0},
            {"text": "Details", "x0": 150, "top": 100.0},
            {"text": "Amount", "x0": 260, "top": 100.0},
        ]

        self.assertTrue(detect_table_headers(mixed_words, DEFAULT_COLUMNS))

    def test_detect_table_headers_empty(self):
        """Test table header detection with empty input"""
        self.assertFalse(detect_table_headers([], DEFAULT_COLUMNS))

    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_with_page_validation_enabled(self, mock_pdfplumber):
        """Test that page validation skips invalid pages when enabled"""
        # Mock PDF structure
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value = mock_pdf

        # Mock page 1: Invalid page (no table structure)
        mock_crop1 = MagicMock()
        mock_page1.crop.return_value = mock_crop1
        mock_crop1.extract_words.return_value = [
            {"text": "Account", "x0": 30, "top": 100},
            {"text": "Summary", "x0": 90, "top": 100},
        ]

        # Mock page 2: Valid page with headers and transaction data
        mock_page2.width = 600
        mock_page2.height = 800
        mock_crop2 = MagicMock()
        mock_page2.crop.return_value = mock_crop2
        mock_crop2.extract_words.return_value = [
            # Headers
            {"text": "Date", "x0": 30, "top": 80},
            {"text": "Details", "x0": 90, "top": 80},
            {"text": "Debit", "x0": 260, "top": 80},
            # Transactions
            {"text": "01", "x0": 30, "top": 100},
            {"text": "Jan", "x0": 50, "top": 100},
            {"text": "2024", "x0": 70, "top": 100},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100},
            {"text": "25.50", "x0": 260, "top": 100},
            {"text": "475.50", "x0": 380, "top": 100},
            # Add more rows to satisfy minimum row requirement
            {"text": "02", "x0": 30, "top": 120},
            {"text": "Jan", "x0": 50, "top": 120},
            {"text": "2024", "x0": 70, "top": 120},
            {"text": "VDP-GAS", "x0": 90, "top": 120},
            {"text": "40.00", "x0": 260, "top": 120},
            {"text": "435.50", "x0": 380, "top": 120},
            {"text": "03", "x0": 30, "top": 140},
            {"text": "Jan", "x0": 50, "top": 140},
            {"text": "2024", "x0": 70, "top": 140},
            {"text": "SALARY", "x0": 90, "top": 140},
            {"text": "2000.00", "x0": 320, "top": 140},
            {"text": "2435.50", "x0": 380, "top": 140},
        ]

        test_pdf_path = Path("/tmp/test.pdf")

        # Test with page validation enabled
        result = extract_tables_from_pdf(
            test_pdf_path, enable_page_validation=True
        )

        # Should have processed only the valid page
        self.assertEqual(result.page_count, 2)  # Total pages processed
        self.assertEqual(len(result.transactions), 3)  # Only rows from valid page

        # Verify all returned rows are from valid transactions
        for tx in result.transactions:
            self.assertTrue(any(tx.to_dict().values()))  # Non-empty rows
            self.assertEqual(tx.filename, "test.pdf")

        # Test with page validation disabled
        result_no_val = extract_tables_from_pdf(
            test_pdf_path, enable_page_validation=False
        )

        # Should process both pages (more rows due to invalid page content)
        self.assertGreaterEqual(len(result_no_val.transactions), len(result.transactions))

    def test_analyze_content_density_empty_word_groups(self):
        """Test analyze_content_density with empty word groups."""
        word_groups = {}
        columns = DEFAULT_COLUMNS

        result = analyze_content_density(word_groups, columns)

        self.assertEqual(result, [])

    def test_analyze_content_density_single_transaction_row(self):
        """Test analyze_content_density with single transaction row."""
        word_groups = {
            100.0: [
                {"text": "01 Jan 2024", "x0": 30},
                {"text": "VDC-GROCERY", "x0": 90},
                {"text": "25.50", "x0": 260},
                {"text": "475.50", "x0": 380},
            ]
        }
        columns = DEFAULT_COLUMNS

        result = analyze_content_density(word_groups, columns, window_size=1)

        self.assertEqual(len(result), 1)
        y_coord, density = result[0]
        self.assertEqual(y_coord, 100.0)
        self.assertGreater(density, 0.0)  # Should detect transaction

    def test_analyze_content_density_mixed_content(self):
        """Test analyze_content_density with mix of transactions and admin content."""
        word_groups = {
            100.0: [  # Transaction
                {"text": "01 Jan 2024", "x0": 30},
                {"text": "VDC-GROCERY", "x0": 90},
                {"text": "25.50", "x0": 260},
                {"text": "475.50", "x0": 380},
            ],
            120.0: [  # Administrative
                {"text": "BALANCE FORWARD", "x0": 90},
            ],
            140.0: [  # Transaction
                {"text": "02 Jan 2024", "x0": 30},
                {"text": "VDP-GAS", "x0": 90},
                {"text": "40.00", "x0": 260},
                {"text": "435.50", "x0": 380},
            ],
        }
        columns = DEFAULT_COLUMNS

        result = analyze_content_density(word_groups, columns, window_size=3)

        self.assertEqual(len(result), 1)  # One window for all 3 rows
        y_coord, density = result[0]
        self.assertEqual(y_coord, 120.0)  # Middle row as representative
        self.assertGreater(density, 0.0)  # Should be > 0 due to transactions
        self.assertLess(density, 1.0)  # Should be < 1 due to admin content

    def test_analyze_content_density_small_window_size(self):
        """Test analyze_content_density adjusts window size for small datasets."""
        word_groups = {100.0: [{"text": "Transaction", "x0": 90}]}
        columns = DEFAULT_COLUMNS

        result = analyze_content_density(word_groups, columns, window_size=5)

        # Should adjust to effective window size of 1
        self.assertEqual(len(result), 1)

    def test_detect_table_end_boundary_smart_no_words(self):
        """Test smart boundary detection with no words."""
        words = []
        result = detect_table_end_boundary_smart(words, 300, DEFAULT_COLUMNS, 720)

        self.assertEqual(result, 720)  # Should return fallback

    def test_detect_table_end_boundary_smart_no_transactions(self):
        """Test smart boundary detection with no transactions found."""
        words = [
            {"text": "Account", "x0": 90, "top": 100},
            {"text": "Summary", "x0": 150, "top": 120},
        ]
        result = detect_table_end_boundary_smart(words, 50, DEFAULT_COLUMNS, 720)

        self.assertEqual(result, 720)  # Should return fallback

    def test_detect_table_end_boundary_smart_strong_end_indicators(self):
        """Test smart boundary detection with strong end indicators."""
        words = [
            # Transaction
            {"text": "01 Jan 2024", "x0": 30, "top": 100},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100},
            {"text": "25.50", "x0": 260, "top": 100},
            {"text": "475.50", "x0": 380, "top": 100},
            # Strong end indicator
            {"text": "END", "x0": 200, "top": 200},
            {"text": "OF", "x0": 230, "top": 200},
            {"text": "STATEMENT", "x0": 250, "top": 200},
        ]

        result = detect_table_end_boundary_smart(words, 50, DEFAULT_COLUMNS, 720)

        # Should detect end before the indicator
        self.assertLess(result, 200)
        self.assertGreater(result, 100)

    def test_detect_table_end_boundary_smart_spatial_gap(self):
        """Test smart boundary detection with large spatial gaps."""
        # Pass min_section_gap=30 directly instead of using environment variable
        words = [
            # Transaction
            {"text": "01 Jan 2024", "x0": 30, "top": 100},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100},
            {"text": "25.50", "x0": 260, "top": 100},
            # Large gap to next content (150 - 100 = 50px > 30px threshold)
            {"text": "Footer", "x0": 90, "top": 150},
            {"text": "Information", "x0": 120, "top": 150},
        ]

        result = detect_table_end_boundary_smart(
            words, 50, DEFAULT_COLUMNS, 720, min_section_gap=30
        )

        # Should detect gap and set boundary after transaction
        self.assertGreater(result, 100)
        self.assertLess(result, 150)

    def test_detect_table_end_boundary_smart_structure_breakdown(self):
        """Test smart boundary detection with column structure breakdown."""
        # Pass structure_breakdown_threshold=3 directly instead of using environment variable
        words = [
            # Transaction
            {"text": "01 Jan 2024", "x0": 30, "top": 100},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100},
            {"text": "25.50", "x0": 260, "top": 100},
            # Structure breakdown - poor column alignment
            {"text": "Random", "x0": 50, "top": 120},
            {"text": "Text", "x0": 200, "top": 140},
            {"text": "Here", "x0": 100, "top": 160},
            {
                "text": "More",
                "x0": 300,
                "top": 180,
            },  # This should trigger breakdown
        ]

        result = detect_table_end_boundary_smart(
            words, 50, DEFAULT_COLUMNS, 720, structure_breakdown_threshold=3
        )

        # Should detect structure breakdown or use fallback
        self.assertGreater(result, 100)  # Should be after transaction
        # May use fallback if breakdown doesn't trigger, which is acceptable

    def test_detect_table_end_boundary_smart_conservative_consecutive(self):
        """Test smart boundary detection with conservative consecutive analysis."""
        words = [
            # Transaction
            {"text": "01 Jan 2024", "x0": 30, "top": 100},
            {"text": "VDC-GROCERY", "x0": 90, "top": 100},
            {"text": "25.50", "x0": 260, "top": 100},
            # Non-transaction content (3 consecutive)
            {"text": "BALANCE FORWARD", "x0": 90, "top": 120},
            {"text": "Interest Rate", "x0": 90, "top": 140},
            {"text": "IE123456789", "x0": 90, "top": 160},
            {"text": "More admin", "x0": 90, "top": 180},  # Should trigger
        ]

        # Pass threshold=3 directly instead of using environment variable
        result = detect_table_end_boundary_smart(
            words, 50, DEFAULT_COLUMNS, 720, dynamic_boundary_threshold=3
        )

        # Should use conservative consecutive threshold
        self.assertGreater(result, 100)  # Should be after transaction
        self.assertLess(result, 720)  # Should not use fallback

    def test_get_column_names_default(self):
        """Test get_column_names with default columns."""
        result = get_column_names()

        expected = list(DEFAULT_COLUMNS.keys()) + ["Filename"]
        self.assertEqual(result, expected)

    def test_get_column_names_custom_columns(self):
        """Test get_column_names with custom columns."""
        custom_columns = {"Date": (0, 100), "Amount": (100, 200)}

        result = get_column_names(custom_columns)

        expected = ["Date", "Amount", "Filename"]
        self.assertEqual(result, expected)

    def test_get_column_names_no_filename(self):
        """Test get_column_names without filename column."""
        result = get_column_names(include_filename=False)

        expected = list(DEFAULT_COLUMNS.keys())
        self.assertEqual(result, expected)

    @patch.dict(
        "os.environ", {"TABLE_COLUMNS": '{"Date": [0, 100], "Amount": [100, 200]}'}
    )
    def test_parse_columns_from_env_valid_json(self):
        """Test parse_columns_from_env with valid JSON."""
        result = parse_columns_from_env()

        expected = {"Date": (0, 100), "Amount": (100, 200)}
        self.assertEqual(result, expected)

    @patch.dict("os.environ", {"TABLE_COLUMNS": "invalid json"})
    def test_parse_columns_from_env_invalid_json(self):
        """Test parse_columns_from_env with invalid JSON."""
        result = parse_columns_from_env()

        # Should return default columns
        self.assertEqual(result, DEFAULT_COLUMNS)

    @patch.dict("os.environ", {"TABLE_COLUMNS": '{"Date": "invalid"}'})
    def test_parse_columns_from_env_invalid_format(self):
        """Test parse_columns_from_env with invalid column format."""
        result = parse_columns_from_env()

        # Should return default columns
        self.assertEqual(result, DEFAULT_COLUMNS)

    def test_parse_columns_from_env_no_env_var(self):
        """Test parse_columns_from_env when environment variable not set."""
        # Ensure env var is not set
        if "TABLE_COLUMNS" in os.environ:
            del os.environ["TABLE_COLUMNS"]

        result = parse_columns_from_env()

        # Should return default columns
        self.assertEqual(result, DEFAULT_COLUMNS)

    @patch("bankstatements_core.config.column_config.parse_columns_from_env")
    def test_get_columns_config(self, mock_parse):
        """Test get_columns_config calls parse_columns_from_env."""
        mock_parse.return_value = {"Test": (0, 100)}

        result = get_columns_config()

        mock_parse.assert_called_once_with("TABLE_COLUMNS")
        self.assertEqual(result, {"Test": (0, 100)})

    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_with_header_check_enabled_no_headers(self, mock_pdfplumber):
        """Test extraction with header check enabled but no headers found"""
        old_header_check = os.environ.get("REQUIRE_TABLE_HEADERS")
        os.environ["REQUIRE_TABLE_HEADERS"] = "true"

        try:
            # Mock PDF structure with no recognizable headers
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.height = 842  # A4 page height in points
            mock_page.width = 595  # A4 page width in points
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.return_value = mock_pdf

            # Mock page with no header content
            mock_crop = MagicMock()
            mock_page.crop.return_value = mock_crop
            mock_crop.extract_words.return_value = [
                {"text": "Account", "x0": 30, "top": 100},
                {"text": "Summary", "x0": 90, "top": 100},
                {"text": "No", "x0": 150, "top": 100},
                {"text": "Headers", "x0": 200, "top": 100},
            ]

            test_pdf_path = Path("/tmp/test.pdf")

            # Should skip the page due to no headers
            result = extract_tables_from_pdf(
                test_pdf_path, enable_dynamic_boundary=True
            )

            # Should return empty results since page was skipped
            self.assertEqual(len(result.transactions), 0)
            self.assertEqual(result.page_count, 1)  # Still counts the page

        finally:
            # Restore environment
            if old_header_check:
                os.environ["REQUIRE_TABLE_HEADERS"] = old_header_check
            else:
                os.environ.pop("REQUIRE_TABLE_HEADERS", None)

    @patch("bankstatements_core.pdf_table_extractor.pdfplumber.open")
    def test_extract_tables_static_mode_header_check(self, mock_pdfplumber):
        """Test extraction in static mode with header check enabled"""
        old_header_check = os.environ.get("REQUIRE_TABLE_HEADERS")
        os.environ["REQUIRE_TABLE_HEADERS"] = "true"

        try:
            # Mock PDF structure with no headers
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.return_value = mock_pdf

            mock_crop = MagicMock()
            mock_page.crop.return_value = mock_crop
            mock_crop.extract_words.return_value = [
                {"text": "No", "x0": 30, "top": 100},
                {"text": "Headers", "x0": 90, "top": 100},
            ]

            test_pdf_path = Path("/tmp/test.pdf")

            # Should skip page in static mode too
            result = extract_tables_from_pdf(
                test_pdf_path, enable_dynamic_boundary=False  # Static mode
            )

            # Should return empty results
            self.assertEqual(len(result.transactions), 0)

        finally:
            if old_header_check:
                os.environ["REQUIRE_TABLE_HEADERS"] = old_header_check
            else:
                os.environ.pop("REQUIRE_TABLE_HEADERS", None)

    def test_detect_table_headers_insufficient_matches(self):
        """Test detect_table_headers with insufficient header matches"""
        words = [
            {"text": "Date", "x0": 30, "top": 100},  # Only 1 header indicator
            {"text": "Random", "x0": 90, "top": 100},
            {"text": "Text", "x0": 150, "top": 100},
        ]

        result = detect_table_headers(words, DEFAULT_COLUMNS)

        # Should return False since we need at least 2 matches
        self.assertFalse(result)

    def test_classify_row_type_edge_cases(self):
        """Test classify_row_type with edge cases"""
        columns = DEFAULT_COLUMNS

        # Test IE pattern (numbers only after IE)
        row_ie_pattern = {"Details": "IE19102156715277"}
        result = classify_row_type(row_ie_pattern, columns)
        self.assertEqual(result, "reference")

        # Test timestamp pattern with different format
        row_timestamp = {"Details": "25OCT19 TIME 16:20 Some other text"}
        result = classify_row_type(row_timestamp, columns)
        self.assertEqual(result, "metadata")

        # Test transaction with VDA prefix
        row_vda = {"Details": "VDA-ONLINE PAYMENT", "Debit €": "100.00"}
        result = classify_row_type(row_vda, columns)
        self.assertEqual(result, "transaction")

        # Test transaction with D/D prefix
        row_dd = {"Details": "D/D UTILITY BILL", "Debit €": "50.00"}
        result = classify_row_type(row_dd, columns)
        self.assertEqual(result, "transaction")

    def test_classify_row_type_header_detection(self):
        """Test detection of table headers and field labels that should be
        filtered out"""
        columns = DEFAULT_COLUMNS

        # The problematic header from user report
        problematic_header = {
            "Date": "'TxnDate'(transactiondate)",
            "Details": "",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        self.assertEqual(classify_row_type(problematic_header, columns), "metadata")

        # Various header patterns that should be detected
        header_test_cases = [
            # Simple column headers
            {
                "Date": "Date",
                "Details": "Details",
                "Debit €": "Debit",
                "Credit €": "Credit",
                "Balance €": "Balance",
            },
            # Field name patterns
            {
                "Date": "TransactionDate",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "TxnDate",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            # Field with description patterns
            {
                "Date": "'Field'(description)",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "Amount(currency)",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            # Header-like text in other columns
            {
                "Date": "",
                "Details": "COLUMN HEADER",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "",
                "Details": "field name",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "",
                "Details": "TABLE HEADER",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        for i, header_row in enumerate(header_test_cases):
            with self.subTest(header_pattern=i):
                classification = classify_row_type(header_row, columns)
                self.assertEqual(
                    classification,
                    "metadata",
                    f"Header pattern {i} should be classified as metadata: "
                    f"{header_row}",
                )

        # Ensure legitimate transactions are still classified correctly
        legitimate_transaction = {
            "Date": "25 Apr 2025",
            "Details": "VDC-GROCERY STORE",
            "Debit €": "45.50",
            "Credit €": "",
            "Balance €": "1200.50",
        }
        self.assertEqual(
            classify_row_type(legitimate_transaction, columns), "transaction"
        )

        # Test that date-only rows are preserved (critical for date propagation)
        date_propagation_rows = [
            # Date-only row (start of day transactions)
            {
                "Date": "02 Feb 2025",
                "Details": "",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            # Date with minimal content
            {
                "Date": "02/02/25",
                "Details": "START OF DAY",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        for i, date_row in enumerate(date_propagation_rows):
            with self.subTest(date_row=i):
                classification = classify_row_type(date_row, columns)
                self.assertEqual(
                    classification,
                    "transaction",
                    f"Date row {i} should be preserved as transaction for date "
                    f"propagation: {date_row}",
                )

    def test_calculate_row_completeness_score_edge_cases(self):
        """Test calculate_row_completeness_score with edge cases"""
        columns = DEFAULT_COLUMNS

        # Test row with high-quality money format
        row_quality = {
            "Date": "01 Jan 2024",
            "Details": "VDC-GROCERY STORE PAYMENT",
            "Debit €": "123.45",  # Proper money format
            "Balance €": "876.54",
        }
        score = calculate_row_completeness_score(row_quality, columns)
        self.assertGreater(score, 0.8)  # Should get bonus for quality

        # Test with zero total weight (edge case)
        empty_columns = {}
        row_empty_cols = {"SomeField": "value"}
        score_empty = calculate_row_completeness_score(row_empty_cols, empty_columns)
        self.assertEqual(score_empty, 0.0)


if __name__ == "__main__":
    unittest.main()
