"""Tests for monthly summary service entitlement enforcement."""

from __future__ import annotations

import pytest

from bankstatements_core.entitlements import EntitlementError, Entitlements
from bankstatements_core.services.monthly_summary import MonthlySummaryService


class TestMonthlySummaryEntitlements:
    """Test entitlement enforcement for monthly summary generation."""

    def test_free_tier_allows_monthly_summary(self):
        """Test FREE tier allows monthly summary generation."""
        free_ent = Entitlements.free_tier()

        service = MonthlySummaryService(
            debit_columns=["Debit"],
            credit_columns=["Credit"],
            entitlements=free_ent,
        )

        transactions = [
            {"Date": "01/01/2024", "Debit": "100.00", "Credit": ""},
            {"Date": "02/01/2024", "Debit": "", "Credit": "50.00"},
        ]

        # Should not raise - FREE tier has access
        summary = service.generate(transactions)

        assert summary is not None
        assert "monthly_data" in summary
        assert summary["total_months"] >= 0

    def test_paid_tier_allows_monthly_summary(self):
        """Test PAID tier allows monthly summary generation."""
        paid_ent = Entitlements.paid_tier()

        service = MonthlySummaryService(
            debit_columns=["Debit"],
            credit_columns=["Credit"],
            entitlements=paid_ent,
        )

        transactions = [
            {"Date": "01/01/2024", "Debit": "100.00", "Credit": ""},
            {"Date": "02/01/2024", "Debit": "", "Credit": "50.00"},
        ]

        # Should not raise
        summary = service.generate(transactions)

        assert summary is not None
        assert "monthly_data" in summary
        assert summary["total_months"] >= 0

    def test_no_entitlements_allows_generation(self):
        """Test that service works without entitlements (backwards compatibility)."""
        # When entitlements=None, no enforcement
        service = MonthlySummaryService(
            debit_columns=["Debit"],
            credit_columns=["Credit"],
            entitlements=None,  # No enforcement
        )

        transactions = [
            {"Date": "01/01/2024", "Debit": "100.00", "Credit": ""},
        ]

        # Should not raise (no enforcement)
        summary = service.generate(transactions)
        assert summary is not None

    def test_paid_tier_with_empty_transactions(self):
        """Test PAID tier handles empty transactions list."""
        paid_ent = Entitlements.paid_tier()

        service = MonthlySummaryService(
            debit_columns=["Debit"],
            credit_columns=["Credit"],
            entitlements=paid_ent,
        )

        # Empty transactions list
        summary = service.generate([])

        assert summary is not None
        assert summary["total_months"] == 0
        assert summary["monthly_data"] == []

    def test_paid_tier_generates_correct_summary(self):
        """Test PAID tier generates correct monthly summary data."""
        paid_ent = Entitlements.paid_tier()

        service = MonthlySummaryService(
            debit_columns=["Debit"],
            credit_columns=["Credit"],
            entitlements=paid_ent,
        )

        transactions = [
            {"Date": "01/01/2024", "Debit": "100.00", "Credit": ""},
            {"Date": "15/01/2024", "Debit": "50.00", "Credit": ""},
            {"Date": "01/02/2024", "Debit": "", "Credit": "200.00"},
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 2
        assert len(summary["monthly_data"]) == 2

        # Check first month (January 2024)
        jan_data = summary["monthly_data"][0]
        assert jan_data["Month"] == "2024-01"
        assert jan_data["Debit"] == 150.0  # 100 + 50
        assert jan_data["Total Debit Transactions"] == 2

        # Check second month (February 2024)
        feb_data = summary["monthly_data"][1]
        assert feb_data["Month"] == "2024-02"
        assert feb_data["Credit"] == 200.0
        assert feb_data["Total Credit Transactions"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
