"""Tests for currency parsing and formatting utilities."""

from __future__ import annotations

import pytest

from bankstatements_core.domain.currency import (
    CurrencyParseError,
    format_currency,
    reroute_cr_suffix,
    to_float,
)


class TestToFloat:
    """Test the to_float currency parsing function."""

    def test_parse_basic_float(self):
        """Test parsing basic float string."""
        assert to_float("100.50") == 100.5
        assert to_float("0.99") == 0.99
        assert to_float("1234.56") == 1234.56

    def test_parse_with_currency_symbols(self):
        """Test parsing with various currency symbols."""
        assert to_float("€100.50") == 100.5
        assert to_float("$200.00") == 200.0
        assert to_float("£150.25") == 150.25
        assert to_float("¥1000") == 1000.0

    def test_parse_with_thousands_separator(self):
        """Test parsing with comma as thousands separator."""
        assert to_float("1,234.56") == 1234.56
        assert to_float("€10,000.00") == 10000.0
        assert to_float("1,000,000.50") == 1000000.5

    def test_parse_negative_parentheses(self):
        """Test parsing negative values in parentheses."""
        assert to_float("(100.00)") == -100.0
        assert to_float("(€50.50)") == -50.5

    def test_parse_negative_minus_sign(self):
        """Test parsing negative values with minus sign."""
        assert to_float("-100.00") == -100.0
        assert to_float("€-50.50") == -50.5

    def test_parse_empty_and_none(self):
        """Test parsing empty string and None."""
        assert to_float("") is None
        assert to_float("   ") is None
        assert to_float(None) is None

    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        assert to_float("  100.50  ") == 100.5
        assert to_float("€ 200.00") == 200.0

    def test_parse_disallow_negative(self):
        """Test disallowing negative values."""
        assert to_float("-100.00", allow_negative=False) is None
        assert to_float("(50.00)", allow_negative=False) is None
        assert to_float("100.00", allow_negative=False) == 100.0

    def test_parse_invalid_format(self):
        """Test parsing invalid formats returns None."""
        assert to_float("invalid") is None
        assert to_float("abc123") is None
        assert to_float("€€€") is None


class TestFormatCurrency:
    """Test the format_currency function."""

    def test_format_basic(self):
        """Test basic currency formatting."""
        assert format_currency(100.5) == "€100.50"
        assert format_currency(1234.56) == "€1,234.56"

    def test_format_with_symbol(self):
        """Test formatting with different currency symbols."""
        assert format_currency(100.5, "$") == "$100.50"
        assert format_currency(200.0, "£") == "£200.00"

    def test_format_negative(self):
        """Test formatting negative values."""
        assert format_currency(-100.5) == "-€100.50"
        assert format_currency(-1234.56, "$") == "-$1,234.56"

    def test_format_none(self):
        """Test formatting None returns empty string."""
        assert format_currency(None) == ""

    def test_format_zero(self):
        """Test formatting zero."""
        assert format_currency(0.0) == "€0.00"

    def test_format_decimal_places(self):
        """Test custom decimal places."""
        assert format_currency(100.5, "€", 0) == "€100"
        assert format_currency(100.5, "€", 3) == "€100.500"


class TestCurrencyParseError:
    """Test the CurrencyParseError exception."""

    def test_is_value_error(self):
        """Test CurrencyParseError is a ValueError subclass."""
        assert issubclass(CurrencyParseError, ValueError)

    def test_can_raise(self):
        """Test CurrencyParseError can be raised."""
        with pytest.raises(CurrencyParseError):
            raise CurrencyParseError("Test error")


def test_strip_currency_symbols():
    """strip_currency_symbols removes all supported symbols and whitespace."""
    from bankstatements_core.domain.currency import strip_currency_symbols

    assert strip_currency_symbols("€1,234.56") == "1234.56"
    assert strip_currency_symbols("$100.00") == "100.00"
    assert strip_currency_symbols("£50.00") == "50.00"
    assert strip_currency_symbols("¥1000") == "1000"
    assert strip_currency_symbols("  € 99.99  ") == "99.99"
    assert strip_currency_symbols("123.45") == "123.45"


class TestRerouteCrSuffix:
    """Tests for reroute_cr_suffix (issue #131)."""

    def test_cr_suffix_moves_to_credit(self):
        """300.00CR in Debit is moved to Credit with suffix stripped."""
        row = {"Debit": "300.00CR", "Credit": ""}
        reroute_cr_suffix(row)
        assert row["Credit"] == "300.00"
        assert row["Debit"] == ""

    def test_cr_suffix_lowercase(self):
        """300.00cr (lowercase) is treated the same as CR."""
        row = {"Debit": "300.00cr", "Credit": ""}
        reroute_cr_suffix(row)
        assert row["Credit"] == "300.00"
        assert row["Debit"] == ""

    def test_plain_debit_unchanged(self):
        """A plain debit amount without CR suffix is not rerouted."""
        row = {"Debit": "150.00", "Credit": ""}
        reroute_cr_suffix(row)
        assert row["Debit"] == "150.00"
        assert row["Credit"] == ""

    def test_empty_debit_is_noop(self):
        """Empty Debit value is a no-op."""
        row = {"Debit": "", "Credit": ""}
        reroute_cr_suffix(row)
        assert row["Debit"] == ""
        assert row["Credit"] == ""

    def test_missing_debit_key_is_noop(self):
        """Row with no Debit key is a no-op."""
        row = {"Credit": ""}
        reroute_cr_suffix(row)
        assert row == {"Credit": ""}


def test_yen_through_transaction_get_amount():
    """¥ symbol is stripped correctly by Transaction._clean_amount_string()."""
    from bankstatements_core.domain.models.transaction import Transaction

    tx = Transaction(
        date="01/01/2024",
        details="Tokyo Store",
        debit="¥1000",
        credit=None,
        balance="¥5000",
        filename="test.pdf",
    )
    from decimal import Decimal

    assert tx.get_amount() == Decimal("-1000")
    assert tx.get_balance() == Decimal("5000")
