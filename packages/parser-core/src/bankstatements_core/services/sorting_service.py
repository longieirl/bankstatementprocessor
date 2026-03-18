"""Transaction sorting service.

This module provides a clean service interface for sorting transactions
using different sorting strategies (chronological, original order, etc.).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from bankstatements_core.domain import dicts_to_transactions, transactions_to_dicts

logger = logging.getLogger(__name__)


class SortingStrategy(ABC):
    """Abstract base class for transaction sorting strategies."""

    @abstractmethod
    def sort(self, transactions: list[dict]) -> list[dict]:
        """
        Sort transactions according to the strategy.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Sorted list of transactions
        """
        pass


class ChronologicalSortingStrategy(SortingStrategy):
    """Strategy that sorts transactions chronologically by date.

    Note:
        Accepts list[dict] for backward compatibility but sorts using
        Transaction objects internally for type-safe field access.
    """

    def sort(self, transactions: list[dict]) -> list[dict]:
        """
        Sort transactions chronologically by date.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Sorted list of transaction dicts
        """
        if not transactions:
            return transactions

        from bankstatements_core.processor import parse_transaction_date

        # Convert to domain objects
        tx_objects = dicts_to_transactions(transactions)

        logger.debug("Sorting %d transactions chronologically", len(tx_objects))

        # Sort using domain object's date field (type-safe)
        sorted_txs = sorted(tx_objects, key=lambda tx: parse_transaction_date(tx.date))

        # Convert back to dicts for backward compatibility
        return transactions_to_dicts(sorted_txs)


class NoSortingStrategy(SortingStrategy):
    """Strategy that keeps original order (no sorting)."""

    def sort(self, transactions: list[dict]) -> list[dict]:
        """
        Keep transactions in original order.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Transactions in original order
        """
        logger.debug("Keeping %d transactions in original order", len(transactions))
        return transactions


class TransactionSortingService:
    """
    Service for sorting transactions using configurable strategies.

    Supports different sorting approaches (chronological, original order, etc.)
    through the Strategy pattern.
    """

    def __init__(self, strategy: SortingStrategy):
        """
        Initialize sorting service.

        Args:
            strategy: Sorting strategy to use
        """
        self.strategy = strategy

    def sort(self, transactions: list[dict]) -> list[dict]:
        """
        Sort transactions using the configured strategy.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Sorted list of transactions
        """
        result = self.strategy.sort(transactions)
        logger.info(
            "Sorted %d transactions using %s",
            len(transactions),
            self.strategy.__class__.__name__,
        )
        return result
