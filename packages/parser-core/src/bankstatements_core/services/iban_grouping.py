"""Service for grouping transactions by IBAN."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bankstatements_core.exceptions import InputValidationError

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction

logger = logging.getLogger(__name__)


class IBANGroupingService:
    """Groups transactions by their source IBAN.

    This service extracts IBAN information from transaction data and
    groups transactions by IBAN suffix for separate processing.
    """

    def __init__(self, suffix_length: int = 4):
        """Initialize the IBAN grouping service.

        Args:
            suffix_length: Number of characters from end of IBAN to use
                          as grouping key (default: 4)

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
        if suffix_length > 34:  # Max IBAN length is 34 characters
            raise InputValidationError(
                f"suffix_length cannot exceed 34 (max IBAN length), got {suffix_length}"
            )
        self._suffix_length = suffix_length

    def group_by_iban(
        self,
        rows: list["Transaction"],
        pdf_ibans: dict[str, str],
    ) -> dict[str, list["Transaction"]]:
        """Group transactions by their source IBAN.

        Transactions are grouped by the last N characters of their IBAN,
        where N is the suffix_length. Transactions without an IBAN are
        grouped under "unknown".

        Args:
            rows: List of Transaction objects with filename field
            pdf_ibans: Dictionary mapping PDF filename to full IBAN string

        Returns:
            Dictionary mapping IBAN suffix (or "unknown") to list of transactions
        """
        grouped: dict[str, list["Transaction"]] = {}

        for tx in rows:
            filename = tx.filename
            if not filename:
                logger.warning("Transaction missing filename, grouping under 'unknown'")
                iban_suffix = "unknown"
            else:
                full_iban = pdf_ibans.get(filename)
                if full_iban:
                    iban_suffix = self._extract_suffix(full_iban)
                else:
                    iban_suffix = "unknown"

            if iban_suffix not in grouped:
                grouped[iban_suffix] = []
            grouped[iban_suffix].append(tx)

        self._log_grouping_summary(grouped)

        return grouped

    def _extract_suffix(self, iban: str) -> str:
        """Extract suffix from IBAN for grouping.

        Args:
            iban: Full IBAN string

        Returns:
            Last N characters of IBAN (where N is suffix_length)
        """
        if not iban:
            return ""

        iban_clean = iban.replace(" ", "").upper()

        if len(iban_clean) >= self._suffix_length:
            return iban_clean[-self._suffix_length :]
        else:
            return iban_clean

    def _log_grouping_summary(self, grouped: dict[str, list["Transaction"]]) -> None:
        """Log summary of grouping results.

        Args:
            grouped: Dictionary of grouped transactions
        """
        total_groups = len(grouped)
        total_transactions = sum(len(group) for group in grouped.values())

        logger.info(
            f"Grouped {total_transactions} transaction(s) into "
            f"{total_groups} IBAN group(s)"
        )

        for iban_suffix, transactions in grouped.items():
            if iban_suffix == "unknown":
                logger.info(f"  No IBAN (unknown): {len(transactions)} transaction(s)")
            else:
                logger.info(
                    f"  IBAN ending in {iban_suffix}: "
                    f"{len(transactions)} transaction(s)"
                )
