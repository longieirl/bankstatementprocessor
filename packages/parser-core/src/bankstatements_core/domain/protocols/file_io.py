"""File I/O protocols for dependency inversion."""

from pathlib import Path
from typing import Any, Protocol


class IJsonWriter(Protocol):
    """Protocol for writing JSON data to files."""

    def write_json(self, file_path: Path, data: Any) -> None:
        """Write data as JSON to file.

        Args:
            file_path: Path to write JSON file
            data: Data to serialize to JSON

        Raises:
            IOError: If file write fails
        """
        ...


class IFileDeleter(Protocol):
    """Protocol for deleting files."""

    def delete_file(self, file_path: Path) -> None:
        """Delete a file.

        Args:
            file_path: Path to file to delete

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If deletion fails
        """
        ...


class IFileReader(Protocol):
    """Protocol for reading file contents."""

    def read_text(self, file_path: Path) -> str:
        """Read file contents as text.

        Args:
            file_path: Path to file to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
        """
        ...
