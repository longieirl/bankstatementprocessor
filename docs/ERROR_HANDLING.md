# Error Handling Strategy

This document defines the error handling patterns used throughout the bankstatements codebase to ensure consistent, maintainable, and predictable error management across different architectural layers.

## Overview

The codebase follows a layered architecture with distinct error handling strategies for each layer:

1. **Domain Layer**: Raise domain-specific exceptions
2. **Service Layer**: Catch infrastructure errors, convert to application exceptions
3. **Utility Layer**: Return None or default values for expected failures
4. **Orchestration Layer**: Catch, log, and decide whether to continue or fail

## Error Handling Patterns

### Pattern 1: Catch and Continue (Orchestration Layer)

**When to use**: Processing multiple items where one failure shouldn't stop others.

**Example**: PDF processing orchestrator

```python
# src/services/pdf_processing_orchestrator.py
def process_pdfs(self, pdf_files: list[Path]) -> tuple[list[dict], dict[str, str]]:
    """Process multiple PDFs, continuing on errors."""
    all_rows = []
    excluded_files = {}

    for pdf_path in pdf_files:
        try:
            rows, pages, iban = self._extract_from_single_pdf(pdf_path)
            all_rows.extend(rows)
        except PDFExtractionError as exc:
            # Log and continue - one bad PDF shouldn't stop processing
            logger.error(f"Failed to process {pdf_path.name}: {exc}")
            excluded_files[pdf_path.name] = str(exc)
        except Exception as exc:
            # Unexpected errors also logged but don't stop processing
            logger.exception(f"Unexpected error processing {pdf_path.name}")
            excluded_files[pdf_path.name] = f"Unexpected error: {exc}"

    return all_rows, excluded_files
```

**Characteristics**:
- Catches exceptions at iteration level
- Logs failures with context
- Collects errors for reporting
- Continues processing remaining items
- Returns both successes and failures

**Use cases**:
- Batch PDF processing
- Multi-file operations
- Background jobs
- Report generation with partial results

---

### Pattern 2: Catch and Convert (Service Layer)

**When to use**: Converting infrastructure/external errors to domain exceptions.

**Example**: IBAN extraction service

```python
# src/extraction/iban_extractor.py
def extract_iban(self, text: str) -> str | None:
    """Extract IBAN from text, converting low-level errors."""
    try:
        # External library call that might fail
        matches = self._iban_pattern.findall(text)
        if matches:
            return self._validate_iban(matches[0])
        return None
    except re.error as exc:
        # Convert regex error to domain-appropriate response
        logger.warning(f"Regex error during IBAN extraction: {exc}")
        return None
    except ValueError as exc:
        # Convert validation error to domain response
        logger.debug(f"Invalid IBAN format: {exc}")
        return None
```

**Characteristics**:
- Catches infrastructure exceptions (regex, I/O, network)
- Converts to domain-appropriate exceptions or None
- Preserves context through logging
- Shields callers from implementation details
- Maintains service contract (returns expected types)

**Use cases**:
- External API calls
- File I/O operations
- Parsing/validation operations
- Database access
- Third-party library interactions

---

### Pattern 3: Return None (Utility Layer)

**When to use**: Pure functions where failure is expected and None is meaningful.

**Example**: Date parsing utilities

```python
# src/services/date_parser.py
def parse_date(self, date_str: str) -> datetime | None:
    """Parse date string, returning None if invalid."""
    if not date_str or not date_str.strip():
        return None

    # Try multiple date formats
    for fmt in self.DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue  # Try next format

    # All formats failed - return None (expected for invalid dates)
    return None
```

**Characteristics**:
- No exception throwing for expected failures
- Returns None as valid "not found" indicator
- Simple, predictable contract
- Caller decides how to handle None
- No logging (too noisy for utilities)

**Use cases**:
- Type conversions (to_float, to_int)
- Date/time parsing
- String formatting
- Simple validators
- Helper functions

---

### Pattern 4: Fail Fast (Validation Layer)

**When to use**: Validating critical preconditions that indicate programmer error.

**Example**: Configuration validation

```python
# src/config/processor_config.py
@dataclass
class ProcessorConfig:
    """Configuration with validation."""

    input_dir: Path
    output_dir: Path

    def __post_init__(self) -> None:
        """Validate configuration on construction."""
        if not self.input_dir.exists():
            raise ValueError(
                f"Input directory does not exist: {self.input_dir}"
            )

        if self.input_dir == self.output_dir:
            raise ValueError(
                "Input and output directories cannot be the same"
            )
```

**Characteristics**:
- Raises exceptions for invalid state
- Fails early before work begins
- Clear error messages
- Indicates programmer error (not user error)
- No recovery expected

**Use cases**:
- Configuration validation
- Precondition checking
- Type/range validation
- Contract enforcement
- Builder pattern validation

---

## Exception Hierarchy

### Domain Exceptions

Custom exceptions for business logic errors:

```python
# src/exceptions.py (future)
class BankStatementError(Exception):
    """Base exception for bank statement processing."""
    pass

class PDFExtractionError(BankStatementError):
    """Error during PDF extraction."""
    pass

class TemplateDetectionError(BankStatementError):
    """Error detecting bank template."""
    pass

class ValidationError(BankStatementError):
    """Data validation error."""
    pass
```

### When to Create Custom Exceptions

