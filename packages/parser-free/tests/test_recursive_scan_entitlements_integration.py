"""Integration tests for IBAN requirement entitlement enforcement.

This module tests that PAID tier features (no IBAN requirement) cannot be enabled
by simply setting environment variables or configuration flags without proper
license entitlements. Note: Recursive scanning is now FREE tier.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.facades.processing_facade import BankStatementProcessingFacade
from bankstatements_free.app import AppConfig, ConfigurationError


class TestRecursiveScanEntitlementEnforcement:
    """Test entitlement enforcement for tier-specific features."""

    def test_free_tier_allows_recursive_scan(self):
        """Test FREE tier allows recursive scanning (now available to all)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create config with recursive scanning ENABLED
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,  # Should be allowed
            )

            # Use FREE tier entitlements
            free_entitlements = Entitlements.free_tier()
            facade = BankStatementProcessingFacade(config, free_entitlements)

            # Should NOT raise - recursive scanning is now FREE tier
            summary = facade.process_all()

            # Verify it ran successfully (no PDFs, but shouldn't error)
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_free_tier_works_with_all_features(self):
        """Test FREE tier works with all FREE features enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create config with all FREE tier features
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,  # Available in FREE tier
                generate_monthly_summary=True,  # Available in FREE tier
                output_formats=["csv", "json", "excel"],  # All formats available
            )

            # FREE tier entitlements
            free_entitlements = Entitlements.free_tier()
            facade = BankStatementProcessingFacade(config, free_entitlements)

            # Should work fine (no PDFs, but shouldn't error)
            summary = facade.process_all()

            # Verify it ran successfully
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_can_enable_recursive_scan(self):
        """Test PAID tier allows recursive scanning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create PDFs in subdirectory
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "test.pdf").write_text("fake pdf")

            # Create config with recursive scanning ENABLED
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,  # Enable
            )

            # PAID tier entitlements
            paid_entitlements = Entitlements.paid_tier()
            facade = BankStatementProcessingFacade(config, paid_entitlements)

            # Should work without error
            summary = facade.process_all()

            # Verify it ran (will try to process the fake PDF)
            assert summary is not None

    def test_paid_tier_respects_recursive_scan_false(self):
        """Test PAID tier respects recursive_scan=False setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create config with recursive scanning DISABLED
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=False,  # Explicitly disabled
            )

            # PAID tier entitlements (has permission, but not requested)
            paid_entitlements = Entitlements.paid_tier()
            facade = BankStatementProcessingFacade(config, paid_entitlements)

            # Should work fine
            summary = facade.process_all()

            assert summary["pdf_count"] == 0

    def test_no_entitlements_defaults_to_free_tier(self):
        """Test that missing entitlements defaults to FREE tier behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Config with all FREE features enabled
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,  # FREE tier feature
                generate_monthly_summary=True,  # FREE tier feature
            )

            # No entitlements provided (should default to FREE tier)
            facade = BankStatementProcessingFacade(config, entitlements=None)

            # Should work fine - all features are FREE tier (no PDFs, but shouldn't error)
            summary = facade.process_all()

            # Verify it ran successfully
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_difference_is_iban_requirement(self):
        """Test that PAID tier's unique feature is no IBAN requirement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Config with all features
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,  # FREE tier feature
                generate_monthly_summary=True,  # FREE tier feature
                output_formats=["csv", "json", "excel"],  # All FREE tier
            )

            # Both tiers support these features
            free_entitlements = Entitlements.free_tier()
            paid_entitlements = Entitlements.paid_tier()

            # The difference is IBAN requirement
            assert free_entitlements.require_iban is True
            assert paid_entitlements.require_iban is False

            # Both can process with these features enabled
            facade_free = BankStatementProcessingFacade(config, free_entitlements)
            facade_paid = BankStatementProcessingFacade(config, paid_entitlements)

            summary_free = facade_free.process_all()
            summary_paid = facade_paid.process_all()

            # Both should work (no PDFs, but shouldn't error)
            assert summary_free["pdf_count"] == 0
            assert summary_paid["pdf_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
