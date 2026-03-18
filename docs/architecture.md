# Architecture Documentation

## Overview

This document describes the architecture of the Bank Statement Processor application after comprehensive refactoring to implement SOLID principles and design patterns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Application                          │
│  (app.py - Entry point with Facade pattern)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Processing Facade                         │
│  Simplified high-level interface for bank statement         │
│  processing with built-in error handling                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Processor Factory                         │
│  Creates configured BankStatementProcessor instances        │
│  using Builder pattern                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              BankStatementProcessor (Core)                   │
│  Orchestrates PDF extraction, duplicate detection,          │
│  sorting, and output generation                             │
└─────┬───────────────────────────────────────────────┬───────┘
      │                                               │
      ▼                                               ▼
┌─────────────────┐                         ┌──────────────────┐
│   Extraction    │                         │    Services      │
│   Components    │                         │   (Business      │
│                 │                         │    Logic)        │
└─────────────────┘                         └──────────────────┘
```

## Module Structure

### Core Modules

#### `src/app.py`
- Application entry point
- Configuration management via AppConfig
- Main() function using Facade pattern (11 lines)

#### `src/processor.py`
- BankStatementProcessor - main orchestration class
- Coordinates extraction, deduplication, sorting, and output
- Uses injected services and strategies
- ~205 lines (reduced from 720)

### Pattern Implementations

#### `src/patterns/`
Design pattern implementations for flexible architecture.

**strategies.py**
- Strategy Pattern implementations:
  - `DuplicateDetectionStrategy` (AllFields, DateAmount)
  - `OutputFormatStrategy` (CSV, JSON, Excel) with Template Method
  - `SortingStrategy` (Chronological, NoSorting)

**factories.py**
- Factory Pattern: `ProcessorFactory`
- Creates configured processor instances from AppConfig

**repositories.py**
- Repository Pattern: `TransactionRepository`
- Abstracts file I/O operations
- `FileSystemTransactionRepository` implementation
- Configuration Singleton: `get_config_singleton()`

### Service Layer

#### `src/services/`
Business logic services following Single Responsibility Principle.

**duplicate_detector.py**
- `DuplicateDetectionService`
- Handles duplicate transaction detection
- Uses injected strategy pattern

**sorting_service.py**
- `TransactionSortingService`
- Handles transaction sorting
- Uses Strategy pattern (Chronological vs NoSorting)

**monthly_summary.py**
- `MonthlySummaryService`
- Generates monthly transaction summaries
- Groups by month, calculates totals and counts

**totals_calculator.py**
- `ColumnTotalsService`
- Calculates column totals with pattern matching
- Formats totals rows for output

### Extraction Components

#### `src/extraction/`
PDF extraction and data processing components.

**column_identifier.py**
- `ColumnTypeIdentifier`
- Identifies column types (date, debit, credit, etc.)
- Pattern-based matching

**row_classifiers.py**
- Chain of Responsibility pattern for row classification
- Multiple classifier classes:
  - HeaderMetadataClassifier
  - AdministrativeClassifier
  - ReferenceCodeClassifier
  - FXContinuationClassifier
  - TransactionClassifier
  - etc.

**boundary_detector.py**
- `TableBoundaryDetector`
- Template Method pattern for boundary detection
- Multiple detection phases with fallbacks

**pdf_extractor.py**
- `PDFTableExtractor`
- Main PDF extraction orchestration
- Page-by-page processing

### Builder Pattern

#### `src/builders/`

**processor_builder.py**
- `BankStatementProcessorBuilder`
- Fluent interface for processor construction
- Validates required parameters
- Simplifies complex object creation

### Facade Pattern

#### `src/facades/`

**processing_facade.py**
- `BankStatementProcessingFacade`
- Simplified high-level interface
- Hides complexity of configuration, setup, and error handling
- Two main methods:
  - `from_environment()` - create from environment variables
  - `process_with_error_handling()` - process with comprehensive error handling

### Configuration

#### `src/config/`

**environment_parser.py**
- `EnvironmentParser`
- Centralized environment variable parsing
- Type-safe parsing (float, int, bool, JSON, CSV)
- Eliminates duplication across modules

### Utilities

#### `src/utils.py`
- Helper functions for data conversion
- Column sum calculation
- Date column identification
- Float conversion utilities

## Design Patterns Applied

### 1. Strategy Pattern
**Purpose**: Define a family of algorithms, encapsulate each one, make them interchangeable.

**Implementations**:
- Duplicate Detection (AllFields, DateAmount)
- Output Formats (CSV, JSON, Excel)
- Sorting (Chronological, NoSorting)

**Benefits**:
- Easy to add new strategies without modifying existing code
- Strategies can be swapped at runtime
- Each strategy is independently testable

### 2. Repository Pattern
**Purpose**: Mediate between domain and data mapping layers.

**Implementation**: `TransactionRepository`

**Benefits**:
- Abstracts file I/O operations
- Easy to swap implementations (FileSystem, S3, Database)
- Simplifies testing with mock repositories

### 3. Singleton Pattern
**Purpose**: Ensure a class has only one instance, provide global access.

**Implementation**: Configuration singleton (`get_config_singleton()`)

**Benefits**:
- Configuration loaded once
- Consistent configuration across application
- Reduced overhead

### 4. Factory Pattern
**Purpose**: Create objects without specifying exact class.

**Implementation**: `ProcessorFactory`

**Benefits**:
- Encapsulates complex creation logic
- Creates properly configured instances
- Centralizes processor construction

### 5. Chain of Responsibility
**Purpose**: Pass request along chain of handlers.

**Implementation**: Row classification chain

**Benefits**:
- Easy to add new classifiers
- Classifiers can be reordered
- Each classifier is independent and testable

### 6. Builder Pattern
**Purpose**: Construct complex objects step by step.

**Implementation**: `BankStatementProcessorBuilder`

**Benefits**:
- Fluent, readable interface
- Validates required parameters
- Scales well as parameters increase

### 7. Facade Pattern
**Purpose**: Provide simplified interface to complex subsystem.

**Implementation**: `BankStatementProcessingFacade`

**Benefits**:
- Hides complexity from clients
- Simple, high-level interface
- Easier to use, less error-prone

### 8. Template Method Pattern
**Purpose**: Define skeleton of algorithm, let subclasses override steps.

**Implementation**: `OutputFormatStrategy.write()`

**Benefits**:
- Reduces code duplication
- Consistent structure across strategies
- Easy to add new output formats

## SOLID Principles

### Single Responsibility Principle (SRP)
Each class has one clear responsibility:
- `DuplicateDetectionService` - only handles duplicate detection
- `TransactionSortingService` - only handles sorting
- `MonthlySummaryService` - only generates monthly summaries
- `ColumnTotalsService` - only calculates totals

### Open/Closed Principle (OCP)
Open for extension, closed for modification:
- Add new output formats by extending `OutputFormatStrategy`
- Add new duplicate strategies by extending `DuplicateDetectionStrategy`
- Add new classifiers to Chain of Responsibility without modifying existing ones

### Liskov Substitution Principle (LSP)
Derived classes are substitutable for base classes:
- All `OutputFormatStrategy` implementations can be used interchangeably
- All `DuplicateDetectionStrategy` implementations are interchangeable
- All `SortingStrategy` implementations are interchangeable

### Interface Segregation Principle (ISP)
Clients shouldn't depend on interfaces they don't use:
- Small, focused interfaces (Strategy base classes)
- Optional functionality via hook methods (e.g., `_supports_totals()`)

### Dependency Inversion Principle (DIP)
Depend on abstractions, not concretions:
- Processor depends on `TransactionRepository` interface, not concrete implementation
- Services use injected strategies, not hardcoded implementations
- Factory creates dependencies and injects them

## Data Flow

```
1. PDF Files (Input)
        ↓
