"""
Repository Pattern implementations for data access abstraction.

This module provides abstract interfaces and concrete implementations for
accessing data (files, configuration, etc.) without exposing the underlying
storage mechanism.
"""  # pragma: no cover

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from bankstatements_core.config.app_config import AppConfig


class TransactionRepository(ABC):
    """Abstract repository for transaction data persistence."""

    @abstractmethod
    def save_as_json(self, transactions: list[dict], file_path: Path) -> None:
        """
        Save transactions to a JSON file.

        Args:
            transactions: List of transaction dictionaries
            file_path: Path to save the JSON file
        """
        pass

    @abstractmethod
    def save_as_csv(self, data: str, file_path: Path) -> None:
        """
        Save data to a CSV file.

        Args:
            data: CSV formatted string
            file_path: Path to save the CSV file
        """
        pass

    @abstractmethod
    def append_to_csv(self, file_path: Path, content: str) -> None:
        """
        Append content to an existing CSV file.

        Args:
            file_path: Path to the CSV file
            content: Content to append
        """
        pass

    @abstractmethod
    def load_from_json(self, file_path: Path) -> list[dict]:
        """
        Load transactions from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            List of transaction dictionaries
        """
        pass


class FileSystemTransactionRepository(TransactionRepository):
    """
    Concrete repository implementation for file system storage.

    This implementation stores transactions as JSON and CSV files on the local
    file system.
    """

    def save_as_json(self, transactions: list[dict], file_path: Path) -> None:
        """Save transactions to a JSON file with formatted output."""
        file_path.write_text(json.dumps(transactions, indent=2), encoding="utf-8")

    def save_as_csv(self, data: str, file_path: Path) -> None:
        """Save CSV data to a file."""
        file_path.write_text(data, encoding="utf-8")

    def append_to_csv(self, file_path: Path, content: str) -> None:
        """Append content to an existing CSV file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)

    def load_from_json(self, file_path: Path) -> list[dict]:
        """Load transactions from a JSON file."""
        if not file_path.exists():
            return []
        content = file_path.read_text(encoding="utf-8")
        data: list[dict] = json.loads(content)
        return data

    def save_json_file(self, file_path: Path, data: Any) -> None:
        """
        Save data to a JSON file.

        Args:
            file_path: Path where JSON file should be saved
            data: Data to serialize to JSON (dict, list, or any JSON-serializable type)
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def write_json(self, file_path: Path, data: Any) -> None:
        """
        Write data as JSON to file (implements IJsonWriter protocol).

        Args:
            file_path: Path to write JSON file
            data: Data to serialize to JSON

        Raises:
            IOError: If file write fails
        """
        self.save_json_file(file_path, data)

    def delete_file(self, file_path: Path) -> None:
        """
        Delete a file (implements IFileDeleter protocol).

        Args:
            file_path: Path to file to delete

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If deletion fails
        """
        file_path.unlink()

    def read_text(self, file_path: Path) -> str:
        """
        Read file contents as text (implements IFileReader protocol).

        Args:
            file_path: Path to file to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
        """
        return file_path.read_text(encoding="utf-8")


class ConfigRepository(ABC):
    """Abstract repository for application configuration."""

    @abstractmethod
    def get_config(self) -> AppConfig:
        """
        Load application configuration.

        Returns:
            AppConfig instance with loaded configuration
        """
        pass


class EnvironmentConfigRepository(ConfigRepository):
    """
    Concrete repository implementation for environment-based configuration.

    This implementation loads configuration from environment variables.
    """

    def get_config(self) -> AppConfig:
        """Load configuration from environment variables."""
        return AppConfig.from_env()


# Singleton-like module-level instance for configuration
_config_instance: AppConfig | None = None


def get_config_singleton() -> AppConfig:
    """
    Get the singleton configuration instance.

    This provides a simple singleton pattern using module-level variables,
    which is more Pythonic than a traditional Singleton class.

    Returns:
        Shared AppConfig instance
    """
    global _config_instance
    if _config_instance is None:
        repository = EnvironmentConfigRepository()
        _config_instance = repository.get_config()
    return _config_instance


def reset_config_singleton() -> None:
    """
    Reset the configuration singleton.

    This is primarily useful for testing, allowing tests to reload
    configuration with different environment variables.
    """
    global _config_instance
    _config_instance = None
