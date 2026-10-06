"""Internal transfer detection across accounts.

Matches debit transactions in one account with credit transactions in another
account when the amounts are equal and the dates are within a configurable window.
Matched pairs are marked as internal_transfer and assigned a shared group ID.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from dateutil import parser as dateutil_parser

from bankstatements_core.domain.models.transaction import Transaction

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DATE_FORMATS = (
    "%d %b %Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d %B %Y",
    "%d/%m/%y",
)

_TransferCandidate = tuple[Transaction, date, Decimal]


def _parse_date(tx: Transaction) -> date | None:
    raw = tx.date.strip()
    if not raw:
        return None
    enriched = Transaction._enrich_date(raw, tx.additional_fields)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(enriched, fmt).date()
        except ValueError:
            continue
    try:
        return dateutil_parser.parse(enriched, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _group_id(tx_a: Transaction, tx_b: Transaction, amount: Decimal) -> str:
    key = "|".join([*sorted([tx_a.filename, tx_b.filename]), str(amount)])
    digest = hashlib.sha256(key.encode()).hexdigest()[:8].upper()
    return f"TXFER-{digest}"


def _best_credit_match(  # noqa: PLR0913
    tx_d: Transaction,
    date_d: date,
    amount_d: Decimal,
    credits: list[_TransferCandidate],
    used: set[int],
    window: timedelta,
) -> Transaction | None:
    best_tx_c: Transaction | None = None
    best_diff: timedelta = window + timedelta(days=1)
    for tx_c, date_c, amount_c in credits:
        if id(tx_c) in used:
            continue
        if tx_c.filename == tx_d.filename or amount_c != amount_d:
            continue
        diff = abs(date_c - date_d)
        if diff <= window and diff < best_diff:
            best_tx_c = tx_c
            best_diff = diff
    return best_tx_c


def _tag_pair(tx_d: Transaction, tx_c: Transaction, amount: Decimal) -> None:
    group = _group_id(tx_d, tx_c, amount)
    tx_d.transaction_type = "internal_transfer"
    tx_d.transfer_group_id = group
    tx_c.transaction_type = "internal_transfer"
    tx_c.transfer_group_id = group
    logger.info(
        "Transfer matched: %s in %s <-> %s, group %s",
        amount,
        tx_d.filename,
        tx_c.filename,
        group,
    )


class TransferDetectionService:
    """Detects internal transfers across accounts.

    Marks matched transaction pairs with transaction_type='internal_transfer'
    and a shared transfer_group_id so they can be identified and excluded from
    income/expense analysis.
    """

    def __init__(self, date_window_days: int = 3) -> None:
        self.date_window_days = date_window_days

    def detect_transfers(self, transactions: list[Transaction]) -> int:
        """Detect and tag internal transfers in-place.

        Args:
            transactions: Flat list of all transactions from all accounts.

        Returns:
            Number of matched pairs found.
        """
        window = timedelta(days=self.date_window_days)
        debits: list[_TransferCandidate] = []
        credits: list[_TransferCandidate] = []

        for tx in transactions:
            if tx.transaction_type == "internal_transfer":
                continue
            parsed = _parse_date(tx)
            if parsed is None:
                continue
            amount = tx.get_amount()
            if amount is None or amount == Decimal(0):
                continue
            if amount < 0:
                debits.append((tx, parsed, abs(amount)))
            else:
                credits.append((tx, parsed, amount))

        used: set[int] = set()
        pairs = 0
        for tx_d, date_d, amount_d in debits:
            if id(tx_d) in used:
                continue
            tx_c = _best_credit_match(tx_d, date_d, amount_d, credits, used, window)
            if tx_c is not None:
                _tag_pair(tx_d, tx_c, amount_d)
                used.add(id(tx_d))
                used.add(id(tx_c))
                pairs += 1

        if pairs:
            logger.info("Transfer detection: %s pair(s) found", pairs)
        return pairs
