"""Tests for Transaction domain model."""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankstatements_core.domain.models.transaction import Transaction


class TestTransactionCreation:
    """Test Transaction creation and initialization."""

    def test_create_debit_transaction(self):
        """Test creating a debit transaction."""
        tx = Transaction(
            date="01/12/2023",
            details="TESCO STORES",
            debit="45.23",
            credit=None,
            balance="1234.56",
            filename="statement.pdf",
        )

        assert tx.date == "01/12/2023"
        assert tx.details == "TESCO STORES"
        assert tx.debit == "45.23"
        assert tx.credit is None
        assert tx.balance == "1234.56"
        assert tx.filename == "statement.pdf"

    def test_create_credit_transaction(self):
        """Test creating a credit transaction."""
        tx = Transaction(
            date="02/12/2023",
            details="SALARY PAYMENT",
            debit=None,
            credit="2500.00",
            balance="3734.56",
            filename="statement.pdf",
        )

        assert tx.is_credit()
        assert not tx.is_debit()

    def test_create_with_additional_fields(self):
        """Test creating transaction with additional bank-specific fields."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
            additional_fields={"Reference": "REF123", "Category": "Shopping"},
        )

        assert tx.additional_fields["Reference"] == "REF123"
        assert tx.additional_fields["Category"] == "Shopping"


class TestTransactionTypeChecking:
    """Test transaction type checking methods."""

    def test_is_debit(self):
        """Test is_debit() method."""
        tx = Transaction(
            date="01/12/2023",
            details="Purchase",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert tx.is_debit()
        assert not tx.is_credit()

    def test_is_credit(self):
        """Test is_credit() method."""
        tx = Transaction(
            date="01/12/2023",
            details="Deposit",
            debit=None,
            credit="500.00",
            balance="600.00",
            filename="test.pdf",
        )

        assert tx.is_credit()
        assert not tx.is_debit()

    def test_empty_debit_not_considered_debit(self):
        """Test that empty string debit is not considered a debit."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert not tx.is_debit()


