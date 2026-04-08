"""
Tests for domain-specific exception hierarchy.

Tests verify that:
1. All exceptions inherit from BankStatementError
2. Exceptions can be raised and caught correctly
3. Exception messages are preserved
4. Exception chaining works (using 'from e')
5. Specific exceptions can be caught while letting others bubble up
"""

import pytest

from bankstatements_core.exceptions import (
    BankStatementError,
    ConfigurationError,
    DataValidationError,
    DuplicateDetectionError,
    EntitlementError,
    InputValidationError,
    PDFExtractionError,
    PDFReadError,
    ProcessingError,
    TableExtractionError,
    TemplateDetectionError,
    TemplateError,
    TemplateValidationError,
    TransactionProcessingError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit correctly from BankStatementError."""

    def test_base_exception(self):
        """BankStatementError is a subclass of Exception."""
        assert issubclass(BankStatementError, Exception)

    def test_configuration_error_hierarchy(self):
        """ConfigurationError inherits from BankStatementError."""
        assert issubclass(ConfigurationError, BankStatementError)
        assert issubclass(ConfigurationError, Exception)

    def test_pdf_extraction_error_hierarchy(self):
        """PDF extraction errors inherit from BankStatementError."""
        assert issubclass(PDFExtractionError, BankStatementError)
        assert issubclass(PDFReadError, PDFExtractionError)
        assert issubclass(TableExtractionError, PDFExtractionError)

        # Specific errors are also BankStatementErrors
        assert issubclass(PDFReadError, BankStatementError)
        assert issubclass(TableExtractionError, BankStatementError)

    def test_template_error_hierarchy(self):
        """Template errors inherit from BankStatementError."""
        assert issubclass(TemplateError, BankStatementError)
        assert issubclass(TemplateDetectionError, TemplateError)
        assert issubclass(TemplateValidationError, TemplateError)

        # Specific errors are also BankStatementErrors
        assert issubclass(TemplateDetectionError, BankStatementError)
        assert issubclass(TemplateValidationError, BankStatementError)

    def test_validation_error_hierarchy(self):
        """Validation errors inherit from BankStatementError."""
        assert issubclass(ValidationError, BankStatementError)
        assert issubclass(DataValidationError, ValidationError)
        assert issubclass(InputValidationError, ValidationError)

        # Specific errors are also BankStatementErrors
        assert issubclass(DataValidationError, BankStatementError)
        assert issubclass(InputValidationError, BankStatementError)

    def test_entitlement_error_hierarchy(self):
        """EntitlementError inherits from BankStatementError."""
        assert issubclass(EntitlementError, BankStatementError)

    def test_processing_error_hierarchy(self):
        """Processing errors inherit from BankStatementError."""
        assert issubclass(ProcessingError, BankStatementError)
        assert issubclass(DuplicateDetectionError, ProcessingError)
        assert issubclass(TransactionProcessingError, ProcessingError)

        # Specific errors are also BankStatementErrors
        assert issubclass(DuplicateDetectionError, BankStatementError)
        assert issubclass(TransactionProcessingError, BankStatementError)


class TestExceptionMessages:
    """Test that exceptions preserve error messages."""

    def test_base_exception_message(self):
        """BankStatementError preserves message."""
        with pytest.raises(BankStatementError) as exc_info:
            raise BankStatementError("Test error message")
        assert str(exc_info.value) == "Test error message"

    def test_configuration_error_message(self):
        """ConfigurationError preserves message with context."""
        message = "TABLE_TOP_Y (100) must be less than TABLE_BOTTOM_Y (50)"
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError(message)
        assert str(exc_info.value) == message
        assert "TABLE_TOP_Y" in str(exc_info.value)
        assert "TABLE_BOTTOM_Y" in str(exc_info.value)

    def test_pdf_read_error_message(self):
        """PDFReadError includes file path in message."""
        pdf_path = "/path/to/statement.pdf"
        message = f"Cannot read PDF {pdf_path}: File corrupted"
        with pytest.raises(PDFReadError) as exc_info:
            raise PDFReadError(message)
        assert pdf_path in str(exc_info.value)
        assert "corrupted" in str(exc_info.value).lower()

    def test_input_validation_error_message(self):
        """InputValidationError includes parameter details."""
        message = "suffix_length must be >= 1, got -5"
        with pytest.raises(InputValidationError) as exc_info:
            raise InputValidationError(message)
        assert "suffix_length" in str(exc_info.value)
        assert "-5" in str(exc_info.value)


class TestExceptionCatching:
    """Test that exceptions can be caught at different levels of hierarchy."""

    def test_catch_specific_exception(self):
        """Specific exceptions can be caught by their type."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid config")

    def test_catch_by_base_class(self):
        """Specific exceptions can be caught by base class."""
        with pytest.raises(BankStatementError):
            raise ConfigurationError("Invalid config")

    def test_catch_by_intermediate_class(self):
        """Specific exceptions can be caught by intermediate class."""
        with pytest.raises(PDFExtractionError):
            raise PDFReadError("Cannot read PDF")

        with pytest.raises(ValidationError):
            raise InputValidationError("Invalid parameter")

    def test_catch_specific_over_general(self):
        """More specific exception handlers are used first."""
        caught_exception = None

        try:
            raise PDFReadError("Cannot read PDF")
        except PDFReadError:
            caught_exception = "PDFReadError"
        except PDFExtractionError:
            caught_exception = "PDFExtractionError"
        except BankStatementError:
            caught_exception = "BankStatementError"

        assert caught_exception == "PDFReadError"

    def test_catch_all_domain_errors(self):
        """All domain errors can be caught with BankStatementError."""
        errors_raised = []

        for error_class in [
            ConfigurationError,
            PDFReadError,
            TemplateDetectionError,
            InputValidationError,
            EntitlementError,
            DuplicateDetectionError,
        ]:
            try:
                raise error_class("Test error")
            except BankStatementError:
                errors_raised.append(error_class.__name__)

        assert len(errors_raised) == 6


