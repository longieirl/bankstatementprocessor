"""Tests for domain converters."""

from bankstatements_core.domain.converters import (
    dict_to_transaction,
    dicts_to_transactions,
    transaction_to_dict,
    transactions_to_dicts,
)
from bankstatements_core.domain.models.transaction import Transaction


def test_dict_to_transaction():
    """Test converting single dict to Transaction."""
    row = {
        "Date": "01/01/23",
        "Details": "Test Transaction",
        "Debit €": "50.00",
        "Credit €": None,
        "Balance €": "100.00",
        "Filename": "test.pdf",
    }

    tx = dict_to_transaction(row)

    assert isinstance(tx, Transaction)
    assert tx.date == "01/01/23"
    assert tx.details == "Test Transaction"
    assert tx.debit == "50.00"
    assert tx.is_debit()


def test_transaction_to_dict():
    """Test converting single Transaction to dict."""
    tx = Transaction(
        date="01/01/23",
        details="Test Transaction",
        debit="50.00",
        credit=None,
        balance="100.00",
        filename="test.pdf",
    )

    row = transaction_to_dict(tx)

    assert isinstance(row, dict)
    assert row["Date"] == "01/01/23"
    assert row["Details"] == "Test Transaction"
    assert row["Debit €"] == "50.00"
    assert row["Credit €"] is None
    assert row["Balance €"] == "100.00"
    assert row["Filename"] == "test.pdf"


def test_dicts_to_transactions():
    """Test converting list of dicts to Transactions."""
    rows = [
        {
            "Date": "01/01/23",
            "Details": "Test 1",
            "Debit €": "50.00",
            "Credit €": None,
            "Balance €": "100.00",
            "Filename": "test.pdf",
        },
        {
            "Date": "02/01/23",
            "Details": "Test 2",
            "Debit €": None,
            "Credit €": "25.00",
            "Balance €": "125.00",
            "Filename": "test.pdf",
        },
    ]

    transactions = dicts_to_transactions(rows)

    assert len(transactions) == 2
    assert all(isinstance(tx, Transaction) for tx in transactions)
    assert transactions[0].date == "01/01/23"
    assert transactions[1].is_credit()


def test_transactions_to_dicts():
    """Test converting list of Transactions to dicts."""
    transactions = [
        Transaction(
            date="01/01/23",
            details="Test 1",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        ),
        Transaction(
            date="02/01/23",
            details="Test 2",
            debit=None,
            credit="25.00",
            balance="125.00",
            filename="test.pdf",
        ),
    ]

    rows = transactions_to_dicts(transactions)

    assert len(rows) == 2
    assert all(isinstance(row, dict) for row in rows)
    assert rows[0]["Date"] == "01/01/23"
    assert rows[1]["Credit €"] == "25.00"
