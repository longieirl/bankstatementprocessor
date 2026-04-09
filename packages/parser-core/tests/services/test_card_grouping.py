"""Tests for CCGroupingService (CC-07)."""

from __future__ import annotations

import logging
import unittest

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.card_grouping import CCGroupingService


class TestCCGroupingService(unittest.TestCase):
    """Test CCGroupingService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = CCGroupingService(suffix_length=4)

    def test_group_by_card_single_card(self):
        """Three transactions from same CC file group under last-4 of card number."""
        rows = [
            Transaction.from_dict({"Filename": "cc.pdf", "Details": "Purchase 1"}),
            Transaction.from_dict({"Filename": "cc.pdf", "Details": "Purchase 2"}),
            Transaction.from_dict({"Filename": "cc.pdf", "Details": "Purchase 3"}),
        ]
        pdf_card_numbers = {"cc.pdf": "**** **** **** 1234"}

        grouped = self.service.group_by_card(rows, pdf_card_numbers)

        self.assertEqual(len(grouped), 1)
        self.assertIn("1234", grouped)
        self.assertEqual(len(grouped["1234"]), 3)

    def test_group_by_card_multiple_cards(self):
        """Transactions from 2 files with different cards group into 2 separate keys."""
        rows = [
            Transaction.from_dict({"Filename": "cc1.pdf", "Details": "Purchase A"}),
            Transaction.from_dict({"Filename": "cc2.pdf", "Details": "Purchase B"}),
            Transaction.from_dict({"Filename": "cc1.pdf", "Details": "Purchase C"}),
        ]
        pdf_card_numbers = {
            "cc1.pdf": "**** **** **** 1234",
            "cc2.pdf": "**** **** **** 5678",
        }

        grouped = self.service.group_by_card(rows, pdf_card_numbers)

        self.assertEqual(len(grouped), 2)
        self.assertIn("1234", grouped)
        self.assertIn("5678", grouped)
        self.assertEqual(len(grouped["1234"]), 2)
        self.assertEqual(len(grouped["5678"]), 1)

    def test_group_by_card_unknown_fallback(self):
        """pdf_card_numbers value of 'unknown' groups under 'unknown' key."""
        rows = [
            Transaction.from_dict({"Filename": "cc.pdf", "Details": "Purchase"}),
        ]
        pdf_card_numbers = {"cc.pdf": "unknown"}

        grouped = self.service.group_by_card(rows, pdf_card_numbers)

        self.assertEqual(len(grouped), 1)
        self.assertIn("unknown", grouped)
        self.assertEqual(len(grouped["unknown"]), 1)

    def test_group_by_card_missing_filename(self):
        """Transaction with no filename groups under 'unknown'."""
        rows = [
            Transaction.from_dict({"Details": "No filename here"}),  # No Filename field
            Transaction.from_dict({"Filename": "cc.pdf", "Details": "Purchase"}),
        ]
        pdf_card_numbers = {"cc.pdf": "**** **** **** 9999"}

        with self.assertLogs(
            "bankstatements_core.services.card_grouping", level=logging.WARNING
        ):
            grouped = self.service.group_by_card(rows, pdf_card_numbers)

        self.assertIn("unknown", grouped)
        self.assertIn("9999", grouped)
        self.assertEqual(len(grouped["unknown"]), 1)
        self.assertEqual(len(grouped["9999"]), 1)

    def test_group_by_card_empty_input(self):
        """Empty transaction list returns empty dict."""
        grouped = self.service.group_by_card([], {})
        self.assertEqual(grouped, {})

    def test_extract_suffix_masked_card(self):
        """'**** **** **** 1234' -> strip non-alphanumeric -> '1234' -> last 4 -> '1234'."""
        suffix = self.service._extract_suffix("**** **** **** 1234")
        self.assertEqual(suffix, "1234")

    def test_extract_suffix_partial_mask(self):
        """'1234 56** **** 7890' -> strip non-alphanumeric -> '123456****7890'
        -> strip * -> '1234567890' -> last 4 -> '7890'."""
        suffix = self.service._extract_suffix("1234 56** **** 7890")
        self.assertEqual(suffix, "7890")

    def test_extract_suffix_empty(self):
        """Empty string returns empty string."""
        suffix = self.service._extract_suffix("")
        self.assertEqual(suffix, "")

    def test_custom_suffix_length(self):
        """suffix_length=6 returns last 6 chars of cleaned card number."""
        service = CCGroupingService(suffix_length=6)
        # "1234 5678 9012 3456" -> clean -> "1234567890123456" -> last 6 -> "123456"
        suffix = service._extract_suffix("1234 5678 9012 3456")
        self.assertEqual(suffix, "123456")


if __name__ == "__main__":
    unittest.main()
