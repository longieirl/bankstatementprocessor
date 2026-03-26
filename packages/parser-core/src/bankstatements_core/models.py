from __future__ import annotations

from typing import TypedDict


class TransactionRow(TypedDict):
    Date: str
    Details: str
    Debit_AMT: str | None  # Python-safe column name (currency-agnostic)
    Credit_AMT: str | None  # Python-safe column name (currency-agnostic)
    Balance_AMT: str | None  # Python-safe column name (currency-agnostic)
    Filename: str
    document_type: str  # Type of financial document: "bank_statement" | "credit_card_statement" | "loan_statement"
    transaction_type: str  # Type of transaction: "purchase" | "payment" | "fee" | "refund" | "transfer" | "interest" | "other"
