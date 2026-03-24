"""Tests for PDFProcessingOrchestrator entitlements consistency."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.config.processor_config import ExtractionConfig
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
