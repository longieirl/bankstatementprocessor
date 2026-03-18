"""Tests for file I/O protocols."""

import json
import tempfile
from pathlib import Path

import pytest

from bankstatements_core.domain.protocols.file_io import IFileDeleter, IFileReader, IJsonWriter
from bankstatements_core.patterns.repositories import FileSystemTransactionRepository


class TestIJsonWriterProtocol:
    """Tests for IJsonWriter protocol implementation."""

    def test_repository_implements_ijsonwriter(self):
        """Test that FileSystemTransactionRepository implements IJsonWriter protocol."""
        repo = FileSystemTransactionRepository()

        # Should have write_json method
        assert hasattr(repo, "write_json")
        assert callable(repo.write_json)

    def test_write_json_creates_file(self):
        """Test that write_json creates a JSON file."""
        repo = FileSystemTransactionRepository()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            test_data = {"key": "value", "number": 42}

            repo.write_json(test_file, test_data)

            assert test_file.exists()
            with open(test_file, "r") as f:
                loaded = json.load(f)
                assert loaded == test_data

    def test_write_json_overwrites_existing(self):
        """Test that write_json overwrites existing files."""
        repo = FileSystemTransactionRepository()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"

            # Write first time
            repo.write_json(test_file, {"version": 1})

            # Write second time
            repo.write_json(test_file, {"version": 2})

            # Should have second version
            with open(test_file, "r") as f:
                loaded = json.load(f)
                assert loaded["version"] == 2


class TestIFileDeleterProtocol:
    """Tests for IFileDeleter protocol implementation."""

    def test_repository_implements_ifiledeleter(self):
        """Test that FileSystemTransactionRepository implements IFileDeleter protocol."""
        repo = FileSystemTransactionRepository()

        # Should have delete_file method
        assert hasattr(repo, "delete_file")
        assert callable(repo.delete_file)

    def test_delete_file_removes_file(self):
        """Test that delete_file removes a file."""
        repo = FileSystemTransactionRepository()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = Path(f.name)

        try:
            assert test_file.exists()

            repo.delete_file(test_file)

            assert not test_file.exists()
        finally:
            # Cleanup if test fails
            if test_file.exists():
                test_file.unlink()

    def test_delete_file_raises_on_nonexistent(self):
        """Test that delete_file raises FileNotFoundError for nonexistent files."""
        repo = FileSystemTransactionRepository()

        nonexistent = Path("/tmp/definitely_does_not_exist_12345.txt")

        with pytest.raises(FileNotFoundError):
            repo.delete_file(nonexistent)


class TestIFileReaderProtocol:
    """Tests for IFileReader protocol implementation."""

    def test_repository_implements_ifilereader(self):
        """Test that FileSystemTransactionRepository implements IFileReader protocol."""
        repo = FileSystemTransactionRepository()

        # Should have read_text method
        assert hasattr(repo, "read_text")
        assert callable(repo.read_text)

    def test_read_text_returns_content(self):
        """Test that read_text returns file contents."""
        repo = FileSystemTransactionRepository()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            test_content = "Hello, World!\nLine 2\n"
            f.write(test_content)

        try:
            content = repo.read_text(test_file)
            assert content == test_content
        finally:
            test_file.unlink()

    def test_read_text_raises_on_nonexistent(self):
        """Test that read_text raises FileNotFoundError for nonexistent files."""
        repo = FileSystemTransactionRepository()

        nonexistent = Path("/tmp/definitely_does_not_exist_12345.txt")

        with pytest.raises(FileNotFoundError):
            repo.read_text(nonexistent)


class TestProtocolUsage:
    """Tests demonstrating protocol usage patterns."""

    def test_function_accepting_ijsonwriter(self):
        """Test that functions can accept IJsonWriter protocol."""

        def save_config(writer: IJsonWriter, path: Path, config: dict):
            """Example function that accepts IJsonWriter."""
            writer.write_json(path, config)

        repo = FileSystemTransactionRepository()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_data = {"setting": "value"}

            save_config(repo, config_file, config_data)

            assert config_file.exists()

    def test_function_accepting_ifiledeleter(self):
        """Test that functions can accept IFileDeleter protocol."""

        def cleanup_temp(deleter: IFileDeleter, temp_file: Path):
            """Example function that accepts IFileDeleter."""
            if temp_file.exists():
                deleter.delete_file(temp_file)

        repo = FileSystemTransactionRepository()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = Path(f.name)

        cleanup_temp(repo, temp_file)

        assert not temp_file.exists()

    def test_function_accepting_ifilereader(self):
        """Test that functions can accept IFileReader protocol."""

        def load_config(reader: IFileReader, path: Path) -> str:
            """Example function that accepts IFileReader."""
            return reader.read_text(path)

        repo = FileSystemTransactionRepository()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            f.write("test content")

        try:
            content = load_config(repo, test_file)
            assert content == "test content"
        finally:
            test_file.unlink()
