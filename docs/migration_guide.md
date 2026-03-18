# Migration Guide

## Overview

This guide helps developers migrate code to use the refactored architecture. The refactoring maintains backward compatibility where possible, but introduces new, better ways to accomplish tasks.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Breaking Changes](#breaking-changes)
3. [Deprecated Patterns](#deprecated-patterns)
4. [New Recommended Patterns](#new-recommended-patterns)
5. [Step-by-Step Migration](#step-by-step-migration)

---

## Quick Start

### Before (Old Way)
```python
from src.processor import BankStatementProcessor

# Old: Direct instantiation with many parameters
processor = BankStatementProcessor(
    input_dir=Path("/input"),
    output_dir=Path("/output"),
    table_top_y=300,
    table_bottom_y=720,
    columns=None,
    enable_dynamic_boundary=False,
    sort_by_date=True,
    totals_columns=["debit", "credit"],
    generate_monthly_summary=True,
    output_strategies=None,
    duplicate_strategy=None,
    repository=None
)
```

### After (New Way)
```python
from src.builders import BankStatementProcessorBuilder

# New: Builder pattern with fluent interface
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/input"))
    .with_output_dir(Path("/output"))
    .with_date_sorting(True)
    .with_monthly_summary(True)
    .with_totals(["debit", "credit"])
    .build()
)
```

### Using Facade (Simplest)
```python
from src.facades import BankStatementProcessingFacade

# Simplest: Let facade handle everything
facade = BankStatementProcessingFacade.from_environment()
exit_code = facade.process_with_error_handling()
```

---

## Breaking Changes

### None!

The refactoring was designed to maintain backward compatibility. All existing code should continue to work.

However, some patterns are now **deprecated** and have better alternatives.

---

## Deprecated Patterns

### 1. Direct Processor Instantiation

❌ **Deprecated**:
```python
processor = BankStatementProcessor(
    input_dir=path1,
    output_dir=path2,
    # ... 10 more parameters
)
```

✅ **Recommended**:
```python
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(path1)
    .with_output_dir(path2)
    .build()
)
```

**Why**: Builder pattern is more readable, validates parameters, and scales better.

### 2. Direct Function Calls for Services

❌ **Deprecated**:
```python
from src.processor import generate_monthly_summary

summary = generate_monthly_summary(transactions, column_names)
```

✅ **Recommended**:
```python
from src.services import MonthlySummaryService

service = MonthlySummaryService(debit_columns, credit_columns)
summary = service.generate(transactions)
```

**Why**: Service objects are more testable and follow SRP.

### 3. Complex main() Logic

❌ **Deprecated**:
```python
def main():
    setup_logging()
    config = get_config_singleton()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    # ... 50 more lines ...
```

✅ **Recommended**:
```python
def main():
    facade = BankStatementProcessingFacade.from_environment()
    return facade.process_with_error_handling()
```

**Why**: Facade hides complexity and provides cleaner interface.

---

## New Recommended Patterns

### 1. Using Services

Services encapsulate business logic with single responsibility.

#### Duplicate Detection

**Old Way**:
```python
# Logic was embedded in processor
unique, duplicates = processor._detect_duplicates(transactions)
```

**New Way**:
```python
from src.services import DuplicateDetectionService
from src.patterns.strategies import AllFieldsDuplicateStrategy

strategy = AllFieldsDuplicateStrategy()
service = DuplicateDetectionService(strategy)
unique, duplicates = service.detect_and_separate(transactions)
```

#### Transaction Sorting

**Old Way**:
```python
# Logic was embedded in processor
sorted_txns = processor._sort_transactions_by_date(transactions)
```

**New Way**:
```python
from src.services import TransactionSortingService, ChronologicalSortingStrategy

strategy = ChronologicalSortingStrategy()
service = TransactionSortingService(strategy)
sorted_txns = service.sort(transactions)
```

#### Monthly Summary

**Old Way**:
```python
from src.processor import generate_monthly_summary

summary = generate_monthly_summary(transactions, columns)
```

**New Way**:
```python
from src.services import MonthlySummaryService

service = MonthlySummaryService(
    debit_columns=["Debit €"],
    credit_columns=["Credit €"]
)
summary = service.generate(transactions)
```

### 2. Using Builder Pattern

**Benefits**:
- Self-documenting code
- Parameter validation
- Fluent interface
- Easy to add new parameters

**Example**:
```python
from src.builders import BankStatementProcessorBuilder
from src.patterns.strategies import DateAmountDuplicateStrategy

# Clear, readable configuration
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/data/input"))
    .with_output_dir(Path("/data/output"))
    .with_table_bounds(top_y=250, bottom_y=650)
    .with_dynamic_boundary(True)
    .with_date_sorting(True)
    .with_monthly_summary(True)
    .with_totals(["debit", "credit", "balance"])
    .with_duplicate_strategy(DateAmountDuplicateStrategy())
    .build()
)
```

### 3. Using Facade Pattern

**Benefits**:
- Simplest way to run processing
- Hides all complexity
- Comprehensive error handling

**Example**:
```python
from src.facades import BankStatementProcessingFacade

# From environment variables (simplest)
facade = BankStatementProcessingFacade.from_environment()
exit_code = facade.process_with_error_handling()

# With custom config
from src.app import AppConfig
config = AppConfig(
    input_dir=Path("/input"),
    output_dir=Path("/output"),
    # ... other config
)
facade = BankStatementProcessingFacade(config)
summary = facade.process_all()
```

### 4. Using Factory Pattern

**Benefits**:
- Centralized creation logic
- Easy to create configured instances
- Works with Builder pattern

**Example**:
```python
from src.patterns.factories import ProcessorFactory
from src.app import AppConfig

# Create from configuration
config = AppConfig.from_env()
processor = ProcessorFactory.create_from_config(config)

# Custom strategies
from src.patterns.strategies import DateAmountDuplicateStrategy
processor = ProcessorFactory.create_from_config(
    config,
    duplicate_strategy=DateAmountDuplicateStrategy()
)
```

---

## Step-by-Step Migration

### Step 1: Update Imports

**Old**:
```python
from src.processor import BankStatementProcessor, generate_monthly_summary
```

**New**:
```python
from src.builders import BankStatementProcessorBuilder
from src.services import MonthlySummaryService
from src.facades import BankStatementProcessingFacade
```

### Step 2: Replace Direct Instantiation

**Old**:
```python
processor = BankStatementProcessor(
    input_dir, output_dir, 300, 720, None, False, True, None, True, None, None, None
)
```

**New**:
```python
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(input_dir)
    .with_output_dir(output_dir)
    .build()  # Uses sensible defaults
)
```

### Step 3: Replace Service Function Calls

**Old**:
```python
summary = generate_monthly_summary(transactions, columns)
```

**New**:
```python
service = MonthlySummaryService(debit_cols, credit_cols)
summary = service.generate(transactions)
```

### Step 4: Simplify Main Logic

**Old**:
```python
def main():
    setup_logging()
    try:
        config = get_config_singleton()
        config.output_dir.mkdir(parents=True, exist_ok=True)
        columns = get_columns_config()
        processor = ProcessorFactory.create_from_config(config)
        summary = processor.run()
        log_summary(summary)
        return 0
    except ConfigurationError as e:
        logger.error("Config error: %s", e)
        return 1
    # ... more error handling
```

**New**:
```python
def main():
    try:
        facade = BankStatementProcessingFacade.from_environment()
        return facade.process_with_error_handling()
    except ConfigurationError as e:
        logger.error("Config error: %s", e)
        return 1
```

### Step 5: Update Tests

**Old**:
```python
def test_processing():
    processor = BankStatementProcessor(
        input_dir, output_dir, 300, 720, None, False, True, None, True, None, None, None
    )
    # ... test logic
```

**New**:
```python
def test_processing():
    processor = (
        BankStatementProcessorBuilder()
        .with_input_dir(input_dir)
        .with_output_dir(output_dir)
        .build()
    )
    # ... test logic
```

---

## Common Migration Scenarios

### Scenario 1: Custom Duplicate Strategy

**Old**:
```python
from src.patterns.strategies import DateAmountDuplicateStrategy

processor = BankStatementProcessor(
    input_dir=path1,
    output_dir=path2,
    duplicate_strategy=DateAmountDuplicateStrategy(),
    # ... many more params
)
```

**New**:
```python
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(path1)
    .with_output_dir(path2)
    .with_duplicate_strategy(DateAmountDuplicateStrategy())
    .build()
)
```

### Scenario 2: Custom Output Formats

**Old**:
```python
from src.patterns.strategies import CSVOutputStrategy, ExcelOutputStrategy

strategies = {
    "csv": CSVOutputStrategy(),
    "excel": ExcelOutputStrategy()
}

processor = BankStatementProcessor(
    input_dir=path1,
    output_dir=path2,
    output_strategies=strategies,
    # ... many more params
)
```

**New**:
```python
strategies = {
    "csv": CSVOutputStrategy(),
    "excel": ExcelOutputStrategy()
}

processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(path1)
    .with_output_dir(path2)
    .with_output_strategies(strategies)
    .build()
)
```

### Scenario 3: Testing with Mock Repository

**Old**:
```python
from unittest.mock import MagicMock

mock_repo = MagicMock()
processor = BankStatementProcessor(
    input_dir, output_dir, 300, 720, None, False, True,
    None, True, None, None, mock_repo
)
```

**New**:
```python
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(input_dir)
    .with_output_dir(output_dir)
    .with_repository(mock_repo)
    .build()
)
```

---

## Testing Migration

### Unit Test Migration

**Old**:
```python
def test_monthly_summary():
    from src.processor import generate_monthly_summary

    transactions = [...]
    columns = ["Date", "Debit €", "Credit €"]

    summary = generate_monthly_summary(transactions, columns)
    assert summary["total_months"] == 1
```

**New**:
```python
def test_monthly_summary():
    from src.services import MonthlySummaryService

    transactions = [...]
    debit_cols = ["Debit €"]
    credit_cols = ["Credit €"]

    service = MonthlySummaryService(debit_cols, credit_cols)
    summary = service.generate(transactions)
    assert summary["total_months"] == 1
```

### Integration Test Migration

**Old**:
```python
def test_full_processing():
    processor = BankStatementProcessor(
        input_dir, output_dir, 300, 720, None, False, True,
        ["debit", "credit"], True, None, None, None
    )
    summary = processor.run()
    assert summary["pdf_count"] > 0
```

**New**:
```python
def test_full_processing():
    processor = (
        BankStatementProcessorBuilder()
        .with_input_dir(input_dir)
        .with_output_dir(output_dir)
        .with_totals(["debit", "credit"])
        .with_monthly_summary(True)
        .build()
    )
    summary = processor.run()
    assert summary["pdf_count"] > 0
```

---

## Performance Considerations

The refactoring **does not** negatively impact performance:

### Same Performance
- Service layer adds minimal overhead (just method calls)
- Builder pattern overhead is negligible (only during construction)
- Facade pattern adds no runtime overhead

### Potential Improvements
- Repository pattern enables caching strategies
- Strategy pattern allows performance tuning per algorithm
- Services are stateless and could be parallelized

### Benchmarking
```python
import time

# Benchmark old vs new approach
start = time.time()
# ... old code ...
old_time = time.time() - start

start = time.time()
# ... new code ...
new_time = time.time() - start

print(f"Old: {old_time:.2f}s, New: {new_time:.2f}s")
```

---

## Troubleshooting

### Issue: Builder validation error

**Error**: `ValueError: Input directory is required. Use with_input_dir().`

**Solution**: Make sure to call required methods before `build()`:
```python
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(path)  # Required
    .with_output_dir(path)  # Required
    .build()
)
```

### Issue: Service needs column names

**Error**: Service expects specific column names but they're not provided.

**Solution**: Extract column names before creating service:
```python
from src.pdf_table_extractor import get_columns_config

columns = get_columns_config()
debit_cols = [col for col in columns if "debit" in col.lower()]
credit_cols = [col for col in columns if "credit" in col.lower()]

service = MonthlySummaryService(debit_cols, credit_cols)
```

### Issue: Facade raises ConfigurationError

**Error**: Configuration error when using facade.

**Solution**: Check environment variables are set:
```bash
export INPUT_DIR="/path/to/input"
export OUTPUT_DIR="/path/to/output"
# ... other required env vars
```

Or provide config directly:
```python
config = AppConfig(
    input_dir=Path("/input"),
    output_dir=Path("/output"),
    # ... required fields
)
facade = BankStatementProcessingFacade(config)
```

---

## Getting Help

### Documentation
- [Architecture Documentation](./architecture.md)
- [Design Patterns Guide](./design_patterns_guide.md)
- Code docstrings (use `help(Class)` in Python)

### Code Examples
- Check `tests/` directory for usage examples
- Each service has comprehensive test coverage showing usage

### Questions?
- Open an issue on GitHub
- Check existing code for patterns
- Review test files for examples

---

## Summary

### Key Takeaways

1. **Backward Compatible**: Old code still works
2. **Builder Pattern**: Use for processor creation
3. **Services**: Use for business logic
4. **Facade**: Use for simple high-level operations
5. **Factory**: Use for configured creation
6. **Tests**: Update to use new patterns

### Migration Priority

**High Priority** (Do First):
1. Replace direct processor instantiation with Builder
2. Update main() to use Facade
3. Update tests to use Builder

**Medium Priority** (Do Soon):
4. Replace function calls with Services
5. Update integration tests

**Low Priority** (Nice to Have):
6. Use Factory for complex creation scenarios
7. Implement custom strategies if needed

### Next Steps

1. Read [Architecture Documentation](./architecture.md)
2. Read [Design Patterns Guide](./design_patterns_guide.md)
3. Start with high-priority migrations
4. Run tests after each change
5. Gradually adopt new patterns

Remember: Migration can be gradual. The old patterns still work, but new patterns provide better maintainability and testability.
