"""Service for filtering transactions by year (FILTER_YEAR).

Restricts transactions to an inclusive range of years. The year of each
transaction is resolved strictly: it must be explicit in the date string or
inferable from the statement year for yearless dates. When the year cannot be
determined, processing aborts (YearFilterError) rather than guessing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.exceptions import YearFilterError
from bankstatements_core.services.date_parser import DateParserService

logger = logging.getLogger(__name__)


class YearFilterStrategy(ABC):
    """Strategy for restricting a list of transactions by year."""

    @abstractmethod
    def filter(self, transactions: list[Transaction], source: str) -> list[Transaction]:
        """Return the transactions that fall within the configured years.

        Args:
            transactions: Transactions to filter
            source: Human-readable origin (e.g. PDF filename) for error messages
        """
        ...


class NoYearFilterStrategy(YearFilterStrategy):
    """No-op strategy: include every transaction regardless of year."""

    def filter(self, transactions: list[Transaction], source: str) -> list[Transaction]:
        return transactions


class YearRangeFilterStrategy(YearFilterStrategy):
    """Keep only transactions whose year is within [min_year, max_year]."""

    def __init__(
        self,
        min_year: int,
        max_year: int,
        date_parser: DateParserService | None = None,
    ):
        self._min_year = min_year
        self._max_year = max_year
        self._date_parser = date_parser or DateParserService()

    def filter(self, transactions: list[Transaction], source: str) -> list[Transaction]:
        kept: list[Transaction] = []
        for tx in transactions:
            hint = tx.additional_fields.get("statement_year")
            hint_year = int(hint) if hint and hint.isdigit() else None
            year = self._date_parser.try_resolve_year(tx.date, hint_year=hint_year)
            if year is None:
                logger.error(
                    "Cannot filter by year: no determinable year in date '%s' in %s. Aborting.",
                    tx.date,
                    source,
                )
                raise YearFilterError(
                    f"No determinable year in date '{tx.date}' in {source}"
                )
            if self._min_year <= year <= self._max_year:
                kept.append(tx)

        removed = len(transactions) - len(kept)
        if removed > 0:
            logger.info(
                "Year filter removed %d transaction(s) outside %d-%d from %s",
                removed,
                self._min_year,
                self._max_year,
                source,
            )
        return kept


class TransactionYearFilterService:
    """Applies a YearFilterStrategy to transaction lists."""

    def __init__(self, strategy: YearFilterStrategy):
        self._strategy = strategy

    @property
    def is_active(self) -> bool:
        """True when a real year restriction is configured (not include-all)."""
        return not isinstance(self._strategy, NoYearFilterStrategy)

    def filter(
        self, transactions: list[Transaction], source: str = ""
    ) -> list[Transaction]:
        """Filter transactions using the configured strategy."""
        return self._strategy.filter(transactions, source)

    @classmethod
    def from_range(
        cls, year_range: tuple[int, int] | None
    ) -> TransactionYearFilterService:
        """Build a service from a (min, max) range; None means include all."""
        if year_range is None:
            return cls(NoYearFilterStrategy())
        return cls(YearRangeFilterStrategy(year_range[0], year_range[1]))
