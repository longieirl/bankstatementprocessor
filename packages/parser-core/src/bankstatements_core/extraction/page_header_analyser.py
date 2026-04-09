"""Page header analysis for PDF bank statements.

Encapsulates logic that inspects the page area before the transaction table:
credit card detection and IBAN extraction.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.extraction.iban_extractor import IBANExtractor

logger = logging.getLogger(__name__)

_CREDIT_CARD_PATTERNS = [
    r"card\s+number",
    r"credit\s+limit",
    r"credit\s+card",
    r"\bvisa\b",
    r"\bmastercard\b",
]

_IBAN_HEADER_Y = 350

# Patterns for extracting the statement year from a payment due date field.
# Matches lines like:
#   "Payment Due  3 Mar 2026"
#   "Payment Due Date: 20 Feb 2026"
#   "Total Minimum Payment Due 17th April, 2026"
#   "Total Minimum Payment Due 20th March, 2026"
_PAYMENT_DUE_PATTERNS = [
    r"Payment\s+Due\s+Date\s*[:\s]\s*\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+(\d{4})",
    r"Payment\s+Due\s+\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+(\d{4})",
]


class PageHeaderAnalyser:
    """Inspects the page header area for credit card indicators and IBAN."""

    def __init__(self, iban_extractor: IBANExtractor) -> None:
        self._iban_extractor = iban_extractor

    def is_credit_card_statement(self, page: Any, table_top_y: int) -> bool:
        """Return True if the page header contains credit card indicators.

        Args:
            page: pdfplumber page object
            table_top_y: Top Y boundary of the transaction table; header is above this

        Returns:
            True if credit card statement detected, False otherwise
        """
        try:
            header_area = page.crop((0, 0, page.width, table_top_y))
            header_text = header_area.extract_text()
            if header_text:
                for pattern in _CREDIT_CARD_PATTERNS:
                    if re.search(pattern, header_text, re.IGNORECASE):
                        logger.debug(
                            "Credit card indicator found in header: pattern '%s' matched",
                            pattern,
                        )
                        return True
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning("Error checking for credit card statement: %s", e)
        return False

    def extract_statement_year(self, page: Any) -> int | None:
        """Extract the statement year from a 'Payment Due' or 'Payment Due Date' field.

        Scans the full page 1 text for patterns like:
        - "Payment Due  3 Mar 2026"
        - "Payment Due Date: 20 Feb 2026"

        Args:
            page: pdfplumber page object (page 1 only)

        Returns:
            Four-digit year as int if found, None otherwise
        """
        try:
            page_text = page.extract_text()
            if page_text:
                for pattern in _PAYMENT_DUE_PATTERNS:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        year = int(match.group(1))
                        logger.debug(
                            "Statement year %d extracted from 'Payment Due' field", year
                        )
                        return year
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning("Error extracting statement year from page: %s", e)
        return None

    def extract_iban(self, page: Any) -> str | None:
        """Extract account IBAN from the page header area (y < 350).

        Args:
            page: pdfplumber page object

        Returns:
            IBAN string if found, None otherwise
        """
        try:
            header_area = page.crop((0, 0, page.width, _IBAN_HEADER_Y))
            header_text = header_area.extract_text()
            if header_text:
                iban = self._iban_extractor.extract_iban(header_text)
                if iban:
                    return iban

            header_words = header_area.extract_words(use_text_flow=True)
            if header_words:
                iban = self._iban_extractor.extract_iban_from_pdf_words(header_words)
                if iban:
                    return iban
        except (AttributeError, ValueError, KeyError, TypeError) as e:
            logger.warning("Error extracting IBAN from page: %s", e)

        return None
