"""
Parameterized tests for utils.py using pytest.
This reduces test duplication and makes it easier to add new test cases.
"""

from __future__ import annotations

import pytest

from bankstatements_core.utils import format_currency, to_float


class TestToFloatParametrized:
    """Parameterized tests for to_float function"""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            # Standard formats
            ("123.45", 123.45),
            ("0.00", 0.0),
            ("€10,000.99", 10000.99),
            # Different currency symbols
            ("€123.45", 123.45),
            ("$123.45", 123.45),
            ("£123.45", 123.45),
            ("¥123", 123.0),
            # With thousands separator
            ("1,234.56", 1234.56),
            ("€1,234.56", 1234.56),
            # Whitespace handling
            ("  123.45  ", 123.45),
            ("  €123.45  ", 123.45),
            # Negative values
            ("-123.45", -123.45),
            ("(123.45)", -123.45),
            ("-€123.45", -123.45),
            ("€-123.45", -123.45),
            ("(€123.45)", -123.45),
            # Positive sign
            ("+123.45", 123.45),
            ("€+123.45", 123.45),
        ],
    )
    def test_to_float_valid_conversions(self, input_value, expected):
        """Test various valid currency string conversions"""
        assert to_float(input_value) == expected

    @pytest.mark.parametrize(
        "input_value",
        [
            "",  # Empty string
            "   ",  # Whitespace only
            None,  # None input
            "€",  # Just currency symbol
            "abc",  # Invalid format
            "€€€",  # Multiple symbols
        ],
    )
    def test_to_float_invalid_inputs(self, input_value):
        """Test that invalid inputs return None"""
        assert to_float(input_value) is None

    @pytest.mark.parametrize(
        "input_value",
        [
            "-123.45",
            "(123.45)",
            "-€123.45",
            "(€123.45)",
        ],
    )
    def test_to_float_disallow_negative(self, input_value):
        """Test that negative values are rejected when allow_negative=False"""
        assert to_float(input_value, allow_negative=False) is None

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("123.45", 123.45),
            ("€1,000", 1000.0),
            ("+50.00", 50.0),
        ],
    )
    def test_to_float_allow_negative_false_positive_values(self, input_value, expected):
        """Test that positive values work when allow_negative=False"""
        assert to_float(input_value, allow_negative=False) == expected


class TestFormatCurrencyParametrized:
    """Parameterized tests for format_currency function"""

    @pytest.mark.parametrize(
        "value,symbol,decimals,expected",
        [
            # Basic formatting
            (1234.5, "€", 2, "€1,234.50"),
            (100, "$", 2, "$100.00"),
            (0, "€", 2, "€0.00"),
            # Negative values
            (-50, "€", 2, "-€50.00"),
            (-1234.56, "$", 2, "-$1,234.56"),
            # Different decimal places
            (100.123, "€", 3, "€100.123"),
            (100.1, "€", 1, "€100.1"),
            (100, "€", 0, "€100"),
            # Large numbers
            (1000000, "€", 2, "€1,000,000.00"),
            (999999.99, "$", 2, "$999,999.99"),
        ],
    )
    def test_format_currency_various_formats(self, value, symbol, decimals, expected):
        """Test various currency formatting scenarios"""
        assert format_currency(value, symbol, decimals) == expected

    def test_format_currency_none_value(self):
        """Test that None value returns empty string"""
        assert format_currency(None) == ""
