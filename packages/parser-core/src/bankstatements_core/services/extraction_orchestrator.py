"""Service for orchestrating PDF extraction with template detection."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.pdf_reader import IPDFReader
    from bankstatements_core.domain.protocols.services import ITemplateDetector

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.extraction.extraction_facade import extract_tables_from_pdf
from bankstatements_core.templates import TemplateDetector, TemplateRegistry
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """Orchestrates PDF extraction with template detection.

    This service manages the template detection system and coordinates
    the extraction of transactions from individual PDF files.
    """

    def __init__(
        self,
        extraction_config: ExtractionConfig | None = None,
        template_detector: ITemplateDetector | None = None,
        forced_template: BankTemplate | None = None,
        entitlements: Entitlements | None = None,
        pdf_reader: IPDFReader | None = None,
    ):
        """Initialize the extraction orchestrator.

        Args:
            extraction_config: Configuration for PDF extraction
            template_detector: Optional template detector instance
            forced_template: Optional forced template to use for all PDFs
            entitlements: Optional entitlements for tier-based filtering
            pdf_reader: Optional PDF reader for dependency injection (default: use pdfplumber adapter)
        """
        self._config = extraction_config or ExtractionConfig()
        self._template_detector = template_detector
        self._forced_template = forced_template
        self._entitlements = entitlements

        # Inject PDF reader or use default pdfplumber adapter
        if pdf_reader is None:
            from bankstatements_core.adapters.pdfplumber_adapter import (
                PDFPlumberReaderAdapter,
            )

            self._pdf_reader: IPDFReader = PDFPlumberReaderAdapter()  # type: ignore[assignment]
        else:
            self._pdf_reader = pdf_reader

        # Initialize template detection if not provided
        if self._template_detector is None and self._forced_template is None:
            self._initialize_template_system()

    def _initialize_template_system(self) -> None:
        """Initialize template detection system."""
        try:
            template_registry = TemplateRegistry.from_default_config()

            # Filter templates based on entitlements
            # (FREE tier requires IBAN patterns)
            if self._entitlements and self._entitlements.require_iban:
                all_templates = template_registry.list_all()
                iban_only_ids = {
                    t.id for t in all_templates if t.detection.iban_patterns
                }
                skipped = len(all_templates) - len(iban_only_ids)

                if skipped:
                    skipped_names = ", ".join(
                        t.name for t in all_templates if not t.detection.iban_patterns
                    )
                    logger.warning(
                        f"{self._entitlements.tier} tier requires IBAN "
                        f"patterns for PDF processing. "
                        f"Ignoring {skipped} template(s) "
                        f"without IBAN patterns: {skipped_names}"
                    )
                    template_registry = template_registry.filtered_by_ids(iban_only_ids)

            self._template_detector = TemplateDetector(template_registry)

            # Log enabled templates after filtering
            enabled_templates = template_registry.list_enabled()
            enabled_names = ", ".join(t.name for t in enabled_templates)
            logger.info(
                f"Template detection system initialized with "
                f"{len(enabled_templates)} enabled template(s): "
                f"{enabled_names}"
            )

            # Check for forced template override from environment
            force_template_id = os.getenv("FORCE_TEMPLATE")
            if force_template_id and self._template_detector:
                forced = self._template_detector.force_template(force_template_id)
                self._forced_template = forced
                if self._forced_template:
                    logger.info(
                        f"FORCE_TEMPLATE set: Using '{self._forced_template.name}' "
                        "for all PDFs"
                    )
                else:
                    logger.error(
                        f"FORCE_TEMPLATE '{force_template_id}' not found. "
                        "Using auto-detection."
                    )
        except (ValueError, FileNotFoundError, KeyError) as e:
            # Expected errors: invalid config, missing files, missing keys
            logger.warning(
                f"Failed to initialize template system: {e}. "
                "Using default configuration."
            )
        # Let unexpected errors (AttributeError, TypeError, etc.) bubble up

    def extract_from_pdf(
        self,
        pdf_path: Path,
        forced_template: BankTemplate | None = None,
    ) -> ExtractionResult:
        """Extract transactions from a single PDF file.

        Args:
            pdf_path: Path to the PDF file
            forced_template: Optional template to force for this PDF
                           (overrides instance forced_template)

        Returns:
            ExtractionResult containing extracted transactions, page count, IBAN,
            and document-level warnings
        """
        # Determine which template to use
        template = forced_template or self._forced_template

        # If no forced template, detect it (only if file exists)
        if template is None and self._template_detector and pdf_path.exists():
            template = self._detect_template(pdf_path)

        # Log template usage
        if template:
            logger.info(f"Using template: {template.name} for {pdf_path.name}")

        # Extract transactions using template
        result = extract_tables_from_pdf(
            pdf_path,
            self._config.table_top_y,
            self._config.table_bottom_y,
            self._config.columns,
            self._config.enable_dynamic_boundary,
            template=template,
        )

        # Log IBAN if found
        if result.iban:
            logger.info(
                f"IBAN extracted from {pdf_path.name}: {result.iban[:4]}****{result.iban[-4:]}"
            )

        return result

    def _detect_template(self, pdf_path: Path) -> BankTemplate | None:
        """Detect template for a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Detected BankTemplate or None if detection fails
        """
        if not self._template_detector:
            return None

        try:
            with self._pdf_reader.open(pdf_path) as pdf_doc:
                first_page_adapter = pdf_doc.pages[0]
                # Template detector expects pdfplumber.Page, so unwrap the adapter
                first_page = first_page_adapter.underlying_page  # type: ignore[attr-defined]
                template = self._template_detector.detect_template(pdf_path, first_page)
                logger.info(f"Detected template: {template.name} for {pdf_path.name}")
                return template
        except (OSError, AttributeError, IndexError, KeyError) as e:
            # Expected errors: file access, page access, missing attributes, missing keys
            logger.warning(
                f"Template detection failed for {pdf_path.name}: {e}. "
                "Using defaults."
            )
            return None
        # Let unexpected errors bubble up
