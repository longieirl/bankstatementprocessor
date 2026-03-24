"""Tests for ProcessorFactory.create_custom entitlements wiring."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.patterns.factories import ProcessorFactory


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


class TestProcessorFactoryCreateCustomEntitlements(unittest.TestCase):
    def test_entitlements_passed_through_to_processor(self):
        """create_custom(entitlements=...) stores the value on the processor."""
        ent = Entitlements.paid_tier()
        processor = ProcessorFactory.create_custom(
            input_dir=_tmp(),
            output_dir=_tmp(),
            entitlements=ent,
        )
        self.assertEqual(processor.entitlements, ent)

    def test_no_entitlements_defaults_to_none(self):
        """create_custom() without entitlements preserves None (backward compat)."""
        processor = ProcessorFactory.create_custom(
            input_dir=_tmp(),
            output_dir=_tmp(),
        )
        self.assertIsNone(processor.entitlements)

    def test_free_tier_entitlements_passed_through(self):
        """FREE tier entitlements are passed through correctly."""
        ent = Entitlements.free_tier()
        processor = ProcessorFactory.create_custom(
            input_dir=_tmp(),
            output_dir=_tmp(),
            entitlements=ent,
        )
        self.assertEqual(processor.entitlements, ent)
        self.assertTrue(processor.entitlements.require_iban)
