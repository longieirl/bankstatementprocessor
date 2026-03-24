"""Tests for RowBuilder."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bankstatements_core.extraction.row_builder import RowBuilder

TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


def _make_classifier(side_effect=None, return_value="transaction"):
    classifier = Mock()
    if side_effect:
        classifier.classify.side_effect = side_effect
    else:
        classifier.classify.return_value = return_value
    return classifier


class TestRowBuilder:
    def test_transaction_row_returned(self):
        classifier = _make_classifier(return_value="transaction")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        words = [
            {"text": "01/01", "x0": 5, "x1": 40, "top": 320},
            {"text": "Tesco", "x0": 60, "x1": 110, "top": 320},
            {"text": "12.50", "x0": 210, "x1": 245, "top": 320},
        ]
        rows = builder.build_rows(words)
        assert len(rows) == 1
        assert rows[0]["Date"] == "01/01"
        assert rows[0]["Details"] == "Tesco"

    def test_metadata_row_excluded(self):
        classifier = _make_classifier(return_value="metadata")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        words = [{"text": "Some footer", "x0": 60, "x1": 150, "top": 320}]
        rows = builder.build_rows(words)
        assert rows == []

    def test_continuation_row_included(self):
        classifier = _make_classifier(return_value="continuation")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        words = [{"text": "continued desc", "x0": 60, "x1": 180, "top": 325}]
        rows = builder.build_rows(words)
        assert len(rows) == 1

    def test_only_transactions_returned_mixed(self):
        def classify(row, cols):
            return "transaction" if row.get("Details") else "metadata"

        classifier = _make_classifier(side_effect=classify)
        builder = RowBuilder(TEST_COLUMNS, classifier)
        # Row at y=320 has Details → transaction; row at y=400 has no Details → metadata
        words = [
            {"text": "Tesco", "x0": 60, "x1": 110, "top": 320},
            {
                "text": "NoDetails",
                "x0": 5,
                "x1": 40,
                "top": 400,
            },  # lands in Date column only
        ]
        rows = builder.build_rows(words)
        assert len(rows) == 1
        assert rows[0]["Details"] == "Tesco"

    def test_rightmost_column_strict_boundary(self):
        """Word that starts inside rightmost column but extends beyond should be excluded."""
        classifier = _make_classifier(return_value="transaction")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        # x1=360 exceeds Balance € xmax=350 → strict check fails
        words = [
            {"text": "Tesco", "x0": 60, "x1": 110, "top": 320},
            {"text": "1234.56", "x0": 305, "x1": 360, "top": 320},  # bleeds past 350
        ]
        rows = builder.build_rows(words)
        assert len(rows) == 1
        assert rows[0]["Balance €"] == ""  # strict boundary rejected it

    def test_rightmost_column_strict_boundary_accepts_contained_word(self):
        """Word fully contained within rightmost column should be accepted."""
        classifier = _make_classifier(return_value="transaction")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        words = [
            {"text": "Tesco", "x0": 60, "x1": 110, "top": 320},
            {"text": "100.00", "x0": 305, "x1": 345, "top": 320},  # within 300–350
        ]
        rows = builder.build_rows(words)
        assert rows[0]["Balance €"] == "100.00"

    def test_words_grouped_by_y(self):
        classifier = _make_classifier(return_value="transaction")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        words = [
            {"text": "01/01", "x0": 5, "x1": 40, "top": 320},
            {"text": "Tesco", "x0": 60, "x1": 110, "top": 320},
            {"text": "02/01", "x0": 5, "x1": 40, "top": 340},
            {"text": "Lidl", "x0": 60, "x1": 100, "top": 340},
        ]
        rows = builder.build_rows(words)
        assert len(rows) == 2
        assert rows[0]["Date"] == "01/01"
        assert rows[1]["Date"] == "02/01"

    def test_empty_words_returns_empty(self):
        builder = RowBuilder(TEST_COLUMNS, _make_classifier())
        assert builder.build_rows([]) == []

    def test_x1_estimated_when_missing(self):
        """Words without x1 should still be placed using estimated width."""
        classifier = _make_classifier(return_value="transaction")
        builder = RowBuilder(TEST_COLUMNS, classifier)
        # No x1 key; estimation: x0 + max(len("Hi")*3, 10) = 5 + 10 = 15
        words = [{"text": "Hi", "x0": 60, "top": 320}]
        rows = builder.build_rows(words)
        assert len(rows) == 1
