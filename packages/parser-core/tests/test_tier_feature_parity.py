"""Tests to ensure FREE and PAID tiers have correct feature parity.

Verifies that both tiers have access to the same output formats and
features, with only IBAN requirement differing.
"""

from __future__ import annotations

import pytest

from bankstatements_core.entitlements import Entitlements


class TestTierFeatureParity:
    """Test feature parity between FREE and PAID tiers."""

    def test_both_tiers_allow_all_output_formats(self):
        """Test both FREE and PAID tiers allow all output formats."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        # Both should have same output formats
        assert free_ent.allowed_output_formats == paid_ent.allowed_output_formats

        # Both should allow CSV, JSON, Excel
        for format_name in ["csv", "json", "excel", "xlsx"]:
            free_ent.check_output_format(format_name)  # Should not raise
            paid_ent.check_output_format(format_name)  # Should not raise

    def test_both_tiers_allow_monthly_summary(self):
        """Test both FREE and PAID tiers allow monthly summaries."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        assert free_ent.allow_monthly_summary is True
        assert paid_ent.allow_monthly_summary is True

        # Should not raise
        free_ent.check_monthly_summary()
        paid_ent.check_monthly_summary()

    def test_both_tiers_allow_expense_analysis(self):
        """Test both FREE and PAID tiers allow expense analysis."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        assert free_ent.allow_expense_analysis is True
        assert paid_ent.allow_expense_analysis is True

        # Should not raise
        free_ent.check_expense_analysis()
        paid_ent.check_expense_analysis()

    def test_both_tiers_allow_recursive_scan(self):
        """Test both FREE and PAID tiers allow recursive directory scanning."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        # Both tiers allow recursive scanning
        assert free_ent.allow_recursive_scan is True
        assert paid_ent.allow_recursive_scan is True

        # Should not raise for either tier
        free_ent.check_recursive_scan()
        paid_ent.check_recursive_scan()

    def test_free_tier_has_iban_requirement(self):
        """Test FREE tier requires IBAN patterns in templates."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        assert free_ent.require_iban is True
        assert paid_ent.require_iban is False


class TestFreeTierFullyFunctional:
    """Test FREE tier is fully functional for core use cases."""

    def test_free_tier_can_process_pdfs(self):
        """Test FREE tier has all capabilities for PDF processing."""
        ent = Entitlements.free_tier()

        # Can output to all formats
        for format in ["csv", "json", "excel", "xlsx"]:
            ent.check_output_format(format)

        # Can generate insights
        ent.check_monthly_summary()
        ent.check_expense_analysis()

        # Can use recursive scanning
        ent.check_recursive_scan()

        # Only limitation: IBAN required
        assert ent.require_iban is True

    def test_paid_tier_only_removes_iban_requirement(self):
        """Test PAID tier only removes IBAN requirement (allows credit card statements)."""
        free_ent = Entitlements.free_tier()
        paid_ent = Entitlements.paid_tier()

        # Same output formats
        assert free_ent.allowed_output_formats == paid_ent.allowed_output_formats

        # Same feature access
        assert free_ent.allow_monthly_summary == paid_ent.allow_monthly_summary
        assert free_ent.allow_expense_analysis == paid_ent.allow_expense_analysis
        assert free_ent.allow_recursive_scan == paid_ent.allow_recursive_scan

        # Only difference: IBAN requirement
        assert free_ent.require_iban != paid_ent.require_iban
        assert free_ent.require_iban is True
        assert paid_ent.require_iban is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
