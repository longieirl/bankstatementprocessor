"""Exclusion detector to filter out templates with matching exclude keywords."""

from __future__ import annotations

import logging
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class ExclusionDetector(BaseDetector):
    """Filters out templates if exclude keywords are found in the PDF.

    This detector runs FIRST in the chain to reject documents that match
    unwanted criteria before other detectors run. For example, credit card
    templates can exclude documents containing "IBAN" to avoid matching
    bank statements.
    """

    @property
    def name(self) -> str:
        return "Exclusion"

    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Filter templates based on exclude keywords.

        Searches the top 50% of the page for exclude keywords. If found,
        the template is given confidence=0.0 (excluded). Otherwise,
        confidence=1.0 (allowed).

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for EXCLUDED templates only.
            Excluded templates have confidence=0.0.
            Templates that are NOT excluded return no results (empty list),
            allowing other detectors to properly score them.
        """
        results: list[DetectionResult] = []

        # Extract text from top 50% of page (account info + header area)
        # Search from top (0) to y=400 to capture headers and account details
        header_bbox = (0, 0, first_page.width, 400)

        try:
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not text:
            logger.debug("No text found in header area for exclusion detection")
            # No text = can't exclude, return empty list (allow other detectors)
            return results

        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()

        # Check each template for exclude keywords
        for template in templates:
            if not template.detection.exclude_keywords:
                # No exclusion rules - skip this template (don't add to results)
                logger.debug(
                    "Template '%s' has no exclusion rules, skipping", template.name
                )
                continue

            # Check for exclude keywords
            excluded = False
            matched_keywords = []

            for keyword in template.detection.exclude_keywords:
                if keyword.lower() in text_lower:
                    excluded = True
                    matched_keywords.append(keyword)

            if excluded:
                # Only add result if template is EXCLUDED
                logger.info(
                    "Template '%s' EXCLUDED due to keywords: %s",
                    template.name,
                    ", ".join(matched_keywords),
                )
                results.append(
                    DetectionResult(
                        template=template,
                        confidence=0.0,  # Excluded
                        detector_name=self.name,
                        match_details={
                            "excluded": True,
                            "matched_keywords": matched_keywords,
                            "reason": "exclude_keywords_matched",
                        },
                    )
                )
            else:
                # Template is allowed - don't add to results
                logger.debug(
                    "Template '%s' allowed (no exclude keywords matched)", template.name
                )

        return results
