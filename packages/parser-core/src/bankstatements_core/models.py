from __future__ import annotations

from typing import TypedDict


class TransactionRow(TypedDict):
    Date: str
    Details: str
    Debit_EUR: str | None  # Changed from "Debit €"
    Credit_EUR: str | None  # Changed from "Credit €"
    Balance_EUR: str | None  # Changed from "Balance €"
    Filename: str
    document_type: str  # Type of financial document: "bank_statement" | "credit_card_statement" | "loan_statement"
    transaction_type: str  # Type of transaction: "purchase" | "payment" | "fee" | "refund" | "transfer" | "interest" | "other"
