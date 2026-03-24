"""Domain layer for bank statement processing.

This package contains domain models and business logic, separated from
infrastructure concerns like PDF extraction and file I/O.
"""

from __future__ import annotations

from bankstatements_core.domain.converters import (
    dict_to_transaction,
    dicts_to_transactions,
    transaction_to_dict,
    transactions_to_dicts,
)
from bankstatements_core.domain.models.extraction_result import ExtractionResult
from bankstatements_core.domain.models.transaction import Transaction

__all__ = [
    "Transaction",
    "ExtractionResult",
    "dict_to_transaction",
    "dicts_to_transactions",
    "transaction_to_dict",
    "transactions_to_dicts",
]
