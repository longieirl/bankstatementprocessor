"""Tests for data retention service (GDPR Article 5.1.e Storage Limitation)."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bankstatements_core.services.data_retention import DataRetentionService


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory with test files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def retention_service(temp_output_dir):
    """Create a DataRetentionService instance."""
    return DataRetentionService(retention_days=7, output_dir=temp_output_dir)


def create_test_file(output_dir: Path, filename: str, age_days: int = 0) -> Path:
    """
    Create a test file with specified age.

    Args:
        output_dir: Directory to create file in
        filename: Name of file to create
        age_days: How many days old the file should be

    Returns:
        Path to created file
    """
    file_path = output_dir / filename
    file_path.write_text("test data")

    # Set modification time
    if age_days > 0:
        old_time = datetime.now() - timedelta(days=age_days)
        timestamp = old_time.timestamp()
        os.utime(file_path, (timestamp, timestamp))

    return file_path


class TestDataRetentionServiceInitialization:
    """Test DataRetentionService initialization."""

    def test_initialization_with_retention_days(self, temp_output_dir):
        """Test service initializes with retention period."""
        service = DataRetentionService(retention_days=30, output_dir=temp_output_dir)
        assert service.retention_days == 30
        assert service.output_dir == temp_output_dir

    def test_initialization_with_zero_retention(self, temp_output_dir):
        """Test service initializes with zero retention (no limit)."""
        service = DataRetentionService(retention_days=0, output_dir=temp_output_dir)
        assert service.retention_days == 0

    def test_output_patterns_configured(self, retention_service):
        """Test output file patterns are configured."""
        assert "*.csv" in retention_service.output_patterns
        assert "*.json" in retention_service.output_patterns
        assert "*.xlsx" in retention_service.output_patterns


class TestFindExpiredFiles:
    """Test finding expired files based on retention policy."""

    def test_find_expired_files_with_no_files(self, retention_service):
        """Test no expired files when directory is empty."""
        expired = retention_service.find_expired_files()
        assert expired == []

    def test_find_expired_files_with_retention_zero(self, temp_output_dir):
        """Test no files found when retention is 0 (no limit)."""
        service = DataRetentionService(retention_days=0, output_dir=temp_output_dir)
        create_test_file(temp_output_dir, "old.csv", age_days=100)
        expired = service.find_expired_files()
        assert expired == []

    def test_find_expired_files_with_old_csv(self, retention_service, temp_output_dir):
        """Test finds expired CSV file."""
        old_file = create_test_file(temp_output_dir, "old.csv", age_days=10)
        expired = retention_service.find_expired_files()
        assert len(expired) == 1
        assert expired[0] == old_file

    def test_find_expired_files_with_old_json(self, retention_service, temp_output_dir):
        """Test finds expired JSON file."""
        old_file = create_test_file(temp_output_dir, "old.json", age_days=10)
        expired = retention_service.find_expired_files()
        assert len(expired) == 1
        assert expired[0] == old_file

    def test_find_expired_files_with_old_xlsx(self, retention_service, temp_output_dir):
        """Test finds expired Excel file."""
        old_file = create_test_file(temp_output_dir, "old.xlsx", age_days=10)
        expired = retention_service.find_expired_files()
        assert len(expired) == 1
        assert expired[0] == old_file

    def test_find_expired_files_ignores_recent_files(
        self, retention_service, temp_output_dir
    ):
        """Test does not find recent files."""
        create_test_file(temp_output_dir, "recent.csv", age_days=1)
        expired = retention_service.find_expired_files()
        assert expired == []

    def test_find_expired_files_mixed_ages(self, retention_service, temp_output_dir):
        """Test correctly identifies mix of old and recent files."""
        old_file1 = create_test_file(temp_output_dir, "old1.csv", age_days=10)
        old_file2 = create_test_file(temp_output_dir, "old2.json", age_days=15)
        create_test_file(temp_output_dir, "recent1.csv", age_days=1)
        create_test_file(temp_output_dir, "recent2.xlsx", age_days=3)

        expired = retention_service.find_expired_files()
        assert len(expired) == 2
        assert old_file1 in expired
        assert old_file2 in expired

    def test_find_expired_files_nonexistent_directory(self, tmp_path):
        """Test handles nonexistent directory gracefully."""
        nonexistent_dir = tmp_path / "nonexistent"
        service = DataRetentionService(retention_days=7, output_dir=nonexistent_dir)
        expired = service.find_expired_files()
        assert expired == []


class TestCleanupExpiredFiles:
    """Test cleanup of expired files."""

    def test_cleanup_expired_files_deletes_old_file(
        self, retention_service, temp_output_dir
    ):
        """Test cleanup deletes expired file."""
        old_file = create_test_file(temp_output_dir, "old.csv", age_days=10)
        deleted_count = retention_service.cleanup_expired_files()
        assert deleted_count == 1
        assert not old_file.exists()

    def test_cleanup_expired_files_preserves_recent_files(
        self, retention_service, temp_output_dir
    ):
        """Test cleanup does not delete recent files."""
        recent_file = create_test_file(temp_output_dir, "recent.csv", age_days=1)
        deleted_count = retention_service.cleanup_expired_files()
        assert deleted_count == 0
        assert recent_file.exists()

    def test_cleanup_expired_files_no_files(self, retention_service):
        """Test cleanup with no files returns zero."""
        deleted_count = retention_service.cleanup_expired_files()
        assert deleted_count == 0

    def test_cleanup_expired_files_multiple_files(
        self, retention_service, temp_output_dir
    ):
        """Test cleanup deletes multiple expired files."""
        create_test_file(temp_output_dir, "old1.csv", age_days=10)
        create_test_file(temp_output_dir, "old2.json", age_days=15)
        create_test_file(temp_output_dir, "old3.xlsx", age_days=20)

        deleted_count = retention_service.cleanup_expired_files()
        assert deleted_count == 3
        assert len(list(temp_output_dir.glob("*"))) == 0


class TestCleanupAllFiles:
    """Test cleanup of all files (GDPR Article 17)."""

    def test_cleanup_all_files_deletes_everything(
        self, retention_service, temp_output_dir
    ):
        """Test cleanup_all_files deletes all output files."""
        create_test_file(temp_output_dir, "file1.csv", age_days=1)
        create_test_file(temp_output_dir, "file2.json", age_days=10)
        create_test_file(temp_output_dir, "file3.xlsx", age_days=100)

        deleted_count = retention_service.cleanup_all_files()
        assert deleted_count == 3
        assert len(list(temp_output_dir.glob("*"))) == 0

    def test_cleanup_all_files_no_files(self, retention_service):
        """Test cleanup_all_files with empty directory."""
        deleted_count = retention_service.cleanup_all_files()
        assert deleted_count == 0

    def test_cleanup_all_files_nonexistent_directory(self, tmp_path):
        """Test cleanup_all_files with nonexistent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        service = DataRetentionService(retention_days=7, output_dir=nonexistent_dir)
        deleted_count = service.cleanup_all_files()
        assert deleted_count == 0


