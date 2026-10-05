"""Service for discovering PDF files in input directory."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFDiscoveryService:
    """Discovers PDF files in input directory.

    This service encapsulates the logic for finding PDF files.
    """

    def __init__(self) -> None:
        """Initialize the PDF discovery service."""

    def discover_pdfs(
        self,
        input_dir: Path,
        recursive: bool = True,
    ) -> list[Path]:
        """Discover PDF files in input directory.

        Args:
            input_dir: Directory to search for PDF files
            recursive: Whether to search recursively in subdirectories.

        Returns:
            List of Path objects for discovered PDF files

        Raises:
            FileNotFoundError: If input directory doesn't exist
        """
        if not input_dir.exists():
            logger.info("Input directory not found, creating: %s", input_dir)
            try:
                input_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Created input directory: %s", input_dir)
            except OSError as e:
                # Expected errors: permission issues, filesystem errors
                raise FileNotFoundError(
                    f"Input directory not found and could not be created: {input_dir}. Error: {e}"
                ) from e
            # Let unexpected errors bubble up

        if not input_dir.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")

        # Discover PDF files
        if recursive:
            pattern = "**/*.pdf"
            logger.info("Scanning %s recursively for PDF files", input_dir)
        else:
            pattern = "*.pdf"
            logger.info("Scanning %s for PDF files", input_dir)

        pdf_files = sorted(input_dir.glob(pattern))

        logger.info("Discovered %d PDF file(s)", len(pdf_files))

        return pdf_files
