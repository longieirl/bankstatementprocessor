"""IBAN-based template detector."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class IBANDetector(BaseDetector):
    """Detects template by matching IBAN pattern in PDF content."""

    @property
    def name(self) -> str:
        return "IBAN"

    def detect(  # noqa: C901, PLR0912
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect templates by searching for IBAN patterns in header area.

        Only searches the top 40% of the page to avoid matching IBANs that
        might appear in transaction descriptions (e.g., transfers between accounts).

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            IBAN matches have high confidence (0.95-1.0).
        """
        results: list[DetectionResult] = []

        # Extract text from header/account info area only
        # In pdfplumber: top=0 is at top of page, values increase downward
        # Search from top (0) to y=400 to capture account info area
        # This avoids false positives from IBANs in transaction descriptions
        header_bbox = (0, 0, first_page.width, 400)

        try:
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not text:
            logger.debug("No text found in header area for IBAN detection")
            return results

        # Search for IBAN (basic pattern: 2 letters + numbers)
        iban_pattern = r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}\b"
        matches = re.finditer(iban_pattern, text)

        found_ibans = [match.group(0) for match in matches]

        if found_ibans:
            logger.debug(f"Found IBAN candidates in header area: {found_ibans}")

        # Check each template's IBAN patterns
        for template in templates:
            if not template.detection.iban_patterns:
                continue

            matched_iban = None
            matched_pattern = None

            for iban in found_ibans:
                for pattern in template.detection.iban_patterns:
                    try:
                        if re.match(pattern, iban):
                            matched_iban = iban
                            matched_pattern = pattern
                            break
                    except re.error as e:
                        logger.error(
                            f"Invalid IBAN regex pattern '{pattern}' "
                            f"in template '{template.id}': {e}"
                        )
                if matched_iban:
                    break

            if matched_iban and matched_pattern:
                # IBAN match = high confidence (0.95 base)
                # +0.05 if pattern is specific (length > 10)
                confidence = 0.95
                if len(matched_pattern) > 10:
                    confidence = 1.0

                logger.info(
                    f"IBAN '{matched_iban}' matched template '{template.name}' "
                    f"(pattern: {matched_pattern}, confidence: {confidence})"
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={
                            "iban": matched_iban,
                            "pattern": matched_pattern,
                        },
                    )
                )

        if not results:
            logger.debug("No IBAN match found in header area for any template")

        return results
