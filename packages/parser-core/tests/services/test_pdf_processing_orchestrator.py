"""Behavioral tests for PDFProcessingOrchestrator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.services.pdf_processing_orchestrator import (
    PDFProcessingOrchestrator,
)


def _make_orchestrator(extraction_orchestrator=None):
    """Build a PDFProcessingOrchestrator with minimal required args."""
    return PDFProcessingOrchestrator(
        extraction_config=ExtractionConfig(table_top_y=100, table_bottom_y=700),
        column_names=["Date", "Details", "Debit", "Credit"],
        output_dir=Path(tempfile.mkdtemp()),
        repository=MagicMock(),
        extraction_orchestrator=extraction_orchestrator,
    )


class TestPDFWithTransactionsNotExcluded(unittest.TestCase):
    def _get_exclusion_reason(self, orch):
        """Extract the exclusion reason from the save_json_file call."""
        call_args_list = orch.repository.save_json_file.call_args_list
        for call in call_args_list:
            _, payload = call[0]
            if isinstance(payload, dict) and "excluded_files" in payload:
                return payload["excluded_files"][0]["reason"]
        return None

    def test_pdf_with_transactions_not_excluded(self):
        """A PDF with transactions present must NOT be excluded from output."""
        from bankstatements_core.domain.models.transaction import Transaction

        orch = _make_orchestrator()
        orch.pdf_discovery.discover_pdfs = MagicMock(
            return_value=[Path("/tmp/test.pdf")]
        )
        txn = Transaction(
            date="2024-01-01",
            details="Test",
            debit=None,
            credit="50.00",
            balance=None,
            filename="test.pdf",
        )
        orch.extraction_orchestrator.extract_from_pdf = MagicMock(
            return_value=ExtractionResult(
                transactions=[txn],
                page_count=1,
                iban=None,
                source_file=Path("/tmp/test.pdf"),
            )
        )
        results, pdf_count, _ = orch.process_all_pdfs(Path("/tmp"))
        reason = self._get_exclusion_reason(orch)
        self.assertIsNone(reason, "PDF with transactions must not be excluded")


class TestSaveCardNumbers(unittest.TestCase):
    """Tests for _save_card_numbers and cc.json output."""

    def _make_orchestrator_with_cc_result(self, card_number):
        from bankstatements_core.domain.models.transaction import Transaction

        orch = _make_orchestrator()
        orch.pdf_discovery.discover_pdfs = MagicMock(
            return_value=[Path("/tmp/cc_statement.pdf")]
        )
        txn = Transaction(
            date="2024-01-01",
            details="Purchase",
            debit="50.00",
            credit=None,
            balance=None,
            filename="cc_statement.pdf",
        )
        orch.extraction_orchestrator.extract_from_pdf = MagicMock(
            return_value=ExtractionResult(
                transactions=[txn],
                page_count=1,
                iban=None,
                source_file=Path("/tmp/cc_statement.pdf"),
                card_number=card_number,
            )
        )
        return orch

    def test_cc_json_written_with_masked_and_digest(self):
        """cc.json is written when a CC PDF is processed; entry has card_masked and card_digest."""
        import hashlib

        card_number = "4402 60** **** 9459"
        orch = self._make_orchestrator_with_cc_result(card_number)
        orch.process_all_pdfs(Path("/tmp"))

        cc_call = next(
            (
                c
                for c in orch.repository.save_json_file.call_args_list
                if "cc.json" in str(c[0][0])
            ),
            None,
        )
        self.assertIsNotNone(cc_call, "cc.json was not written")
        payload = cc_call[0][1]
        self.assertEqual(len(payload), 1)
        entry = payload[0]

        self.assertEqual(entry["pdf_filename"], "cc_statement.pdf")
        self.assertEqual(entry["card_masked"], "4402********9459")  # 16 chars stripped → 8 middle stars
        self.assertEqual(len(entry["card_digest"]), 64)
        self.assertEqual(
            entry["card_digest"], hashlib.sha256(card_number.encode()).hexdigest()
        )

    def test_card_masked_strips_spaces_and_masks_middle(self):
        """card_masked: spaces removed, first-4 + asterisks + last-4."""
        orch = self._make_orchestrator_with_cc_result("440260****9459")
        orch.process_all_pdfs(Path("/tmp"))

        cc_call = next(
            (
                c
                for c in orch.repository.save_json_file.call_args_list
                if "cc.json" in str(c[0][0])
            ),
            None,
        )
        self.assertIsNotNone(cc_call)
        entry = cc_call[0][1][0]
        # "440260****9459" has no spaces → stripped is 14 chars → 6 middle stars
        self.assertEqual(entry["card_masked"], "4402******9459")
        self.assertNotIn(" ", entry["card_masked"])
