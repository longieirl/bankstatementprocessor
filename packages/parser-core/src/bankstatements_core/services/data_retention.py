"""Data retention service for GDPR compliance (Article 5.1.e Storage Limitation)."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.file_io import IFileDeleter
    from bankstatements_core.services.processing_activity_log import ProcessingActivityLog

logger = logging.getLogger(__name__)


class DataRetentionService:
    """
    Service for managing data retention and secure deletion of output files.

    Implements GDPR Article 5.1.e (Storage Limitation) and Article 17 (Right to Erasure).
    """

    def __init__(
        self,
        retention_days: int,
        output_dir: Path,
        file_deleter: "IFileDeleter | None" = None,
    ):
        """
        Initialize data retention service.

        Args:
            retention_days: Number of days to retain files (0 = no automatic cleanup)
            output_dir: Directory containing output files to manage
            file_deleter: Optional file deleter for dependency injection (default: use direct file I/O)
        """
        self.retention_days = retention_days
        self.output_dir = output_dir
        self._file_deleter = file_deleter
        self.output_patterns = [
            "*.csv",
            "*.json",
            "*.xlsx",
        ]

    def find_expired_files(self) -> list[Path]:
        """
        Find files older than the retention period.

        Returns:
            List of Path objects for expired files
        """
        if self.retention_days == 0:
            return []

        if not self.output_dir.exists():
            return []

        expired_files = []
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        for pattern in self.output_patterns:
            for file_path in self.output_dir.glob(pattern):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        expired_files.append(file_path)

        return expired_files

    def cleanup_expired_files(
        self, audit_log: "ProcessingActivityLog" | None = None
    ) -> int:
        """
        Delete files older than retention period with secure deletion.

        Args:
            audit_log: Optional activity log for recording deletions

        Returns:
            Number of files deleted
        """
        expired_files = self.find_expired_files()

        if not expired_files:
            logger.info("No expired files found")
            return 0

        deleted_count = 0
        for file_path in expired_files:
            try:
                age_days = (
                    datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                ).days
                self._secure_delete(file_path)
                logger.info(
                    "Deleted expired file: %s (age: %d days)", file_path.name, age_days
                )

                # Log deletion event
                if audit_log:
                    audit_log.log_deletion(
                        file_name=file_path.name,
                        reason="Data retention policy",
                        age_days=age_days,
                    )

                deleted_count += 1
            except OSError as e:
                # Expected errors: file system errors, permission issues
                logger.error("Failed to delete %s: %s", file_path, e)
            # Let unexpected errors bubble up

        logger.info("Cleanup completed: %d files deleted", deleted_count)
        return deleted_count

    def cleanup_all_files(
        self, audit_log: "ProcessingActivityLog" | None = None
    ) -> int:
        """
        Delete all output files (GDPR Article 17: Right to Erasure).

        Args:
            audit_log: Optional activity log for recording deletions

        Returns:
            Number of files deleted
        """
        if not self.output_dir.exists():
            return 0

        deleted_count = 0
        for pattern in self.output_patterns:
            for file_path in self.output_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        age_days = (
                            datetime.now()
                            - datetime.fromtimestamp(file_path.stat().st_mtime)
                        ).days
                        self._secure_delete(file_path)
                        logger.info("Deleted file: %s", file_path.name)

                        # Log deletion event
                        if audit_log:
                            audit_log.log_deletion(
                                file_name=file_path.name,
                                reason="Right to erasure (Article 17)",
                                age_days=age_days,
                            )

                        deleted_count += 1
                    except OSError as e:
                        # Expected errors: file system errors, permission issues
                        logger.error("Failed to delete %s: %s", file_path, e)
                    # Let unexpected errors bubble up

        logger.info("All files deleted: %d files", deleted_count)
        return deleted_count

    def cleanup_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
        audit_log: "ProcessingActivityLog" | None = None,
    ) -> int:
        """
        Delete files within a specific date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            audit_log: Optional activity log for recording deletions

        Returns:
            Number of files deleted
        """
        if not self.output_dir.exists():
            return 0

        deleted_count = 0
        for pattern in self.output_patterns:
            for file_path in self.output_dir.glob(pattern):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if start_date <= file_mtime <= end_date:
                        try:
                            age_days = (datetime.now() - file_mtime).days
                            self._secure_delete(file_path)
                            logger.info(
                                "Deleted file: %s (date: %s)",
                                file_path.name,
                                file_mtime.strftime("%Y-%m-%d"),
                            )

                            # Log deletion event
                            if audit_log:
                                audit_log.log_deletion(
                                    file_name=file_path.name,
                                    reason=f"Date range deletion ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
                                    age_days=age_days,
                                )

                            deleted_count += 1
                        except OSError as e:
                            # Expected errors: file system errors, permission issues
                            logger.error("Failed to delete %s: %s", file_path, e)
                        # Let unexpected errors bubble up

        logger.info("Date range cleanup completed: %d files deleted", deleted_count)
        return deleted_count

    def _secure_delete(self, file_path: Path) -> None:
        """
        Securely delete a file by overwriting with random data 3 times.

        Args:
            file_path: Path to file to delete

        Raises:
            Exception: If deletion fails
        """
        # Get file size
        file_size = file_path.stat().st_size

        # Overwrite 3 times with random data
        for i in range(3):
            try:
                with open(file_path, "wb") as f:
                    # Write random data in chunks for better performance
                    chunk_size = 8192
                    remaining = file_size
                    while remaining > 0:
                        write_size = min(chunk_size, remaining)
                        f.write(secrets.token_bytes(write_size))
                        remaining -= write_size
                    f.flush()
                    os.fsync(f.fileno())
            except OSError as e:
                # Expected errors: file system errors, permission issues
                logger.warning(
                    "Failed to overwrite %s (pass %d/3): %s", file_path, i + 1, e
                )
            # Let unexpected errors bubble up

        # Finally delete the file
        if self._file_deleter:
            self._file_deleter.delete_file(file_path)
        else:
            file_path.unlink()
