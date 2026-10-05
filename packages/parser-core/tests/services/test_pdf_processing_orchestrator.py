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
