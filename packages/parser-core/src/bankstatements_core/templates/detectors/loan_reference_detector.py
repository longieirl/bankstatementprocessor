"""Loan reference-based template detector for loan statements."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class LoanReferenceDetector(BaseDetector):
    """Detects loan statement templates by matching loan reference patterns.

    Searches for loan references (e.g., "Loan Ref: 12345", "Mortgage Account: ABC123")
    in the header area of the PDF. This helps distinguish loan statements from
    regular bank statements.
    """

    @property
    def name(self) -> str:
        return "LoanReference"

    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect templates by searching for loan reference patterns in header area.

        Searches the top portion of the page (y=0 to y=400) where loan references
        typically appear in statement headers.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            Loan reference matches have high confidence (0.90-0.95).
        """
        results: list[DetectionResult] = []

        # Extract text from header/account info area only
        header_bbox = (0, 0, first_page.width, 400)

        try:
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not text:
            logger.debug("No text found in header area for loan reference detection")
            return results

        # Check each template's loan reference patterns
        for template in templates:
            loan_patterns = template.detection.get_loan_reference_patterns()
            if not loan_patterns:
                continue

            matched_ref = None
            matched_pattern = None

            for pattern in loan_patterns:
                try:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        matched_ref = match.group(0)
                        matched_pattern = pattern
                        break
                except re.error as e:
                    logger.error(
                        f"Invalid loan reference regex pattern '{pattern}' "
                        f"in template '{template.id}': {e}"
                    )

                if matched_ref:
                    break

            if matched_ref and matched_pattern:
                # Loan reference match = high confidence (0.90 base)
                # +0.05 if pattern is specific (length > 20)
                confidence = 0.90
                if len(matched_pattern) > 20:
                    confidence = 0.95

                logger.info(
                    f"Loan reference '{matched_ref}' matched template '{template.name}' "
                    f"(pattern: {matched_pattern}, confidence: {confidence})"
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={
                            "loan_reference": matched_ref,
                            "pattern": matched_pattern,
                        },
                    )
                )

        if not results:
            logger.debug(
                "No loan reference match found in header area for any template"
            )

        return results
