"""Tests for ColumnTypeIdentifier class."""

from __future__ import annotations

from bankstatements_core.extraction.column_identifier import (
    ColumnType,
    ColumnTypeIdentifier,
)


class TestColumnTypeIdentify:
    """Tests for identify() method."""

    def test_identify_date_column(self):
        """Test identification of date columns."""
        assert ColumnTypeIdentifier.identify("Date") == ColumnType.DATE
        assert ColumnTypeIdentifier.identify("Transaction Date") == ColumnType.DATE
        assert ColumnTypeIdentifier.identify("time") == ColumnType.DATE
        assert ColumnTypeIdentifier.identify("When") == ColumnType.DATE

    def test_identify_description_column(self):
        """Test identification of description columns."""
        assert ColumnTypeIdentifier.identify("Details") == ColumnType.DESCRIPTION
        assert ColumnTypeIdentifier.identify("Description") == ColumnType.DESCRIPTION
        assert ColumnTypeIdentifier.identify("Memo") == ColumnType.DESCRIPTION
        assert ColumnTypeIdentifier.identify("Reference") == ColumnType.DESCRIPTION
        assert (
            ColumnTypeIdentifier.identify("Transaction Details")
            == ColumnType.DESCRIPTION
        )
        assert ColumnTypeIdentifier.identify("Desc") == ColumnType.DESCRIPTION

    def test_identify_debit_column(self):
        """Test identification of debit columns."""
        assert ColumnTypeIdentifier.identify("Debit €") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("Withdrawal") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("Out") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("Expense") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("Charge") == ColumnType.DEBIT

    def test_identify_credit_column(self):
        """Test identification of credit columns."""
        assert ColumnTypeIdentifier.identify("Credit €") == ColumnType.CREDIT
        assert ColumnTypeIdentifier.identify("Deposit") == ColumnType.CREDIT
        assert ColumnTypeIdentifier.identify("In") == ColumnType.CREDIT
        assert ColumnTypeIdentifier.identify("Income") == ColumnType.CREDIT
        assert ColumnTypeIdentifier.identify("Payment") == ColumnType.CREDIT

    def test_identify_balance_column(self):
        """Test identification of balance columns."""
        assert ColumnTypeIdentifier.identify("Balance €") == ColumnType.BALANCE
        assert ColumnTypeIdentifier.identify("Total") == ColumnType.BALANCE
        assert ColumnTypeIdentifier.identify("Amount") == ColumnType.BALANCE
        assert ColumnTypeIdentifier.identify("Sum") == ColumnType.BALANCE

    def test_identify_other_column(self):
        """Test identification of unknown columns."""
        assert ColumnTypeIdentifier.identify("Unknown") == ColumnType.OTHER
        assert ColumnTypeIdentifier.identify("Custom Field") == ColumnType.OTHER
        assert ColumnTypeIdentifier.identify("XYZ") == ColumnType.OTHER

    def test_identify_case_insensitive(self):
        """Test that identification is case-insensitive."""
        assert ColumnTypeIdentifier.identify("DATE") == ColumnType.DATE
        assert ColumnTypeIdentifier.identify("DeBit €") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("BALANCE") == ColumnType.BALANCE
        assert ColumnTypeIdentifier.identify("description") == ColumnType.DESCRIPTION

    def test_identify_with_special_characters(self):
        """Test identification with special characters and currency symbols."""
        assert ColumnTypeIdentifier.identify("Debit €") == ColumnType.DEBIT
        assert ColumnTypeIdentifier.identify("Credit $") == ColumnType.CREDIT
        assert ColumnTypeIdentifier.identify("Balance (USD)") == ColumnType.BALANCE


