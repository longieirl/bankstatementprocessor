"""Configuration management for bank statement processor."""

from __future__ import annotations

from bankstatements_core.config.environment_parser import EnvironmentParser
from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    OutputConfig,
    ProcessingConfig,
    ProcessorConfig,
)

__all__ = [
    "EnvironmentParser",
    "ExtractionConfig",
    "OutputConfig",
    "ProcessingConfig",
    "ProcessorConfig",
]
