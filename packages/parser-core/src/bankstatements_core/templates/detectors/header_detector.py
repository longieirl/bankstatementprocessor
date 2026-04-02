"""Header keyword-based template detector."""

from __future__ import annotations

import logging
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class HeaderDetector(BaseDetector):
    """Detects template by searching for bank keywords in page header."""

    @property
    def name(self) -> str:
        return "Header"

    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect template by searching for header keywords in page header area.

        Only searches the top 30% of the page to avoid false positives from
        transaction descriptions that might contain bank names.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            Header matches have medium confidence (0.70-0.75).
        """
        results: list[DetectionResult] = []

        # Extract text from header area only
        # In pdfplumber: top=0 is at top of page, values increase downward
        # Search from top (0) to y=250 to capture header/bank name area
        # This avoids false positives from transaction descriptions
        header_bbox = (0, 0, first_page.width, 250)

        try:
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not text:
            logger.debug("No text found in header area for header detection")
            return results

        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()

        for template in templates:
            if not template.detection.header_keywords:
                continue

            matched_keywords = []
            for keyword in template.detection.header_keywords:
                if keyword.lower() in text_lower:
                    matched_keywords.append(keyword)

            if matched_keywords:
                # Header match = medium confidence (0.70 base)
                # +0.05 for each additional keyword (up to 0.75)
                confidence = 0.70 + min(len(matched_keywords) - 1, 1) * 0.05

                logger.info(
                    "Header keywords %s found for template '%s' (confidence: %s)",
                    matched_keywords,
                    template.name,
                    confidence,
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={"matched_keywords": matched_keywords},
                    )
                )

        if not results:
            logger.debug(
                "No header keyword match found in header area for any template"
            )

        return results
