"""PDF Processing Orchestrator for bank statement extraction.

This module orchestrates the complete PDF processing pipeline including:
- PDF discovery
- Individual PDF extraction
- Error handling and exclusion tracking
- IBAN extraction and storage
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.entitlements import Entitlements

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.services import (
        IPDFDiscovery,
        ITransactionFilter,
    )
    from bankstatements_core.patterns.repositories import (
        FileSystemTransactionRepository,
    )
    from bankstatements_core.services.extraction_orchestrator import (
        ExtractionOrchestrator,
    )

logger = logging.getLogger(__name__)


class PDFProcessingOrchestrator:
    """Orchestrates PDF processing pipeline.

    Handles:
    - Discovery of PDF files in input directory
    - Processing each PDF with extraction orchestrator
    - Filtering extracted transactions
    - Tracking excluded files and IBANs
    - Error handling for failed PDFs
    """

    def __init__(
        self,
        extraction_config: ExtractionConfig,
        column_names: list[str],
        output_dir: Path,
        repository: FileSystemTransactionRepository,
        entitlements: Entitlements | None = None,
        pdf_discovery: IPDFDiscovery | None = None,
        extraction_orchestrator: ExtractionOrchestrator | None = None,
        filter_service: ITransactionFilter | None = None,
    ):
        """Initialize PDF processing orchestrator.

        Args:
            extraction_config: Configuration for PDF extraction
            column_names: List of column names for filtering
            output_dir: Directory to save IBAN and exclusion logs
            repository: Transaction repository for file I/O operations
            entitlements: Optional entitlements for feature restrictions (e.g., recursive scanning)
            pdf_discovery: Service for discovering PDF files (optional, creates default if None)
            extraction_orchestrator: Service for extracting data from PDFs (optional, creates default if None)
            filter_service: Service for filtering transactions (optional, creates default if None)
        """
        from bankstatements_core.services.extraction_orchestrator import (
            ExtractionOrchestrator,
        )
        from bankstatements_core.services.pdf_discovery import PDFDiscoveryService
        from bankstatements_core.services.transaction_filter import (
            TransactionFilterService,
        )

        self.extraction_config = extraction_config
        self.column_names = column_names
        self.output_dir = output_dir
        self.repository = repository
        self.entitlements = entitlements
        # Initialize services with provided instances or create defaults
        self.pdf_discovery = pdf_discovery or PDFDiscoveryService(
            entitlements=entitlements
        )
        self.extraction_orchestrator = (
            extraction_orchestrator
            or ExtractionOrchestrator(
                extraction_config=extraction_config, entitlements=entitlements
            )
        )
        if (
            extraction_orchestrator is not None
            and extraction_orchestrator._entitlements != entitlements
        ):
            raise ValueError(
                "ExtractionOrchestrator entitlements must match PDFProcessingOrchestrator "
                "entitlements. Pass a consistent entitlements object to both, or omit "
                "extraction_orchestrator to have it created automatically."
            )
        self.filter_service = filter_service or TransactionFilterService(column_names)

    def process_all_pdfs(
        self, input_dir: Path, recursive: bool = False
    ) -> tuple[list[ExtractionResult], int, int]:
        """Process all PDF files in the input directory.

        Args:
            input_dir: Directory containing PDF files
            recursive: Whether to search subdirectories recursively

        Returns:
            Tuple of (results, pdf_count, pages_read) where pdf_count is total PDFs
            discovered (including excluded/failed), results contains one ExtractionResult
            per successfully processed PDF, and pages_read is the total page count across
            all PDFs attempted (including excluded ones).
        """
        # Discover PDF files
        pdf_files = self.pdf_discovery.discover_pdfs(input_dir, recursive=recursive)

        results: list[ExtractionResult] = []
        pages_read = 0
        pdf_ibans: dict[str, str] = {}
        excluded_files: list[dict[str, Any]] = []

        # Process each PDF
        for idx, pdf in enumerate(pdf_files, 1):
            logger.info("Processing PDF %d of %d", idx, len(pdf_files))

            try:
                result = self.extraction_orchestrator.extract_from_pdf(pdf)
                pages_read += result.page_count

                # Check if should be excluded (no IBAN and no data)
                if (
                    result.iban is None
                    and len(result.transactions) == 0
                    and result.page_count > 0
                ):
                    excluded_files.append(
                        {
                            "filename": pdf.name,
                            "path": str(pdf),
                            "reason": (
                                "Could not be processed - no IBAN found "
                                "(likely credit card statement)"
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "pages": result.page_count,
                        }
                    )
                    logger.warning(
                        "PDF %d (%s) could not be processed: No IBAN found, no data extracted",
                        idx,
                        pdf.name,
                    )
                    continue

                # Store IBAN if found
                if result.iban:
                    pdf_ibans[pdf.name] = result.iban

                # Apply filters to extracted rows
                filtered_rows = self.filter_service.apply_all_filters(
                    result.transactions
                )
                result.transactions = filtered_rows

                logger.info(
                    "Successfully processed PDF %d: %d transactions extracted",
                    idx,
                    len(filtered_rows),
                )
                results.append(result)

            except (OSError, ValueError, AttributeError, KeyError) as e:
                # Expected errors: file I/O, invalid PDF structure, missing attributes, missing keys
                logger.error(
                    "Failed to process PDF %d: %s. Continuing with next file.",
                    idx,
                    str(e),
                )
                continue
            # Let unexpected errors bubble up

        # Save IBANs to output file
        if pdf_ibans:
            self._save_ibans(pdf_ibans)

        # Save excluded files to JSON log
        if excluded_files:
            self._save_excluded_files(excluded_files)

        return results, len(pdf_files), pages_read

    def _save_ibans(self, pdf_ibans: dict[str, str]) -> None:
        """Save extracted IBANs to JSON file.

        Args:
            pdf_ibans: Dictionary mapping PDF filenames to IBANs
        """
        ibans_path = self.output_dir / "ibans.json"
        logger.info("Saving %d IBANs to: %s", len(pdf_ibans), ibans_path)

        # Convert to list format without persisting raw IBANs (PII protection)
        iban_list: list[dict[str, str]] = []
        for filename, iban in pdf_ibans.items():
            masked = f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"
            digest = hashlib.sha256(iban.encode("utf-8")).hexdigest()
            iban_list.append(
                {
                    "pdf_filename": filename,
                    "iban_masked": masked,
                    "iban_digest": digest,
                }
            )

        self.repository.save_json_file(ibans_path, iban_list)

    def _save_excluded_files(self, excluded_files: list[dict[str, Any]]) -> None:
        """Save excluded files log to JSON.

        Args:
            excluded_files: List of excluded file metadata
        """
        excluded_path = self.output_dir / "excluded_files.json"
        logger.info(
            "Saving %d excluded files to: %s", len(excluded_files), excluded_path
        )

        # Add summary metadata
        excluded_log = {
            "summary": {
                "total_excluded": len(excluded_files),
                "generated_at": datetime.now().isoformat(),
                "note": (
                    "Files excluded from processing due to "
                    "missing IBAN or no extractable data"
                ),
            },
            "excluded_files": excluded_files,
        }

        self.repository.save_json_file(excluded_path, excluded_log)

        logger.warning(
            "%d PDFs were excluded (see %s for details)",
            len(excluded_files),
            excluded_path,
        )
