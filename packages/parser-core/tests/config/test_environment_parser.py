"""Tests for EnvironmentParser class."""

from __future__ import annotations

import json
import os

import pytest

from bankstatements_core.config.environment_parser import EnvironmentParser


class TestParseFloat:
    """Tests for parse_float method."""

    def test_parse_valid_float(self, monkeypatch):
        """Test parsing a valid float value."""
        monkeypatch.setenv("TEST_FLOAT", "0.75")
        assert EnvironmentParser.parse_float("TEST_FLOAT", 0.5) == 0.75

    def test_parse_float_missing_uses_default(self, monkeypatch):
        """Test that missing variable returns default."""
        monkeypatch.delenv("TEST_FLOAT", raising=False)
        assert EnvironmentParser.parse_float("TEST_FLOAT", 0.5) == 0.5

    def test_parse_float_invalid_uses_default(self, monkeypatch):
        """Test that invalid float returns default."""
        monkeypatch.setenv("TEST_FLOAT", "not_a_float")
        assert EnvironmentParser.parse_float("TEST_FLOAT", 0.5) == 0.5

    def test_parse_float_integer_value(self, monkeypatch):
        """Test parsing an integer as float."""
        monkeypatch.setenv("TEST_FLOAT", "5")
        assert EnvironmentParser.parse_float("TEST_FLOAT", 0.5) == 5.0

    def test_parse_float_negative_value(self, monkeypatch):
        """Test parsing negative float."""
        monkeypatch.setenv("TEST_FLOAT", "-3.14")
        assert EnvironmentParser.parse_float("TEST_FLOAT", 0.0) == -3.14

    def test_parse_float_zero(self, monkeypatch):
        """Test parsing zero."""
        monkeypatch.setenv("TEST_FLOAT", "0.0")
        assert EnvironmentParser.parse_float("TEST_FLOAT", 1.0) == 0.0


class TestParseInt:
    """Tests for parse_int method."""

    def test_parse_valid_int(self, monkeypatch):
        """Test parsing a valid integer value."""
        monkeypatch.setenv("TEST_INT", "300")
        assert EnvironmentParser.parse_int("TEST_INT", 0) == 300

    def test_parse_int_missing_uses_default(self, monkeypatch):
        """Test that missing variable returns default."""
        monkeypatch.delenv("TEST_INT", raising=False)
        assert EnvironmentParser.parse_int("TEST_INT", 100) == 100

    def test_parse_int_invalid_raises_error(self, monkeypatch):
        """Test that invalid integer raises ValueError."""
        monkeypatch.setenv("TEST_INT", "not_an_int")
        with pytest.raises(ValueError, match="TEST_INT must be an integer"):
            EnvironmentParser.parse_int("TEST_INT", 0)

    def test_parse_int_float_raises_error(self, monkeypatch):
        """Test that float value raises ValueError."""
        monkeypatch.setenv("TEST_INT", "3.14")
        with pytest.raises(ValueError, match="TEST_INT must be an integer"):
            EnvironmentParser.parse_int("TEST_INT", 0)

    def test_parse_int_negative_value(self, monkeypatch):
        """Test parsing negative integer."""
        monkeypatch.setenv("TEST_INT", "-42")
        assert EnvironmentParser.parse_int("TEST_INT", 0) == -42

    def test_parse_int_zero(self, monkeypatch):
        """Test parsing zero."""
        monkeypatch.setenv("TEST_INT", "0")
        assert EnvironmentParser.parse_int("TEST_INT", 100) == 0


class TestParseBool:
    """Tests for parse_bool method."""

    def test_parse_bool_true_lowercase(self, monkeypatch):
        """Test parsing 'true' as True."""
        monkeypatch.setenv("TEST_BOOL", "true")
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is True

    def test_parse_bool_true_uppercase(self, monkeypatch):
        """Test parsing 'True' as True."""
        monkeypatch.setenv("TEST_BOOL", "True")
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is True

    def test_parse_bool_true_mixed_case(self, monkeypatch):
        """Test parsing 'TrUe' as True."""
        monkeypatch.setenv("TEST_BOOL", "TrUe")
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is True

    def test_parse_bool_false_lowercase(self, monkeypatch):
        """Test parsing 'false' as False."""
        monkeypatch.setenv("TEST_BOOL", "false")
        assert EnvironmentParser.parse_bool("TEST_BOOL", True) is False

    def test_parse_bool_false_uppercase(self, monkeypatch):
        """Test parsing 'False' as False."""
        monkeypatch.setenv("TEST_BOOL", "False")
        assert EnvironmentParser.parse_bool("TEST_BOOL", True) is False

    def test_parse_bool_missing_uses_default_false(self, monkeypatch):
        """Test that missing variable returns default (False)."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is False

    def test_parse_bool_missing_uses_default_true(self, monkeypatch):
        """Test that missing variable returns default (True)."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert EnvironmentParser.parse_bool("TEST_BOOL", True) is True

    def test_parse_bool_invalid_value_returns_false(self, monkeypatch):
        """Test that any non-'true' value returns False."""
        monkeypatch.setenv("TEST_BOOL", "yes")
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is False

    def test_parse_bool_one_returns_false(self, monkeypatch):
        """Test that '1' is treated as False (not 'true')."""
        monkeypatch.setenv("TEST_BOOL", "1")
        assert EnvironmentParser.parse_bool("TEST_BOOL", False) is False


