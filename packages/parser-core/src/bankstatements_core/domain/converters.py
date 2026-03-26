"""Converters between Transaction domain objects and dicts.

This module provides utility functions for converting between Transaction objects
and dictionary representations, enabling gradual migration to domain models.
"""

from __future__ import annotations

from bankstatements_core.domain.models.transaction import Transaction


def dicts_to_transactions(rows: list[dict]) -> list[Transaction]:
    """Convert list of dict rows to Transaction objects.

    Args:
        rows: List of transaction dictionaries

    Returns:
        List of Transaction objects

    Examples:
        >>> rows = [{"Date": "01/01/23", "Details": "Test", "Debit €": "50.00",
        ...          "Credit €": None, "Balance €": "100.00", "Filename": "test.pdf"}]
        >>> transactions = dicts_to_transactions(rows)
        >>> transactions[0].date
        '01/01/23'
    """
    return [Transaction.from_dict(row) for row in rows]


def transactions_to_dicts(transactions: list[Transaction]) -> list[dict]:
    """Convert list of Transaction objects to dicts.

    Args:
        transactions: List of Transaction objects

    Returns:
        List of dictionaries with standard column names

    Examples:
        >>> tx = Transaction(date="01/01/23", details="Test", debit="50.00",
        ...                  credit=None, balance="100.00", filename="test.pdf")
        >>> dicts = transactions_to_dicts([tx])
        >>> dicts[0]["Date"]
        '01/01/23'
    """
    return [tx.to_dict(currency_symbol="") for tx in transactions]


def dict_to_transaction(row: dict) -> Transaction:
    """Convert single dict row to Transaction object.

    Args:
        row: Transaction dictionary

    Returns:
        Transaction object

    Examples:
        >>> row = {"Date": "01/01/23", "Details": "Test", "Debit €": "50.00",
        ...        "Credit €": None, "Balance €": "100.00", "Filename": "test.pdf"}
        >>> tx = dict_to_transaction(row)
        >>> tx.is_debit()
        True
    """
    return Transaction.from_dict(row)


def transaction_to_dict(transaction: Transaction) -> dict:
    """Convert single Transaction object to dict.

    Args:
        transaction: Transaction object

    Returns:
        Dictionary with standard column names

    Examples:
        >>> tx = Transaction(date="01/01/23", details="Test", debit="50.00",
        ...                  credit=None, balance="100.00", filename="test.pdf")
        >>> row = transaction_to_dict(tx)
        >>> row["Debit"]
        '50.00'
    """
    return transaction.to_dict(currency_symbol="")
