"""Tests for expense analysis service."""

from __future__ import annotations

from bankstatements_core.services.expense_analysis import ExpenseAnalysisService


class TestExpenseAnalysisService:
    """Tests for ExpenseAnalysisService."""

    def test_initialization(self):
        """Test service initialization."""
        service = ExpenseAnalysisService()
        assert service is not None

    def test_analyze_empty_transactions(self):
        """Test analyzing empty transaction list."""
        service = ExpenseAnalysisService()
        result = service.analyze([])

        assert result["total_transactions_analyzed"] == 0
        assert result["insights"]["recurring_charges"] == []
        assert result["insights"]["high_value_transactions"] == []

    def test_analyze_single_transaction(self):
        """Test analyzing single transaction."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Test Transaction",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            }
        ]

        result = service.analyze(transactions)

        assert result["total_transactions_analyzed"] == 1
        assert result["insights"]["recurring_charges"] == []
        # Single transaction won't be outlier (std_dev = 0)
        assert len(result["insights"]["high_value_transactions"]) == 0

    def test_detect_recurring_charges_monthly_pattern(self):
        """Test detecting monthly recurring charges with exact description matching."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "NETFLIX SUBSCRIPTION",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jan 2023",
                "Details": "NETFLIX SUBSCRIPTION",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "984.01",
                "Filename": "test.pdf",
            },
            {
                "Date": "28 Feb 2023",
                "Details": "NETFLIX SUBSCRIPTION",  # Exact same description
                "Debit €": "16.49",  # +3% variation (within ±5%)
                "Credit €": "",
                "Balance €": "967.52",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Mar 2023",
                "Details": "NETFLIX SUBSCRIPTION",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "951.53",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        recurring = result["insights"]["recurring_charges"]
        assert len(recurring) == 1
        assert recurring[0]["description"] == "NETFLIX SUBSCRIPTION"
        assert recurring[0]["frequency"] == "monthly"
        assert recurring[0]["occurrences"] == 4
        assert 29 <= recurring[0]["average_interval_days"] <= 31

    def test_no_recurring_charges_for_variable_amounts(self):
        """Test that variable amounts don't match as recurring."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "GROCERY STORE",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "30 Jan 2023",
                "Details": "GROCERY STORE",
                "Debit €": "120.00",  # >5% variation
                "Credit €": "",
                "Balance €": "950.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        assert len(result["insights"]["recurring_charges"]) == 0

    def test_no_recurring_charges_for_irregular_intervals(self):
        """Test that intervals between bands (e.g. 11 days) don't match as recurring."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST CHARGE",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "12 Jan 2023",  # 11 days — between weekly (5-9) and fortnightly (12-16)
                "Details": "TEST CHARGE",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "950.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        assert len(result["insights"]["recurring_charges"]) == 0

    def test_detect_high_value_transactions(self):
        """Test detecting high-value outliers."""
        service = ExpenseAnalysisService()
        # Create transactions: 10 normal + 1 outlier
        normal_transactions = [
            {
                "Date": f"{i:02d} Jan 2023",
                "Details": f"Transaction {i}",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            }
            for i in range(1, 11)
        ]

        # Add a clear outlier (1000 vs average 100)
        outlier_transaction = {
            "Date": "15 Jan 2023",
            "Details": "LARGE PURCHASE",
            "Debit €": "1000.00",
            "Credit €": "",
            "Balance €": "1000.00",
            "Filename": "test.pdf",
        }

        transactions = normal_transactions + [outlier_transaction]
        result = service.analyze(transactions)

        high_value = result["insights"]["high_value_transactions"]
        assert len(high_value) > 0
        assert high_value[0]["description"] == "LARGE PURCHASE"
        assert high_value[0]["amount"] == 1000.00
        assert high_value[0]["is_outlier"] is True

    def test_no_outliers_for_uniform_amounts(self):
        """Test that uniform amounts don't produce outliers."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": f"{i:02d} Jan 2023",
                "Details": f"Transaction {i}",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            }
            for i in range(1, 6)
        ]

        result = service.analyze(transactions)

        # All same amount → std_dev = 0 → no outliers
        assert len(result["insights"]["high_value_transactions"]) == 0

    def test_statistics_calculation(self):
        """Test statistics are calculated correctly."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Transaction 1",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "02 Jan 2023",
                "Details": "Transaction 2",
                "Debit €": "200.00",
                "Credit €": "",
                "Balance €": "800.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "03 Jan 2023",
                "Details": "Transaction 3",
                "Debit €": "",
                "Credit €": "500.00",
                "Balance €": "1300.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        stats = result["insights"]["statistics"]
        assert stats["total_debits"] == 300.00
        assert stats["total_credits"] == 500.00
        assert stats["mean_transaction_amount"] > 0
        assert "std_dev" in stats

    def test_handle_missing_debit_credit_fields(self):
        """Test handling transactions with missing amount fields."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Test Transaction",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            }
        ]

        result = service.analyze(transactions)

        # Should not crash, returns empty insights
        assert result["total_transactions_analyzed"] == 1
        assert len(result["insights"]["recurring_charges"]) == 0

    def test_handle_invalid_date_format(self):
        """Test handling transactions with invalid dates."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "INVALID DATE",
                "Details": "Test",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "01 Jan 2023",
                "Details": "Test",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "900.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # Should handle gracefully, not crash
        assert result["total_transactions_analyzed"] == 2

    def test_normalize_description(self):
        """Test description normalization."""
        service = ExpenseAnalysisService()

        assert service._normalize_description("NETFLIX") == "netflix"
        assert service._normalize_description("  Netflix  ") == "netflix"
        assert (
            service._normalize_description("Netflix Subscription")
            == "netflix subscription"
        )
        assert service._normalize_description("") == ""

    def test_clean_amount_string(self):
        """Test amount string cleaning."""
        service = ExpenseAnalysisService()

        assert service._clean_amount_string("€100.00") == "100.00"
        assert service._clean_amount_string("$50.25") == "50.25"
        assert service._clean_amount_string("1,234.56") == "1234.56"
        assert service._clean_amount_string("  100.00  ") == "100.00"
        assert service._clean_amount_string("") == "0"

    def test_recurring_charges_with_credit_transactions(self):
        """Test recurring charges work with credit transactions too."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "SALARY PAYMENT",
                "Debit €": "",
                "Credit €": "2500.00",
                "Balance €": "2500.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jan 2023",
                "Details": "SALARY PAYMENT",
                "Debit €": "",
                "Credit €": "2500.00",
                "Balance €": "5000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "28 Feb 2023",
                "Details": "SALARY PAYMENT",
                "Debit €": "",
                "Credit €": "2500.00",
                "Balance €": "7500.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        recurring = result["insights"]["recurring_charges"]
        assert len(recurring) == 1
        assert recurring[0]["description"] == "SALARY PAYMENT"
        assert recurring[0]["average_amount"] == 2500.00

    def test_empty_insights_structure(self):
        """Test empty insights structure is correct."""
        service = ExpenseAnalysisService()
        empty = service._empty_insights()

        assert "summary" in empty
        assert "generated_at" in empty
        assert "total_transactions_analyzed" in empty
        assert empty["total_transactions_analyzed"] == 0
        assert "insights" in empty
        assert "recurring_charges" in empty["insights"]
        assert "high_value_transactions" in empty["insights"]
        assert "statistics" in empty["insights"]

    def test_empty_insights_with_error(self):
        """Test empty insights includes error message."""
        service = ExpenseAnalysisService()
        empty = service._empty_insights(error="Test error")

        assert "error" in empty
        assert empty["error"] == "Test error"

    def test_multiple_different_recurring_charges(self):
        """Test detecting multiple different recurring charges."""
        service = ExpenseAnalysisService()
        transactions = [
            # Netflix - monthly
            {
                "Date": "01 Jan 2023",
                "Details": "Netflix",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jan 2023",
                "Details": "Netflix",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "984.01",
                "Filename": "test.pdf",
            },
            {
                "Date": "28 Feb 2023",
                "Details": "Netflix",
                "Debit €": "15.99",
                "Credit €": "",
                "Balance €": "968.02",
                "Filename": "test.pdf",
            },
            # Spotify - monthly
            {
                "Date": "05 Jan 2023",
                "Details": "Spotify",
                "Debit €": "9.99",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "05 Feb 2023",
                "Details": "Spotify",
                "Debit €": "9.99",
                "Credit €": "",
                "Balance €": "990.01",
                "Filename": "test.pdf",
            },
            {
                "Date": "05 Mar 2023",
                "Details": "Spotify",
                "Debit €": "9.99",
                "Credit €": "",
                "Balance €": "980.02",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        recurring = result["insights"]["recurring_charges"]
        assert len(recurring) == 2

        descriptions = [r["description"] for r in recurring]
        assert "Netflix" in descriptions
        assert "Spotify" in descriptions

    def test_boundary_interval_25_days(self):
        """Test 25-day interval is detected (lower boundary)."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "26 Jan 2023",  # 25 days later
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "950.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # 25 days should be detected as recurring
        assert len(result["insights"]["recurring_charges"]) == 1

    def test_boundary_interval_35_days(self):
        """Test 35-day interval is detected (upper boundary)."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "05 Feb 2023",  # 35 days later
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "950.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # 35 days should be detected as recurring
        assert len(result["insights"]["recurring_charges"]) == 1

    def test_boundary_interval_24_days_not_detected(self):
        """Test 24-day interval is NOT detected (just below boundary)."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "25 Jan 2023",  # 24 days later
                "Details": "TEST",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "950.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # 24 days should NOT be detected
        assert len(result["insights"]["recurring_charges"]) == 0

    def test_boundary_amount_variance_5_percent(self):
        """Test 5% amount variance is accepted."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jan 2023",
                "Details": "TEST",
                "Debit €": "105.00",  # Exactly +5%
                "Credit €": "",
                "Balance €": "895.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # 5% variance should be accepted
        assert len(result["insights"]["recurring_charges"]) == 1

    def test_boundary_amount_variance_6_percent_rejected(self):
        """Test amount variance >5% from average is rejected."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "TEST",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "1000.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jan 2023",
                "Details": "TEST",
                "Debit €": "120.00",  # Average would be 110, so 100 is -9%, 120 is +9% > 5%
                "Credit €": "",
                "Balance €": "880.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # >5% variance from average should be rejected
        assert len(result["insights"]["recurring_charges"]) == 0

    def test_repeated_vendors_detection(self):
        """Test detection of repeated vendors with varying amounts."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "13 Jan 2025",
                "Details": "VDP-TRIA ENERGY LT",
                "Debit €": "515.00",
                "Credit €": "",
                "Balance €": "9334.33",
                "Filename": "test.pdf",
            },
            {
                "Date": "31 Jul 2025",
                "Details": "VDP-TRIA ENERGY LT",
                "Debit €": "800.00",
                "Credit €": "",
                "Balance €": "8500.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "15 Feb 2025",
                "Details": "Other Vendor",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "9000.00",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        # Should detect TRIA as repeated vendor (not single transaction vendors)
        repeated = result["insights"]["repeated_vendors"]
        assert len(repeated) == 1
        assert repeated[0]["description"] == "VDP-TRIA ENERGY LT"
        assert repeated[0]["transaction_count"] == 2
        assert repeated[0]["total_spent"] == 1315.00
        assert repeated[0]["average_amount"] == 657.50
        assert repeated[0]["min_amount"] == 515.00
        assert repeated[0]["max_amount"] == 800.00
        assert len(repeated[0]["transactions"]) == 2

    def test_repeated_vendors_sorted_by_total_spent(self):
        """Test that repeated vendors are sorted by total spent descending."""
        service = ExpenseAnalysisService()
        transactions = [
            # Vendor A: 2 transactions, total 100
            {
                "Date": "1 Jan 2025",
                "Details": "Vendor A",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "1000",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "Vendor A",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "950",
                "Filename": "test.pdf",
            },
            # Vendor B: 2 transactions, total 500
            {
                "Date": "3 Jan 2025",
                "Details": "Vendor B",
                "Debit €": "200",
                "Credit €": "",
                "Balance €": "750",
                "Filename": "test.pdf",
            },
            {
                "Date": "4 Jan 2025",
                "Details": "Vendor B",
                "Debit €": "300",
                "Credit €": "",
                "Balance €": "450",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        assert len(repeated) == 2
        # Should be sorted by total_spent descending
        assert repeated[0]["description"] == "Vendor B"
        assert repeated[0]["total_spent"] == 500.00
        assert repeated[1]["description"] == "Vendor A"
        assert repeated[1]["total_spent"] == 100.00

    def test_repeated_vendors_excludes_single_transactions(self):
        """Test that vendors with only 1 transaction are excluded."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "1 Jan 2025",
                "Details": "Single Vendor",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "1000",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "Repeated Vendor",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "950",
                "Filename": "test.pdf",
            },
            {
                "Date": "3 Jan 2025",
                "Details": "Repeated Vendor",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "900",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        assert len(repeated) == 1
        assert repeated[0]["description"] == "Repeated Vendor"
        # Single Vendor should not appear

    def test_repeated_vendors_with_credit_transactions(self):
        """Test repeated vendors detection with credit transactions."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "1 Jan 2025",
                "Details": "Refund Company",
                "Debit €": "",
                "Credit €": "100",
                "Balance €": "1100",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "Refund Company",
                "Debit €": "",
                "Credit €": "200",
                "Balance €": "1300",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        assert len(repeated) == 1
        assert repeated[0]["description"] == "Refund Company"
        assert repeated[0]["total_spent"] == 300.00
        assert repeated[0]["transaction_count"] == 2

    def test_repeated_vendors_with_empty_descriptions(self):
        """Test that transactions with empty descriptions are excluded."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "1 Jan 2025",
                "Details": "",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "950",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "",
                "Debit €": "50",
                "Credit €": "",
                "Balance €": "900",
                "Filename": "test.pdf",
            },
            {
                "Date": "3 Jan 2025",
                "Details": "Valid Vendor",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "800",
                "Filename": "test.pdf",
            },
            {
                "Date": "4 Jan 2025",
                "Details": "Valid Vendor",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "700",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        # Only Valid Vendor should be detected (empty descriptions excluded)
        assert len(repeated) == 1
        assert repeated[0]["description"] == "Valid Vendor"

    def test_repeated_vendors_invalid_amounts_excluded(self):
        """Test that transactions with invalid amounts are handled gracefully."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "1 Jan 2025",
                "Details": "Bad Amounts",
                "Debit €": "invalid",
                "Credit €": "",
                "Balance €": "1000",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "Bad Amounts",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "1000",
                "Filename": "test.pdf",
            },
            {
                "Date": "3 Jan 2025",
                "Details": "Good Vendor",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "900",
                "Filename": "test.pdf",
            },
            {
                "Date": "4 Jan 2025",
                "Details": "Good Vendor",
                "Debit €": "200",
                "Credit €": "",
                "Balance €": "700",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        # Bad Amounts should be excluded (no valid amounts), only Good Vendor included
        assert len(repeated) == 1
        assert repeated[0]["description"] == "Good Vendor"

    def test_repeated_vendors_date_sorting_failure_handled(self):
        """Test that invalid dates don't crash repeated vendors detection."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "invalid-date",
                "Details": "Test Vendor",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "1000",
                "Filename": "test.pdf",
            },
            {
                "Date": "another-bad-date",
                "Details": "Test Vendor",
                "Debit €": "200",
                "Credit €": "",
                "Balance €": "800",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        # Should still detect the vendor even with bad dates (uses unsorted fallback)
        assert len(repeated) == 1
        assert repeated[0]["description"] == "Test Vendor"
        assert repeated[0]["total_spent"] == 300.00

    def test_repeated_vendors_empty_list_when_no_repeats(self):
        """Test that empty list is returned when no vendors have multiple transactions."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "1 Jan 2025",
                "Details": "Vendor A",
                "Debit €": "100",
                "Credit €": "",
                "Balance €": "900",
                "Filename": "test.pdf",
            },
            {
                "Date": "2 Jan 2025",
                "Details": "Vendor B",
                "Debit €": "200",
                "Credit €": "",
                "Balance €": "700",
                "Filename": "test.pdf",
            },
            {
                "Date": "3 Jan 2025",
                "Details": "Vendor C",
                "Debit €": "300",
                "Credit €": "",
                "Balance €": "400",
                "Filename": "test.pdf",
            },
        ]

        result = service.analyze(transactions)

        repeated = result["insights"]["repeated_vendors"]
        assert len(repeated) == 0

    def test_empty_insights_includes_repeated_vendors(self):
        """Test that empty insights structure includes repeated_vendors field."""
        service = ExpenseAnalysisService()
        result = service._empty_insights()

        assert "repeated_vendors" in result["insights"]

    def test_analyze_returns_empty_insights_on_unexpected_error(self):
        """Test except Exception handler returns empty insights with error key."""
        from unittest.mock import patch

        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Test",
                "Debit €": "10.00",
                "Credit €": "",
                "Balance €": "100.00",
                "Filename": "test.pdf",
            }
        ]
        with patch.object(
            service, "_detect_recurring_charges", side_effect=RuntimeError("boom")
        ):
            result = service.analyze(transactions)

        assert result["total_transactions_analyzed"] == 0
        assert result["insights"]["recurring_charges"] == []
        assert result["error"] == "boom"

    def test_analyze_skips_transactions_with_empty_description(self):
        """Test _group_similar_descriptions skips empty-details transactions."""
        service = ExpenseAnalysisService()
        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "",
                "Debit €": "10.00",
                "Credit €": "",
                "Balance €": "100.00",
                "Filename": "test.pdf",
            },
            {
                "Date": "15 Jan 2023",
                "Details": "",
                "Debit €": "20.00",
                "Credit €": "",
                "Balance €": "80.00",
                "Filename": "test.pdf",
            },
        ]
        result = service.analyze(transactions)

        assert result["total_transactions_analyzed"] == 2
        assert result["insights"]["recurring_charges"] == []
        assert result["insights"]["repeated_vendors"] == []


def _tx(date: str, details: str, debit: str) -> dict:
    return {
        "Date": date,
        "Details": details,
        "Debit €": debit,
        "Credit €": "",
        "Balance €": "1000.00",
        "Filename": "test.pdf",
    }


class TestRecurringChargesEnrichment:
    """Tests for enriched recurring charge fields added in the intelligence extension."""

    def _netflix_txns(self) -> list[dict]:
        return [
            _tx("01 Jan 2023", "NETFLIX SUBSCRIPTION", "17.99"),
            _tx("01 Feb 2023", "NETFLIX SUBSCRIPTION", "17.99"),
            _tx("01 Mar 2023", "NETFLIX SUBSCRIPTION", "17.99"),
            _tx("01 Apr 2023", "NETFLIX SUBSCRIPTION", "17.99"),
        ]

    def test_new_fields_present(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        for key in (
            "frequency",
            "average_amount",
            "amount_variation",
            "first_occurrence",
            "last_occurrence",
            "annualised_cost",
            "next_expected",
            "is_subscription",
            "confidence",
        ):
            assert key in rec, f"Missing key: {key}"

    def test_first_and_last_occurrence(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        assert rec["first_occurrence"] == "01 Jan 2023"
        assert rec["last_occurrence"] == "01 Apr 2023"

    def test_annualised_cost_monthly(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        assert rec["frequency"] == "monthly"
        assert abs(rec["annualised_cost"] - 17.99 * 12) < 0.02

    def test_amount_variation_zero_for_identical_amounts(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        assert rec["amount_variation"] == 0.0

    def test_next_expected_date(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        # Last = 01 Apr 2023, avg_interval = (31+28+31)/3 = 30 days → 01 May 2023
        assert rec["next_expected"] == "01 May 2023"

    def test_is_subscription_true_for_netflix(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        assert rec["is_subscription"] is True

    def test_is_subscription_false_for_non_subscription(self):
        txns = [
            _tx("01 Jan 2023", "LANDLORD RENT", "1200.00"),
            _tx("01 Feb 2023", "LANDLORD RENT", "1200.00"),
            _tx("01 Mar 2023", "LANDLORD RENT", "1200.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        rec = result["insights"]["recurring_charges"][0]
        assert rec["is_subscription"] is False

    def test_confidence_high_for_consistent_payments(self):
        result = ExpenseAnalysisService().analyze(self._netflix_txns())
        rec = result["insights"]["recurring_charges"][0]
        assert rec["confidence"] >= 0.85

    def test_confidence_between_0_and_1(self):
        txns = [
            _tx("01 Jan 2023", "GYM MEMBERSHIP", "45.00"),
            _tx("30 Jan 2023", "GYM MEMBERSHIP", "46.00"),  # ~4% variation
        ]
        result = ExpenseAnalysisService().analyze(txns)
        recurring = result["insights"]["recurring_charges"]
        if recurring:
            assert 0.0 <= recurring[0]["confidence"] <= 1.0

    def test_weekly_frequency_detected(self):
        txns = [
            _tx("01 Jan 2023", "COFFEE CLUB", "5.00"),
            _tx("08 Jan 2023", "COFFEE CLUB", "5.00"),
            _tx("15 Jan 2023", "COFFEE CLUB", "5.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        rec = result["insights"]["recurring_charges"][0]
        assert rec["frequency"] == "weekly"
        assert abs(rec["annualised_cost"] - 5.00 * 52) < 0.02

    def test_quarterly_frequency_detected(self):
        txns = [
            _tx("01 Jan 2023", "INSURANCE PREMIUM", "300.00"),
            _tx("01 Apr 2023", "INSURANCE PREMIUM", "300.00"),
            _tx("01 Jul 2023", "INSURANCE PREMIUM", "300.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        rec = result["insights"]["recurring_charges"][0]
        assert rec["frequency"] == "quarterly"
        assert abs(rec["annualised_cost"] - 300.00 * 4) < 0.02

    def test_annual_frequency_detected(self):
        txns = [
            _tx("01 Jan 2022", "DOMAIN RENEWAL", "15.00"),
            _tx("01 Jan 2023", "DOMAIN RENEWAL", "15.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        rec = result["insights"]["recurring_charges"][0]
        assert rec["frequency"] == "annual"
        assert rec["annualised_cost"] == 15.00

    def test_fortnightly_frequency_detected(self):
        txns = [
            _tx("01 Jan 2023", "PAYROLL DEDUCTION", "50.00"),
            _tx("15 Jan 2023", "PAYROLL DEDUCTION", "50.00"),
            _tx("29 Jan 2023", "PAYROLL DEDUCTION", "50.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        rec = result["insights"]["recurring_charges"][0]
        assert rec["frequency"] == "fortnightly"
        assert abs(rec["annualised_cost"] - 50.00 * 26) < 0.02

    def test_gap_interval_not_detected(self):
        """11-day interval falls between weekly and fortnightly — not detected."""
        txns = [
            _tx("01 Jan 2023", "MYSTERY CHARGE", "10.00"),
            _tx("12 Jan 2023", "MYSTERY CHARGE", "10.00"),
        ]
        result = ExpenseAnalysisService().analyze(txns)
        assert result["insights"]["recurring_charges"] == []


class TestRecurringIntelligenceToggle:
    """Tests for recurring_intelligence=False legacy mode."""

    def _monthly_txns(self) -> list[dict]:
        return [
            _tx("01 Jan 2023", "SPOTIFY", "9.99"),
            _tx("01 Feb 2023", "SPOTIFY", "9.99"),
            _tx("01 Mar 2023", "SPOTIFY", "9.99"),
        ]

    def test_legacy_mode_monthly_detected(self):
        svc = ExpenseAnalysisService(recurring_intelligence=False)
        result = svc.analyze(self._monthly_txns())
        recurring = result["insights"]["recurring_charges"]
        assert len(recurring) == 1
        assert recurring[0]["frequency"] == "monthly"

    def test_legacy_mode_basic_fields_only(self):
        svc = ExpenseAnalysisService(recurring_intelligence=False)
        result = svc.analyze(self._monthly_txns())
        rec = result["insights"]["recurring_charges"][0]
        for key in ("description", "average_amount", "frequency", "occurrences", "transactions", "average_interval_days"):
            assert key in rec
        for enriched_key in ("amount_variation", "first_occurrence", "last_occurrence", "annualised_cost", "next_expected", "is_subscription", "confidence"):
            assert enriched_key not in rec

    def test_legacy_mode_weekly_not_detected(self):
        svc = ExpenseAnalysisService(recurring_intelligence=False)
        txns = [
            _tx("01 Jan 2023", "COFFEE CLUB", "5.00"),
            _tx("08 Jan 2023", "COFFEE CLUB", "5.00"),
            _tx("15 Jan 2023", "COFFEE CLUB", "5.00"),
        ]
        result = svc.analyze(txns)
        assert result["insights"]["recurring_charges"] == []

    def test_legacy_mode_quarterly_not_detected(self):
        svc = ExpenseAnalysisService(recurring_intelligence=False)
        txns = [
            _tx("01 Jan 2023", "INSURANCE", "300.00"),
            _tx("01 Apr 2023", "INSURANCE", "300.00"),
            _tx("01 Jul 2023", "INSURANCE", "300.00"),
        ]
        result = svc.analyze(txns)
        assert result["insights"]["recurring_charges"] == []

    def test_default_is_intelligence_on(self):
        svc = ExpenseAnalysisService()
        assert svc.recurring_intelligence is True

    def test_toggle_off_explicit(self):
        svc = ExpenseAnalysisService(recurring_intelligence=False)
        assert svc.recurring_intelligence is False