class TestSecureDelete:
    """Test secure file deletion."""

    def test_secure_delete_overwrites_file(self, retention_service, temp_output_dir):
        """Test secure delete overwrites file content."""
        # Create file with known content
        file_path = temp_output_dir / "sensitive.csv"
        original_content = "sensitive data" * 1000
        file_path.write_text(original_content)

        # Secure delete
        retention_service._secure_delete(file_path)

        # File should no longer exist
        assert not file_path.exists()

    def test_secure_delete_handles_empty_file(self, retention_service, temp_output_dir):
        """Test secure delete handles empty file."""
        file_path = temp_output_dir / "empty.csv"
        file_path.write_text("")

        retention_service._secure_delete(file_path)
        assert not file_path.exists()

    def test_secure_delete_large_file(self, retention_service, temp_output_dir):
        """Test secure delete handles large files efficiently."""
        file_path = temp_output_dir / "large.csv"
        # Write 1MB of random data
        file_path.write_bytes(secrets.token_bytes(1024 * 1024))

        retention_service._secure_delete(file_path)
        assert not file_path.exists()


class TestCleanupByDate:
    """Test cleanup by date range."""

    def test_cleanup_by_date_range(self, retention_service, temp_output_dir):
        """Test cleanup files within date range."""
        # Create files with different ages
        old_file = create_test_file(temp_output_dir, "old.csv", age_days=30)
        target_file = create_test_file(temp_output_dir, "target.csv", age_days=15)
        recent_file = create_test_file(temp_output_dir, "recent.csv", age_days=1)

        # Delete files between 10 and 20 days old
        start_date = datetime.now() - timedelta(days=20)
        end_date = datetime.now() - timedelta(days=10)

        deleted_count = retention_service.cleanup_by_date(start_date, end_date)

        assert deleted_count == 1
        assert not target_file.exists()
        assert old_file.exists()
        assert recent_file.exists()

    def test_cleanup_by_date_range_empty(self, retention_service, temp_output_dir):
        """Test cleanup with date range that matches no files."""
        create_test_file(temp_output_dir, "file.csv", age_days=1)

        start_date = datetime.now() - timedelta(days=100)
        end_date = datetime.now() - timedelta(days=90)

        deleted_count = retention_service.cleanup_by_date(start_date, end_date)
        assert deleted_count == 0


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_cleanup_expired_files_handles_deletion_error(
        self, retention_service, temp_output_dir, monkeypatch
    ):
        """Test cleanup handles errors gracefully during deletion."""
        create_test_file(temp_output_dir, "old.csv", age_days=10)

        # Mock _secure_delete to raise an error
        def mock_secure_delete(file_path):
            raise PermissionError("Cannot delete file")

        monkeypatch.setattr(retention_service, "_secure_delete", mock_secure_delete)

        # Should not raise, should return 0
        deleted_count = retention_service.cleanup_expired_files()
        assert deleted_count == 0

    def test_cleanup_all_files_handles_deletion_error(
        self, retention_service, temp_output_dir, monkeypatch
    ):
        """Test cleanup_all_files handles errors gracefully."""
        create_test_file(temp_output_dir, "file.csv", age_days=1)

        # Mock _secure_delete to raise an error
        def mock_secure_delete(file_path):
            raise PermissionError("Cannot delete file")

        monkeypatch.setattr(retention_service, "_secure_delete", mock_secure_delete)

        deleted_count = retention_service.cleanup_all_files()
        assert deleted_count == 0

    def test_cleanup_by_date_handles_deletion_error(
        self, retention_service, temp_output_dir, monkeypatch
    ):
        """Test cleanup_by_date handles errors gracefully."""
        create_test_file(temp_output_dir, "file.csv", age_days=15)

        # Mock _secure_delete to raise an error
        def mock_secure_delete(file_path):
            raise PermissionError("Cannot delete file")

        monkeypatch.setattr(retention_service, "_secure_delete", mock_secure_delete)

        start_date = datetime.now() - timedelta(days=20)
        end_date = datetime.now() - timedelta(days=10)

        deleted_count = retention_service.cleanup_by_date(start_date, end_date)
        assert deleted_count == 0

    def test_secure_delete_handles_overwrite_error(
        self, retention_service, temp_output_dir, monkeypatch
    ):
        """Test secure delete continues even if overwrite fails."""
        file_path = temp_output_dir / "file.csv"
        file_path.write_text("test content")

        # Mock open to fail during overwrite but only for our specific file
        original_open = open

        def mock_open(path, *args, **kwargs):
            # Only fail for our test file when writing binary
            if str(path) == str(file_path) and (
                "wb" in args or kwargs.get("mode") == "wb"
            ):
                raise IOError("Cannot write")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should still delete the file even if overwrite fails
        retention_service._secure_delete(file_path)
        # Verify file was deleted
        assert not file_path.exists()