class TestExceptionChaining:
    """Test that exception chaining works correctly with 'from e'."""

    def test_exception_chaining_preserves_original(self):
        """Original exception is preserved with 'from e'."""
        original_error = ValueError("Original error")

        with pytest.raises(ConfigurationError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise ConfigurationError("Config error") from e

        # Check that original exception is preserved
        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_exception_chaining_provides_context(self):
        """Exception chaining provides full error context."""
        with pytest.raises(PDFReadError) as exc_info:
            try:
                raise FileNotFoundError("File not found: test.pdf")
            except FileNotFoundError as e:
                raise PDFReadError(f"Cannot open PDF: {e}") from e

        # Original error is accessible
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)
        # New error has additional context
        assert "Cannot open PDF" in str(exc_info.value)


class TestExceptionUsagePatterns:
    """Test real-world usage patterns for exceptions."""

    def test_constructor_validation_pattern(self):
        """InputValidationError for constructor parameter validation."""

        class Service:
            def __init__(self, value: int):
                if value < 0:
                    raise InputValidationError(f"value must be >= 0, got {value}")
                self.value = value

        # Valid construction
        service = Service(5)
        assert service.value == 5

        # Invalid construction
        with pytest.raises(InputValidationError) as exc_info:
            Service(-1)
        assert "must be >= 0" in str(exc_info.value)
        assert "-1" in str(exc_info.value)

    def test_boundary_validation_pattern(self):
        """ConfigurationError for configuration boundary validation."""

        def validate_table_bounds(top: int, bottom: int):
            if top >= bottom:
                raise ConfigurationError(
                    f"TABLE_TOP_Y ({top}) must be less than TABLE_BOTTOM_Y ({bottom})"
                )

        # Valid bounds
        validate_table_bounds(10, 100)  # Should not raise

        # Invalid bounds
        with pytest.raises(ConfigurationError) as exc_info:
            validate_table_bounds(100, 50)
        assert "TABLE_TOP_Y" in str(exc_info.value)
        assert "100" in str(exc_info.value)
        assert "50" in str(exc_info.value)

    def test_file_processing_error_pattern(self):
        """PDFReadError for file access failures."""

        def open_pdf(path: str):
            try:
                # Simulate file not found
                raise FileNotFoundError(f"No such file: {path}")
            except FileNotFoundError as e:
                raise PDFReadError(f"Cannot read PDF {path}: {e}") from e

        with pytest.raises(PDFReadError) as exc_info:
            open_pdf("/nonexistent/file.pdf")

        assert "Cannot read PDF" in str(exc_info.value)
        assert "/nonexistent/file.pdf" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_entitlement_checking_pattern(self):
        """EntitlementError for tier restrictions."""

        def check_feature_access(tier: str, feature: str):
            allowed_features = {"free": ["csv"], "premium": ["csv", "excel", "json"]}

            if feature not in allowed_features.get(tier, []):
                raise EntitlementError(
                    f"Feature '{feature}' not available in {tier} tier. "
                    f"Allowed: {', '.join(allowed_features[tier])}"
                )

        # Valid access
        check_feature_access("premium", "excel")  # Should not raise

        # Invalid access
        with pytest.raises(EntitlementError) as exc_info:
            check_feature_access("free", "excel")
        assert "not available in free tier" in str(exc_info.value)
        assert "excel" in str(exc_info.value).lower()


class TestExceptionExports:
    """Test that all exceptions are exported in __all__."""

    def test_all_exceptions_exported(self):
        """All exception classes are in __all__."""
        from bankstatements_core import exceptions

        expected_exports = [
            "BankStatementError",
            "ConfigurationError",
            "PDFExtractionError",
            "PDFReadError",
            "TableExtractionError",
            "TemplateError",
            "TemplateDetectionError",
            "TemplateValidationError",
            "ValidationError",
            "DataValidationError",
            "InputValidationError",
            "EntitlementError",
            "ProcessingError",
            "DuplicateDetectionError",
            "TransactionProcessingError",
        ]

        for export in expected_exports:
            assert export in exceptions.__all__, f"{export} not in __all__"
            assert hasattr(exceptions, export), f"{export} not defined"

    def test_can_import_all_exceptions(self):
        """All exceptions can be imported directly."""
        # This test ensures the imports at the top of this file work
        exceptions_list = [
            BankStatementError,
            ConfigurationError,
            PDFExtractionError,
            PDFReadError,
            TableExtractionError,
            TemplateError,
            TemplateDetectionError,
            TemplateValidationError,
            ValidationError,
            DataValidationError,
            InputValidationError,
            EntitlementError,
            ProcessingError,
            DuplicateDetectionError,
            TransactionProcessingError,
        ]

        # All should be classes
        for exc_class in exceptions_list:
            assert isinstance(exc_class, type)
            assert issubclass(exc_class, Exception)
