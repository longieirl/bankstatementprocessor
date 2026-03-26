"""Tests for credit card aware duplicate detection strategy."""

from __future__ import annotations

import pytest

from bankstatements_core.patterns.strategies import CreditCardDuplicateStrategy


class TestCreditCardDuplicateStrategy:
    """Test credit card duplicate detection strategy."""

    def test_same_transaction_type_amount_date_detected_as_duplicate(self):
        """Should detect duplicates when date, type, and amount match."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO STORES",
                "Debit_AMT": "45.23",
                "Filename": "card1.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO SUPERMARKET",  # Different description
                "Debit_AMT": "45.23",
                "Filename": "card2.pdf",
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        assert len(unique) == 1
        assert len(duplicates) == 1
        assert duplicates[0]["Filename"] == "card2.pdf"

    def test_different_transaction_types_not_duplicate(self):
        """Should NOT treat purchase and payment with same amount as duplicates."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO STORES",
                "Debit_AMT": "50.00",
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "PAYMENT RECEIVED",
                "Credit_AMT": "50.00",
                "Filename": "card.pdf",
                "transaction_type": "payment",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_same_amount_different_dates_not_duplicate(self):
        """Should NOT treat same amount on different dates as duplicate."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO",
                "Debit_AMT": "45.23",
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "02/12/2023",  # Different date
                "Details": "POS TESCO",
                "Debit_AMT": "45.23",
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_description_variations_allowed(self):
        """Should ignore description variations (focus on date/type/amount)."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "TESCO STORE 123",
                "Debit_AMT": "45.23",
                "Filename": "card1.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "TESCO STORES LTD",  # Different merchant description
                "Debit_AMT": "45.23",
                "Filename": "card2.pdf",
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Should be detected as duplicate despite different descriptions
        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_multiple_small_purchases_same_day_not_duplicate(self):
        """Should allow multiple small purchases with same amount on same day."""
        strategy = CreditCardDuplicateStrategy()

        # Scenario: Two different coffee purchases on same day, same amount
        # These should NOT be duplicates (common scenario)
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "COFFEE SHOP A",
                "Debit_AMT": "4.50",
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "COFFEE SHOP B",
                "Debit_AMT": "4.50",
                "Filename": "card.pdf",  # Same file
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Same file = not duplicate (within-file duplicates are kept)
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_cross_file_duplicate_detection(self):
        """Should detect duplicates across different files."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "POS AMAZON",
                "Debit_AMT": "99.99",
                "Filename": "statement_nov.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "AMAZON PURCHASE",
                "Debit_AMT": "99.99",
                "Filename": "statement_dec.pdf",  # Different file
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        assert len(unique) == 1
        assert len(duplicates) == 1
        assert duplicates[0]["Filename"] == "statement_dec.pdf"

    def test_same_file_not_marked_duplicate(self):
        """Should NOT mark transactions from same file as duplicates."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "TRANSACTION 1",
                "Debit_AMT": "50.00",
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "TRANSACTION 2",
                "Debit_AMT": "50.00",
                "Filename": "card.pdf",  # Same file
                "transaction_type": "purchase",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Both kept as unique (same file)
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_handles_missing_transaction_type(self):
        """Should gracefully handle missing transaction_type field."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "PURCHASE",
                "Debit_AMT": "50.00",
                "Filename": "card1.pdf",
                # Missing transaction_type
            },
            {
                "Date": "01/12/2023",
                "Details": "PURCHASE",
                "Debit_AMT": "50.00",
                "Filename": "card2.pdf",
                # Missing transaction_type
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Should still detect as duplicate (defaults to "other")
        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_credit_amount_handled_correctly(self):
        """Should handle credit amounts (refunds/payments)."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "05/12/2023",
                "Details": "REFUND",
                "Credit_AMT": "25.00",  # Credit, not Debit
                "Filename": "card1.pdf",
                "transaction_type": "refund",
            },
            {
                "Date": "05/12/2023",
                "Details": "REFUND PROCESSED",
                "Credit_AMT": "25.00",
                "Filename": "card2.pdf",
                "transaction_type": "refund",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_debit_and_credit_same_amount_not_duplicate(self):
        """Should NOT match debit and credit of same amount."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "PURCHASE",
                "Debit_AMT": "50.00",
                "Credit_AMT": None,
                "Filename": "card.pdf",
                "transaction_type": "purchase",
            },
            {
                "Date": "01/12/2023",
                "Details": "REFUND",
                "Debit_AMT": None,
                "Credit_AMT": "50.00",
                "Filename": "card.pdf",
                "transaction_type": "refund",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Different transaction types = not duplicate
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_zero_amount_transactions(self):
        """Should handle zero amount transactions."""
        strategy = CreditCardDuplicateStrategy()

        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "AUTHORIZATION HOLD",
                "Debit_AMT": None,
                "Credit_AMT": None,
                "Filename": "card1.pdf",
                "transaction_type": "other",
            },
            {
                "Date": "01/12/2023",
                "Details": "AUTHORIZATION HOLD",
                "Debit_AMT": None,
                "Credit_AMT": None,
                "Filename": "card2.pdf",
                "transaction_type": "other",
            },
        ]

        unique, duplicates = strategy.detect_duplicates(transactions)

        # Same date, type, and amount (0.00) = duplicate
        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_create_key_format(self):
        """Should create key in format: date:transaction_type:amount."""
        strategy = CreditCardDuplicateStrategy()

        transaction = {
            "Date": "01/12/2023",
            "Details": "POS TESCO",
            "Debit_AMT": "45.23",
            "transaction_type": "purchase",
        }

        key = strategy.create_key(transaction)

        assert key == "01/12/2023:purchase:45.23"

    def test_create_key_handles_missing_transaction_type(self):
        """Should use 'other' when transaction_type is missing."""
        strategy = CreditCardDuplicateStrategy()

        transaction = {
            "Date": "01/12/2023",
            "Details": "UNKNOWN",
            "Debit_AMT": "10.00",
        }

        key = strategy.create_key(transaction)

        assert key == "01/12/2023:other:10.00"

    def test_create_key_prefers_debit_over_credit(self):
        """Should use Debit amount when both Debit and Credit exist."""
        strategy = CreditCardDuplicateStrategy()

        transaction = {
            "Date": "01/12/2023",
            "Details": "TRANSACTION",
            "Debit_AMT": "50.00",
            "Credit_AMT": "25.00",  # Both present
            "transaction_type": "purchase",
        }

        key = strategy.create_key(transaction)

        # Should use Debit (50.00), not Credit
        assert key == "01/12/2023:purchase:50.00"
