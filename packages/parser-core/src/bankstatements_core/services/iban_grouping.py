"""Service for grouping transactions by IBAN."""

from __future__ import annotations

import logging

from bankstatements_core.exceptions import InputValidationError

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
        rows: list[dict],
        pdf_ibans: dict[str, str],
    ) -> dict[str, list[dict]]:
        """Group transactions by their source IBAN.

        Transactions are grouped by the last N characters of their IBAN,
        where N is the suffix_length. Transactions without an IBAN are
        grouped under "unknown".

        Args:
            rows: List of transaction dictionaries with 'Filename' field
            pdf_ibans: Dictionary mapping PDF filename to full IBAN string

        Returns:
            Dictionary mapping IBAN suffix (or "unknown") to list of transactions
        """
        grouped: dict[str, list[dict]] = {}

        for row in rows:
            filename = row.get("Filename")
            if not filename:
                logger.warning("Row missing Filename field, grouping under 'unknown'")
                iban_suffix = "unknown"
            else:
                # Get IBAN for this file
                full_iban = pdf_ibans.get(filename)
                if full_iban:
                    iban_suffix = self._extract_suffix(full_iban)
                else:
                    iban_suffix = "unknown"

            # Add row to appropriate group
            if iban_suffix not in grouped:
                grouped[iban_suffix] = []
            grouped[iban_suffix].append(row)

        # Log grouping results
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

        # Remove whitespace and convert to uppercase
        iban_clean = iban.replace(" ", "").upper()

        # Extract suffix
        if len(iban_clean) >= self._suffix_length:
            return iban_clean[-self._suffix_length :]
        else:
            # If IBAN is shorter than suffix length, use whole IBAN
            return iban_clean

    def _log_grouping_summary(self, grouped: dict[str, list[dict]]) -> None:
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