2. PDFTableExtractor
   - Extract text and positions
   - Classify rows (Chain of Responsibility)
   - Detect table boundaries
        ↓
3. Raw Transaction Data
        ↓
4. BankStatementProcessor
   - DuplicateDetectionService (detect duplicates)
   - TransactionSortingService (sort chronologically)
   - MonthlySummaryService (generate summary)
        ↓
5. Processed Data
        ↓
6. Output Strategies (Template Method)
   - CSV (with optional totals)
   - JSON
   - Excel (with optional totals)
        ↓
7. Output Files
```

## Testing Architecture

### Test Coverage: 95.50%
- 462 tests passing
- 1 test skipped

### Test Organization

```
tests/
├── test_app.py                  # Application entry point tests
├── test_processor.py            # Core processor tests
├── builders/                    # Builder pattern tests
│   └── test_processor_builder.py
├── config/                      # Configuration tests
│   └── test_environment_parser.py
├── extraction/                  # Extraction component tests
│   ├── test_boundary_detector.py
│   ├── test_column_identifier.py
│   ├── test_pdf_extractor.py
│   └── test_row_classifiers.py
├── facades/                     # Facade pattern tests
│   └── test_processing_facade.py
└── services/                    # Service layer tests
    ├── test_duplicate_detector.py
    ├── test_monthly_summary.py
    ├── test_sorting_service.py
    └── test_totals_calculator.py
