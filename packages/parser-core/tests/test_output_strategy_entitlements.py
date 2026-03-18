"""Tests for output strategy entitlement enforcement."""

from __future__ import annotations

import pytest

from bankstatements_core.entitlements import EntitlementError, Entitlements
from bankstatements_core.patterns.strategies import (
    CSVOutputStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
    create_output_strategy,
)


class TestOutputStrategyEntitlements:
    """Test entitlement enforcement for output strategies."""

    def test_free_tier_allows_csv(self):
        """Test FREE tier allows CSV output."""
        free_ent = Entitlements.free_tier()

        # Should not raise
        strategy = create_output_strategy("csv", free_ent)
        assert isinstance(strategy, CSVOutputStrategy)

    def test_free_tier_allows_csv_case_insensitive(self):
        """Test FREE tier allows CSV in any case."""
        free_ent = Entitlements.free_tier()

        # Should not raise
        strategy = create_output_strategy("CSV", free_ent)
        assert isinstance(strategy, CSVOutputStrategy)

    def test_free_tier_allows_json(self):
        """Test FREE tier allows JSON output."""
        free_ent = Entitlements.free_tier()

        # Should not raise
        strategy = create_output_strategy("json", free_ent)
        assert isinstance(strategy, JSONOutputStrategy)

    def test_free_tier_allows_excel(self):
        """Test FREE tier allows Excel output."""
        free_ent = Entitlements.free_tier()

        # Should not raise - "excel" normalizes to "xlsx"
        create_output_strategy("excel", free_ent)
        # Excel strategy might not be imported if openpyxl not installed
        # Just verify no entitlement error

    def test_free_tier_allows_xlsx(self):
        """Test FREE tier allows XLSX output."""
        free_ent = Entitlements.free_tier()

        # Should not raise
        create_output_strategy("xlsx", free_ent)
        # Excel strategy might not be imported if openpyxl not installed
        # Just verify no entitlement error

    def test_paid_tier_allows_csv(self):
        """Test PAID tier allows CSV output."""
        paid_ent = Entitlements.paid_tier()

        strategy = create_output_strategy("csv", paid_ent)
        assert isinstance(strategy, CSVOutputStrategy)

    def test_paid_tier_allows_json(self):
        """Test PAID tier allows JSON output."""
        paid_ent = Entitlements.paid_tier()

        strategy = create_output_strategy("json", paid_ent)
        assert isinstance(strategy, JSONOutputStrategy)

    def test_paid_tier_allows_excel(self):
        """Test PAID tier allows Excel output."""
        paid_ent = Entitlements.paid_tier()

        strategy = create_output_strategy("excel", paid_ent)
        assert isinstance(strategy, ExcelOutputStrategy)

    def test_paid_tier_allows_xlsx(self):
        """Test PAID tier allows XLSX output (alias for excel)."""
        paid_ent = Entitlements.paid_tier()

        strategy = create_output_strategy("xlsx", paid_ent)
        assert isinstance(strategy, ExcelOutputStrategy)

    def test_paid_tier_all_formats_case_insensitive(self):
        """Test PAID tier allows all formats regardless of case."""
        paid_ent = Entitlements.paid_tier()

        # All should work
        create_output_strategy("CSV", paid_ent)
        create_output_strategy("Json", paid_ent)
        create_output_strategy("XLSX", paid_ent)
        create_output_strategy("Excel", paid_ent)

    def test_invalid_format_on_paid_tier_raises_entitlement_error(self):
        """Test that invalid format names are caught by entitlement check on PAID tier."""
        paid_ent = Entitlements.paid_tier()

        # Since PAID tier checks entitlements first, invalid formats
        # will raise EntitlementError (not ValueError)
        with pytest.raises(EntitlementError) as exc_info:
            create_output_strategy("pdf", paid_ent)

        assert "pdf" in str(exc_info.value).lower()

    def test_invalid_format_on_free_tier_raises_entitlement_error(self):
        """Test that invalid format names are caught by entitlement check on FREE tier."""
        free_ent = Entitlements.free_tier()

        # Invalid format raises EntitlementError (checked before format validation)
        with pytest.raises(EntitlementError):
            create_output_strategy("invalid", free_ent)

        with pytest.raises(EntitlementError):
            create_output_strategy("pdf", free_ent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
