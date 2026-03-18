"""
Tests for constructor validation in service classes.

Verifies that services validate their constructor parameters and fail fast
with clear error messages when given invalid inputs.
"""

import pytest

from bankstatements_core.exceptions import InputValidationError
from bankstatements_core.services.duplicate_detector import DuplicateDetectionService
from bankstatements_core.services.iban_grouping import IBANGroupingService
from bankstatements_core.services.transaction_filter import TransactionFilterService


class TestIBANGroupingServiceValidation:
    """Test constructor validation for IBANGroupingService."""

    def test_valid_suffix_length(self):
        """Valid suffix_length values are accepted."""
        # Test various valid values
        for length in [1, 4, 10, 34]:
            service = IBANGroupingService(suffix_length=length)
            assert service._suffix_length == length

    def test_suffix_length_not_integer(self):
        """Raises InputValidationError if suffix_length is not an integer."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=4.5)  # type: ignore
        assert "suffix_length must be int" in str(exc_info.value)
        assert "float" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length="4")  # type: ignore
        assert "suffix_length must be int" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_suffix_length_less_than_one(self):
        """Raises InputValidationError if suffix_length < 1."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=0)
        assert "suffix_length must be >= 1" in str(exc_info.value)
        assert "got 0" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=-5)
        assert "suffix_length must be >= 1" in str(exc_info.value)
        assert "got -5" in str(exc_info.value)

    def test_suffix_length_exceeds_max_iban_length(self):
        """Raises InputValidationError if suffix_length > 34 (max IBAN length)."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=35)
        assert "cannot exceed 34" in str(exc_info.value)
        assert "max IBAN length" in str(exc_info.value)
        assert "got 35" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=100)
        assert "cannot exceed 34" in str(exc_info.value)
        assert "got 100" in str(exc_info.value)

    def test_error_message_context(self):
        """Error messages include helpful context."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=-1)

        error_msg = str(exc_info.value)
        # Should include parameter name
        assert "suffix_length" in error_msg
        # Should include actual value provided
        assert "-1" in error_msg
        # Should include constraint
        assert ">= 1" in error_msg


class TestDuplicateDetectionServiceValidation:
    """Test constructor validation for DuplicateDetectionService."""

    def test_valid_strategy(self):
        """Valid strategy object is accepted."""

        class MockStrategy:
            def detect_duplicates(self, transactions):
                return transactions, []

        strategy = MockStrategy()
        service = DuplicateDetectionService(strategy=strategy)
        assert service.strategy is strategy

    def test_strategy_is_none(self):
        """Raises InputValidationError if strategy is None."""
        with pytest.raises(InputValidationError) as exc_info:
            DuplicateDetectionService(strategy=None)  # type: ignore
        assert "strategy cannot be None" in str(exc_info.value)

    def test_strategy_missing_detect_duplicates_method(self):
        """Raises InputValidationError if strategy lacks detect_duplicates method."""

        class InvalidStrategy:
            pass

        with pytest.raises(InputValidationError) as exc_info:
            DuplicateDetectionService(strategy=InvalidStrategy())  # type: ignore
        assert "must have 'detect_duplicates' method" in str(exc_info.value)
        assert "InvalidStrategy" in str(exc_info.value)

    def test_strategy_not_an_object(self):
        """Raises InputValidationError if strategy is not an object."""
        with pytest.raises(InputValidationError) as exc_info:
            DuplicateDetectionService(strategy="invalid")  # type: ignore
        assert "must have 'detect_duplicates' method" in str(exc_info.value)

    def test_error_message_includes_type(self):
        """Error message includes the actual type provided."""

        class WrongStrategy:
            pass

        with pytest.raises(InputValidationError) as exc_info:
            DuplicateDetectionService(strategy=WrongStrategy())  # type: ignore

        error_msg = str(exc_info.value)
        assert "WrongStrategy" in error_msg


