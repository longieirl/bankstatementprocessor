"""Filename-based template detector."""

from __future__ import annotations

import logging
from fnmatch import fnmatch
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class FilenameDetector(BaseDetector):
    """Detects template by matching filename patterns."""

    @property
    def name(self) -> str:
        return "Filename"

    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect templates by matching filename against glob patterns.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF (unused)
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            Filename matches have medium-high confidence (0.80-0.90).
        """
        filename = pdf_path.name
        logger.debug("Checking filename: %s", filename)

        results = []

        for template in templates:
            # Only check templates that have explicit filename patterns configured
            # If filename_patterns is empty, skip this template for filename detection
            if not template.detection.filename_patterns:
                continue

            matched_patterns = []
            for pattern in template.detection.filename_patterns:
                if fnmatch(filename, pattern):
                    matched_patterns.append(pattern)

            if matched_patterns:
                # Filename match = medium-high confidence (0.80 base)
                # +0.10 if multiple patterns match (more specific)
                confidence = 0.80
                if len(matched_patterns) > 1:
                    confidence = 0.90

                logger.info(
                    "Filename '%s' matched template '%s' (patterns: %s, confidence: %s)",
                    filename,
                    template.name,
                    matched_patterns,
                    confidence,
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={
                            "filename": filename,
                            "matched_patterns": matched_patterns,
                        },
                    )
                )

        if not results:
            logger.debug("No filename match found for any template")

        return results