```

### Testing Approach
- Unit tests for each service and component
- Integration tests for processor with real data
- Mock strategies for testing processor in isolation
- Test all design pattern implementations

## Performance Considerations

### Optimizations
- Pandas vectorization for column calculations
- Efficient duplicate detection using dict lookups
- Stream processing for large PDFs
- Lazy loading of PDF pages

### Scalability
- Repository pattern allows easy swap to cloud storage (S3)
- Services are stateless and could be parallelized
- Strategy pattern allows performance tuning per algorithm

## Error Handling

### Structured Error Handling
- Specific exception types (ConfigurationError)
- Clear error messages with context
- Proper exit codes:
  - 0: Success
  - 1: Configuration error
  - 2: File not found
  - 3: Permission error
  - 4: Unexpected error
  - 130: User interrupt (Ctrl+C)

### Logging
- Structured logging throughout application
- Info level for normal operations
- Warning level for recoverable issues
- Error level for failures
- Debug level for detailed diagnostics

## Future Extensibility

### Easy to Add
1. **New Output Format**: Extend `OutputFormatStrategy`, implement abstract methods
2. **New Duplicate Strategy**: Extend `DuplicateDetectionStrategy`, implement `create_key()`
3. **New Row Classifier**: Create classifier class, add to chain
4. **New Repository**: Implement `TransactionRepository` interface (e.g., S3Repository)
5. **New Service**: Create service class, inject into processor

### Architectural Benefits
- Low coupling between components
- High cohesion within components
- Easy to test in isolation
- Clear separation of concerns
- Extensible without modification (OCP)

## Maintenance Guidelines

### Adding New Features
1. Identify which layer the feature belongs to (Service, Strategy, etc.)
2. Create focused class with single responsibility
3. Write tests first (TDD)
4. Inject dependencies via constructor
5. Use appropriate design pattern

### Modifying Existing Features
1. Check if behavior can be extended via new strategy
2. If modifying core logic, ensure backward compatibility
3. Update tests to cover changes
4. Maintain 90%+ test coverage
5. Update documentation

### Code Review Checklist
- [ ] Single Responsibility Principle followed?
- [ ] Dependencies injected, not hardcoded?
- [ ] Tests written with good coverage?
- [ ] Documentation updated?
- [ ] Backward compatible?
- [ ] Uses appropriate design pattern?
- [ ] Error handling comprehensive?

## Conclusion

This architecture provides:
- **Maintainability**: Clear structure, focused components
- **Testability**: High test coverage, easy to mock
- **Extensibility**: Easy to add new features via patterns
- **Readability**: Self-documenting code with clear intent
- **Reliability**: Comprehensive error handling and testing

The refactoring reduced complexity while improving flexibility and maintainability, setting a solid foundation for future development.