Create custom exceptions when:
1. You need to catch specific error types differently
2. Error represents a domain concept (not infrastructure)
3. Multiple layers need to handle it differently
4. Error needs additional context beyond message

Don't create custom exceptions for:
- One-off errors that won't be caught specifically
- Infrastructure errors (use existing: IOError, ValueError)
- Errors that can be represented by None

---

## Logging Guidelines

### What to Log

**ERROR level**:
- Expected but problematic conditions (malformed PDF, missing data)
- Recoverable failures in processing
- Failed external service calls

**WARNING level**:
- Deprecated functionality usage
- Fallback to default behavior
- Suspicious but valid data

**INFO level**:
- Processing milestones (PDF started/completed)
- Configuration loaded
- Major state transitions

**DEBUG level**:
- Detailed processing steps
- Data transformations
- Algorithm decisions

### What NOT to Log

- Personal data (GDPR compliance)
- Passwords, tokens, credentials
- Full stack traces for expected errors
- High-frequency debug messages in production

### Logging Examples

```python
# Good: Context + action + outcome
logger.info(f"Processing PDF {pdf_num}/{total}: {pdf_path.name}")
logger.error(f"Failed to parse date '{date_str}': invalid format")
logger.warning(f"No IBAN found in {pdf_path.name}, using filename for grouping")

# Bad: Too vague or missing context
logger.info("Processing")
logger.error("Error")
logger.warning("Something wrong")
```

---

## Decision Tree

Use this flowchart to decide which pattern to use:

```
Is this a utility function (pure, stateless)?
├─ YES → Use Pattern 3 (Return None)
└─ NO → Is this processing multiple items?
    ├─ YES → Use Pattern 1 (Catch and Continue)
    └─ NO → Is this calling external code/infrastructure?
        ├─ YES → Use Pattern 2 (Catch and Convert)
        └─ NO → Is this a precondition/validation?
            ├─ YES → Use Pattern 4 (Fail Fast)
            └─ NO → Let exceptions propagate
```

---

## Anti-Patterns

### ❌ Catching Everything

```python
# BAD: Swallows all errors including KeyboardInterrupt, SystemExit
try:
    process_pdf(path)
except:  # noqa
    logger.error("Error processing PDF")
```

**Fix**: Catch specific exceptions or use `except Exception`.

---

### ❌ Empty Exception Handlers

```python
# BAD: Silent failure, impossible to debug
try:
    value = float(text)
except ValueError:
    pass  # What happened? Why?
```

**Fix**: Log the error or return explicit None.

---

### ❌ Exception as Control Flow

```python
# BAD: Using exceptions for normal control flow
try:
    date_col = columns["Date"]
except KeyError:
    date_col = columns["Transaction Date"]
```

**Fix**: Use `get()` or explicit checks.

```python
# GOOD
date_col = columns.get("Date") or columns.get("Transaction Date")
```

---

### ❌ Logging and Re-raising

```python
# BAD: Duplicate logging in every layer
try:
    result = process()
except Exception as exc:
    logger.error(f"Process failed: {exc}")
    raise  # Upper layer will also log this
```

**Fix**: Log at the handling layer, not at every propagation point.

---

## Testing Error Handling

### Test Expected Errors

```python
def test_parse_date_with_invalid_format():
    """Test that invalid dates return None."""
    service = DateParserService()
    result = service.parse_date("not-a-date")
    assert result is None
```

### Test Error Recovery

```python
def test_process_continues_on_pdf_error(mocker):
    """Test that one bad PDF doesn't stop batch processing."""
    mocker.patch("extract_pdf", side_effect=[
        PDFExtractionError("Bad PDF"),  # First fails
        (rows, 5, "IE12345"),  # Second succeeds
    ])

    orchestrator = PDFProcessingOrchestrator()
    rows, excluded = orchestrator.process_pdfs([pdf1, pdf2])

    assert len(rows) > 0  # Second PDF was processed
    assert pdf1.name in excluded  # First PDF was logged
```

### Test Exception Conversion

```python
def test_iban_extractor_handles_regex_error(mocker):
    """Test that regex errors are converted to None."""
    mocker.patch("re.findall", side_effect=re.error("Bad pattern"))

    extractor = IBANExtractor()
    result = extractor.extract_iban("some text")

    assert result is None  # Error converted, not propagated
```

---

## Best Practices Summary

1. **Be Specific**: Catch specific exceptions, not `Exception` or bare `except`
2. **Provide Context**: Log enough information to debug the issue
3. **Fail Appropriately**: Choose fail-fast vs. continue based on operation type
4. **Don't Swallow**: Always log or handle caught exceptions
5. **Test Error Paths**: Write tests for error conditions, not just happy paths
6. **Document Behavior**: Document what exceptions a function raises
7. **Use Type Hints**: Use `| None` return types to signal possible failure
8. **Clean Up Resources**: Use context managers (`with`) for resource management
9. **Respect Layers**: Convert exceptions at layer boundaries
10. **Keep It Simple**: Don't create custom exceptions unless needed

---

## References

- **Python Exception Hierarchy**: https://docs.python.org/3/library/exceptions.html
- **Logging Best Practices**: https://docs.python.org/3/howto/logging.html
- **GDPR Logging Guidelines**: See `docs/GDPR_COMPLIANCE.md`
- **Security Logging**: See `docs/SECURITY_LOGGING.md`

---

## Revision History

- **2025-02-01**: Initial version documenting error handling patterns