class TestTransactionAmounts:
    """Test transaction amount handling."""

    def test_get_amount_debit(self):
        """Test get_amount() returns negative for debit."""
        tx = Transaction(
            date="01/12/2023",
            details="Purchase",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount == Decimal("-50.00")

    def test_get_amount_credit(self):
        """Test get_amount() returns positive for credit."""
        tx = Transaction(
            date="01/12/2023",
            details="Deposit",
            debit=None,
            credit="500.00",
            balance="600.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount == Decimal("500.00")

    def test_get_amount_with_currency_symbol(self):
        """Test get_amount() handles currency symbols."""
        tx = Transaction(
            date="01/12/2023",
            details="Purchase",
            debit="€50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount == Decimal("-50.00")

    def test_get_amount_with_comma_separator(self):
        """Test get_amount() handles comma thousand separators."""
        tx = Transaction(
            date="01/12/2023",
            details="Large purchase",
            debit="1,234.56",
            credit=None,
            balance="5000.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount == Decimal("-1234.56")

    def test_get_amount_invalid_returns_none(self):
        """Test get_amount() returns None for invalid amounts."""
        tx = Transaction(
            date="01/12/2023",
            details="Invalid",
            debit="not-a-number",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount is None

    def test_get_amount_no_amount_returns_none(self):
        """Test get_amount() returns None when no amount present."""
        tx = Transaction(
            date="01/12/2023",
            details="No amount",
            debit=None,
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        amount = tx.get_amount()
        assert amount is None


class TestTransactionBalance:
    """Test transaction balance handling."""

    def test_get_balance(self):
        """Test get_balance() returns Decimal."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="1234.56",
            filename="test.pdf",
        )

        balance = tx.get_balance()
        assert balance == Decimal("1234.56")

    def test_get_balance_with_currency_symbol(self):
        """Test get_balance() handles currency symbols."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="€1,234.56",
            filename="test.pdf",
        )

        balance = tx.get_balance()
        assert balance == Decimal("1234.56")

    def test_get_balance_none_returns_none(self):
        """Test get_balance() returns None for None balance."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance=None,
            filename="test.pdf",
        )

        balance = tx.get_balance()
        assert balance is None

    def test_get_balance_empty_string_returns_none(self):
        """Test get_balance() returns None for empty string."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="",
            filename="test.pdf",
        )

        balance = tx.get_balance()
        assert balance is None


class TestTransactionValidation:
    """Test transaction validation methods."""

    def test_has_valid_date(self):
        """Test has_valid_date() method."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert tx.has_valid_date()

    def test_has_valid_date_empty_returns_false(self):
        """Test has_valid_date() returns False for empty date."""
        tx = Transaction(
            date="",
            details="Test",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert not tx.has_valid_date()

    def test_has_valid_details(self):
        """Test has_valid_details() method."""
        tx = Transaction(
            date="01/12/2023",
            details="TESCO STORES",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert tx.has_valid_details()

    def test_has_valid_details_empty_returns_false(self):
        """Test has_valid_details() returns False for empty details."""
        tx = Transaction(
            date="01/12/2023",
            details="",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )

        assert not tx.has_valid_details()


class TestTransactionFromDict:
    """Test Transaction.from_dict() conversion."""

    def test_from_dict_standard_columns(self):
        """Test from_dict() with standard column names."""
        data = {
            "Date": "01/12/2023",
            "Details": "TESCO STORES",
            "Debit €": "45.23",
            "Credit €": None,
            "Balance €": "1234.56",
            "Filename": "statement.pdf",
        }

        tx = Transaction.from_dict(data)

        assert tx.date == "01/12/2023"
        assert tx.details == "TESCO STORES"
        assert tx.debit == "45.23"
        assert tx.credit is None
        assert tx.balance == "1234.56"
        assert tx.filename == "statement.pdf"

    def test_from_dict_alternative_column_names(self):
        """Test from_dict() handles alternative column naming."""
        data = {
            "Transaction Date": "01/12/2023",
            "Description": "Payment",
            "Debit_EUR": "50.00",
            "Credit_EUR": None,
            "Running Balance": "100.00",
            "source_pdf": "test.pdf",
        }

        tx = Transaction.from_dict(data)

        assert tx.date == "01/12/2023"
        assert tx.details == "Payment"
        assert tx.debit == "50.00"
        assert tx.filename == "test.pdf"

    def test_from_dict_with_additional_fields(self):
        """Test from_dict() captures additional fields."""
        data = {
            "Date": "01/12/2023",
            "Details": "Test",
            "Debit €": "50.00",
            "Credit €": None,
            "Balance €": "100.00",
            "Filename": "test.pdf",
            "Reference": "REF123",
            "Category": "Shopping",
        }

        tx = Transaction.from_dict(data)

        assert tx.additional_fields["Reference"] == "REF123"
        assert tx.additional_fields["Category"] == "Shopping"

    def test_from_dict_missing_fields_use_defaults(self):
        """Test from_dict() uses defaults for missing fields."""
        data = {"Date": "01/12/2023", "Details": "Test"}

        tx = Transaction.from_dict(data)

        assert tx.date == "01/12/2023"
        assert tx.details == "Test"
        assert tx.debit is None
        assert tx.credit is None
        assert tx.balance is None
        assert tx.filename == ""


class TestTransactionToDict:
    """Test Transaction.to_dict() conversion."""

    def test_to_dict(self):
        """Test to_dict() conversion."""
        tx = Transaction(
            date="01/12/2023",
            details="TESCO STORES",
            debit="45.23",
            credit=None,
            balance="1234.56",
            filename="statement.pdf",
        )

        result = tx.to_dict()

        assert result["Date"] == "01/12/2023"
        assert result["Details"] == "TESCO STORES"
        assert result["Debit €"] == "45.23"
        assert result["Credit €"] is None
        assert result["Balance €"] == "1234.56"
        assert result["Filename"] == "statement.pdf"

    def test_to_dict_with_additional_fields(self):
        """Test to_dict() includes additional fields."""
        tx = Transaction(
            date="01/12/2023",
            details="Test",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
            additional_fields={"Reference": "REF123"},
        )

        result = tx.to_dict()

        assert result["Reference"] == "REF123"

    def test_roundtrip_from_dict_to_dict(self):
        """Test roundtrip conversion from_dict() -> to_dict()."""
        original_data = {
            "Date": "01/12/2023",
            "Details": "TESCO STORES",
            "Debit €": "45.23",
            "Credit €": None,
            "Balance €": "1234.56",
            "Filename": "statement.pdf",
        }

        tx = Transaction.from_dict(original_data)
        result = tx.to_dict()

        assert result["Date"] == original_data["Date"]
        assert result["Details"] == original_data["Details"]
        assert result["Debit €"] == original_data["Debit €"]
        assert result["Balance €"] == original_data["Balance €"]


class TestTransactionRepr:
    """Test Transaction string representation."""

    def test_repr_debit(self):
        """Test __repr__() for debit transaction."""
        tx = Transaction(
            date="01/12/2023",
            details="TESCO STORES PURCHASE",
            debit="45.23",
            credit=None,
            balance="1234.56",
            filename="statement.pdf",
        )

        repr_str = repr(tx)

        assert "01/12/2023" in repr_str
        assert "TESCO STORES" in repr_str
        assert "Dr=45.23" in repr_str
        assert "1234.56" in repr_str

    def test_repr_credit(self):
        """Test __repr__() for credit transaction."""
        tx = Transaction(
            date="02/12/2023",
            details="SALARY PAYMENT",
            debit=None,
            credit="2500.00",
            balance="3734.56",
            filename="statement.pdf",
        )

        repr_str = repr(tx)

        assert "02/12/2023" in repr_str
        assert "Cr=2500.00" in repr_str
