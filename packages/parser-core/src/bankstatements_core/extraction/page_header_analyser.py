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
                            f"Credit card indicator found in header: pattern '{pattern}' matched"
                        )
                        return True
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"Error checking for credit card statement: {e}")
        return False

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
            logger.warning(f"Error extracting IBAN from page: {e}")

        return None
