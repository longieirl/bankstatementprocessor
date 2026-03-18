"""Tests for IBAN grouping service."""

from __future__ import annotations

import logging
import unittest

from bankstatements_core.services.iban_grouping import IBANGroupingService


class TestIBANGroupingService(unittest.TestCase):
    """Test IBANGroupingService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = IBANGroupingService(suffix_length=4)

    def test_group_by_iban_with_valid_ibans(self):
        """Test grouping with valid IBANs."""
        rows = [
            {"Filename": "file1.pdf", "Details": "Transaction 1"},
            {"Filename": "file2.pdf", "Details": "Transaction 2"},
            {"Filename": "file1.pdf", "Details": "Transaction 3"},
        ]
        pdf_ibans = {
            "file1.pdf": "IE12 BOFI 9000 0112 3456",
            "file2.pdf": "IE12 BOFI 9000 0198 7654",
        }

        grouped = self.service.group_by_iban(rows, pdf_ibans)

        # Should have 2 groups (last 4 digits: 3456 and 7654)
        self.assertEqual(len(grouped), 2)
        self.assertIn("3456", grouped)
        self.assertIn("7654", grouped)
        self.assertEqual(len(grouped["3456"]), 2)  # file1 has 2 transactions
        self.assertEqual(len(grouped["7654"]), 1)  # file2 has 1 transaction

    def test_group_by_iban_without_iban(self):
        """Test grouping when PDF has no IBAN."""
        rows = [
            {"Filename": "file1.pdf", "Details": "Transaction 1"},
            {"Filename": "file2.pdf", "Details": "Transaction 2"},
        ]
        pdf_ibans = {
            "file1.pdf": "IE12 BOFI 9000 0112 3456",
            # file2.pdf has no IBAN
        }

        grouped = self.service.group_by_iban(rows, pdf_ibans)

        # Should have 2 groups (3456 and unknown)
        self.assertEqual(len(grouped), 2)
        self.assertIn("3456", grouped)
        self.assertIn("unknown", grouped)
        self.assertEqual(len(grouped["3456"]), 1)
        self.assertEqual(len(grouped["unknown"]), 1)

    def test_group_by_iban_missing_filename(self, caplog=None):
        """Test grouping when row has no filename."""
        rows = [
            {"Details": "Transaction 1"},  # No Filename field
            {"Filename": "file1.pdf", "Details": "Transaction 2"},
        ]
        pdf_ibans = {
            "file1.pdf": "IE12 BOFI 9000 0112 3456",
        }

        with self.assertLogs("bankstatements_core.services.iban_grouping", level=logging.WARNING):
            grouped = self.service.group_by_iban(rows, pdf_ibans)

        # Row without filename should go to unknown
        self.assertIn("unknown", grouped)
        self.assertIn("3456", grouped)
        self.assertEqual(len(grouped["unknown"]), 1)
        self.assertEqual(len(grouped["3456"]), 1)

    def test_extract_suffix_standard_iban(self):
        """Test suffix extraction from standard IBAN."""
        iban = "IE12 BOFI 9000 0112 3456"
        suffix = self.service._extract_suffix(iban)
        self.assertEqual(suffix, "3456")

    def test_extract_suffix_no_spaces(self):
        """Test suffix extraction from IBAN without spaces."""
        iban = "IE12BOFI90000112345"
        suffix = self.service._extract_suffix(iban)
        self.assertEqual(suffix, "2345")

    def test_extract_suffix_short_iban(self):
        """Test suffix extraction when IBAN is shorter than suffix length."""
        iban = "AB"
        suffix = self.service._extract_suffix(iban)
        self.assertEqual(suffix, "AB")

    def test_extract_suffix_empty_iban(self):
        """Test suffix extraction from empty IBAN."""
        suffix = self.service._extract_suffix("")
        self.assertEqual(suffix, "")

    def test_extract_suffix_lowercase(self):
        """Test suffix extraction converts to uppercase."""
        iban = "ie12 bofi 9000 0112 abcd"
        suffix = self.service._extract_suffix(iban)
        self.assertEqual(suffix, "ABCD")

    def test_custom_suffix_length(self):
        """Test custom suffix length."""
        service = IBANGroupingService(suffix_length=6)
        iban = "IE12 BOFI 9000 0112 3456"
        suffix = service._extract_suffix(iban)
        self.assertEqual(suffix, "123456")


if __name__ == "__main__":
    unittest.main()
