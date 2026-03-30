"""Duplicate detection service for bank transactions.

This module provides a clean service interface for detecting and separating
duplicate transactions using configurable detection strategies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bankstatements_core.exceptions import InputValidationError

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction
    from bankstatements_core.patterns.strategies import DuplicateDetectionStrategy

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """
    Service for detecting and separating duplicate transactions.

    Uses a configurable DuplicateDetectionStrategy to determine what
    constitutes a duplicate transaction.
    """

    def __init__(self, strategy: DuplicateDetectionStrategy):
        """
        Initialize duplicate detection service.

        Args:
            strategy: Strategy to use for duplicate detection

        Raises:
            InputValidationError: If strategy is None or invalid
        """
        if strategy is None:
            raise InputValidationError("strategy cannot be None")
        if not hasattr(strategy, "detect_duplicates"):
            raise InputValidationError(
                f"strategy must have 'detect_duplicates' method, "
                f"got {type(strategy).__name__}"
            )
        self.strategy = strategy

    def detect_and_separate(
        self, transactions: list[Transaction]
    ) -> tuple[list[Transaction], list[Transaction]]:
        """
        Detect duplicates and separate into unique and duplicate lists.

        Args:
            transactions: List of Transaction objects to process

        Returns:
            Tuple of (unique_transactions, duplicate_transactions)
        """
        unique, duplicates = self.strategy.detect_duplicates(transactions)

        logger.info(
            "Duplicate detection using %s strategy: %d unique, %d duplicates",
            self.strategy.__class__.__name__,
            len(unique),
            len(duplicates),
        )

        return unique, duplicates

    def get_statistics(
        self,
        unique_transactions: list[Transaction],
        duplicate_transactions: list[Transaction],
    ) -> dict[str, int | float]:
        """
        Get statistics about duplicate detection results.

        Args:
            unique_transactions: List of unique transactions
            duplicate_transactions: List of duplicate transactions

        Returns:
            Dictionary with statistics (total, unique, duplicates, duplicate_rate)
        """
        total = len(unique_transactions) + len(duplicate_transactions)
        duplicate_rate = (
            (len(duplicate_transactions) / total * 100) if total > 0 else 0.0
        )

        return {
            "total": total,
            "unique": len(unique_transactions),
            "duplicates": len(duplicate_transactions),
            "duplicate_rate_percent": round(duplicate_rate, 2),
        }
