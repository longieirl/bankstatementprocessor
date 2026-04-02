"""Column header-based template detector."""

from __future__ import annotations

import logging
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class ColumnHeaderDetector(BaseDetector):
    """Detects template by matching expected column headers in table."""

    @property
    def name(self) -> str:
        return "ColumnHeader"

    def detect(  # noqa: C901
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect templates by finding column headers near top of table area.

        Searches the upper 50% of the page where column headers typically appear,
        avoiding false matches on similar words in transaction descriptions.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            Column matches have lower confidence (0.60-0.90).
        """
        results: list[DetectionResult] = []

        # Extract text from area where column headers typically appear
        # In pdfplumber: top=0 is at top of page, values increase downward
        # Search from top (0) to y=350 to capture column headers
        # This avoids false positives from similar words in transaction descriptions
        header_area_bbox = (0, 0, first_page.width, 350)

        try:
            page_text = first_page.crop(header_area_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            page_text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not page_text:
            logger.debug("No text found in header area for column header detection")
            return results

        page_text_lower = page_text.lower()

        # Check each template's column headers
        for template in templates:
            if not template.detection.column_headers:
                continue

            # Count how many expected headers are found
            found_headers = []
            expected_count = len(template.detection.column_headers)

            for header in template.detection.column_headers:
                if header.lower() in page_text_lower:
                    found_headers.append(header)

            found_count = len(found_headers)
            match_ratio = found_count / expected_count if expected_count > 0 else 0

            # Require at least 70% of headers to match
            match_threshold = 0.7
            if match_ratio >= match_threshold:
                # Column match = medium-low confidence (0.60 base)
                # Scale up to 0.90 for >90% match ratio
                if match_ratio >= 0.9:
                    confidence = 0.90
                elif match_ratio >= 0.8:
                    confidence = 0.75
                else:
                    confidence = 0.60

                logger.info(
                    "Column headers matched template '%s' (%s/%s headers found, confidence: %s)",
                    template.name,
                    found_count,
                    expected_count,
                    confidence,
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={
                            "found_headers": found_headers,
                            "expected_count": expected_count,
                            "found_count": found_count,
                            "match_ratio": match_ratio,
                        },
                    )
                )

        if not results:
            logger.debug("No column header match found in header area for any template")

        return results
