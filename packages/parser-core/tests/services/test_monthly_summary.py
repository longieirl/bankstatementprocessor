"""Tests for monthly summary service."""

from __future__ import annotations

from bankstatements_core.services.monthly_summary import MonthlySummaryService


class TestMonthlySummaryService:
    """Tests for MonthlySummaryService."""

    def test_initialization(self):
        """Test service initialization."""
        debit_cols = ["Debit €"]
        credit_cols = ["Credit €"]
        service = MonthlySummaryService(debit_cols, credit_cols)
        assert service.debit_columns == debit_cols
        assert service.credit_columns == credit_cols

    def test_generate_single_month(self):
        """Test generating summary for single month."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Transaction 1",
                "Debit €": "50.00",
                "Credit €": "",
            },
            {
                "Date": "15 Jan 2023",
                "Details": "Transaction 2",
                "Debit €": "",
                "Credit €": "100.00",
            },
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 1
        assert len(summary["monthly_data"]) == 1
        assert summary["monthly_data"][0]["Month"] == "2023-01"
        assert summary["monthly_data"][0]["Debit"] == 50.00
        assert summary["monthly_data"][0]["Total Debit Transactions"] == 1
        assert summary["monthly_data"][0]["Credit"] == 100.00
        assert summary["monthly_data"][0]["Total Credit Transactions"] == 1

    def test_generate_multiple_months(self):
        """Test generating summary for multiple months."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "50.00", "Credit €": ""},
            {"Date": "15 Feb 2023", "Debit €": "", "Credit €": "100.00"},
            {"Date": "10 Mar 2023", "Debit €": "25.00", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 3
        assert len(summary["monthly_data"]) == 3
        # Should be sorted by month
        assert summary["monthly_data"][0]["Month"] == "2023-01"
        assert summary["monthly_data"][1]["Month"] == "2023-02"
        assert summary["monthly_data"][2]["Month"] == "2023-03"

    def test_generate_empty_transactions(self):
        """Test generating summary with empty transaction list."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        summary = service.generate([])

        assert summary["total_months"] == 0
        assert len(summary["monthly_data"]) == 0

    def test_generate_multiple_transactions_same_month(self):
        """Test multiple transactions in the same month."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "50.00", "Credit €": ""},
            {"Date": "10 Jan 2023", "Debit €": "30.00", "Credit €": ""},
            {"Date": "20 Jan 2023", "Debit €": "", "Credit €": "100.00"},
            {"Date": "25 Jan 2023", "Debit €": "", "Credit €": "50.00"},
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 1
        monthly = summary["monthly_data"][0]
        assert monthly["Debit"] == 80.00  # 50 + 30
        assert monthly["Total Debit Transactions"] == 2
        assert monthly["Credit"] == 150.00  # 100 + 50
        assert monthly["Total Credit Transactions"] == 2

    def test_generate_with_zero_amounts(self):
        """Test that zero amounts are not counted."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "0.00", "Credit €": ""},
            {"Date": "10 Jan 2023", "Debit €": "50.00", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        monthly = summary["monthly_data"][0]
        assert monthly["Debit"] == 50.00
        assert monthly["Total Debit Transactions"] == 1  # Only non-zero

    def test_generate_with_empty_amounts(self):
        """Test handling of empty amount values."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "", "Credit €": ""},
            {"Date": "10 Jan 2023", "Debit €": "50.00", "Credit €": "100.00"},
        ]

        summary = service.generate(transactions)

        monthly = summary["monthly_data"][0]
        assert monthly["Debit"] == 50.00
        assert monthly["Credit"] == 100.00

    def test_generate_with_multiple_debit_columns(self):
        """Test with multiple debit columns."""
        service = MonthlySummaryService(["Debit €", "Debit $"], ["Credit €"])
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Debit €": "50.00",
                "Debit $": "25.00",
                "Credit €": "",
            }
        ]

        summary = service.generate(transactions)

        monthly = summary["monthly_data"][0]
        # Should sum both debit columns
        assert monthly["Debit"] == 75.00
        assert monthly["Total Debit Transactions"] == 2

    def test_generate_with_multiple_credit_columns(self):
        """Test with multiple credit columns."""
        service = MonthlySummaryService(["Debit €"], ["Credit €", "Credit $"])
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Debit €": "",
                "Credit €": "100.00",
                "Credit $": "50.00",
            }
        ]

        summary = service.generate(transactions)

        monthly = summary["monthly_data"][0]
        # Should sum both credit columns
        assert monthly["Credit"] == 150.00
        assert monthly["Total Credit Transactions"] == 2

    def test_generate_with_missing_date(self):
        """Test handling transactions with missing dates."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "", "Debit €": "50.00", "Credit €": ""},
            {"Date": "01 Jan 2023", "Debit €": "30.00", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        # Should have 2 months: "Unknown" and "2023-01"
        assert summary["total_months"] == 2

    def test_generate_with_different_date_formats(self):
        """Test with various date formats."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "50.00", "Credit €": ""},
            {"Date": "15/02/2023", "Debit €": "30.00", "Credit €": ""},
            {"Date": "10-03-2023", "Debit €": "25.00", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 3
        # All should parse to correct months
        assert summary["monthly_data"][0]["Month"] == "2023-01"
        assert summary["monthly_data"][1]["Month"] == "2023-02"
        assert summary["monthly_data"][2]["Month"] == "2023-03"

    def test_generate_includes_metadata(self):
        """Test that summary includes required metadata."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [{"Date": "01 Jan 2023", "Debit €": "50.00", "Credit €": ""}]

        summary = service.generate(transactions)

        assert "summary" in summary
        assert summary["summary"] == "Monthly Transaction Summary"
        assert "generated_at" in summary
        assert "total_months" in summary
        assert "monthly_data" in summary

    def test_generate_rounds_amounts(self):
        """Test that amounts are rounded to 2 decimal places."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Jan 2023", "Debit €": "50.123", "Credit €": ""},
            {"Date": "10 Jan 2023", "Debit €": "30.456", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        monthly = summary["monthly_data"][0]
        # Should round to 2 decimal places
        assert monthly["Debit"] == 80.58  # 50.123 + 30.456 = 80.579 -> 80.58

    def test_generate_year_spanning_transactions(self):
        """Test transactions spanning multiple years."""
        service = MonthlySummaryService(["Debit €"], ["Credit €"])
        transactions = [
            {"Date": "01 Dec 2022", "Debit €": "50.00", "Credit €": ""},
            {"Date": "15 Jan 2023", "Debit €": "30.00", "Credit €": ""},
            {"Date": "10 Feb 2023", "Debit €": "25.00", "Credit €": ""},
        ]

        summary = service.generate(transactions)

        assert summary["total_months"] == 3
        assert summary["monthly_data"][0]["Month"] == "2022-12"
        assert summary["monthly_data"][1]["Month"] == "2023-01"
        assert summary["monthly_data"][2]["Month"] == "2023-02"
