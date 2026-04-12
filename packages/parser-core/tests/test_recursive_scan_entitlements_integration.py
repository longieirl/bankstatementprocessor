# packages/parser-core/tests/test_recursive_scan_entitlements_integration.py
"""Integration tests for entitlement enforcement via BankStatementProcessingFacade."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bankstatements_core.config.app_config import AppConfig
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.facades.processing_facade import BankStatementProcessingFacade


class TestRecursiveScanEntitlementEnforcement:
    def test_free_tier_allows_recursive_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir, output_dir=output_dir, recursive_scan=True
            )
            facade = BankStatementProcessingFacade(config, Entitlements.free_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_free_tier_works_with_all_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
                output_formats=["csv", "json", "excel"],
            )
            facade = BankStatementProcessingFacade(config, Entitlements.free_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_can_enable_recursive_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "test.pdf").write_text("fake pdf")
            config = AppConfig(
                input_dir=input_dir, output_dir=output_dir, recursive_scan=True
            )
            facade = BankStatementProcessingFacade(config, Entitlements.paid_tier())
            summary = facade.process_all()
            assert summary is not None

    def test_paid_tier_respects_recursive_scan_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir, output_dir=output_dir, recursive_scan=False
            )
            facade = BankStatementProcessingFacade(config, Entitlements.paid_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0

    def test_no_entitlements_defaults_to_free_tier(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
            )
            facade = BankStatementProcessingFacade(config, entitlements=None)
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_difference_is_iban_requirement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
                output_formats=["csv", "json", "excel"],
            )
            free_entitlements = Entitlements.free_tier()
            paid_entitlements = Entitlements.paid_tier()
            assert free_entitlements.require_iban is True
            assert paid_entitlements.require_iban is False
            facade_free = BankStatementProcessingFacade(config, free_entitlements)
            facade_paid = BankStatementProcessingFacade(config, paid_entitlements)
            summary_free = facade_free.process_all()
            summary_paid = facade_paid.process_all()
            assert summary_free["pdf_count"] == 0
            assert summary_paid["pdf_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
