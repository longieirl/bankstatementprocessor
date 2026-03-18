"""Service for discovering PDF files in input directory."""

from __future__ import annotations

import logging
from pathlib import Path

from bankstatements_core.entitlements import EntitlementError, Entitlements

logger = logging.getLogger(__name__)


class PDFDiscoveryService:
    """Discovers PDF files in input directory with entitlement support.

    This service encapsulates the logic for finding PDF files while
    respecting entitlement restrictions (e.g., recursive scanning).
    """

    def __init__(self, entitlements: Entitlements | None = None):
        """Initialize the PDF discovery service.

        Args:
            entitlements: Optional entitlements for feature restrictions.
                         If None, allows all features.
        """
        self._entitlements = entitlements

    def discover_pdfs(
        self,
        input_dir: Path,
        recursive: bool = False,
    ) -> list[Path]:
        """Discover PDF files in input directory.

        Args:
            input_dir: Directory to search for PDF files
            recursive: Whether to search recursively in subdirectories.
                      Subject to entitlement restrictions.

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

        # Check entitlements for recursive scanning
        if recursive and self._entitlements:
            try:
                self._entitlements.check_recursive_scan()
            except EntitlementError as e:
                # Expected: FREE tier users attempting recursive scan
                logger.warning(
                    "Recursive scanning not allowed: %s. Scanning only top-level directory.",
                    str(e),
                    exc_info=True,
                )
                recursive = False
            # Let unexpected errors bubble up

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