class TestTransactionFilterServiceValidation:
    """Test constructor validation for TransactionFilterService."""

    def test_valid_column_names(self):
        """Valid column_names list is accepted."""
        column_names = ["Date", "Details", "Amount"]
        service = TransactionFilterService(column_names=column_names)
        assert service._column_names == column_names

    def test_empty_column_names(self):
        """Raises InputValidationError if column_names is empty."""
        with pytest.raises(InputValidationError) as exc_info:
            TransactionFilterService(column_names=[])
        assert "column_names cannot be empty" in str(exc_info.value)

    def test_column_names_not_a_list(self):
        """Raises InputValidationError if column_names is not a list."""
        with pytest.raises(InputValidationError) as exc_info:
            TransactionFilterService(column_names="Date,Details")  # type: ignore
        assert "column_names must be list" in str(exc_info.value)
        assert "str" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            TransactionFilterService(column_names=("Date", "Details"))  # type: ignore
        assert "column_names must be list" in str(exc_info.value)
        assert "tuple" in str(exc_info.value)

    def test_column_names_contains_non_strings(self):
        """Raises InputValidationError if column_names contains non-strings."""
        with pytest.raises(InputValidationError) as exc_info:
            TransactionFilterService(column_names=["Date", 123, "Amount"])  # type: ignore
        assert "must contain only strings" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            TransactionFilterService(column_names=["Date", None, "Amount"])  # type: ignore
        assert "must contain only strings" in str(exc_info.value)

    def test_single_column_name(self):
        """Single column name is valid."""
        service = TransactionFilterService(column_names=["Date"])
        assert service._column_names == ["Date"]


class TestConstructorValidationIntegration:
    """Integration tests for constructor validation across services."""

    def test_validation_happens_at_construction(self):
        """Validation happens immediately at construction, not later."""
        # Should fail immediately, not when calling methods
        with pytest.raises(InputValidationError):
            IBANGroupingService(suffix_length=-1)

        with pytest.raises(InputValidationError):
            DuplicateDetectionService(strategy=None)  # type: ignore

        with pytest.raises(InputValidationError):
            TransactionFilterService(column_names=[])

    def test_fail_fast_prevents_invalid_state(self):
        """Invalid objects are never created."""
        # Try to create invalid service - should raise immediately
        with pytest.raises(InputValidationError):
            IBANGroupingService(suffix_length=0)

    def test_error_messages_are_actionable(self):
        """Error messages provide clear, actionable information."""
        # Test IBANGroupingService error message
        try:
            IBANGroupingService(suffix_length=50)
        except InputValidationError as e:
            error_msg = str(e)
            # Should tell what's wrong
            assert "cannot exceed 34" in error_msg
            # Should tell what was provided
            assert "50" in error_msg
            # Should tell the limit
            assert "max IBAN length" in error_msg

        # Test TransactionFilterService error message
        try:
            TransactionFilterService(column_names=[])
        except InputValidationError as e:
            error_msg = str(e)
            # Should tell what's wrong
            assert "cannot be empty" in error_msg
            # Should identify the parameter
            assert "column_names" in error_msg

    def test_validation_does_not_affect_valid_usage(self):
        """Validation does not impact valid usage."""
        # All valid constructions should work normally
        iban_service = IBANGroupingService(suffix_length=4)
        assert iban_service._suffix_length == 4

        class ValidStrategy:
            def detect_duplicates(self, transactions):
                return transactions, []

        dup_service = DuplicateDetectionService(strategy=ValidStrategy())
        assert dup_service.strategy is not None

        filter_service = TransactionFilterService(column_names=["Date", "Amount"])
        assert filter_service._column_names == ["Date", "Amount"]


class TestValidationErrorDetails:
    """Test that validation errors provide helpful details."""

    def test_error_includes_parameter_name(self):
        """Error message includes the parameter name."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=-1)
        assert "suffix_length" in str(exc_info.value)

    def test_error_includes_actual_value(self):
        """Error message includes the actual value provided."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=100)
        assert "100" in str(exc_info.value)

    def test_error_includes_constraint(self):
        """Error message includes the constraint violated."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=0)
        assert ">= 1" in str(exc_info.value)

        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length=50)
        assert "34" in str(exc_info.value)

    def test_error_includes_type_information(self):
        """Error message includes type information when type is wrong."""
        with pytest.raises(InputValidationError) as exc_info:
            IBANGroupingService(suffix_length="4")  # type: ignore
        assert "int" in str(exc_info.value)
        assert "str" in str(exc_info.value)
