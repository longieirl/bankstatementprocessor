"""Monthly summary service for bank transactions.

This module provides a clean service interface for generating monthly
transaction summaries with debit/credit totals and counts.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from bankstatements_core.domain import Transaction, dicts_to_transactions
from bankstatements_core.domain.currency import strip_currency_symbols
from bankstatements_core.services.date_parser import DateParserService

logger = logging.getLogger(__name__)

_date_parser_service = DateParserService()


class MonthlySummaryService:
    """
    Service for generating monthly transaction summaries.

    Groups transactions by month and calculates monthly statistics
    including debit/credit totals and transaction counts.

    Note:
        Uses Transaction domain model internally for type-safe date handling
        and Decimal precision in financial calculations. Supports multiple
        debit/credit columns per transaction (e.g., "Debit €" and "Debit $").
    """

    def __init__(
        self,
        debit_columns: list[str],
        credit_columns: list[str],
        entitlements: Any = None,
    ):
        """
        Initialize monthly summary service.

        Args:
            debit_columns: List of column names containing debit amounts (ignored when using Transaction model)
            credit_columns: List of column names containing credit amounts (ignored when using Transaction model)
            entitlements: Optional entitlements for enforcement (None = no enforcement)

        Note:
            debit_columns and credit_columns are kept for backward compatibility but are not used
            when working with Transaction objects. The Transaction model has standard debit/credit fields.
        """
        self.debit_columns = debit_columns
        self.credit_columns = credit_columns
        self.entitlements = entitlements

    def generate(self, transactions: list[dict]) -> dict[str, Any]:
        """
        Generate monthly summary from transactions.

        Enforces entitlements if provided - monthly summaries are only
        available in PAID tier.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with monthly summaries containing:
            - summary: Description text
            - generated_at: ISO timestamp of generation
            - total_months: Number of months with transactions
            - monthly_data: List of monthly statistics

        Raises:
            EntitlementError: If monthly summary is not allowed for the tier

        Note:
            Uses Transaction domain model internally for type-safe date handling
            and Decimal precision, while supporting multiple debit/credit columns.
        """
        # Enforce entitlements at entry point (defense in depth)
        if self.entitlements is not None:
            self.entitlements.check_monthly_summary()
            logger.info("Monthly summary generation authorized")
        logger.info(
            "Generating monthly summary - Debit columns: %s, Credit columns: %s",
            self.debit_columns,
            self.credit_columns,
        )

        # Convert to domain objects at boundary for type-safe date access
        tx_objects = dicts_to_transactions(transactions)

        # Group transactions by month using domain objects for date, but original dicts for columns
        monthly_data = self._group_by_month(tx_objects, transactions)

        # Aggregate data for each month
        summary_data = self._aggregate_monthly_data(monthly_data)

        return {
            "summary": "Monthly Transaction Summary",
            "generated_at": datetime.now().isoformat(),
            "total_months": len(summary_data),
            "monthly_data": summary_data,
        }

    def _group_by_month(
        self, transactions: list[Transaction], original_dicts: list[dict]
    ) -> dict[str, dict[str, Any]]:
        """
        Group transactions by month using Transaction domain objects for dates,
        and original dicts for multi-column support.

        Args:
            transactions: List of Transaction domain objects (for type-safe date access)
            original_dicts: List of original transaction dicts (for multi-column access)

        Returns:
            Dictionary mapping month keys (YYYY-MM) to month data
        """
        monthly_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "debit_total": Decimal("0"),  # Use Decimal for precision
                "debit_count": 0,
                "credit_total": Decimal("0"),
                "credit_count": 0,
                "transactions": [],
            }
        )

        for tx, tx_dict in zip(transactions, original_dicts):
            # Use domain object's date field (type-safe)
            date_obj = _date_parser_service.parse_transaction_date(tx.date)

            # Format as YYYY-MM for grouping
            month_key = (
                date_obj.strftime("%Y-%m") if date_obj.year > 1970 else "Unknown"
            )

            monthly_data[month_key]["transactions"].append(tx)

            # Process all configured debit columns (multi-column support)
            for debit_col in self.debit_columns:
                if debit_col in tx_dict:
                    debit_value = tx_dict[debit_col]
                    if debit_value and str(debit_value).strip():
                        decimal_value = self._parse_amount(str(debit_value))
                        if decimal_value and decimal_value > 0:
                            monthly_data[month_key]["debit_total"] += decimal_value
                            monthly_data[month_key]["debit_count"] += 1

            # Process all configured credit columns (multi-column support)
            for credit_col in self.credit_columns:
                if credit_col in tx_dict:
                    credit_value = tx_dict[credit_col]
                    if credit_value and str(credit_value).strip():
                        decimal_value = self._parse_amount(str(credit_value))
                        if decimal_value and decimal_value > 0:
                            monthly_data[month_key]["credit_total"] += decimal_value
                            monthly_data[month_key]["credit_count"] += 1

        return monthly_data

    def _parse_amount(self, amount_str: str) -> Decimal | None:
        """
        Parse amount string to Decimal with currency handling.

        Args:
            amount_str: Amount string (may contain currency symbols, commas)

        Returns:
            Decimal value or None if parsing fails
        """
        try:
            cleaned = strip_currency_symbols(amount_str).strip()
            if cleaned:
                return Decimal(cleaned)
        except (ValueError, TypeError, ArithmeticError):
            return None
        return None

    def _aggregate_monthly_data(
        self, monthly_data: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Aggregate monthly data into summary format.

        Args:
            monthly_data: Dictionary mapping month keys to month data with Decimal totals

        Returns:
            List of monthly summary dictionaries sorted by month
        """
        summary_data = []
        for month, data in sorted(monthly_data.items()):
            # Convert Decimal to float and round for JSON serialization
            debit_total = float(data["debit_total"])
            credit_total = float(data["credit_total"])

            summary_data.append(
                {
                    "Month": month,
                    "Debit": round(debit_total, 2),
                    "Total Debit Transactions": data["debit_count"],
                    "Credit": round(credit_total, 2),
                    "Total Credit Transactions": data["credit_count"],
                }
            )

        return summary_data
