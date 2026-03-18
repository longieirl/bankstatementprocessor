# Design Patterns Guide

## Introduction

This guide explains when and how to use each design pattern implemented in the Bank Statement Processor. It provides practical examples and guidelines for developers.

## Table of Contents

1. [Strategy Pattern](#strategy-pattern)
2. [Repository Pattern](#repository-pattern)
3. [Singleton Pattern](#singleton-pattern)
4. [Factory Pattern](#factory-pattern)
5. [Chain of Responsibility](#chain-of-responsibility)
6. [Builder Pattern](#builder-pattern)
7. [Facade Pattern](#facade-pattern)
8. [Template Method Pattern](#template-method-pattern)

---

## Strategy Pattern

### What It Is
Defines a family of algorithms, encapsulates each one, and makes them interchangeable.

### When to Use
- You have multiple algorithms for the same task
- You want to switch algorithms at runtime
- You want to avoid conditional logic for choosing algorithms

### Implementations in Codebase

#### 1. Duplicate Detection Strategy

**Location**: `src/patterns/strategies.py`

**Use Case**: Different ways to identify duplicate transactions.

**Example**:
```python
from src.patterns.strategies import AllFieldsDuplicateStrategy, DateAmountDuplicateStrategy

# Strict matching: all fields must match
strict_strategy = AllFieldsDuplicateStrategy()

# Lenient matching: only date and amount
lenient_strategy = DateAmountDuplicateStrategy()

# Use in service
from src.services import DuplicateDetectionService
service = DuplicateDetectionService(lenient_strategy)
unique, duplicates = service.detect_and_separate(transactions)
```

**Creating Your Own Strategy**:
```python
class CustomDuplicateStrategy(DuplicateDetectionStrategy):
    def create_key(self, transaction: dict) -> str:
        # Implement your custom logic
        date = transaction.get("Date", "")
        details = transaction.get("Details", "")
        return f"{date}:{details}"
```

#### 2. Output Format Strategy

**Location**: `src/patterns/strategies.py`

**Use Case**: Different output formats (CSV, JSON, Excel).

**Example**:
```python
from src.patterns.strategies import CSVOutputStrategy, JSONOutputStrategy

# Write as CSV
csv_strategy = CSVOutputStrategy()
csv_strategy.write(transactions, output_path, columns, include_totals=True)

# Write as JSON
json_strategy = JSONOutputStrategy()
json_strategy.write(transactions, output_path, columns)
```

**Creating Your Own Format**:
```python
class XMLOutputStrategy(OutputFormatStrategy):
    def _prepare_data(self, transactions, column_names):
        # Convert to XML structure
        return transactions

    def _write_data(self, data, file_path, column_names, **kwargs):
        # Write XML file
        import xml.etree.ElementTree as ET
        root = ET.Element("transactions")
        for txn in data:
            txn_elem = ET.SubElement(root, "transaction")
            for key, value in txn.items():
                ET.SubElement(txn_elem, key).text = str(value)
        tree = ET.ElementTree(root)
        tree.write(file_path)
```

#### 3. Sorting Strategy

**Location**: `src/services/sorting_service.py`

**Use Case**: Different ways to sort transactions.

**Example**:
```python
from src.services import ChronologicalSortingStrategy, NoSortingStrategy

# Sort by date
chrono_strategy = ChronologicalSortingStrategy()
sorted_txns = chrono_strategy.sort(transactions)

# Keep original order
no_sort_strategy = NoSortingStrategy()
same_order = no_sort_strategy.sort(transactions)
```

### Best Practices
- Keep strategies focused and single-purpose
- Make strategies stateless when possible
- Use dependency injection to provide strategies
- Test each strategy independently

---

## Repository Pattern

### What It Is
Mediates between the domain and data mapping layers, abstracting data access.

### When to Use
- You want to decouple business logic from data access
- You want to easily swap data sources (filesystem, database, cloud)
- You want to simplify testing with mock repositories

### Implementation in Codebase

**Location**: `src/patterns/repositories.py`

**Use Case**: Abstract file I/O operations.

**Example**:
```python
from src.patterns.repositories import FileSystemTransactionRepository

# Use the repository
repo = FileSystemTransactionRepository()
transactions = repo.read(file_path)
repo.save(transactions, output_path)
```

**Creating Your Own Repository**:
```python
class S3TransactionRepository(TransactionRepository):
    def __init__(self, bucket_name: str):
        self.bucket = bucket_name
        self.s3_client = boto3.client('s3')

    def read(self, file_path: Path) -> List[dict]:
        # Read from S3
        obj = self.s3_client.get_object(
            Bucket=self.bucket,
            Key=str(file_path)
        )
        return json.loads(obj['Body'].read())

    def save(self, transactions: List[dict], file_path: Path) -> None:
        # Save to S3
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=str(file_path),
            Body=json.dumps(transactions)
        )
```

**Using in Processor**:
```python
from src.builders import BankStatementProcessorBuilder

s3_repo = S3TransactionRepository("my-bucket")
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/input"))
    .with_output_dir(Path("/output"))
    .with_repository(s3_repo)  # Inject custom repository
    .build()
)
```

### Best Practices
- Keep repository interface simple and focused
- Repository methods should be atomic operations
- Use dependency injection to provide repositories
- Mock repositories for testing

---

## Singleton Pattern

### What It Is
Ensures a class has only one instance and provides global access point.

### When to Use
- You need exactly one instance of a class
- The instance should be accessible globally
- Lazy initialization is beneficial

### Implementation in Codebase

**Location**: `src/patterns/repositories.py`

**Use Case**: Configuration management.

**Example**:
```python
from src.patterns.repositories import get_config_singleton, reset_config_singleton

# Get configuration (creates on first call)
config = get_config_singleton()

# Subsequent calls return same instance
config2 = get_config_singleton()
assert config is config2  # Same object

# Reset for testing
reset_config_singleton()
```

### Best Practices
- Use sparingly (can make testing harder)
- Provide reset mechanism for testing
- Consider dependency injection as alternative
- Document that class is singleton in docstring

---

## Factory Pattern

### What It Is
Creates objects without specifying their exact class.

### When to Use
- Object creation is complex
- You want to centralize creation logic
- You need to create different objects based on conditions

### Implementation in Codebase

**Location**: `src/patterns/factories.py`

**Use Case**: Create configured processor instances.

**Example**:
```python
from src.app import AppConfig
from src.patterns.factories import ProcessorFactory

# Create from configuration
config = AppConfig.from_env()
processor = ProcessorFactory.create_from_config(config)

# Create for specific bank type (if implemented)
processor = ProcessorFactory.create_for_bank("aib", config)
```

**Extending the Factory**:
```python
class ProcessorFactory:
    @staticmethod
    def create_for_bank(bank_type: str, config: AppConfig):
        """Create processor configured for specific bank."""
        if bank_type == "aib":
            # AIB-specific configuration
            strategy = DateAmountDuplicateStrategy()
        elif bank_type == "boi":
            # BOI-specific configuration
            strategy = AllFieldsDuplicateStrategy()
        else:
            strategy = AllFieldsDuplicateStrategy()

        return ProcessorFactory.create_from_config(
            config,
            duplicate_strategy=strategy
        )
```

### Best Practices
- Factory methods should return interface types, not concrete types
- Use factory when creation logic is complex
- Consider builder pattern for very complex creation
- Keep factory methods static unless state is needed

---

## Chain of Responsibility

### What It Is
Passes a request along a chain of handlers until one handles it.

### When to Use
- Multiple objects can handle a request
- Handler isn't known in advance
- You want to decouple sender from receiver

### Implementation in Codebase

**Location**: `src/extraction/row_classifiers.py`

**Use Case**: Classify PDF rows (transaction, header, metadata, etc.).

**Example**:
```python
from src.extraction.row_classifiers import create_row_classifier_chain

# Create the chain
classifier_chain = create_row_classifier_chain()

# Classify a row
row_type = classifier_chain.classify(row_data)
# Returns: "transaction", "header", "metadata", etc.
```

**Adding New Classifier**:
```python
class CustomRowClassifier(RowClassifier):
    def classify(self, row: dict) -> Optional[str]:
        # Check if this classifier can handle the row
        if self._is_custom_type(row):
            return "custom_type"

        # Pass to next in chain
        if self.next_classifier:
            return self.next_classifier.classify(row)

        return None

    def _is_custom_type(self, row: dict) -> bool:
        # Your custom logic
        return "CUSTOM" in row.get("text", "")

# Add to chain
def create_row_classifier_chain():
    custom = CustomRowClassifier()
    header = HeaderMetadataClassifier()
    admin = AdministrativeClassifier()

    # Build chain
    custom.next_classifier = header
    header.next_classifier = admin
    # ... continue chain

    return custom  # Return head of chain
```

### Best Practices
- Each handler should have single responsibility
- Handlers should be independent and stateless
- Order matters - put most specific handlers first
- Always have fallback handler at end of chain

---

## Builder Pattern

### What It Is
Constructs complex objects step by step with fluent interface.

### When to Use
- Object has many parameters (>5)
- Many parameters are optional
- You want readable, self-documenting construction
- Construction requires validation

### Implementation in Codebase

**Location**: `src/builders/processor_builder.py`

**Use Case**: Build BankStatementProcessor instances.

**Example**:
```python
from src.builders import BankStatementProcessorBuilder

processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/input"))
    .with_output_dir(Path("/output"))
    .with_table_bounds(200, 600)
    .with_date_sorting(True)
    .with_monthly_summary(True)
    .with_totals(["debit", "credit"])
    .build()
)
```

**Minimal Configuration**:
```python
# Only required parameters
processor = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/input"))
    .with_output_dir(Path("/output"))
    .build()  # Uses sensible defaults
)
```

**Reusing Builders**:
```python
# Create base configuration
base_builder = (
    BankStatementProcessorBuilder()
    .with_input_dir(Path("/input"))
    .with_date_sorting(True)
    .with_monthly_summary(True)
)

# Create variations
processor1 = base_builder.with_output_dir(Path("/output1")).build()
processor2 = base_builder.with_output_dir(Path("/output2")).build()
```

### Best Practices
- Return `self` from builder methods for chaining
- Validate required parameters in `build()`
- Provide sensible defaults for optional parameters
- Make builder methods named clearly (with_*, set_*, add_*)
- Consider immutability (create new builder for each change)

---

## Facade Pattern

### What It Is
Provides a simplified interface to a complex subsystem.

### When to Use
- Subsystem is complex with many dependencies
- You want to hide complexity from clients
- You want to decouple clients from subsystem details

### Implementation in Codebase

**Location**: `src/facades/processing_facade.py`

**Use Case**: Simplify bank statement processing interface.

**Example**:
```python
from src.facades import BankStatementProcessingFacade

# Simple usage
facade = BankStatementProcessingFacade.from_environment()
exit_code = facade.process_with_error_handling()

# The facade handles:
# - Loading configuration
# - Creating output directories
# - Creating processor
# - Running processing
# - Error handling with proper exit codes
```

**Before (without facade)**:
```python
# Complex, error-prone
setup_logging()
config = get_config_singleton()
config.output_dir.mkdir(parents=True, exist_ok=True)
config.log_configuration()
columns = get_columns_config()
processor = ProcessorFactory.create_from_config(config)
try:
    summary = processor.run()
    log_summary(summary)
except ConfigurationError as e:
    logger.error("Config error: %s", e)
    return 1
# ... more error handling ...
```

**After (with facade)**:
```python
# Simple, clean
facade = BankStatementProcessingFacade.from_environment()
return facade.process_with_error_handling()
```

### Best Practices
- Facade should provide coarse-grained operations
- Don't expose subsystem details through facade
- Facade can use other patterns internally
- Keep facade interface simple and intuitive
- One facade can delegate to other facades

---

## Template Method Pattern

### What It Is
Defines skeleton of algorithm in base class, letting subclasses override specific steps.

### When to Use
- Multiple classes have similar algorithms with variations
- You want to avoid code duplication in similar algorithms
- You want to enforce a specific algorithm structure

### Implementation in Codebase

**Location**: `src/patterns/strategies.py` (OutputFormatStrategy)

**Use Case**: Define common structure for writing output files.

**Template Method Structure**:
```python
class OutputFormatStrategy(ABC):
    def write(self, transactions, file_path, column_names, **kwargs):
        """Template method - defines the algorithm."""
        # Step 1: Extract common parameters
        include_totals = kwargs.get("include_totals", False)
        totals_columns = kwargs.get("totals_columns", [])

        # Step 2: Prepare data (abstract - subclass implements)
        data = self._prepare_data(transactions, column_names)

        # Step 3: Write data (abstract - subclass implements)
        self._write_data(data, file_path, column_names, **kwargs)

        # Step 4: Write totals (hook - optional override)
        if include_totals and totals_columns and self._supports_totals():
            self._write_totals(data, file_path, column_names, totals_columns)

    @abstractmethod
    def _prepare_data(self, transactions, column_names):
        """Step to override."""
        pass

    @abstractmethod
    def _write_data(self, data, file_path, column_names, **kwargs):
        """Step to override."""
        pass

    def _supports_totals(self) -> bool:
        """Hook method - optional override."""
        return False

    def _write_totals(self, data, file_path, column_names, totals_columns):
        """Hook method - optional override."""
        pass
```

**Implementing Subclass**:
```python
class CSVOutputStrategy(OutputFormatStrategy):
    def _prepare_data(self, transactions, column_names):
        """Override: prepare as DataFrame."""
        return pd.DataFrame(transactions, columns=column_names)

    def _write_data(self, data, file_path, column_names, **kwargs):
        """Override: write to CSV."""
        data.to_csv(file_path, index=False)

    def _supports_totals(self) -> bool:
        """Override hook: CSV supports totals."""
        return True

    def _write_totals(self, data, file_path, column_names, totals_columns):
        """Override hook: append totals to CSV."""
        # Implementation...
```

### Template Method vs Strategy

**Use Template Method when:**
- Algorithms have same structure but different steps
- You want to enforce algorithm structure
- Variations are steps within one algorithm

**Use Strategy when:**
- Entire algorithms are different
- Algorithms are independent and interchangeable
- No common structure to enforce

### Best Practices
- Template method should be in base class (don't override)
- Abstract methods must be implemented by subclasses
- Hook methods have default implementation (can override)
- Document which methods are abstract vs hooks
- Keep template method simple and readable

---

## Choosing the Right Pattern

### Decision Tree

```
Need to switch algorithms at runtime?
├─ Yes → Strategy Pattern
└─ No → Continue

Need to hide complexity of subsystem?
├─ Yes → Facade Pattern
└─ No → Continue

Need to construct complex object?
├─ Many parameters? → Builder Pattern
├─ Complex creation logic? → Factory Pattern
└─ No → Continue

Need to process requests in sequence?
├─ Yes → Chain of Responsibility
└─ No → Continue

Have algorithms with similar structure?
├─ Yes → Template Method Pattern
└─ No → Continue

Need to abstract data access?
├─ Yes → Repository Pattern
└─ No → Continue

Need exactly one instance?
└─ Singleton Pattern (use sparingly!)
```

### Common Combinations

**Factory + Builder**
- Factory creates builder, builder constructs object
- Example: `ProcessorFactory` uses `BankStatementProcessorBuilder`

**Facade + Strategy**
- Facade provides simple interface, uses strategies internally
- Example: `ProcessingFacade` uses output strategies

**Template Method + Strategy**
- Template method defines structure, strategies provide algorithms
- Example: `OutputFormatStrategy` (template) with different format strategies

**Repository + Factory**
- Factory creates repository, repository handles data access
- Example: Factory creates `FileSystemTransactionRepository`

## Conclusion

Design patterns provide proven solutions to common problems. Key principles:

1. **Don't Force It**: Use patterns when they solve a real problem
2. **Keep It Simple**: Don't over-engineer
3. **Be Consistent**: Use same patterns for similar problems
4. **Test Thoroughly**: Each pattern implementation should be well-tested
5. **Document Usage**: Explain why pattern was chosen

Remember: Patterns are tools, not rules. Use them to improve code quality, not for their own sake.
