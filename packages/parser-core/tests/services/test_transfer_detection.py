"""Tests for TransferDetectionService."""

from __future__ import annotations

import pytest

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.transfer_detection import (
    TransferDetectionService,
    _group_id,
    _parse_date,
)


def _tx(
    date: str,
    debit: str | None = None,
    credit: str | None = None,
    filename: str = "a.pdf",
    transaction_type: str = "",
    statement_year: str = "",
) -> Transaction:
    add = {}
    if statement_year:
        add["statement_year"] = statement_year
    return Transaction(
        date=date,
        details="Test",
        debit=debit,
        credit=credit,
        balance=None,
        filename=filename,
        additional_fields=add,
        transaction_type=transaction_type,
    )


class TestParseDate:
    def test_dd_mmm_yyyy(self) -> None:
        tx = _tx("3 Feb 2026")
        assert _parse_date(tx) is not None
        d = _parse_date(tx)
        assert d is not None
        assert d.year == 2026
        assert d.month == 2
        assert d.day == 3

    def test_dd_slash_mm_yyyy(self) -> None:
        tx = _tx("19/12/2025")
        d = _parse_date(tx)
        assert d is not None
        assert d.year == 2025
        assert d.month == 12
        assert d.day == 19

    def test_yearless_cc_enriched(self) -> None:
        tx = _tx("3 Feb", statement_year="2026")
        d = _parse_date(tx)
        assert d is not None
        assert d.year == 2026

    def test_empty_date_returns_none(self) -> None:
        tx = _tx("")
        assert _parse_date(tx) is None


class TestTransferDetectionService:
    def test_exact_match_marked(self) -> None:
        bank = _tx("19/12/2025", debit="1000.00", filename="aib.pdf")
        revolut = _tx("19/12/2025", credit="1000.00", filename="revolut.pdf")
        svc = TransferDetectionService()
        pairs = svc.detect_transfers([bank, revolut])
        assert pairs == 1
        assert bank.transaction_type == "internal_transfer"
        assert revolut.transaction_type == "internal_transfer"
        assert bank.transfer_group_id == revolut.transfer_group_id
        assert bank.transfer_group_id.startswith("TXFER-")

    def test_within_date_window(self) -> None:
        bank = _tx("19/12/2025", debit="500.00", filename="aib.pdf")
        revolut = _tx("21/12/2025", credit="500.00", filename="revolut.pdf")
        pairs = TransferDetectionService(date_window_days=3).detect_transfers(
            [bank, revolut]
        )
        assert pairs == 1

    def test_outside_date_window_not_matched(self) -> None:
        bank = _tx("19/12/2025", debit="500.00", filename="aib.pdf")
        revolut = _tx("26/12/2025", credit="500.00", filename="revolut.pdf")
        pairs = TransferDetectionService(date_window_days=3).detect_transfers(
            [bank, revolut]
        )
        assert pairs == 0
        assert bank.transaction_type != "internal_transfer"

    def test_different_amounts_not_matched(self) -> None:
        bank = _tx("19/12/2025", debit="1000.00", filename="aib.pdf")
        revolut = _tx("19/12/2025", credit="999.99", filename="revolut.pdf")
        pairs = TransferDetectionService().detect_transfers([bank, revolut])
        assert pairs == 0

    def test_same_filename_not_matched(self) -> None:
        tx1 = _tx("19/12/2025", debit="200.00", filename="aib.pdf")
        tx2 = _tx("19/12/2025", credit="200.00", filename="aib.pdf")
        pairs = TransferDetectionService().detect_transfers([tx1, tx2])
        assert pairs == 0

    def test_already_tagged_skipped(self) -> None:
        bank = _tx(
            "19/12/2025",
            debit="300.00",
            filename="aib.pdf",
            transaction_type="internal_transfer",
        )
        revolut = _tx("19/12/2025", credit="300.00", filename="revolut.pdf")
        pairs = TransferDetectionService().detect_transfers([bank, revolut])
        assert pairs == 0

    def test_group_id_deterministic(self) -> None:
        tx_a = _tx("19/12/2025", debit="400.00", filename="aib.pdf")
        tx_b = _tx("19/12/2025", credit="400.00", filename="revolut.pdf")
        from decimal import Decimal

        g1 = _group_id(tx_a, tx_b, Decimal("400.00"))
        g2 = _group_id(tx_b, tx_a, Decimal("400.00"))
        assert g1 == g2

    def test_best_match_wins_closest_date(self) -> None:
        bank = _tx("19/12/2025", debit="100.00", filename="aib.pdf")
        close = _tx("20/12/2025", credit="100.00", filename="revolut.pdf")
        far = _tx("21/12/2025", credit="100.00", filename="n26.pdf")
        pairs = TransferDetectionService(date_window_days=3).detect_transfers(
            [bank, close, far]
        )
        assert pairs == 1
        assert close.transaction_type == "internal_transfer"
        assert far.transaction_type != "internal_transfer"

    def test_each_credit_used_once(self) -> None:
        bank1 = _tx("19/12/2025", debit="50.00", filename="aib.pdf")
        bank2 = _tx("19/12/2025", debit="50.00", filename="aib2.pdf")
        revolut = _tx("19/12/2025", credit="50.00", filename="revolut.pdf")
        pairs = TransferDetectionService().detect_transfers([bank1, bank2, revolut])
        assert pairs == 1

    def test_returns_pair_count(self) -> None:
        txns = [
            _tx("01/01/2025", debit="100.00", filename="a.pdf"),
            _tx("01/01/2025", credit="100.00", filename="b.pdf"),
            _tx("02/01/2025", debit="200.00", filename="c.pdf"),
            _tx("02/01/2025", credit="200.00", filename="d.pdf"),
        ]
        assert TransferDetectionService().detect_transfers(txns) == 2

    def test_zero_amount_skipped(self) -> None:
        tx = _tx("01/01/2025", debit="0.00", filename="a.pdf")
        other = _tx("01/01/2025", credit="0.00", filename="b.pdf")
        assert TransferDetectionService().detect_transfers([tx, other]) == 0

    def test_transaction_with_no_parseable_date_skipped(self) -> None:
        bank = _tx("", debit="100.00", filename="a.pdf")
        revolut = _tx("01/01/2025", credit="100.00", filename="b.pdf")
        pairs = TransferDetectionService().detect_transfers([bank, revolut])
        assert pairs == 0
