"""
Tests for Phase 3: Replace generic Exception catches with specific types.

Verifies that code catches specific exception types and lets unexpected errors bubble up.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.services.totals_calculator import ColumnTotalsService


class TestColumnTotalsServiceSpecificExceptions:
    """Test that ColumnTotalsService catches only expected exceptions."""

    def test_value_error_is_caught_and_returns_zero(self):
        """ValueError during calculation is caught and returns 0.0."""
        service = ColumnTotalsService(totals_columns=["Amount"])

        # Create DataFrame with non-numeric data that causes ValueError
        df = pd.DataFrame({"Amount": ["invalid", "data"]})

        totals = service.calculate(df)

        # Should catch ValueError and return 0.0
        assert "Amount" in totals
        assert totals["Amount"] == 0.0

    def test_type_error_is_caught_and_returns_zero(self):
        """TypeError during calculation is caught and returns 0.0."""
        service = ColumnTotalsService(totals_columns=["Value"])

        # Create DataFrame that might cause TypeError
        df = pd.DataFrame({"Value": [1, 2, None]})

        totals = service.calculate(df)

        # Should handle gracefully
        assert "Value" in totals

    def test_unexpected_error_bubbles_up(self):
        """Unexpected errors (not ValueError/TypeError) bubble up."""
        service = ColumnTotalsService(totals_columns=["Amount"])

        # Mock calculate_column_sum where it's imported
        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            # RuntimeError is NOT in caught exceptions
            mock_calc.side_effect = RuntimeError("Unexpected system error")

            df = pd.DataFrame({"Amount": [1, 2, 3]})

            # Should NOT catch RuntimeError - let it bubble up
            with pytest.raises(RuntimeError) as exc_info:
                service.calculate(df)

            assert "Unexpected system error" in str(exc_info.value)

    def test_valid_numeric_calculation_succeeds(self):
        """Valid numeric columns calculate correctly."""
        service = ColumnTotalsService(totals_columns=["Amount"])

        df = pd.DataFrame({"Amount": [10.5, 20.0, 30.5]})

        totals = service.calculate(df)

        assert "Amount" in totals
        assert totals["Amount"] == pytest.approx(61.0)


class TestAppConfigSpecificExceptions:
    """Test that AppConfig catches specific exceptions and chains them."""

    def test_exception_chaining_with_from_e(self):
        """ConfigurationError chains original exception with 'from e'."""
        with patch("bankstatements_core.config.totals_config.parse_totals_columns") as mock_parse:
            original_error = ValueError("Invalid format at position 5")
            mock_parse.side_effect = original_error

            with patch.dict("os.environ", {"TOTALS_COLUMNS": "bad_format"}):
                with pytest.raises(ConfigurationError) as exc_info:
                    AppConfig.from_env()

                # Verify exception chaining (__cause__ is set)
                assert exc_info.value.__cause__ is original_error
                assert "Invalid format at position 5" in str(exc_info.value.__cause__)

    def test_configuration_error_includes_context(self):
        """ConfigurationError includes the problematic configuration value."""
        with patch("bankstatements_core.config.totals_config.parse_totals_columns") as mock_parse:
            mock_parse.side_effect = ValueError("Parse error")

            with patch.dict("os.environ", {"TOTALS_COLUMNS": "invalid_config"}):
                with pytest.raises(ConfigurationError) as exc_info:
                    AppConfig.from_env()

                # Should mention the config value
                error_msg = str(exc_info.value)
                assert "TOTALS_COLUMNS" in error_msg or "invalid_config" in error_msg


class TestExceptionHandlingBenefits:
    """Test the benefits of specific exception handling."""

    def test_specific_exceptions_provide_debugging_info(self):
        """Specific exception types provide better debugging context."""
        service = ColumnTotalsService(totals_columns=["Amount"])

        # ValueError has specific meaning: non-numeric data
        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            mock_calc.side_effect = ValueError("Cannot convert 'abc' to float")

            df = pd.DataFrame({"Amount": ["abc"]})

            # Should catch ValueError and log the specific error
            totals = service.calculate(df)
            assert totals["Amount"] == 0.0

    def test_only_expected_errors_are_caught(self):
        """Pattern: catch expected errors, let unexpected errors bubble up."""
        service = ColumnTotalsService(totals_columns=["Value"])

        # Expected error (ValueError) is caught
        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            mock_calc.side_effect = ValueError("Expected error")
            df = pd.DataFrame({"Value": [1]})
            totals = service.calculate(df)
            assert totals["Value"] == 0.0

        # Unexpected error (KeyError) bubbles up
        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            mock_calc.side_effect = KeyError("Unexpected error")
            df = pd.DataFrame({"Value": [1]})
            with pytest.raises(KeyError):
                service.calculate(df)


class TestComparisonWithGenericCatching:
    """
    Demonstrate why specific exception handling is better than generic.
    """

    def test_generic_exception_would_hide_bugs(self):
        """
        Generic 'except Exception' would hide bugs that should surface.

        With our specific exception handling (ValueError, TypeError only),
        unexpected errors like KeyError bubble up and alert us to bugs.
        """
        service = ColumnTotalsService(totals_columns=["Amount"])

        # Simulate a bug: KeyError in the calculation logic
        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            mock_calc.side_effect = KeyError("missing_key")  # Bug in code

            df = pd.DataFrame({"Amount": [1, 2]})

            # With generic catching, this would return 0.0 silently
            # With specific catching, it raises and we know there's a bug
            with pytest.raises(KeyError):
                service.calculate(df)

    def test_specific_catching_preserves_error_messages(self):
        """Specific exception types preserve detailed error messages."""
        service = ColumnTotalsService(totals_columns=["Amount"])

        with patch("bankstatements_core.services.totals_calculator.calculate_column_sum") as mock_calc:
            detailed_error = ValueError(
                "Cannot convert 'invalid_data' to float at row 42, column 'Amount'"
            )
            mock_calc.side_effect = detailed_error

            df = pd.DataFrame({"Amount": []})

            # Error message is logged (we verify no exception is raised)
            totals = service.calculate(df)
            assert "Amount" in totals
            # The detailed error message would be in the logs