class TestParseJsonList:
    """Tests for parse_json_list method."""

    def test_parse_valid_json_list(self, monkeypatch):
        """Test parsing a valid JSON list."""
        monkeypatch.setenv("TEST_JSON", '["item1", "item2", "item3"]')
        result = EnvironmentParser.parse_json_list("TEST_JSON", [])
        assert result == ["item1", "item2", "item3"]

    def test_parse_json_list_missing_uses_default(self, monkeypatch):
        """Test that missing variable returns default."""
        monkeypatch.delenv("TEST_JSON", raising=False)
        result = EnvironmentParser.parse_json_list("TEST_JSON", ["default"])
        assert result == ["default"]

    def test_parse_json_list_invalid_json_uses_default(self, monkeypatch):
        """Test that invalid JSON returns default."""
        monkeypatch.setenv("TEST_JSON", "not valid json")
        result = EnvironmentParser.parse_json_list("TEST_JSON", ["default"])
        assert result == ["default"]

    def test_parse_json_list_not_list_uses_default(self, monkeypatch):
        """Test that non-list JSON returns default."""
        monkeypatch.setenv("TEST_JSON", '{"key": "value"}')
        result = EnvironmentParser.parse_json_list("TEST_JSON", ["default"])
        assert result == ["default"]

    def test_parse_json_list_empty_list(self, monkeypatch):
        """Test parsing an empty JSON list."""
        monkeypatch.setenv("TEST_JSON", "[]")
        result = EnvironmentParser.parse_json_list("TEST_JSON", ["default"])
        assert result == []

    def test_parse_json_list_with_numbers(self, monkeypatch):
        """Test parsing a JSON list with numbers."""
        monkeypatch.setenv("TEST_JSON", "[1, 2, 3]")
        result = EnvironmentParser.parse_json_list("TEST_JSON", [])
        assert result == [1, 2, 3]

    def test_parse_json_list_with_mixed_types(self, monkeypatch):
        """Test parsing a JSON list with mixed types."""
        monkeypatch.setenv("TEST_JSON", '["string", 42, true, null]')
        result = EnvironmentParser.parse_json_list("TEST_JSON", [])
        assert result == ["string", 42, True, None]


class TestParseCsvList:
    """Tests for parse_csv_list method."""

    def test_parse_valid_csv_list(self, monkeypatch):
        """Test parsing a valid CSV list."""
        monkeypatch.setenv("TEST_CSV", "debit, credit, balance")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", [])
        assert result == ["debit", "credit", "balance"]

    def test_parse_csv_list_no_spaces(self, monkeypatch):
        """Test parsing CSV list without spaces."""
        monkeypatch.setenv("TEST_CSV", "debit,credit,balance")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", [])
        assert result == ["debit", "credit", "balance"]

    def test_parse_csv_list_missing_uses_default(self, monkeypatch):
        """Test that missing variable returns default."""
        monkeypatch.delenv("TEST_CSV", raising=False)
        result = EnvironmentParser.parse_csv_list("TEST_CSV", ["default"])
        assert result == ["default"]

    def test_parse_csv_list_empty_string_uses_default(self, monkeypatch):
        """Test that empty string returns default."""
        monkeypatch.setenv("TEST_CSV", "")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", ["default"])
        assert result == ["default"]

    def test_parse_csv_list_whitespace_only_uses_default(self, monkeypatch):
        """Test that whitespace-only string returns default."""
        monkeypatch.setenv("TEST_CSV", "   ")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", ["default"])
        assert result == ["default"]

    def test_parse_csv_list_filters_empty_items(self, monkeypatch):
        """Test that empty items are filtered out."""
        monkeypatch.setenv("TEST_CSV", "debit,  ,credit, , balance")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", [])
        assert result == ["debit", "credit", "balance"]

    def test_parse_csv_list_single_item(self, monkeypatch):
        """Test parsing CSV list with single item."""
        monkeypatch.setenv("TEST_CSV", "debit")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", [])
        assert result == ["debit"]

    def test_parse_csv_list_default_none(self, monkeypatch):
        """Test that default=None results in empty list."""
        monkeypatch.delenv("TEST_CSV", raising=False)
        result = EnvironmentParser.parse_csv_list("TEST_CSV")
        assert result == []

    def test_parse_csv_list_preserves_case(self, monkeypatch):
        """Test that case is preserved in items."""
        monkeypatch.setenv("TEST_CSV", "Debit, CREDIT, Balance")
        result = EnvironmentParser.parse_csv_list("TEST_CSV", [])
        assert result == ["Debit", "CREDIT", "Balance"]
