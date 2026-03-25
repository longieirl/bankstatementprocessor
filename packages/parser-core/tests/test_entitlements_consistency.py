"""Tests for entitlements consistency across factory and orchestrator construction."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.patterns.factories import ProcessorFactory
from bankstatements_core.services.pdf_processing_orchestrator import (
    PDFProcessingOrchestrator,
)


class TestProcessorFactoryCreateCustomEntitlements:
    """Tests for entitlements handling in ProcessorFactory.create_custom()."""

    def test_create_custom_with_entitlements_passes_to_processor(self, tmp_path):
        """create_custom() passes entitlements through to BankStatementProcessor."""
        paid = Entitlements.paid_tier()
        processor = ProcessorFactory.create_custom(
            input_dir=tmp_path,
            output_dir=tmp_path,
            entitlements=paid,
        )
        assert processor.entitlements == paid

    def test_create_custom_without_entitlements_defaults_to_none(self, tmp_path):
        """Regression guard: omitting entitlements still produces a valid processor."""
        processor = ProcessorFactory.create_custom(
            input_dir=tmp_path,
            output_dir=tmp_path,
        )
        assert processor.entitlements is None

    def test_create_custom_entitlements_explicit_param_not_swallowed_by_kwargs(
        self, tmp_path
    ):
        """entitlements passed as explicit kwarg is not silently dropped."""
        free = Entitlements.free_tier()
        processor = ProcessorFactory.create_custom(
            input_dir=tmp_path,
            output_dir=tmp_path,
            entitlements=free,
        )
        assert processor.entitlements == free


class TestPDFProcessingOrchestratorEntitlementsConsistency:
    """Tests for entitlements consistency assertion in PDFProcessingOrchestrator."""

    def _make_orchestrator(self, *, orchestrator_ents, extractor_ents, tmp_path):
        from bankstatements_core.config.column_config import get_column_names
        from bankstatements_core.config.processor_config import ExtractionConfig
        from bankstatements_core.patterns.repositories import (
            FileSystemTransactionRepository,
        )
        from bankstatements_core.services.extraction_orchestrator import (
            ExtractionOrchestrator,
        )

        extraction_config = ExtractionConfig(
            table_top_y=100,
            table_bottom_y=700,
            columns={},
        )
        repo = MagicMock(spec=FileSystemTransactionRepository)
        extraction_orchestrator = ExtractionOrchestrator(
            extraction_config=extraction_config,
            entitlements=extractor_ents,
        )
        return PDFProcessingOrchestrator(
            extraction_config=extraction_config,
            column_names=get_column_names(),
            output_dir=tmp_path,
            repository=repo,
            entitlements=orchestrator_ents,
            extraction_orchestrator=extraction_orchestrator,
        )

    def test_mismatched_entitlements_raises(self, tmp_path):
        """Constructing orchestrator with mismatched entitlements raises AssertionError."""
        with pytest.raises((AssertionError, ValueError)):
            self._make_orchestrator(
                orchestrator_ents=Entitlements.free_tier(),
                extractor_ents=Entitlements.paid_tier(),
                tmp_path=tmp_path,
            )

    def test_matching_entitlements_does_not_raise(self, tmp_path):
        """Constructing orchestrator with consistent entitlements is fine."""
        paid = Entitlements.paid_tier()
        orch = self._make_orchestrator(
            orchestrator_ents=paid,
            extractor_ents=paid,
            tmp_path=tmp_path,
        )
        assert orch.entitlements == paid

    def test_both_none_entitlements_does_not_raise(self, tmp_path):
        """None/None (no entitlements) is a valid consistent configuration."""
        orch = self._make_orchestrator(
            orchestrator_ents=None,
            extractor_ents=None,
            tmp_path=tmp_path,
        )
        assert orch.entitlements is None
