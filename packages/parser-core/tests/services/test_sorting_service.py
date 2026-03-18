"""Tests for transaction sorting service."""

from __future__ import annotations

import pytest

from bankstatements_core.services.sorting_service import (
    ChronologicalSortingStrategy,
    NoSortingStrategy,
    TransactionSortingService,
)


class TestChronologicalSortingStrategy:
    """Tests for ChronologicalSortingStrategy."""

    def test_sort_chronologically(self):
        """Test sorting transactions by date chronologically."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            {"Date": "15 Jan 2023", "Details": "Transaction 3"},
            {"Date": "01 Jan 2023", "Details": "Transaction 1"},
            {"Date": "10 Jan 2023", "Details": "Transaction 2"},
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0]["Details"] == "Transaction 1"  # 01 Jan
        assert sorted_txns[1]["Details"] == "Transaction 2"  # 10 Jan
        assert sorted_txns[2]["Details"] == "Transaction 3"  # 15 Jan

    def test_sort_with_different_date_formats(self):
        """Test sorting with various date formats."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            {"Date": "15/01/2023", "Details": "Transaction 3"},
            {"Date": "01 Jan 2023", "Details": "Transaction 1"},
            {"Date": "10-01-2023", "Details": "Transaction 2"},
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        # All are from January 2023, so should sort by day
        assert sorted_txns[0]["Details"] == "Transaction 1"  # Day 1
        assert sorted_txns[1]["Details"] == "Transaction 2"  # Day 10
        assert sorted_txns[2]["Details"] == "Transaction 3"  # Day 15

    def test_sort_empty_list(self):
        """Test sorting empty transaction list."""
        strategy = ChronologicalSortingStrategy()
        sorted_txns = strategy.sort([])
        assert len(sorted_txns) == 0

    def test_sort_single_transaction(self):
        """Test sorting single transaction."""
        strategy = ChronologicalSortingStrategy()
        transactions = [{"Date": "01 Jan 2023", "Details": "Single"}]
        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 1
        assert sorted_txns[0]["Details"] == "Single"

    def test_sort_with_missing_dates(self):
        """Test sorting when some transactions have missing dates."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            {"Date": "15 Jan 2023", "Details": "Has date"},
            {"Date": "", "Details": "No date"},
            {"Date": "01 Jan 2023", "Details": "Has date 2"},
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        # Transactions with empty dates should sort to beginning (epoch date)

    def test_sort_same_dates(self):
        """Test sorting transactions with same dates."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            {"Date": "01 Jan 2023", "Details": "Transaction A"},
            {"Date": "01 Jan 2023", "Details": "Transaction B"},
            {"Date": "01 Jan 2023", "Details": "Transaction C"},
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        # All have same date, order may be stable or not


class TestNoSortingStrategy:
    """Tests for NoSortingStrategy."""

    def test_keeps_original_order(self):
        """Test that original order is preserved."""
        strategy = NoSortingStrategy()
        transactions = [
            {"Date": "15 Jan 2023", "Details": "Transaction 3"},
            {"Date": "01 Jan 2023", "Details": "Transaction 1"},
            {"Date": "10 Jan 2023", "Details": "Transaction 2"},
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0]["Details"] == "Transaction 3"
        assert sorted_txns[1]["Details"] == "Transaction 1"
        assert sorted_txns[2]["Details"] == "Transaction 2"

    def test_no_sort_empty_list(self):
        """Test with empty transaction list."""
        strategy = NoSortingStrategy()
        sorted_txns = strategy.sort([])
        assert len(sorted_txns) == 0

    def test_no_sort_single_transaction(self):
        """Test with single transaction."""
        strategy = NoSortingStrategy()
        transactions = [{"Date": "01 Jan 2023", "Details": "Single"}]
        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 1
        assert sorted_txns[0]["Details"] == "Single"


class TestTransactionSortingService:
    """Tests for TransactionSortingService."""

    def test_initialization_with_chronological_strategy(self):
        """Test service initialization with chronological strategy."""
        strategy = ChronologicalSortingStrategy()
        service = TransactionSortingService(strategy)
        assert service.strategy == strategy

    def test_initialization_with_no_sorting_strategy(self):
        """Test service initialization with no sorting strategy."""
        strategy = NoSortingStrategy()
        service = TransactionSortingService(strategy)
        assert service.strategy == strategy

    def test_sort_with_chronological_strategy(self):
        """Test sorting using chronological strategy."""
        strategy = ChronologicalSortingStrategy()
        service = TransactionSortingService(strategy)

        transactions = [
            {"Date": "15 Jan 2023", "Details": "Transaction 3"},
            {"Date": "01 Jan 2023", "Details": "Transaction 1"},
            {"Date": "10 Jan 2023", "Details": "Transaction 2"},
        ]

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0]["Details"] == "Transaction 1"
        assert sorted_txns[1]["Details"] == "Transaction 2"
        assert sorted_txns[2]["Details"] == "Transaction 3"

    def test_sort_with_no_sorting_strategy(self):
        """Test sorting using no sorting strategy."""
        strategy = NoSortingStrategy()
        service = TransactionSortingService(strategy)

        transactions = [
            {"Date": "15 Jan 2023", "Details": "Transaction 3"},
            {"Date": "01 Jan 2023", "Details": "Transaction 1"},
            {"Date": "10 Jan 2023", "Details": "Transaction 2"},
        ]

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 3
        # Original order preserved
        assert sorted_txns[0]["Details"] == "Transaction 3"
        assert sorted_txns[1]["Details"] == "Transaction 1"
        assert sorted_txns[2]["Details"] == "Transaction 2"

    def test_sort_empty_list(self):
        """Test sorting empty list."""
        strategy = ChronologicalSortingStrategy()
        service = TransactionSortingService(strategy)
        sorted_txns = service.sort([])
        assert len(sorted_txns) == 0

    def test_strategy_can_be_changed(self):
        """Test that strategy can be changed."""
        chronological = ChronologicalSortingStrategy()
        no_sort = NoSortingStrategy()

        service = TransactionSortingService(chronological)
        assert service.strategy == chronological

        # Change strategy
        service.strategy = no_sort
        assert service.strategy == no_sort

    def test_sort_large_dataset(self):
        """Test sorting with larger dataset."""
        strategy = ChronologicalSortingStrategy()
        service = TransactionSortingService(strategy)

        # Create 100 transactions with random-ish dates
        transactions = []
        for i in range(100):
            day = (i % 28) + 1
            transactions.append(
                {
                    "Date": f"{day:02d} Jan 2023",
                    "Details": f"Transaction {i}",
                }
            )

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 100

        # Verify first few are early dates
        assert "01 Jan" in sorted_txns[0]["Date"] or "02 Jan" in sorted_txns[0]["Date"]
