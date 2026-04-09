"""Tests for DateParserService — yearless date parsing and hint_year support."""

from __future__ import annotations

from datetime import datetime

import pytest

from bankstatements_core.services.date_parser import DateParserService


@pytest.fixture()
def service() -> DateParserService:
    return DateParserService()


class TestParseYearlessDate:
    """Tests for _parse_yearless_date with hint_year."""

    def test_abbreviated_month_with_hint_year(self, service):
        result = service._parse_yearless_date("3 Feb", 2026)
        assert result == datetime(2026, 2, 3)

    def test_full_month_name_with_hint_year(self, service):
        result = service._parse_yearless_date("3 February", 2026)
        assert result == datetime(2026, 2, 3)

    def test_single_digit_day(self, service):
        result = service._parse_yearless_date("5 Jan", 2025)
        assert result == datetime(2025, 1, 5)

    def test_two_digit_day(self, service):
        result = service._parse_yearless_date("18 Mar", 2026)
        assert result == datetime(2026, 3, 18)

    def test_returns_none_when_no_hint_year(self, service):
        assert service._parse_yearless_date("3 Feb", None) is None

    def test_returns_none_for_non_yearless_format(self, service):
        assert service._parse_yearless_date("01/02/2026", 2026) is None

    def test_hint_year_overrides_default(self, service):
        result = service._parse_yearless_date("1 Dec", 2024)
        assert result is not None
        assert result.year == 2024

    def test_all_months_abbreviated(self, service):
        months = [
            ("Jan", 1),
            ("Feb", 2),
            ("Mar", 3),
            ("Apr", 4),
            ("May", 5),
            ("Jun", 6),
            ("Jul", 7),
            ("Aug", 8),
            ("Sep", 9),
            ("Oct", 10),
            ("Nov", 11),
            ("Dec", 12),
        ]
        for abbr, month_num in months:
            result = service._parse_yearless_date(f"1 {abbr}", 2026)
            assert result is not None, f"Failed to parse '1 {abbr}'"
            assert result.month == month_num


class TestParseTransactionDateWithHintYear:
    """Tests for parse_transaction_date with hint_year for yearless dates."""

    def test_yearless_date_resolved_with_hint(self, service):
        result = service.parse_transaction_date("3 Feb", hint_year=2026)
        assert result == datetime(2026, 2, 3)

    def test_yearless_date_returns_epoch_without_hint(self, service):
        result = service.parse_transaction_date("3 Feb")
        assert result == service.EPOCH_DATE

    def test_full_month_name_yearless_with_hint(self, service):
        result = service.parse_transaction_date("18 February", hint_year=2026)
        assert result == datetime(2026, 2, 18)

    def test_dated_format_ignores_hint_year(self, service):
        # Dates with year component should not be affected by hint_year
        result = service.parse_transaction_date("01/02/2023", hint_year=2026)
        assert result == datetime(2023, 2, 1)

    def test_dd_mmm_yyyy_ignores_hint_year(self, service):
        result = service.parse_transaction_date("25 Apr 2025", hint_year=2026)
        assert result == datetime(2025, 4, 25)

    def test_empty_string_returns_epoch(self, service):
        assert service.parse_transaction_date("", hint_year=2026) == service.EPOCH_DATE

    def test_unparseable_string_returns_epoch(self, service):
        assert (
            service.parse_transaction_date("not-a-date", hint_year=2026)
            == service.EPOCH_DATE
        )

    def test_yearless_date_logs_no_warning_when_hint_provided(self, service, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            service.parse_transaction_date("3 Feb", hint_year=2026)
        assert "Unable to parse date" not in caplog.text

    def test_yearless_date_logs_warning_without_hint(self, service, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            service.parse_transaction_date("3 Feb")
        assert "Unable to parse date '3 Feb'" in caplog.text


class TestYearlessDateFormats:
    """Verify YEARLESS_DATE_FORMATS constant is correctly defined."""

    def test_yearless_formats_defined(self, service):
        assert "%d %b" in service.YEARLESS_DATE_FORMATS
        assert "%d %B" in service.YEARLESS_DATE_FORMATS

    def test_yearless_formats_not_in_main_formats(self, service):
        # Yearless formats must NOT appear in DATE_FORMATS to avoid ambiguity
        assert "%d %b" not in service.DATE_FORMATS
        assert "%d %B" not in service.DATE_FORMATS
