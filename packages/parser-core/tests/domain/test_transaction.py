"""Tests for Transaction domain model."""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankstatements_core.domain.models.extraction_warning import (
    CODE_DATE_PROPAGATED,
    ExtractionWarning,
)
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
            "Debit_AMT": "50.00",
            "Credit_AMT": None,
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


class TestTransactionEnrichmentFields:
    """Tests for TXEN-01 through TXEN-04: source_page, confidence_score, extraction_warnings."""

    # --- TXEN-01: source_page ---

    def test_source_page_defaults_to_none(self):
        """TXEN-01: Transaction() with no source_page → source_page is None."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        assert tx.source_page is None

    def test_source_page_can_be_set(self):
        """TXEN-01: Transaction(source_page=3) → source_page == 3."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            source_page=3,
        )
        assert tx.source_page == 3

    def test_to_dict_source_page_int_serialises_as_string(self):
        """TXEN-01: to_dict() with source_page=3 → result['source_page'] == '3'."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            source_page=3,
        )
        assert tx.to_dict()["source_page"] == "3"

    def test_to_dict_source_page_none_serialises_as_none(self):
        """TXEN-01: to_dict() with source_page=None → result['source_page'] is None."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        assert tx.to_dict()["source_page"] is None

    def test_from_dict_source_page_string_parses_to_int(self):
        """TXEN-01: from_dict({'source_page': '3', ...}) → source_page == 3 (int)."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Debit €": None,
                "Credit €": "10.00",
                "Balance €": "100.00",
                "Filename": "test.pdf",
                "source_page": "3",
            }
        )
        assert tx.source_page == 3
        assert isinstance(tx.source_page, int)

    def test_from_dict_source_page_absent_defaults_to_none(self):
        """TXEN-01: from_dict({}) (key absent) → source_page is None."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
            }
        )
        assert tx.source_page is None

    def test_source_page_roundtrip_with_value(self):
        """TXEN-01: from_dict(tx.to_dict()) where source_page=3 → source_page == 3."""
        original = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            source_page=3,
        )
        restored = Transaction.from_dict(original.to_dict())
        assert restored.source_page == 3

    def test_source_page_roundtrip_with_none(self):
        """TXEN-01: from_dict(tx.to_dict()) where source_page=None → source_page is None."""
        original = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        restored = Transaction.from_dict(original.to_dict())
        assert restored.source_page is None

    # --- TXEN-02: extraction_warnings ---

    def test_extraction_warnings_defaults_to_empty_list(self):
        """TXEN-02: Transaction() with no extraction_warnings → extraction_warnings == []."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        assert tx.extraction_warnings == []

    def test_extraction_warnings_can_be_set(self):
        """TXEN-02: Transaction(extraction_warnings=[ExtractionWarning(...)]) stores value."""
        w = ExtractionWarning(
            code=CODE_DATE_PROPAGATED,
            message="date propagated from previous row ('01 Jan 2024')",
        )
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            extraction_warnings=[w],
        )
        assert tx.extraction_warnings == [w]

    def test_extraction_warnings_no_shared_mutable_default(self):
        """TXEN-02: Two Transaction() instances have separate extraction_warnings lists."""
        tx1 = Transaction(
            date="01/01/2024",
            details="Test1",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        tx2 = Transaction(
            date="01/01/2024",
            details="Test2",
            debit=None,
            credit="20.00",
            balance="120.00",
            filename="test.pdf",
        )
        tx1.extraction_warnings.append(
            ExtractionWarning(code=CODE_DATE_PROPAGATED, message="test")
        )
        assert tx2.extraction_warnings == []

    def test_to_dict_extraction_warnings_serialises_as_json_string(self):
        """TXEN-02: to_dict() with an ExtractionWarning → JSON string of list of dicts."""
        w = ExtractionWarning(
            code=CODE_DATE_PROPAGATED,
            message="date propagated from previous row ('01 Jan 2024')",
        )
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            extraction_warnings=[w],
        )
        import json

        serialised = json.loads(tx.to_dict()["extraction_warnings"])
        assert serialised == [
            {
                "code": CODE_DATE_PROPAGATED,
                "message": "date propagated from previous row ('01 Jan 2024')",
                "page": None,
            }
        ]

    def test_to_dict_extraction_warnings_empty_serialises_as_json_array(self):
        """TXEN-02: to_dict() with extraction_warnings=[] → '[]'."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        assert tx.to_dict()["extraction_warnings"] == "[]"

    def test_from_dict_extraction_warnings_parses_json_string(self):
        """TXEN-02: from_dict with a JSON-encoded ExtractionWarning → list[ExtractionWarning]."""
        import json

        w = {
            "code": CODE_DATE_PROPAGATED,
            "message": "date propagated from previous row ('01 Jan 2024')",
            "page": None,
        }
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Filename": "test.pdf",
                "extraction_warnings": json.dumps([w]),
            }
        )
        assert len(tx.extraction_warnings) == 1
        assert isinstance(tx.extraction_warnings[0], ExtractionWarning)
        assert tx.extraction_warnings[0].code == CODE_DATE_PROPAGATED

    def test_from_dict_extraction_warnings_absent_defaults_to_empty_list(self):
        """TXEN-02: from_dict({}) (key absent) → extraction_warnings == []."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
            }
        )
        assert tx.extraction_warnings == []

    def test_extraction_warnings_roundtrip(self):
        """TXEN-02: from_dict(tx.to_dict()) preserves extraction_warnings."""
        w = ExtractionWarning(
            code=CODE_DATE_PROPAGATED,
            message="date propagated from previous row ('01 Jan 2024')",
        )
        original = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            extraction_warnings=[w],
        )
        restored = Transaction.from_dict(original.to_dict())
        assert len(restored.extraction_warnings) == 1
        assert restored.extraction_warnings[0].code == CODE_DATE_PROPAGATED
        assert restored.extraction_warnings[0].message == w.message

    def test_extraction_warnings_not_in_additional_fields(self):
        """TXEN-02: extraction_warnings JSON key is gated by standard_keys — not absorbed into additional_fields."""
        import json

        w = {"code": CODE_DATE_PROPAGATED, "message": "test", "page": None}
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Filename": "test.pdf",
                "extraction_warnings": json.dumps([w]),
            }
        )
        assert "extraction_warnings" not in tx.additional_fields

    # --- TXEN-03: confidence_score ---

    def test_confidence_score_defaults_to_one(self):
        """TXEN-03: Transaction() with no confidence_score → confidence_score == 1.0."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        assert tx.confidence_score == 1.0

    def test_confidence_score_can_be_set(self):
        """TXEN-03: Transaction(confidence_score=0.8) → confidence_score == 0.8."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            confidence_score=0.8,
        )
        assert tx.confidence_score == 0.8

    def test_to_dict_confidence_score_serialises_as_string(self):
        """TXEN-03: to_dict() with confidence_score=0.8 → result['confidence_score'] == '0.8'."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            confidence_score=0.8,
        )
        assert tx.to_dict()["confidence_score"] == "0.8"

    def test_from_dict_confidence_score_parses_to_float(self):
        """TXEN-03: from_dict({'confidence_score': '0.8', ...}) → confidence_score == 0.8 (float)."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Filename": "test.pdf",
                "confidence_score": "0.8",
            }
        )
        assert tx.confidence_score == 0.8
        assert isinstance(tx.confidence_score, float)

    def test_from_dict_confidence_score_absent_defaults_to_one(self):
        """TXEN-03: from_dict({}) (key absent) → confidence_score == 1.0."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
            }
        )
        assert tx.confidence_score == 1.0

    def test_confidence_score_roundtrip(self):
        """TXEN-03: from_dict(tx.to_dict()) where confidence_score=0.8 → 0.8."""
        original = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            confidence_score=0.8,
        )
        restored = Transaction.from_dict(original.to_dict())
        assert restored.confidence_score == 0.8

    # --- TXEN-04: standard_keys membership and full round-trip ---

    def test_source_page_in_standard_keys(self):
        """TXEN-04: 'source_page' is gated by standard_keys — not absorbed into additional_fields."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Filename": "test.pdf",
                "source_page": "5",
            }
        )
        assert "source_page" not in tx.additional_fields

    def test_confidence_score_in_standard_keys(self):
        """TXEN-04: 'confidence_score' is gated by standard_keys — not absorbed into additional_fields."""
        tx = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "Test",
                "Filename": "test.pdf",
                "confidence_score": "0.9",
            }
        )
        assert "confidence_score" not in tx.additional_fields

    def test_full_roundtrip_all_three_enrichment_fields(self):
        """TXEN-04: Full round-trip preserves source_page, confidence_score, and extraction_warnings."""
        original = Transaction(
            date="01/01/2024",
            details="Test roundtrip",
            debit="50.00",
            credit=None,
            balance="950.00",
            filename="statement.pdf",
            source_page=3,
            confidence_score=0.8,
            extraction_warnings=[
                ExtractionWarning(code=CODE_DATE_PROPAGATED, message="missing balance")
            ],
        )
        restored = Transaction.from_dict(original.to_dict())
        assert restored.source_page == 3
        assert restored.confidence_score == 0.8
        assert len(restored.extraction_warnings) == 1
        assert restored.extraction_warnings[0].code == CODE_DATE_PROPAGATED

    def test_backward_compat_old_dict_without_new_keys(self):
        """TXEN-04: Old dict without new keys → from_dict() succeeds with defaults."""
        old_data = {
            "Date": "01/12/2023",
            "Details": "TESCO STORES",
            "Debit €": "45.23",
            "Credit €": None,
            "Balance €": "1234.56",
            "Filename": "statement.pdf",
        }
        tx = Transaction.from_dict(old_data)
        assert tx.source_page is None
        assert tx.confidence_score == 1.0
        assert tx.extraction_warnings == []


class TestTransactionToDictCurrencySymbol:
    """Tests for to_dict() currency_symbol parameter (issue #62)."""

    def test_to_dict_with_pound_symbol(self):
        """to_dict() with currency_symbol='£' uses £ in column names."""
        tx = Transaction(
            date="01/01/2024",
            details="UK Store",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )
        d = tx.to_dict(currency_symbol="£")
        assert "Debit £" in d
        assert "Credit £" in d
        assert "Balance £" in d
        assert d["Debit £"] == "50.00"

    def test_to_dict_with_empty_symbol(self):
        """to_dict() with currency_symbol='' uses neutral column names."""
        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )
        d = tx.to_dict(currency_symbol="")
        assert "Debit" in d
        assert "Credit" in d
        assert "Balance" in d
        assert "Debit €" not in d
        assert d["Debit"] == "50.00"

    def test_from_dict_round_trips_pound(self):
        """from_dict() handles 'Debit £' keys produced by to_dict(currency_symbol='£')."""
        tx = Transaction(
            date="01/01/2024",
            details="UK Store",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf",
        )
        d = tx.to_dict(currency_symbol="£")
        tx2 = Transaction.from_dict(d)
        assert tx2.debit == "50.00"
        assert tx2.balance == "100.00"
