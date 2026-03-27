"""
Domain-specific exceptions for bank statement processing.

This module provides a clear exception hierarchy for the bank statements application,
following the "Fail Fast + Clear Errors" principle. All exceptions inherit from
BankStatementError to enable consistent error handling.

Exception Hierarchy:
    BankStatementError (base exception for all domain errors)
    ├── ConfigurationError (invalid configuration)
    ├── PDFExtractionError (PDF processing errors)
    │   ├── PDFReadError (cannot read/open PDF)
    │   └── TableExtractionError (table extraction failures)
    ├── TemplateError (template-related errors)
    │   ├── TemplateDetectionError (template detection failures)
    │   └── TemplateValidationError (invalid template structure)
    ├── ValidationError (validation failures)
    │   ├── DataValidationError (invalid transaction data)
    │   └── InputValidationError (invalid input parameters)
    ├── EntitlementError (tier/license restrictions)
    └── ProcessingError (processing failures)
        ├── DuplicateDetectionError (duplicate detection failures)
        └── TransactionProcessingError (transaction processing failures)

Usage:
    from bankstatements_core.exceptions import ConfigurationError, PDFExtractionError

    # Validate inputs at boundaries
    if not config.is_valid():
        raise ConfigurationError(
            f"Invalid configuration: {config.errors()}"
        )

    # Use specific exceptions for clear error handling
    try:
        extract_pdf(path)
    except PDFReadError as e:
        logger.error(f"Cannot read PDF: {e}")
    except TableExtractionError as e:
        logger.warning(f"Table extraction failed: {e}")
"""


class BankStatementError(Exception):
    """
    Base exception for all bank statement processing errors.

    All domain-specific exceptions inherit from this class, enabling
    consumers to catch all application errors with a single except clause
    while still allowing specific error handling when needed.

    Example:
        try:
            process_bank_statement(pdf_path)
        except BankStatementError as e:
            # Catches all domain errors
            logger.error(f"Processing failed: {e}")
    """

    pass


# ==============================================================================
# Configuration Errors
# ==============================================================================


class ConfigurationError(BankStatementError):
    """
    Raised when configuration is invalid or missing.

    This includes environment variables, application settings, and runtime
    configuration that prevents the application from starting or processing.

    Examples:
        - TABLE_TOP_Y >= TABLE_BOTTOM_Y (invalid bounds)
        - Missing required environment variables
        - Invalid output format specification
        - Conflicting configuration values

    Example:
        if table_top_y >= table_bottom_y:
            raise ConfigurationError(
                f"TABLE_TOP_Y ({table_top_y}) must be less than "
                f"TABLE_BOTTOM_Y ({table_bottom_y})"
            )
    """

    pass


# ==============================================================================
# PDF Extraction Errors
# ==============================================================================


class PDFExtractionError(BankStatementError):
    """
    Base exception for PDF extraction errors.

    Use specific subclasses (PDFReadError, TableExtractionError) when possible
    for more precise error handling. Use this base class only when the specific
    error type is unknown or not applicable.
    """

    pass


class PDFReadError(PDFExtractionError):
    """
    Raised when a PDF file cannot be read or opened.

    This includes:
        - File not found
        - Corrupted PDF files
        - Encrypted PDFs without password
        - Permission denied
        - Invalid PDF format

    Example:
        try:
            pdf = pdfplumber.open(pdf_path)
        except FileNotFoundError:
            raise PDFReadError(f"PDF file not found: {pdf_path}")
        except (OSError, ValueError, RuntimeError) as e:
            raise PDFReadError(f"Cannot read PDF {pdf_path}: {e}") from e
    """

    pass


class TableExtractionError(PDFExtractionError):
    """
    Raised when table extraction from PDF fails.

    This includes:
        - No tables found in PDF
        - Invalid table boundaries
        - Malformed table structure
        - Unexpected table format

    Example:
        if not tables:
            raise TableExtractionError(
                f"No tables found in {pdf_path} with settings: {table_settings}"
            )
    """

    pass


# ==============================================================================
# Template Errors
# ==============================================================================


class TemplateError(BankStatementError):
    """
    Base exception for template-related errors.

    Templates define the structure and extraction rules for different bank
    statement formats. Use specific subclasses for detection vs validation errors.
    """

    pass


