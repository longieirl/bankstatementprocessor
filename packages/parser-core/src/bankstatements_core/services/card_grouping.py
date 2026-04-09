"""Service for grouping transactions by credit card number."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from bankstatements_core.exceptions import InputValidationError

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction

logger = logging.getLogger(__name__)


class CCGroupingService:
    """Groups transactions by their source card number suffix.

    Mirrors IBANGroupingService but uses card number suffixes (last 4 digits)
    instead of IBAN suffixes for grouping credit card statement transactions.
    """

    def __init__(self, suffix_length: int = 4) -> None:
        """Initialize the CC grouping service.

        Args:
            suffix_length: Number of characters from end of cleaned card number
                          to use as grouping key (default: 4)

        Raises:
            InputValidationError: If suffix_length is invalid
        """
        if not isinstance(suffix_length, int):
            raise InputValidationError(
                f"suffix_length must be int, got {type(suffix_length).__name__}"
            )
        if suffix_length < 1:
            raise InputValidationError(
                f"suffix_length must be >= 1, got {suffix_length}"
            )
        self._suffix_length = suffix_length

    def group_by_card(
        self,
        rows: list[Transaction],
        pdf_card_numbers: dict[str, str],
    ) -> dict[str, list[Transaction]]:
        """Group transactions by their source card number suffix.

        Args:
            rows: List of Transaction objects with filename field
            pdf_card_numbers: Dictionary mapping PDF filename to card number string

        Returns:
            Dictionary mapping card suffix (or "unknown") to list of transactions
        """
        grouped: dict[str, list[Transaction]] = {}

        for tx in rows:
            filename = tx.filename
            if not filename:
                logger.warning(
                    "Transaction missing filename, grouping under 'unknown'"
                )
                card_suffix = "unknown"
            else:
                full_card = pdf_card_numbers.get(filename)
                if full_card and full_card != "unknown":
                    card_suffix = self._extract_suffix(full_card)
                else:
                    card_suffix = "unknown"

            if card_suffix not in grouped:
                grouped[card_suffix] = []
            grouped[card_suffix].append(tx)

        self._log_grouping_summary(grouped)

        return grouped

    def _extract_suffix(self, card_number: str) -> str:
        """Extract suffix from card number for grouping.

        Strips all non-alphanumeric characters, uppercases, and takes
        the last suffix_length characters.

        Args:
            card_number: Card number string (may contain *, spaces, etc.)

        Returns:
            Last N characters of cleaned card number
        """
        if not card_number:
            return ""

        cleaned = re.sub(r"[^A-Za-z0-9]", "", card_number).upper()

        if len(cleaned) >= self._suffix_length:
            return cleaned[-self._suffix_length :]
        return cleaned if cleaned else "unknown"

    def _log_grouping_summary(
        self, grouped: dict[str, list[Transaction]]
    ) -> None:
        """Log summary of grouping results."""
        total_groups = len(grouped)
        total_transactions = sum(len(group) for group in grouped.values())

        logger.info(
            "Grouped %s CC transaction(s) into %s card group(s)",
            total_transactions,
            total_groups,
        )

        for card_suffix, transactions in grouped.items():
            if card_suffix == "unknown":
                logger.info(
                    "  No card number (unknown): %s transaction(s)",
                    len(transactions),
                )
            else:
                logger.info(
                    "  Card ending in %s: %s transaction(s)",
                    card_suffix,
                    len(transactions),
                )
