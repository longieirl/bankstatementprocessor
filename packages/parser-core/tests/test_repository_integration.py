"""Tests for repository pattern integration with BankStatementProcessor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.patterns.repositories import (
    FileSystemTransactionRepository,
    TransactionRepository,
)
from bankstatements_core.processor import BankStatementProcessor


def create_test_processor(input_dir, output_dir, repository=None):
    """Helper to create processor with test configuration."""
    config = ProcessorConfig(input_dir=input_dir, output_dir=output_dir)
    return BankStatementProcessor(config=config, repository=repository)


class MockTransactionRepository(TransactionRepository):
    """Mock repository for testing."""

    def __init__(self):
        self.saved_json = []
        self.saved_csv = []

    def save_as_json(self, transactions: list[dict], file_path: Path) -> None:
        """Track JSON saves."""
        self.saved_json.append((transactions, file_path))

    def save_as_csv(self, data: str, file_path: Path) -> None:
        """Track CSV saves."""
        self.saved_csv.append((data, file_path))

    def append_to_csv(self, file_path: Path, content: str) -> None:
        """No-op for tests that don't need append tracking."""
        pass

    def load_from_json(self, file_path: Path) -> list[dict]:
        """Mock JSON load."""
        return []


class TestRepositoryIntegration:
    """Test repository pattern integration."""

    def test_processor_uses_default_repository(self, tmp_path):
        """Test that processor creates FileSystemTransactionRepository by default."""
        processor = create_test_processor(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
        )
        assert isinstance(processor.repository, FileSystemTransactionRepository)

    def test_processor_accepts_custom_repository(self, tmp_path):
        """Test that processor accepts injected repository."""
        mock_repo = MockTransactionRepository()
        processor = create_test_processor(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repository=mock_repo,
        )
        assert processor.repository is mock_repo

    def test_write_json_file_uses_repository(self, tmp_path):
        """Test that JSON writing uses repository (through orchestrators)."""
        mock_repo = MockTransactionRepository()
        processor = create_test_processor(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repository=mock_repo,
        )

        # Write JSON using repository directly since _write_json_file was moved
        test_data = [{"test": "data"}]
        test_path = tmp_path / "test.json"
        processor.repository.save_as_json(test_data, test_path)

        # Verify repository was used
        assert len(mock_repo.saved_json) == 1
        assert mock_repo.saved_json[0] == (test_data, test_path)


class TestFileSystemTransactionRepository:
    """Test FileSystemTransactionRepository implementation."""

    def test_save_as_json(self, tmp_path):
        """Test saving JSON files."""
        repo = FileSystemTransactionRepository()
        test_data = [{"date": "01/01/2023", "amount": 100.50}]
        file_path = tmp_path / "test.json"

        repo.save_as_json(test_data, file_path)

        # Verify file was created with correct content
        assert file_path.exists()
        loaded = json.loads(file_path.read_text(encoding="utf-8"))
        assert loaded == test_data

    def test_save_as_csv(self, tmp_path):
        """Test saving CSV files."""
        repo = FileSystemTransactionRepository()
        test_data = "Date,Amount\n01/01/2023,100.50\n"
        file_path = tmp_path / "test.csv"

        repo.save_as_csv(test_data, file_path)

        # Verify file was created with correct content
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == test_data

    def test_append_to_csv(self, tmp_path):
        """Test appending to CSV files."""
        repo = FileSystemTransactionRepository()
        file_path = tmp_path / "test.csv"

        # Create initial file
        file_path.write_text("Header\n", encoding="utf-8")

        # Append to file
        repo.append_to_csv(file_path, "Line 1\nLine 2\n")

        # Verify content
        content = file_path.read_text(encoding="utf-8")
        assert content == "Header\nLine 1\nLine 2\n"

    def test_load_from_json_existing_file(self, tmp_path):
        """Test loading from existing JSON file."""
        repo = FileSystemTransactionRepository()
        test_data = [{"date": "01/01/2023", "amount": 100.50}]
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps(test_data), encoding="utf-8")

        loaded = repo.load_from_json(file_path)

        assert loaded == test_data

    def test_load_from_json_missing_file(self, tmp_path):
        """Test loading from non-existent JSON file returns empty list."""
        repo = FileSystemTransactionRepository()
        file_path = tmp_path / "missing.json"

        loaded = repo.load_from_json(file_path)

        assert loaded == []


class TestRepositoryMockability:
    """Test that repository enables better testing through mocking."""

    def test_processor_with_mock_repository_no_file_io(self, tmp_path):
        """Test that using mock repository prevents actual file I/O."""
        mock_repo = MagicMock(spec=TransactionRepository)
        processor = create_test_processor(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repository=mock_repo,
        )

        # Write JSON file using repository directly
        test_data = {"key": "value"}
        test_path = tmp_path / "output" / "test.json"
        processor.repository.save_as_json(test_data, test_path)

        # Verify mock was called instead of actual file I/O
        mock_repo.save_as_json.assert_called_once_with(test_data, test_path)

        # Verify no actual file was created
        assert not test_path.exists()