class TemplateDetectionError(TemplateError):
    """
    Raised when template detection fails or returns ambiguous results.

    This includes:
        - Multiple templates match with equal confidence
        - No templates match the PDF structure
        - Template detection service unavailable

    Example:
        if len(matching_templates) > 1:
            raise TemplateDetectionError(
                f"Ambiguous template detection for {pdf_path}: "
                f"{len(matching_templates)} templates matched. "
                f"Matches: {[t.name for t in matching_templates]}"
            )
    """

    pass


class TemplateValidationError(TemplateError):
    """
    Raised when a template structure is invalid.

    This includes:
        - Missing required fields in template
        - Invalid column definitions
        - Inconsistent boundary settings
        - Invalid regular expressions

    Example:
        if not template.has_required_fields():
            raise TemplateValidationError(
                f"Template '{template.name}' missing required fields: "
                f"{template.missing_fields()}"
            )
    """

    pass


# ==============================================================================
# Validation Errors
# ==============================================================================


class ValidationError(BankStatementError):
    """
    Base exception for validation errors.

    Use DataValidationError for transaction/data validation and
    InputValidationError for parameter/input validation.
    """

    pass


class DataValidationError(ValidationError):
    """
    Raised when transaction or extracted data fails validation.

    This includes:
        - Invalid date formats
        - Missing required transaction fields
        - Invalid amount values
        - Data integrity violations

    Example:
        if not transaction.has_date():
            raise DataValidationError(
                f"Transaction missing required date field: {transaction}"
            )
    """

    pass


class InputValidationError(ValidationError):
    """
    Raised when input parameters fail validation.

    This includes:
        - Invalid constructor parameters
        - Out-of-range values
        - Wrong parameter types
        - Null/empty required parameters

    Use this for fail-fast validation at boundaries (constructors, public methods).

    Example:
        def __init__(self, suffix_length: int):
            if suffix_length < 1:
                raise InputValidationError(
                    f"suffix_length must be >= 1, got {suffix_length}"
                )
            self.suffix_length = suffix_length
    """

    pass


# ==============================================================================
# Entitlement Errors
# ==============================================================================


class EntitlementError(BankStatementError):
    """
    Raised when an operation is not allowed by the current entitlement tier.

    This includes:
        - Attempting to use premium features without license
        - Exceeding tier limits (file count, output formats)
        - Expired or invalid license

    Example:
        if format_name not in self.allowed_output_formats:
            raise EntitlementError(
                f"Output format '{format_name}' is not available in "
                f"{self.tier} tier. Allowed formats: "
                f"{', '.join(sorted(self.allowed_output_formats))}"
            )
    """

    pass


# ==============================================================================
# Processing Errors
# ==============================================================================


class ProcessingError(BankStatementError):
    """
    Base exception for processing errors.

    Use specific subclasses when the error type is known.
    """

    pass


class DuplicateDetectionError(ProcessingError):
    """
    Raised when duplicate detection fails.

    This includes:
        - Hash computation failures
        - Invalid duplicate detection strategy
        - Storage errors for seen hashes

    Example:
        if strategy not in VALID_STRATEGIES:
            raise DuplicateDetectionError(
                f"Invalid duplicate detection strategy: '{strategy}'. "
                f"Valid strategies: {', '.join(VALID_STRATEGIES)}"
            )
    """

    pass


class TransactionProcessingError(ProcessingError):
    """
    Raised when transaction processing fails.

    This includes:
        - Row merging failures
        - Transaction filtering errors
        - Data transformation failures

    Example:
        try:
            merged_transactions = merge_rows(rows)
        except (ValueError, KeyError, TypeError) as e:
            raise TransactionProcessingError(
                f"Failed to merge transaction rows: {e}"
            ) from e
    """

    pass


# ==============================================================================
# Exception Registry
# ==============================================================================

# Export all exceptions for convenient importing
__all__ = [
    # Base
    "BankStatementError",
    # Configuration
    "ConfigurationError",
    "DataValidationError",
    "DuplicateDetectionError",
    # Entitlements
    "EntitlementError",
    "InputValidationError",
    # PDF Extraction
    "PDFExtractionError",
    "PDFReadError",
    # Processing
    "ProcessingError",
    "TableExtractionError",
    "TemplateDetectionError",
    # Templates
    "TemplateError",
    "TemplateValidationError",
    "TransactionProcessingError",
    # Validation
    "ValidationError",
]
