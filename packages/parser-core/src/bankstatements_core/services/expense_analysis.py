"""Expense analysis service for detecting patterns and anomalies.

This module provides expense insight generation including recurring charge
detection and high-value transaction anomaly detection.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast

from bankstatements_core.domain import Transaction, dicts_to_transactions
from bankstatements_core.domain.currency import strip_currency_symbols
from bankstatements_core.entitlements import EntitlementError
from bankstatements_core.services.date_parser import DateParserService

if TYPE_CHECKING:
    from bankstatements_core.entitlements import Entitlements

logger = logging.getLogger(__name__)

_date_parser_service = DateParserService()


class ExpenseAnalysisService:
    """
    Service for analyzing expenses and generating insights.

    Detects patterns in transactions including:
    - Recurring charges (subscriptions, monthly bills)
    - High-value transaction anomalies (statistical outliers)

    Available to all users. Entitlement infrastructure maintained for
    potential future feature restrictions.

    Example:
        >>> service = ExpenseAnalysisService()
        >>> transactions = [
        ...     {"Date": "01 Jan 2023", "Details": "Netflix", "Debit €": "15.99", ...},
        ...     {"Date": "31 Jan 2023", "Details": "Netflix", "Debit €": "15.99", ...},
        ... ]
        >>> insights = service.analyze(transactions)
        >>> print(insights["insights"]["recurring_charges"])
    """

    def __init__(self, entitlements: Entitlements | None = None):
        """
        Initialize expense analysis service.

        Args:
            entitlements: Optional entitlements for enforcement (None = no enforcement)
        """
        self.entitlements = entitlements

    def analyze(self, transactions: list[dict]) -> dict[str, Any]:
        """
        Analyze transactions and generate expense insights.

        Checks entitlements if provided (currently available to all users).
        Entitlement infrastructure maintained for potential future restrictions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with expense insights containing:
            - summary: Description text
            - generated_at: ISO timestamp of generation
            - total_transactions_analyzed: Number of transactions
            - insights: {
                recurring_charges: list[dict],
                high_value_transactions: list[dict],
                statistics: dict
              }

        Raises:
            EntitlementError: If expense analysis is not allowed (currently always allowed)

        Note:
            Returns empty insights on error (logs warning, doesn't fail).
        """
        try:
            # Enforce entitlements at entry point (defense in depth)
            if self.entitlements is not None:
                self.entitlements.check_expense_analysis()
                logger.info("Expense analysis authorized")

            if not transactions:
                logger.info("No transactions to analyze")
                return self._empty_insights()

            logger.info("Analyzing %s transactions", len(transactions))

            # Convert to domain objects at boundary for type-safe operations
            tx_objects = dicts_to_transactions(transactions)

            # Calculate statistics first (needed for anomaly detection)
            statistics_data = self._calculate_statistics(tx_objects)

            # Detect patterns
            recurring_charges = self._detect_recurring_charges(tx_objects)
            high_value_txns = self._detect_high_value_transactions(
                tx_objects, statistics_data
            )
            repeated_vendors = self._detect_repeated_vendors(tx_objects)

            return {
                "summary": "Expense Analysis Report",
                "generated_at": datetime.now().isoformat(),
                "total_transactions_analyzed": len(transactions),
                "insights": {
                    "recurring_charges": recurring_charges,
                    "high_value_transactions": high_value_txns,
                    "repeated_vendors": repeated_vendors,
                    "statistics": statistics_data,
                },
            }

        except EntitlementError:
            # Re-raise tier restriction errors (fail fast)
            raise
        except Exception as e:  # noqa: BLE001 — service-boundary catch
            # Unexpected errors: log warning and return empty insights
            logger.warning(
                "Expense analysis failed: %s. Returning empty insights.",
                e,
                exc_info=True,
            )
            return self._empty_insights(error=str(e))

    def _detect_recurring_charges(  # noqa: C901, PLR0912
        self, tx_objects: list[Transaction]
    ) -> list[dict[str, Any]]:
        """
        Detect recurring charges using exact description matching.

        A recurring charge is identified when:
        - Exact same description appears 2+ times
        - No normalization - exact string match required

        Args:
            tx_objects: List of Transaction domain objects

        Returns:
            List of recurring charge dicts with metadata
        """
        # Group transactions by EXACT description (no normalization)
        groups: dict[str, list[Transaction]] = defaultdict(list)
        for tx in tx_objects:
            if tx.details:  # Only group non-empty descriptions
                groups[tx.details].append(tx)

        recurring = []
        for description, txs in groups.items():
            if len(txs) < 2:
                continue  # Need at least 2 occurrences

            # Sort by date for interval calculation
            try:
                txs_sorted = sorted(
                    txs,
                    key=lambda t: _date_parser_service.parse_transaction_date(t.date),
                )
            except (ValueError, TypeError) as e:
                logger.warning("Failed to sort transactions for %s: %s", description, e)
                continue

            # Extract amounts (handle both debit and credit)
            amounts = []
            for tx in txs_sorted:
                amount = self._get_transaction_amount(tx)
                if amount is not None and amount > 0:
                    amounts.append(amount)

            if len(amounts) < 2:
                continue  # Need at least 2 valid amounts

            # Check amount similarity (±5% tolerance)
            avg_amount = sum(amounts) / len(amounts)
            if not all(
                abs(float(a) - float(avg_amount)) <= float(avg_amount) * 0.05
                for a in amounts
            ):
                continue  # Amounts too variable

            # Calculate date intervals
            intervals = []
            for i in range(1, len(txs_sorted)):
                try:
                    date1 = _date_parser_service.parse_transaction_date(
                        txs_sorted[i - 1].date
                    )
                    date2 = _date_parser_service.parse_transaction_date(
                        txs_sorted[i].date
                    )
                    delta = (date2 - date1).days
                    if delta > 0:  # Only positive intervals
                        intervals.append(delta)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning("Failed to calculate interval: %s", e)
                    continue

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            # Check if intervals are in 25-35 day range (monthly-ish)
            if 25 <= avg_interval <= 35:
                recurring.append(
                    {
                        "description": description,
                        "average_amount": round(float(avg_amount), 2),
                        "frequency": "monthly",
                        "occurrences": len(txs_sorted),
                        "transactions": [
                            {
                                "date": tx.date,
                                "amount": round(
                                    float(self._get_transaction_amount(tx) or 0), 2
                                ),
                            }
                            for tx in txs_sorted
                        ],
                        "average_interval_days": round(avg_interval, 1),
                    }
                )

        logger.info("Detected %s recurring charges", len(recurring))
        return recurring

    def _detect_high_value_transactions(
        self, tx_objects: list[Transaction], statistics_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect high-value transaction anomalies using statistical methods.

        Identifies transactions where amount > mean + 2*std_dev.

        Args:
            tx_objects: List of Transaction domain objects
            statistics_data: Pre-calculated statistics (mean, std_dev)

        Returns:
            List of high-value transaction dicts with deviation info
        """
        mean = statistics_data.get("mean_transaction_amount", 0)
        std_dev = statistics_data.get("std_dev", 0)

        if std_dev == 0:
            logger.info("Standard deviation is 0, no outliers possible")
            return []

        threshold = mean + 2 * std_dev
        high_value = []

        for tx in tx_objects:
            amount = self._get_transaction_amount(tx)
            if amount is None or amount <= 0:
                continue

            amount_float = float(amount)
            if amount_float > threshold:
                # std_dev > 0 guaranteed by early return above
                std_dev_from_mean = (amount_float - mean) / std_dev
                high_value.append(
                    {
                        "date": tx.date,
                        "description": tx.details,
                        "amount": round(amount_float, 2),
                        "std_dev_from_mean": round(std_dev_from_mean, 2),
                        "is_outlier": True,
                    }
                )

        # Sort by amount descending
        high_value.sort(key=lambda x: x["amount"], reverse=True)

        logger.info("Detected %s high-value outliers", len(high_value))
        return high_value

    def _detect_repeated_vendors(
        self, tx_objects: list[Transaction]
    ) -> list[dict[str, Any]]:
        """
        Detect vendors/companies with multiple transactions (2+).

        Groups all transactions by exact description, regardless of amount
        variance or date intervals. Useful for identifying all companies
        you've transacted with more than once.

        Args:
            tx_objects: List of Transaction domain objects

        Returns:
            List of vendor dicts with transaction details, sorted by total spent
        """
        # Group transactions by EXACT description
        groups: dict[str, list[Transaction]] = defaultdict(list)
        for tx in tx_objects:
            if tx.details:  # Only group non-empty descriptions
                groups[tx.details].append(tx)

        repeated = []
        for description, txs in groups.items():
            if len(txs) < 2:
                continue  # Need at least 2 transactions

            # Sort by date for chronological ordering
            try:
                txs_sorted = sorted(
                    txs,
                    key=lambda t: _date_parser_service.parse_transaction_date(t.date),
                )
            except (ValueError, TypeError) as e:
                logger.warning("Failed to sort transactions for %s: %s", description, e)
                txs_sorted = txs  # Use unsorted if date parsing fails

            # Extract all amounts
            amounts = []
            for tx in txs_sorted:
                amount = self._get_transaction_amount(tx)
                if amount is not None and amount > 0:
                    amounts.append(float(amount))

            if not amounts:
                continue  # Skip if no valid amounts

            total_spent = sum(amounts)

            repeated.append(
                {
                    "description": description,
                    "transaction_count": len(txs_sorted),
                    "total_spent": round(total_spent, 2),
                    "average_amount": round(total_spent / len(amounts), 2),
                    "min_amount": round(min(amounts), 2),
                    "max_amount": round(max(amounts), 2),
                    "transactions": [
                        {
                            "date": tx.date,
                            "amount": round(
                                float(self._get_transaction_amount(tx) or 0), 2
                            ),
                        }
                        for tx in txs_sorted
                    ],
                }
            )

        # Sort by total spent descending (most expensive vendors first)
        repeated.sort(key=lambda x: cast(float, x["total_spent"]), reverse=True)

        logger.info("Detected %s repeated vendors", len(repeated))
        return repeated

    def _calculate_statistics(self, tx_objects: list[Transaction]) -> dict[str, Any]:
        """
        Calculate basic statistics for transaction amounts.

        Args:
            tx_objects: List of Transaction domain objects

        Returns:
            Dictionary with mean, median, std_dev, totals
        """
        amounts = []
        total_debits = Decimal("0")
        total_credits = Decimal("0")

        for tx in tx_objects:
            amount = self._get_transaction_amount(tx)
            if amount is not None and amount > 0:
                amounts.append(float(amount))

                # Track debits and credits separately
                if tx.is_debit():
                    total_debits += amount
                elif tx.is_credit():
                    total_credits += amount

        if not amounts:
            return {
                "mean_transaction_amount": 0.0,
                "median_transaction_amount": 0.0,
                "std_dev": 0.0,
                "total_debits": 0.0,
                "total_credits": 0.0,
            }

        return {
            "mean_transaction_amount": round(statistics.mean(amounts), 2),
            "median_transaction_amount": round(statistics.median(amounts), 2),
            "std_dev": round(statistics.stdev(amounts), 2) if len(amounts) > 1 else 0.0,
            "total_debits": round(float(total_debits), 2),
            "total_credits": round(float(total_credits), 2),
        }

    def _group_similar_descriptions(
        self, tx_objects: list[Transaction]
    ) -> dict[str, list[Transaction]]:
        """
        Group transactions by normalized description.

        Args:
            tx_objects: List of Transaction domain objects

        Returns:
            Dictionary mapping normalized description to list of transactions
        """
        groups: dict[str, list[Transaction]] = defaultdict(list)

        for tx in tx_objects:
            normalized = self._normalize_description(tx.details)
            if normalized:  # Only group non-empty descriptions
                groups[normalized].append(tx)

        return groups

    def _normalize_description(self, description: str) -> str:
        """
        Normalize description for comparison.

        Converts to lowercase and strips whitespace for consistent matching.

        Args:
            description: Raw transaction description

        Returns:
            Normalized description string
        """
        if not description:
            return ""
        return description.lower().strip()

    def _get_transaction_amount(self, tx: Transaction) -> Decimal | None:
        """
        Extract transaction amount as Decimal.

        Handles both debit and credit transactions, returns absolute value.

        Args:
            tx: Transaction domain object

        Returns:
            Decimal amount or None if not parseable
        """
        try:
            if tx.is_debit() and tx.debit:
                amount_str = self._clean_amount_string(tx.debit)
                return abs(Decimal(amount_str))
            if tx.is_credit() and tx.credit:
                amount_str = self._clean_amount_string(tx.credit)
                return abs(Decimal(amount_str))
        except (InvalidOperation, ValueError, AttributeError):
            return None
        return None

    def _clean_amount_string(self, amount: str) -> str:
        """
        Clean amount string for Decimal conversion.

        Removes currency symbols, spaces, and other non-numeric characters.

        Args:
            amount: Amount string to clean

        Returns:
            Cleaned string suitable for Decimal conversion
        """
        if not amount:
            return "0"

        cleaned = strip_currency_symbols(amount).strip()
        return cleaned if cleaned else "0"

    def _empty_insights(self, error: str | None = None) -> dict[str, Any]:
        """
        Return empty insights structure for error cases.

        Args:
            error: Optional error message

        Returns:
            Empty insights dictionary
        """
        result: dict[str, Any] = {
            "summary": "Expense Analysis Report",
            "generated_at": datetime.now().isoformat(),
            "total_transactions_analyzed": 0,
            "insights": {
                "recurring_charges": [],
                "high_value_transactions": [],
                "repeated_vendors": [],
                "statistics": {},
            },
        }
        if error:
            result["error"] = error
        return result