class TestActivityLogIntegration:
    """Test integration with activity log."""

    def test_cleanup_expired_files_logs_deletion(
        self, retention_service, temp_output_dir
    ):
        """Test cleanup logs deletion events."""
        from bankstatements_core.services.processing_activity_log import ProcessingActivityLog

        # Create activity log
        logs_dir = temp_output_dir / "logs"
        logs_dir.mkdir()
        activity_log = ProcessingActivityLog(logs_dir)

        # Create old file
        create_test_file(temp_output_dir, "old.csv", age_days=10)

        # Cleanup with activity log
        deleted_count = retention_service.cleanup_expired_files(audit_log=activity_log)
        assert deleted_count == 1

        # Verify log entry
        log_file = logs_dir / "processing_activity.jsonl"
        assert log_file.exists()
        content = log_file.read_text()
        assert "deletion" in content
        assert "old.csv" in content

    def test_cleanup_all_files_logs_deletion(self, retention_service, temp_output_dir):
        """Test cleanup_all_files logs deletion events."""
        from bankstatements_core.services.processing_activity_log import ProcessingActivityLog

        logs_dir = temp_output_dir / "logs"
        logs_dir.mkdir()
        activity_log = ProcessingActivityLog(logs_dir)

        create_test_file(temp_output_dir, "file.csv", age_days=1)

        deleted_count = retention_service.cleanup_all_files(audit_log=activity_log)
        assert deleted_count == 1

        log_file = logs_dir / "processing_activity.jsonl"
        content = log_file.read_text()
        assert "Right to erasure" in content

    def test_cleanup_by_date_logs_deletion(self, retention_service, temp_output_dir):
        """Test cleanup_by_date logs deletion events."""
        from bankstatements_core.services.processing_activity_log import ProcessingActivityLog

        logs_dir = temp_output_dir / "logs"
        logs_dir.mkdir()
        activity_log = ProcessingActivityLog(logs_dir)

        create_test_file(temp_output_dir, "file.csv", age_days=15)

        start_date = datetime.now() - timedelta(days=20)
        end_date = datetime.now() - timedelta(days=10)

        deleted_count = retention_service.cleanup_by_date(
            start_date, end_date, audit_log=activity_log
        )
        assert deleted_count == 1

        log_file = logs_dir / "processing_activity.jsonl"
        content = log_file.read_text()
        assert "Date range deletion" in content
