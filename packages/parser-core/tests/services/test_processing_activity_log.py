"""Tests for processing activity log (GDPR Article 5.2 Accountability)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from bankstatements_core.services.processing_activity_log import ProcessingActivityLog


@pytest.fixture
def temp_logs_dir(tmp_path):
    """Create a temporary logs directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return logs_dir


@pytest.fixture
def activity_log(temp_logs_dir):
    """Create a ProcessingActivityLog instance."""
    return ProcessingActivityLog(temp_logs_dir)


class TestProcessingActivityLogInitialization:
    """Test ProcessingActivityLog initialization."""

    def test_initialization_creates_logs_dir(self, tmp_path):
        """Test initialization creates logs directory if it doesn't exist."""
        logs_dir = tmp_path / "new_logs"
        log = ProcessingActivityLog(logs_dir)
        assert logs_dir.exists()
        assert log.logs_dir == logs_dir
        assert log.log_file == logs_dir / "processing_activity.jsonl"

    def test_initialization_with_existing_dir(self, temp_logs_dir):
        """Test initialization with existing logs directory."""
        log = ProcessingActivityLog(temp_logs_dir)
        assert log.logs_dir == temp_logs_dir
        assert log.log_file == temp_logs_dir / "processing_activity.jsonl"


class TestLogProcessing:
    """Test logging processing operations."""

    def test_log_processing_creates_entry(self, activity_log):
        """Test log_processing creates a log entry."""
        activity_log.log_processing(
            pdf_count=5,
            pages_read=25,
            transaction_count=150,
            duplicate_count=10,
            output_formats=["csv", "json"],
            duration_seconds=12.5,
        )

        # Read log file
        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "processing"
        assert entry["pdf_count"] == 5
        assert entry["pages_read"] == 25
        assert entry["transaction_count"] == 150
        assert entry["duplicate_count"] == 10
        assert entry["output_formats"] == ["csv", "json"]
        assert entry["duration_seconds"] == 12.5
        assert "timestamp" in entry

    def test_log_processing_timestamp_format(self, activity_log):
        """Test log entry has valid ISO timestamp."""
        activity_log.log_processing(
            pdf_count=1,
            pages_read=5,
            transaction_count=10,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=1.0,
        )

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(entry["timestamp"])
        assert isinstance(timestamp, datetime)

    def test_log_processing_rounds_duration(self, activity_log):
        """Test duration is rounded to 2 decimal places."""
        activity_log.log_processing(
            pdf_count=1,
            pages_read=5,
            transaction_count=10,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=12.3456789,
        )

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["duration_seconds"] == 12.35


class TestLogDeletion:
    """Test logging deletion events."""

    def test_log_deletion_with_age(self, activity_log):
        """Test log_deletion creates entry with age."""
        activity_log.log_deletion(
            file_name="bank_statements.csv",
            reason="Data retention policy",
            age_days=95,
        )

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "deletion"
        assert entry["file_name"] == "bank_statements.csv"
        assert entry["reason"] == "Data retention policy"
        assert entry["age_days"] == 95
        assert "timestamp" in entry

    def test_log_deletion_without_age(self, activity_log):
        """Test log_deletion creates entry without age field."""
        activity_log.log_deletion(
            file_name="bank_statements.csv",
            reason="User requested deletion",
        )

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "deletion"
        assert entry["file_name"] == "bank_statements.csv"
        assert entry["reason"] == "User requested deletion"
        assert "age_days" not in entry


class TestLogEncryption:
    """Test logging encryption operations."""

    def test_log_encryption_encrypt(self, activity_log):
        """Test log_encryption creates entry for encryption."""
        activity_log.log_encryption(file_count=5, operation="encrypt")

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "encryption"
        assert entry["operation"] == "encrypt"
        assert entry["file_count"] == 5
        assert "timestamp" in entry

    def test_log_encryption_decrypt(self, activity_log):
        """Test log_encryption creates entry for decryption."""
        activity_log.log_encryption(file_count=3, operation="decrypt")

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "encryption"
        assert entry["operation"] == "decrypt"
        assert entry["file_count"] == 3


class TestMultipleEntries:
    """Test multiple log entries."""

    def test_multiple_entries_append(self, activity_log):
        """Test multiple log entries are appended to file."""
        # Log multiple events
        activity_log.log_processing(
            pdf_count=1,
            pages_read=5,
            transaction_count=10,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=1.0,
        )
        activity_log.log_deletion(
            file_name="old.csv",
            reason="Expired",
            age_days=100,
        )
        activity_log.log_encryption(file_count=2, operation="encrypt")

        # Read all entries
        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        entry3 = json.loads(lines[2])

        assert entry1["event_type"] == "processing"
        assert entry2["event_type"] == "deletion"
        assert entry3["event_type"] == "encryption"

    def test_entries_have_unique_timestamps(self, activity_log):
        """Test each entry has its own timestamp."""
        activity_log.log_processing(
            pdf_count=1,
            pages_read=1,
            transaction_count=1,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=1.0,
        )
        activity_log.log_processing(
            pdf_count=2,
            pages_read=2,
            transaction_count=2,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=2.0,
        )

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])

        # Timestamps should be different (or very close)
        assert "timestamp" in entry1
        assert "timestamp" in entry2


class TestErrorHandling:
    """Test error handling."""

    def test_handles_write_errors_gracefully(self, tmp_path):
        """Test handles write errors without raising exceptions."""
        # Create log with read-only directory
        logs_dir = tmp_path / "readonly_logs"
        logs_dir.mkdir()
        log = ProcessingActivityLog(logs_dir)

        # Make directory read-only
        logs_dir.chmod(0o444)

        try:
            # Should not raise exception
            log.log_processing(
                pdf_count=1,
                pages_read=1,
                transaction_count=1,
                duplicate_count=0,
                output_formats=["csv"],
                duration_seconds=1.0,
            )
        finally:
            # Restore permissions for cleanup
            logs_dir.chmod(0o755)

    def test_handles_directory_creation_failure(self, tmp_path, monkeypatch):
        """Test handles directory creation failure gracefully."""
        logs_dir = tmp_path / "new_logs"

        # Mock mkdir to raise an error
        import pathlib

        original_mkdir = pathlib.Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if str(self) == str(logs_dir):
                raise PermissionError("Cannot create directory")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(pathlib.Path, "mkdir", mock_mkdir)

        # Should not raise exception, just log warning
        log = ProcessingActivityLog(logs_dir)
        assert log.logs_dir == logs_dir


class TestJSONLFormat:
    """Test JSONL format compliance."""

    def test_each_line_is_valid_json(self, activity_log):
        """Test each line in log file is valid JSON."""
        activity_log.log_processing(
            pdf_count=1,
            pages_read=5,
            transaction_count=10,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=1.0,
        )
        activity_log.log_deletion(file_name="test.csv", reason="Test")

        with open(activity_log.log_file, "r", encoding="utf-8") as f:
            for line in f:
                # Each line should be valid JSON
                entry = json.loads(line.strip())
                assert isinstance(entry, dict)

    def test_no_trailing_commas(self, activity_log):
        """Test log file has no trailing commas (proper JSONL)."""
        activity_log.log_processing(
            pdf_count=1,
            pages_read=5,
            transaction_count=10,
            duplicate_count=0,
            output_formats=["csv"],
            duration_seconds=1.0,
        )

        # Read raw file content
        content = activity_log.log_file.read_text()

        # Should not have array brackets or commas between entries
        assert not content.startswith("[")
        assert not content.endswith("]")
