"""Card number-based template detector for credit card statements."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class CardNumberDetector(BaseDetector):
    """Detects credit card statement templates by matching card number patterns.

    Searches for masked card numbers (e.g., "**** **** **** 1234") in the header area
    of the PDF. This is highly specific to credit card statements and helps distinguish
    them from bank account statements.
    """

    @property
    def name(self) -> str:
        return "CardNumber"

    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Detect templates by searching for card number patterns in header area.

        Searches the top portion of the page (y=0 to y=400) where card numbers
        typically appear in statement headers. Avoids false positives from card
        numbers appearing in transaction descriptions.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF
            templates: List of templates to check

        Returns:
            List of DetectionResult objects for matching templates.
            Card number matches have high confidence (0.90-0.95).
        """
        results: list[DetectionResult] = []

        # Extract text from header/account info area only
        # In pdfplumber: top=0 is at top of page, values increase downward
        # Search from top (0) to y=400 to capture card info area
        header_bbox = (0, 0, first_page.width, 400)

        try:
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Expected errors: crop failures, missing methods, type mismatches
            # Fallback to full page if cropping fails
            text = first_page.extract_text()
        # Let unexpected errors bubble up

        if not text:
            logger.debug("No text found in header area for card number detection")
            return results

        # Check each template's card number patterns
        for template in templates:
            card_patterns = template.detection.get_card_number_patterns()
            if not card_patterns:
                continue

            matched_card = None
            matched_pattern = None

            for pattern in card_patterns:
                try:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        matched_card = match.group(0)
                        matched_pattern = pattern
                        break
                except re.error as e:
                    logger.error(
                        f"Invalid card number regex pattern '{pattern}' "
                        f"in template '{template.id}': {e}"
                    )

                if matched_card:
                    break

            if matched_card and matched_pattern:
                # Card number match = high confidence (0.90 base)
                # +0.05 if pattern is specific (length > 30)
                confidence = 0.90
                if len(matched_pattern) > 30:
                    confidence = 0.95

                logger.info(
                    f"Card number '{matched_card}' matched template '{template.name}' "
                    f"(pattern: {matched_pattern}, confidence: {confidence})"
                )

                results.append(
                    DetectionResult(
                        template=template,
                        confidence=confidence,
                        detector_name=self.name,
                        match_details={
                            "card_number": matched_card,
                            "pattern": matched_pattern,
                        },
                    )
                )

        if not results:
            logger.debug("No card number match found in header area for any template")

        return results
