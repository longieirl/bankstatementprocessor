"""Tests for PDFProcessingOrchestrator entitlements consistency."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.services.extraction_orchestrator import ExtractionOrchestrator
from bankstatements_core.services.pdf_processing_orchestrator import (
    PDFProcessingOrchestrator,
)


def _make_orchestrator(entitlements=None, extraction_orchestrator=None):
    """Build a PDFProcessingOrchestrator with minimal required args."""
    return PDFProcessingOrchestrator(
        extraction_config=ExtractionConfig(table_top_y=100, table_bottom_y=700),
        column_names=["Date", "Details", "Debit", "Credit"],
        output_dir=Path(tempfile.mkdtemp()),
        repository=MagicMock(),
        entitlements=entitlements,
        extraction_orchestrator=extraction_orchestrator,
    )


class TestPDFProcessingOrchestratorEntitlements(unittest.TestCase):
    def test_default_creates_extraction_orchestrator_with_matching_entitlements(self):
        """When no extraction_orchestrator is injected, the default is wired with
        the same entitlements as the parent."""
        ent = Entitlements.paid_tier()
        orch = _make_orchestrator(entitlements=ent)
        self.assertEqual(orch.extraction_orchestrator._entitlements, ent)

    def test_injected_orchestrator_with_matching_entitlements_is_accepted(self):
        """An explicitly injected ExtractionOrchestrator with the same entitlements
        is accepted without error."""
        ent = Entitlements.free_tier()
        ext_orch = ExtractionOrchestrator(
            extraction_config=ExtractionConfig(table_top_y=100, table_bottom_y=700),
            entitlements=ent,
        )
        orch = _make_orchestrator(entitlements=ent, extraction_orchestrator=ext_orch)
        self.assertIs(orch.extraction_orchestrator, ext_orch)

    def test_injected_orchestrator_with_mismatched_entitlements_raises(self):
        """An explicitly injected ExtractionOrchestrator with different entitlements
        raises ValueError immediately at construction time."""
        parent_ent = Entitlements.free_tier()
        child_ent = Entitlements.paid_tier()
        ext_orch = ExtractionOrchestrator(
            extraction_config=ExtractionConfig(table_top_y=100, table_bottom_y=700),
            entitlements=child_ent,
        )
        with self.assertRaises(ValueError) as ctx:
            _make_orchestrator(
                entitlements=parent_ent, extraction_orchestrator=ext_orch
            )
        self.assertIn("entitlements", str(ctx.exception).lower())

    def test_none_entitlements_both_sides_is_accepted(self):
        """Both parent and injected orchestrator with entitlements=None is valid."""
        ext_orch = ExtractionOrchestrator(
            extraction_config=ExtractionConfig(table_top_y=100, table_bottom_y=700),
            entitlements=None,
        )
        orch = _make_orchestrator(entitlements=None, extraction_orchestrator=ext_orch)
        self.assertIs(orch.extraction_orchestrator, ext_orch)


class TestExclusionReasonTierAware(unittest.TestCase):
    """CC-03/CC-04: Exclusion reason must be tier-aware."""

    def _make_result(self, transactions=None):
        """Build an ExtractionResult with no IBAN and zero pages."""
        return ExtractionResult(
            transactions=transactions if transactions is not None else [],
            page_count=1,
            iban=None,
            source_file=Path("/tmp/test.pdf"),
        )

    def _get_exclusion_reason(self, orch):
        """Extract the exclusion reason from the save_json_file call."""
        call_args_list = orch.repository.save_json_file.call_args_list
        # Find the call that saved excluded_files (second argument is a dict with
        # 'excluded_files' key)
        for call in call_args_list:
            _, payload = call[0]
            if isinstance(payload, dict) and "excluded_files" in payload:
                return payload["excluded_files"][0]["reason"]
        return None

    def _run_process(self, entitlements):
        """Run process_all_pdfs with one mocked PDF and return the orchestrator."""
        orch = _make_orchestrator(entitlements=entitlements)
        orch.pdf_discovery.discover_pdfs = MagicMock(
            return_value=[Path("/tmp/test.pdf")]
        )
        orch.extraction_orchestrator.extract_from_pdf = MagicMock(
            return_value=self._make_result()
        )
        orch.process_all_pdfs(Path("/tmp"))
        return orch

    def test_free_tier_exclusion_mentions_iban(self):
        """CC-03: Free-tier (require_iban=True) exclusion reason must mention IBAN."""
        orch = self._run_process(entitlements=Entitlements.free_tier())
        reason = self._get_exclusion_reason(orch)
        self.assertIsNotNone(reason, "Expected an excluded file record")
        self.assertIn("IBAN", reason.upper())

    def test_paid_tier_exclusion_no_iban_mention(self):
        """CC-04: Paid-tier (require_iban=False) exclusion reason must NOT mention IBAN
        and must mention 'no transactions extracted'."""
        orch = self._run_process(entitlements=Entitlements.paid_tier())
        reason = self._get_exclusion_reason(orch)
        self.assertIsNotNone(reason, "Expected an excluded file record")
        self.assertNotIn("IBAN", reason.upper())
        self.assertIn("no transactions extracted", reason.lower())

    def test_no_entitlements_exclusion_mentions_iban(self):
        """CC-03 backward compat: entitlements=None must behave like free tier (mentions IBAN)."""
        orch = self._run_process(entitlements=None)
        reason = self._get_exclusion_reason(orch)
        self.assertIsNotNone(reason, "Expected an excluded file record")
        self.assertIn("IBAN", reason.upper())

    def test_paid_tier_with_transactions_not_excluded(self):
        """Paid tier with transactions present must NOT be excluded."""
        from bankstatements_core.domain.models.transaction import Transaction

        orch = _make_orchestrator(entitlements=Entitlements.paid_tier())
        orch.pdf_discovery.discover_pdfs = MagicMock(
            return_value=[Path("/tmp/test.pdf")]
        )
        # Build a minimal Transaction to confirm non-zero transactions path
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
        # PDF should not be in excluded_files — save_json_file should NOT have
        # been called with an excluded_files payload
        reason = self._get_exclusion_reason(orch)
        self.assertIsNone(reason, "PDF with transactions must not be excluded")
