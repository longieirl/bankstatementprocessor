"""Tests for transaction sorting service."""

from __future__ import annotations

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.sorting_service import (
    ChronologicalSortingStrategy,
    NoSortingStrategy,
    TransactionSortingService,
)


def _tx(date: str, details: str) -> Transaction:
    return Transaction.from_dict({"Date": date, "Details": details})


def _tx_with_year(date: str, details: str, statement_year: int) -> Transaction:
    """Create a transaction with a statement_year in additional_fields (as stamped by RowPostProcessor)."""
    tx = Transaction.from_dict({"Date": date, "Details": details})
    tx.additional_fields["statement_year"] = str(statement_year)
    return tx


class TestChronologicalSortingStrategy:
    """Tests for ChronologicalSortingStrategy."""

    def test_sort_chronologically(self):
        """Test sorting transactions by date chronologically."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx("15 Jan 2023", "Transaction 3"),
            _tx("01 Jan 2023", "Transaction 1"),
            _tx("10 Jan 2023", "Transaction 2"),
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0].details == "Transaction 1"  # 01 Jan
        assert sorted_txns[1].details == "Transaction 2"  # 10 Jan
        assert sorted_txns[2].details == "Transaction 3"  # 15 Jan

    def test_sort_with_different_date_formats(self):
        """Test sorting with various date formats."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx("15/01/2023", "Transaction 3"),
            _tx("01 Jan 2023", "Transaction 1"),
            _tx("10-01-2023", "Transaction 2"),
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        # All are from January 2023, so should sort by day
        assert sorted_txns[0].details == "Transaction 1"  # Day 1
        assert sorted_txns[1].details == "Transaction 2"  # Day 10
        assert sorted_txns[2].details == "Transaction 3"  # Day 15

    def test_sort_empty_list(self):
        """Test sorting empty transaction list."""
        strategy = ChronologicalSortingStrategy()
        sorted_txns = strategy.sort([])
        assert len(sorted_txns) == 0

    def test_sort_single_transaction(self):
        """Test sorting single transaction."""
        strategy = ChronologicalSortingStrategy()
        transactions = [_tx("01 Jan 2023", "Single")]
        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 1
        assert sorted_txns[0].details == "Single"

    def test_sort_with_missing_dates(self):
        """Test sorting when some transactions have missing dates."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx("15 Jan 2023", "Has date"),
            _tx("", "No date"),
            _tx("01 Jan 2023", "Has date 2"),
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        # Transactions with empty dates should sort to beginning (epoch date)

    def test_sort_same_dates(self):
        """Test sorting transactions with same dates."""
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx("01 Jan 2023", "Transaction A"),
            _tx("01 Jan 2023", "Transaction B"),
            _tx("01 Jan 2023", "Transaction C"),
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
            _tx("15 Jan 2023", "Transaction 3"),
            _tx("01 Jan 2023", "Transaction 1"),
            _tx("10 Jan 2023", "Transaction 2"),
        ]

        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0].details == "Transaction 3"
        assert sorted_txns[1].details == "Transaction 1"
        assert sorted_txns[2].details == "Transaction 2"

    def test_no_sort_empty_list(self):
        """Test with empty transaction list."""
        strategy = NoSortingStrategy()
        sorted_txns = strategy.sort([])
        assert len(sorted_txns) == 0

    def test_no_sort_single_transaction(self):
        """Test with single transaction."""
        strategy = NoSortingStrategy()
        transactions = [_tx("01 Jan 2023", "Single")]
        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 1
        assert sorted_txns[0].details == "Single"


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
            _tx("15 Jan 2023", "Transaction 3"),
            _tx("01 Jan 2023", "Transaction 1"),
            _tx("10 Jan 2023", "Transaction 2"),
        ]

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 3
        assert sorted_txns[0].details == "Transaction 1"
        assert sorted_txns[1].details == "Transaction 2"
        assert sorted_txns[2].details == "Transaction 3"

    def test_sort_with_no_sorting_strategy(self):
        """Test sorting using no sorting strategy."""
        strategy = NoSortingStrategy()
        service = TransactionSortingService(strategy)

        transactions = [
            _tx("15 Jan 2023", "Transaction 3"),
            _tx("01 Jan 2023", "Transaction 1"),
            _tx("10 Jan 2023", "Transaction 2"),
        ]

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 3
        # Original order preserved
        assert sorted_txns[0].details == "Transaction 3"
        assert sorted_txns[1].details == "Transaction 1"
        assert sorted_txns[2].details == "Transaction 2"

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
            transactions.append(_tx(f"{day:02d} Jan 2023", f"Transaction {i}"))

        sorted_txns = service.sort(transactions)
        assert len(sorted_txns) == 100

        # Verify first few are early dates
        assert "01 Jan" in sorted_txns[0].date or "02 Jan" in sorted_txns[0].date


class TestChronologicalSortingWithYearlessDates:
    """Tests for yearless date sorting using statement_year from additional_fields."""

    def test_yearless_dates_sorted_when_year_present(self):
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx_with_year("18 Feb", "Later", 2026),
            _tx_with_year("3 Feb", "Earlier", 2026),
            _tx_with_year("25 Feb", "Latest", 2026),
        ]
        sorted_txns = strategy.sort(transactions)
        assert sorted_txns[0].details == "Earlier"  # 3 Feb
        assert sorted_txns[1].details == "Later"  # 18 Feb
        assert sorted_txns[2].details == "Latest"  # 25 Feb

    def test_yearless_dates_fall_to_epoch_without_year(self):
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx("18 Feb", "No year A"),
            _tx("3 Feb", "No year B"),
        ]
        # Without hint_year both parse to epoch — order undefined but no crash
        sorted_txns = strategy.sort(transactions)
        assert len(sorted_txns) == 2

    def test_yearless_and_full_dates_mixed(self):
        strategy = ChronologicalSortingStrategy()
        transactions = [
            _tx_with_year("18 Feb", "CC yearless", 2026),
            _tx("01/01/2026", "Bank full date"),
            _tx_with_year("3 Feb", "CC earlier", 2026),
        ]
        sorted_txns = strategy.sort(transactions)
        # 01 Jan 2026, 03 Feb 2026, 18 Feb 2026
        assert sorted_txns[0].details == "Bank full date"
        assert sorted_txns[1].details == "CC earlier"
        assert sorted_txns[2].details == "CC yearless"

    def test_invalid_statement_year_in_additional_fields_falls_to_epoch(self):
        strategy = ChronologicalSortingStrategy()
        tx = _tx("3 Feb", "Bad year")
        tx.additional_fields["statement_year"] = "not-an-int"
        # Should not raise — falls back to epoch
        sorted_txns = strategy.sort([tx])
        assert len(sorted_txns) == 1
