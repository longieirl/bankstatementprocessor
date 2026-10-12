"""Tests for TransactionYearFilterService — restrict transactions by year."""

from __future__ import annotations

import pytest

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.exceptions import YearFilterError
from bankstatements_core.services.transaction_year_filter import (
    NoYearFilterStrategy,
    TransactionYearFilterService,
    YearRangeFilterStrategy,
)


def _tx(date: str, statement_year: str | None = None) -> Transaction:
    extra = {"statement_year": statement_year} if statement_year else {}
    return Transaction(
        date=date,
        details="x",
        debit="1.00",
        credit=None,
        balance="1.00",
        filename="s.pdf",
        additional_fields=extra,
    )


class TestFromRange:
    def test_none_builds_noop(self):
        svc = TransactionYearFilterService.from_range(None)
        assert isinstance(svc._strategy, NoYearFilterStrategy)

    def test_range_builds_filter(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        assert isinstance(svc._strategy, YearRangeFilterStrategy)


class TestNoYearFilter:
    def test_passes_all_through(self):
        svc = TransactionYearFilterService.from_range(None)
        txns = [_tx("01/12/2024"), _tx("not-a-date"), _tx("01/12")]
        assert svc.filter(txns, "s.pdf") == txns


class TestYearRangeFilter:
    def test_single_year_keeps_only_matches(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        txns = [_tx("01/06/2024"), _tx("01/06/2025"), _tx("01/06/2026")]
        result = svc.filter(txns, "s.pdf")
        assert [t.date for t in result] == ["01/06/2025"]

    def test_inclusive_range(self):
        svc = TransactionYearFilterService.from_range((2024, 2026))
        txns = [_tx("01/06/2023"), _tx("01/06/2024"), _tx("01/06/2026")]
        result = svc.filter(txns, "s.pdf")
        assert [t.date for t in result] == ["01/06/2024", "01/06/2026"]

    def test_yearless_resolved_via_statement_year(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        txns = [
            _tx("3 Feb", statement_year="2025"),
            _tx("3 Feb", statement_year="2024"),
        ]
        result = svc.filter(txns, "s.pdf")
        assert len(result) == 1
        assert result[0].additional_fields["statement_year"] == "2025"

    def test_empty_result_when_no_match(self):
        svc = TransactionYearFilterService.from_range((2030, 2030))
        assert svc.filter([_tx("01/06/2024")], "s.pdf") == []

    def test_unparseable_date_raises(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        with pytest.raises(YearFilterError):
            svc.filter([_tx("not-a-date")], "s.pdf")

    def test_partial_date_without_year_raises(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        with pytest.raises(YearFilterError):
            svc.filter([_tx("01/12")], "s.pdf")

    def test_yearless_without_hint_raises(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        with pytest.raises(YearFilterError):
            svc.filter([_tx("3 Feb")], "s.pdf")

    def test_error_names_source_and_date(self):
        svc = TransactionYearFilterService.from_range((2025, 2025))
        with pytest.raises(YearFilterError, match="bad.pdf"):
            svc.filter([_tx("not-a-date")], "bad.pdf")
