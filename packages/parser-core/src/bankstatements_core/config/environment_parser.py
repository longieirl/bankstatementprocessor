"""Centralized environment variable parsing to eliminate duplication."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EnvironmentParser:
    """
    Centralized service for parsing environment variables.

    Provides type-safe parsing methods for common environment variable types:
    - Floats (numeric values)
    - Integers (whole numbers)
    - Booleans (true/false flags)
    - JSON lists (complex structured data)
    - CSV lists (comma-separated values)

    This class eliminates duplicate parsing logic across the codebase and
    provides consistent error handling and logging.
    """

    @staticmethod
    def parse_float(var_name: str, default: float) -> float:
        """
        Parse a float environment variable with error handling.

        Args:
            var_name: Name of the environment variable
            default: Default value if variable is not set or invalid

        Returns:
            Parsed float value or default if parsing fails

        Examples:
            >>> os.environ['THRESHOLD'] = '0.75'
            >>> EnvironmentParser.parse_float('THRESHOLD', 0.5)
            0.75
            >>> EnvironmentParser.parse_float('MISSING', 0.5)
            0.5
        """
        value_str = os.getenv(var_name)
        if value_str is None:
            return default

        try:
            return float(value_str)
        except ValueError:
            logger.warning(
                "%s must be a float, got '%s'. Using default: %s",
                var_name,
                value_str,
                default,
            )
            return default

    @staticmethod
    def parse_int(var_name: str, default: int) -> int:
        """
        Parse an integer environment variable with error handling.

        Args:
            var_name: Name of the environment variable
            default: Default value if variable is not set

        Returns:
            Parsed integer value

        Raises:
            ValueError: If the variable value cannot be parsed as integer

        Examples:
            >>> os.environ['TABLE_TOP'] = '300'
            >>> EnvironmentParser.parse_int('TABLE_TOP', 0)
            300
        """
        value_str = os.getenv(var_name, str(default))
        try:
            return int(value_str)
        except ValueError:
            raise ValueError(
                f"{var_name} must be an integer, got: {value_str}"
            ) from None

    @staticmethod
    def parse_bool(var_name: str, default: bool = False) -> bool:
        """
        Parse a boolean environment variable.

        Args:
            var_name: Name of the environment variable
            default: Default value if variable is not set

        Returns:
            Boolean value (True if value.lower() == "true", False otherwise)

        Examples:
            >>> os.environ['ENABLE_FEATURE'] = 'true'
            >>> EnvironmentParser.parse_bool('ENABLE_FEATURE', False)
            True
            >>> os.environ['ENABLE_FEATURE'] = 'True'
            >>> EnvironmentParser.parse_bool('ENABLE_FEATURE', False)
            True
            >>> os.environ['ENABLE_FEATURE'] = 'false'
            >>> EnvironmentParser.parse_bool('ENABLE_FEATURE', True)
            False
        """
        return os.getenv(var_name, str(default)).lower() == "true"

    @staticmethod
    def parse_json_list(var_name: str, default: list[Any]) -> list[Any]:
        """
        Parse a JSON list from environment variable.

        Args:
            var_name: Name of the environment variable
            default: Default list if variable is not set or invalid JSON

        Returns:
            Parsed list or default if parsing fails

        Examples:
            >>> os.environ['PATTERNS'] = '["pattern1", "pattern2"]'
            >>> EnvironmentParser.parse_json_list('PATTERNS', [])
            ['pattern1', 'pattern2']
            >>> EnvironmentParser.parse_json_list('MISSING', ['default'])
            ['default']
        """
        value_str = os.getenv(var_name)
        if value_str is None:
            return default

        try:
            parsed = json.loads(value_str)
            if isinstance(parsed, list):
                return parsed
            else:
                logger.warning(
                    "%s is not a JSON list, got %s. Using default: %s",
                    var_name,
                    type(parsed).__name__,
                    default,
                )
                return default
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "Failed to parse %s as JSON: %s. Using default: %s",
                var_name,
                e,
                default,
            )
            return default

    @staticmethod
    def parse_csv_list(var_name: str, default: list[str] | None = None) -> list[str]:
        """
        Parse a comma-separated list from environment variable.

        Args:
            var_name: Name of the environment variable
            default: Default list if variable is not set (None means empty list)

        Returns:
            List of trimmed non-empty strings

        Examples:
            >>> os.environ['COLUMNS'] = 'debit, credit, balance'
            >>> EnvironmentParser.parse_csv_list('COLUMNS', [])
            ['debit', 'credit', 'balance']
            >>> os.environ['COLUMNS'] = 'debit,  ,credit'
            >>> EnvironmentParser.parse_csv_list('COLUMNS', [])
            ['debit', 'credit']
            >>> EnvironmentParser.parse_csv_list('MISSING', ['default'])
            ['default']
        """
        if default is None:
            default = []

        value_str = os.getenv(var_name)
        if value_str is None or not value_str.strip():
            return default

        # Split by comma, strip whitespace, filter out empty strings
        return [item.strip() for item in value_str.split(",") if item.strip()]
