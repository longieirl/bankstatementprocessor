"""
Design pattern implementations for the bank statement processing system.

This package contains implementations of common design patterns to improve
code maintainability, testability, and flexibility.

These patterns are available for use but not yet fully integrated into the main application flow.
See docs/DESIGN_PATTERNS.md for usage examples.
"""

from __future__ import annotations

from .factories import ProcessorFactory  # pragma: no cover
from .repositories import (  # pragma: no cover
    ConfigRepository,
    EnvironmentConfigRepository,
    FileSystemTransactionRepository,
    TransactionRepository,
)
from .strategies import (  # pragma: no cover
    AllFieldsDuplicateStrategy,
    CSVOutputStrategy,
    DateAmountDuplicateStrategy,
    DuplicateDetectionStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
    OutputFormatStrategy,
)

__all__ = [  # pragma: no cover
    # Repositories
    "ConfigRepository",
    "EnvironmentConfigRepository",
    "TransactionRepository",
    "FileSystemTransactionRepository",
    # Strategies
    "DuplicateDetectionStrategy",
    "AllFieldsDuplicateStrategy",
    "DateAmountDuplicateStrategy",
    "OutputFormatStrategy",
    "CSVOutputStrategy",
    "JSONOutputStrategy",
    "ExcelOutputStrategy",
    # Factories
    "ProcessorFactory",
]