class TestGetColumnsByType:
    """Tests for get_columns_by_type() method."""

    def test_get_date_columns(self):
        """Test getting all date columns."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit €": (200, 250),
            "Credit €": (250, 300),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.DATE)
        assert result == ["Date"]

    def test_get_description_columns(self):
        """Test getting all description columns."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit €": (200, 250),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(
            columns, ColumnType.DESCRIPTION
        )
        assert result == ["Details"]

    def test_get_debit_columns(self):
        """Test getting all debit columns."""
        columns = {
            "Date": (0, 50),
            "Debit €": (200, 250),
            "Withdrawal": (250, 300),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.DEBIT)
        assert set(result) == {"Debit €", "Withdrawal"}

    def test_get_credit_columns(self):
        """Test getting all credit columns."""
        columns = {
            "Date": (0, 50),
            "Credit €": (200, 250),
            "Deposit": (250, 300),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.CREDIT)
        assert set(result) == {"Credit €", "Deposit"}

    def test_get_balance_columns(self):
        """Test getting all balance columns."""
        columns = {
            "Date": (0, 50),
            "Balance €": (200, 250),
            "Total": (250, 300),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.BALANCE)
        assert set(result) == {"Balance €", "Total"}

    def test_get_columns_empty_result(self):
        """Test getting columns when none match the type."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.DEBIT)
        assert result == []

    def test_get_columns_empty_input(self):
        """Test getting columns from empty column dict."""
        columns = {}
        result = ColumnTypeIdentifier.get_columns_by_type(columns, ColumnType.DATE)
        assert result == []


class TestHasType:
    """Tests for has_type() method."""

    def test_has_type_single_requirement_present(self):
        """Test checking for single required type that is present."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        assert ColumnTypeIdentifier.has_type(columns, {ColumnType.DATE})

    def test_has_type_single_requirement_absent(self):
        """Test checking for single required type that is absent."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        assert not ColumnTypeIdentifier.has_type(columns, {ColumnType.DEBIT})

    def test_has_type_multiple_requirements_all_present(self):
        """Test checking for multiple required types that are all present."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit €": (200, 250),
            "Balance €": (250, 300),
        }
        assert ColumnTypeIdentifier.has_type(
            columns, {ColumnType.DATE, ColumnType.DEBIT, ColumnType.BALANCE}
        )

    def test_has_type_multiple_requirements_some_missing(self):
        """Test checking for multiple required types with some missing."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        assert not ColumnTypeIdentifier.has_type(
            columns, {ColumnType.DATE, ColumnType.DEBIT}
        )

    def test_has_type_empty_requirements(self):
        """Test checking with empty requirements set."""
        columns = {
            "Date": (0, 50),
        }
        assert ColumnTypeIdentifier.has_type(columns, set())

    def test_has_type_empty_columns(self):
        """Test checking with empty columns dict."""
        columns = {}
        assert not ColumnTypeIdentifier.has_type(columns, {ColumnType.DATE})

    def test_has_type_multiple_columns_same_type(self):
        """Test that multiple columns of same type satisfy single requirement."""
        columns = {
            "Debit €": (0, 50),
            "Withdrawal": (50, 100),
            "Charge": (100, 150),
        }
        # Should satisfy debit requirement even with multiple debit columns
        assert ColumnTypeIdentifier.has_type(columns, {ColumnType.DEBIT})


class TestGetTypeAsString:
    """Tests for get_type_as_string() method (backward compatibility)."""

    def test_get_type_as_string_date(self):
        """Test string representation for date column."""
        assert ColumnTypeIdentifier.get_type_as_string("Date") == "date"

    def test_get_type_as_string_description(self):
        """Test string representation for description column."""
        assert ColumnTypeIdentifier.get_type_as_string("Details") == "description"

    def test_get_type_as_string_debit(self):
        """Test string representation for debit column."""
        assert ColumnTypeIdentifier.get_type_as_string("Debit €") == "debit"

    def test_get_type_as_string_credit(self):
        """Test string representation for credit column."""
        assert ColumnTypeIdentifier.get_type_as_string("Credit €") == "credit"

    def test_get_type_as_string_balance(self):
        """Test string representation for balance column."""
        assert ColumnTypeIdentifier.get_type_as_string("Balance €") == "balance"

    def test_get_type_as_string_other(self):
        """Test string representation for unknown column."""
        assert ColumnTypeIdentifier.get_type_as_string("Unknown") == "other"


class TestColumnTypeEnum:
    """Tests for ColumnType enum."""

    def test_enum_values(self):
        """Test that enum has correct values."""
        assert ColumnType.DATE.value == "date"
        assert ColumnType.DESCRIPTION.value == "description"
        assert ColumnType.DEBIT.value == "debit"
        assert ColumnType.CREDIT.value == "credit"
        assert ColumnType.BALANCE.value == "balance"
        assert ColumnType.OTHER.value == "other"

    def test_enum_comparison(self):
        """Test enum comparison works correctly."""
        assert ColumnType.DATE == ColumnType.DATE
        assert ColumnType.DATE != ColumnType.DESCRIPTION
        assert ColumnType.DEBIT != ColumnType.CREDIT


class TestFindFirstColumnOfType:
    """Tests for find_first_column_of_type helper method."""

    def test_find_first_description_column(self):
        """Test finding first description column."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit €": (200, 250),
        }
        result = ColumnTypeIdentifier.find_first_column_of_type(columns, "description")
        assert result == "Details"

    def test_find_first_when_multiple_exist(self):
        """Test that it returns first match when multiple columns match."""
        columns = {
            "Debit €": (0, 50),
            "Debit USD": (50, 100),
            "Credit €": (100, 150),
        }
        result = ColumnTypeIdentifier.find_first_column_of_type(columns, "debit")
        assert result in ["Debit €", "Debit USD"]

    def test_find_first_when_none_exist(self):
        """Test that it returns None when no columns match."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        result = ColumnTypeIdentifier.find_first_column_of_type(columns, "credit")
        assert result is None

    def test_find_first_with_empty_columns(self):
        """Test with empty columns dictionary."""
        result = ColumnTypeIdentifier.find_first_column_of_type({}, "debit")
        assert result is None


class TestFindAllColumnsOfType:
    """Tests for find_all_columns_of_type helper method."""

    def test_find_all_debit_columns(self):
        """Test finding all debit columns."""
        columns = {
            "Debit €": (0, 50),
            "Debit USD": (50, 100),
            "Credit €": (100, 150),
        }
        result = ColumnTypeIdentifier.find_all_columns_of_type(columns, "debit")
        assert len(result) == 2
        assert "Debit €" in result
        assert "Debit USD" in result

    def test_find_all_when_none_exist(self):
        """Test that it returns empty list when no columns match."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
        }
        result = ColumnTypeIdentifier.find_all_columns_of_type(columns, "balance")
        assert result == []

    def test_find_all_with_single_match(self):
        """Test finding single matching column."""
        columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Balance": (200, 250),
        }
        result = ColumnTypeIdentifier.find_all_columns_of_type(columns, "balance")
        assert result == ["Balance"]

    def test_find_all_with_empty_columns(self):
        """Test with empty columns dictionary."""
        result = ColumnTypeIdentifier.find_all_columns_of_type({}, "debit")
        assert result == []
