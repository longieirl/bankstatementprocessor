"""Tests for the entitlements system."""

from __future__ import annotations

import pytest

from bankstatements_core.entitlements import EntitlementError, Entitlements


class TestEntitlements:
    """Test entitlements tier definitions and enforcement."""

    def test_free_tier_defaults(self):
        """Test FREE tier has correct defaults."""
        ent = Entitlements.free_tier()

        assert ent.tier == "FREE"
        assert ent.allow_recursive_scan is True  # Available to all users
        assert ent.allowed_output_formats == {"csv", "json", "excel", "xlsx"}
        assert ent.allow_monthly_summary is True  # Available to all users
        assert ent.allow_expense_analysis is True
        assert ent.require_iban is True  # IBAN required in FREE tier

    def test_paid_tier_defaults(self):
        """Test PAID tier has correct defaults."""
        ent = Entitlements.paid_tier()

        assert ent.tier == "PAID"
        assert ent.allow_recursive_scan is True  # Available to all users
        assert ent.allowed_output_formats == {"csv", "json", "excel", "xlsx"}
        assert ent.allow_monthly_summary is True  # Available to all users
        assert ent.allow_expense_analysis is True  # Available to all users
        assert ent.require_iban is False  # PAID tier: No IBAN required

    def test_free_tier_allows_json_output(self):
        """Test FREE tier allows JSON output."""
        ent = Entitlements.free_tier()

        # Should not raise
        ent.check_output_format("json")

    def test_free_tier_allows_xlsx_output(self):
        """Test FREE tier allows XLSX output."""
        ent = Entitlements.free_tier()

        # Should not raise
        ent.check_output_format("xlsx")

    def test_free_tier_allows_csv_output(self):
        """Test FREE tier allows CSV output."""
        ent = Entitlements.free_tier()

        # Should not raise
        ent.check_output_format("csv")
        ent.check_output_format("CSV")  # Case insensitive

    def test_paid_tier_allows_all_formats(self):
        """Test PAID tier allows all output formats."""
        ent = Entitlements.paid_tier()

        # All should not raise
        ent.check_output_format("csv")
        ent.check_output_format("json")
        ent.check_output_format("xlsx")
        ent.check_output_format("CSV")  # Case insensitive
        ent.check_output_format("JSON")

    def test_free_tier_allows_monthly_summary(self):
        """Test FREE tier allows monthly summary (available to all users)."""
        ent = Entitlements.free_tier()

        # Should not raise - monthly summary is available to all users
        ent.check_monthly_summary()

    def test_paid_tier_allows_monthly_summary(self):
        """Test PAID tier allows monthly summary."""
        ent = Entitlements.paid_tier()

        # Should not raise
        ent.check_monthly_summary()

    def test_free_tier_allows_recursive_scan(self):
        """Test FREE tier allows recursive scanning (available to all users)."""
        ent = Entitlements.free_tier()

        # Should not raise - recursive scanning is available to all users
        ent.check_recursive_scan()

    def test_paid_tier_allows_recursive_scan(self):
        """Test PAID tier allows recursive scanning."""
        ent = Entitlements.paid_tier()

        # Should not raise
        ent.check_recursive_scan()

    def test_free_tier_allows_expense_analysis(self):
        """Test FREE tier allows expense analysis (available to all users)."""
        ent = Entitlements.free_tier()

        # Should not raise
        ent.check_expense_analysis()

    def test_paid_tier_allows_expense_analysis(self):
        """Test PAID tier allows expense analysis (available to all users)."""
        ent = Entitlements.paid_tier()

        # Should not raise
        ent.check_expense_analysis()

    def test_entitlements_are_immutable(self):
        """Test that Entitlements dataclass is frozen (immutable)."""
        ent = Entitlements.free_tier()

        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            ent.tier = "PAID"  # type: ignore

    def test_custom_entitlements(self):
        """Test creating custom entitlements configuration."""
        ent = Entitlements(
            tier="PAID",
            allow_recursive_scan=False,  # Custom: PAID but no recursive
            allowed_output_formats={"csv", "json"},  # Custom: no xlsx
            allow_monthly_summary=True,
            allow_expense_analysis=True,
            require_iban=False,  # Custom: no IBAN requirement
        )

        assert ent.tier == "PAID"
        assert not ent.allow_recursive_scan
        assert ent.allowed_output_formats == {"csv", "json"}

        # xlsx should be blocked
        with pytest.raises(EntitlementError):
            ent.check_output_format("xlsx")

        # json should be allowed
        ent.check_output_format("json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
