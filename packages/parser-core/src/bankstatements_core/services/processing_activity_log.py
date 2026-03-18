"""Processing activity log for GDPR compliance (Article 5.2 Accountability)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.file_io import IJsonWriter

logger = logging.getLogger(__name__)


class ProcessingActivityLog:
    """
    Service for logging processing activities for GDPR accountability.

    Implements GDPR Article 5.2 (Accountability) by maintaining an audit trail
    of processing operations without storing sensitive data.

    Log format: JSON Lines (JSONL) - one JSON object per line
    """

    def __init__(self, logs_dir: Path, file_writer: "IJsonWriter | None" = None):
        """
        Initialize processing activity log.

        Args:
            logs_dir: Directory to store log files
            file_writer: Optional file writer for dependency injection (default: use direct file I/O)
        """
        self.logs_dir = logs_dir
        self.log_file = logs_dir / "processing_activity.jsonl"
        self._file_writer = file_writer

        # Ensure logs directory exists
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Expected errors: file system errors, permission issues (PermissionError is subclass of OSError)
            logger.warning("Failed to create logs directory: %s", e)
        # Let unexpected errors bubble up

    def log_processing(
        self,
        pdf_count: int,
        pages_read: int,
        transaction_count: int,
        duplicate_count: int,
        output_formats: list[str],
        duration_seconds: float,
    ) -> None:
        """
        Log a processing operation.

        Args:
            pdf_count: Number of PDFs processed
            pages_read: Total pages read
            transaction_count: Number of unique transactions
            duplicate_count: Number of duplicate transactions
            output_formats: List of output formats generated
            duration_seconds: Processing duration in seconds
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "processing",
            "pdf_count": pdf_count,
            "pages_read": pages_read,
            "transaction_count": transaction_count,
            "duplicate_count": duplicate_count,
            "output_formats": output_formats,
            "duration_seconds": round(duration_seconds, 2),
        }
        self._write_entry(entry)

    def log_deletion(
        self, file_name: str, reason: str, age_days: int | None = None
    ) -> None:
        """
        Log a file deletion event.

        Args:
            file_name: Name of deleted file
            reason: Reason for deletion (e.g., "Data retention policy")
            age_days: Age of file in days (optional)
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "deletion",
            "file_name": file_name,
            "reason": reason,
        }
        if age_days is not None:
            entry["age_days"] = age_days

        self._write_entry(entry)

    def log_encryption(self, file_count: int, operation: str) -> None:
        """
        Log an encryption/decryption operation.

        Args:
            file_count: Number of files encrypted/decrypted
            operation: Operation type ("encrypt" or "decrypt")
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "encryption",
            "operation": operation,
            "file_count": file_count,
        }
        self._write_entry(entry)

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """
        Write a log entry to the JSONL file.

        Args:
            entry: Dictionary containing log data
        """
        try:
            # For JSONL format, we append directly rather than using IJsonWriter
            # since IJsonWriter typically overwrites the entire file
            with open(self.log_file, "a", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
        except (OSError, TypeError) as e:
            # Expected errors: file I/O errors (including permission issues), JSON serialization errors
            logger.warning("Failed to write to activity log: %s", e)
        # Let unexpected errors bubble up
