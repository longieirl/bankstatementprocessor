"""Transaction sorting service.

This module provides a clean service interface for sorting transactions
using different sorting strategies (chronological, original order, etc.).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from bankstatements_core.services.date_parser import DateParserService

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction

logger = logging.getLogger(__name__)

_date_parser_service = DateParserService()


class SortingStrategy(ABC):
    """Abstract base class for transaction sorting strategies."""

    @abstractmethod
    def sort(self, transactions: list["Transaction"]) -> list["Transaction"]:
        """
        Sort transactions according to the strategy.

        Args:
            transactions: List of Transaction objects

        Returns:
            Sorted list of transactions
        """
        pass


class ChronologicalSortingStrategy(SortingStrategy):
    """Strategy that sorts transactions chronologically by date."""

    def sort(self, transactions: list["Transaction"]) -> list["Transaction"]:
        """
        Sort transactions chronologically by date.

        Args:
            transactions: List of Transaction objects

        Returns:
            Sorted list of transactions
        """
        if not transactions:
            return transactions

        logger.debug("Sorting %d transactions chronologically", len(transactions))

        return sorted(
            transactions,
            key=lambda tx: _date_parser_service.parse_transaction_date(tx.date),
        )


class NoSortingStrategy(SortingStrategy):
    """Strategy that keeps original order (no sorting)."""

    def sort(self, transactions: list["Transaction"]) -> list["Transaction"]:
        """
        Keep transactions in original order.

        Args:
            transactions: List of Transaction objects

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

    def sort(self, transactions: list["Transaction"]) -> list["Transaction"]:
        """
        Sort transactions using the configured strategy.

        Args:
            transactions: List of Transaction objects

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
