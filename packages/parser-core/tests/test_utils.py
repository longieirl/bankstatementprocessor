from __future__ import annotations

import unittest

from bankstatements_core.utils import (
    format_currency,
    log_summary,
    parse_bool_env,
    parse_int_env,
    to_float,
)


class TestUtils(unittest.TestCase):
    def test_to_float_valid_amounts(self):
        """Test conversion of valid amount strings to float"""
        # Standard decimal format
        self.assertEqual(to_float("123.45"), 123.45)

        # With euro symbol
        self.assertEqual(to_float("€123.45"), 123.45)

        # With comma thousands separator
        self.assertEqual(to_float("1,234.56"), 1234.56)

        # Zero amount
        self.assertEqual(to_float("0.00"), 0.0)

        # Large amount
        self.assertEqual(to_float("€10,000.99"), 10000.99)

    def test_to_float_edge_cases(self):
        """Test edge cases and invalid inputs"""
        # Empty string
        self.assertIsNone(to_float(""))

        # Whitespace only
        self.assertIsNone(to_float("   "))

        # None input
        self.assertIsNone(to_float(None))

        # Just euro symbol - now returns None gracefully instead of raising
        self.assertIsNone(to_float("€"))

        # Invalid format - now returns None gracefully instead of raising
        self.assertIsNone(to_float("abc"))

    def test_to_float_whitespace_handling(self):
        """Test handling of whitespace in amounts"""
        # Leading/trailing whitespace
        self.assertEqual(to_float("  123.45  "), 123.45)

        # Whitespace with euro symbol
        self.assertEqual(to_float("  €123.45  "), 123.45)

        # Whitespace with comma
        self.assertEqual(to_float("  1,234.56  "), 1234.56)

    def test_to_float_negative_values(self):
        """Test handling of negative amounts"""
        # Negative with minus sign
        self.assertEqual(to_float("-123.45"), -123.45)

        # Negative in parentheses (accounting format)
        self.assertEqual(to_float("(123.45)"), -123.45)

        # Negative with euro symbol
        self.assertEqual(to_float("-€123.45"), -123.45)
        self.assertEqual(to_float("€-123.45"), -123.45)

        # Negative in parentheses with euro
        self.assertEqual(to_float("(€123.45)"), -123.45)

    def test_to_float_disallow_negative(self):
        """Test disallowing negative values"""
        # Should return None when negative not allowed
        self.assertIsNone(to_float("-123.45", allow_negative=False))
        self.assertIsNone(to_float("(123.45)", allow_negative=False))

        # Positive values should still work
        self.assertEqual(to_float("123.45", allow_negative=False), 123.45)

    def test_to_float_different_currencies(self):
        """Test handling of different currency symbols"""
        # Dollar sign
        self.assertEqual(to_float("$123.45"), 123.45)

        # Pound sign
        self.assertEqual(to_float("£123.45"), 123.45)

        # Yen sign
        self.assertEqual(to_float("¥123"), 123.0)

    def test_to_float_type_safety(self):
        """Test that the function has proper type hints"""
        # With proper type hints (str | None), mypy will catch type errors
        # at development time, so runtime type checking is not needed.
        # The function signature enforces that only str or None can be passed.
        # This test verifies the type-safe behavior with valid inputs.

        # Valid string inputs
        self.assertEqual(to_float("123"), 123.0)
        self.assertIsNone(to_float(None))
        self.assertIsNone(to_float(""))

        # Note: Passing int, float, or list would be caught by mypy:
        # to_float(123)  # type error: expected str | None, got int
        # to_float(123.45)  # type error: expected str | None, got float
        # to_float([123])  # type error: expected str | None, got list

    def test_format_currency(self):
        """Test currency formatting"""
        # Basic formatting
        self.assertEqual(format_currency(1234.5), "€1,234.50")

        # Negative value
        self.assertEqual(format_currency(-50), "-€50.00")

        # Different currency symbol
        self.assertEqual(format_currency(100, "$"), "$100.00")

        # Different decimal places
        self.assertEqual(format_currency(100.123, "€", 3), "€100.123")

        # None value
        self.assertEqual(format_currency(None), "")

        # Zero
        self.assertEqual(format_currency(0), "€0.00")

    def test_to_float_plus_sign(self):
        """Test handling of explicit positive sign"""
        self.assertEqual(to_float("+123.45"), 123.45)
        self.assertEqual(to_float("€+123.45"), 123.45)


class TestLogSummary(unittest.TestCase):
    def test_log_summary_basic(self):
        """Test log_summary logs without error."""
        summary = {
            "pdf_count": 2,
            "pages_read": 4,
            "transactions": 15,
            "duplicates": 3,
        }
        # Should not raise
        log_summary(summary)

    def test_log_summary_with_paths(self):
        """Test log_summary handles optional output paths."""
        summary = {
            "pdf_count": 1,
            "pages_read": 2,
            "transactions": 10,
            "duplicates": 0,
            "csv_path": "/output/out.csv",
            "json_path": "/output/out.json",
            "excel_path": "/output/out.xlsx",
            "duplicates_path": "/output/duplicates.csv",
            "monthly_summary_path": "/output/monthly.csv",
        }
        # Should not raise
        log_summary(summary)


class TestParseIntEnv(unittest.TestCase):
    def test_parse_int_env_with_value(self, monkeypatch=None):
        """Test parse_int_env returns parsed value."""
        import os

        os.environ["_TEST_INT_VAR"] = "42"
        try:
            result = parse_int_env("_TEST_INT_VAR", 0)
            assert result == 42
        finally:
            del os.environ["_TEST_INT_VAR"]

    def test_parse_int_env_default(self):
        """Test parse_int_env returns default when var not set."""
        result = parse_int_env("_NONEXISTENT_TEST_VAR_XYZ", 99)
        assert result == 99


class TestParseBoolEnv(unittest.TestCase):
    def test_parse_bool_env_true(self):
        """Test parse_bool_env returns True for 'true'."""
        import os

        os.environ["_TEST_BOOL_VAR"] = "true"
        try:
            result = parse_bool_env("_TEST_BOOL_VAR", False)
            assert result is True
        finally:
            del os.environ["_TEST_BOOL_VAR"]

    def test_parse_bool_env_default(self):
        """Test parse_bool_env returns default when var not set."""
        result = parse_bool_env("_NONEXISTENT_TEST_BOOL_VAR_XYZ", False)
        assert result is False


if __name__ == "__main__":
    unittest.main()
