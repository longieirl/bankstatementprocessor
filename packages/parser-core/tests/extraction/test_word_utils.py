"""TDD tests for extraction/word_utils.py.

Written BEFORE implementation (RED phase). All tests must fail with ImportError
until word_utils.py is created.
"""

from __future__ import annotations

import pytest

from bankstatements_core.extraction.word_utils import (
    assign_words_to_columns,
    calculate_column_coverage,
    group_words_by_y,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit": (200, 250),
    "Credit": (250, 300),
    "Balance": (300, 350),
}


def _word(text: str, x0: float, top: float, x1: float | None = None) -> dict:
    w: dict = {"text": text, "x0": x0, "top": top}
    if x1 is not None:
        w["x1"] = x1
    return w


# ---------------------------------------------------------------------------
# TestGroupWordsByY
# ---------------------------------------------------------------------------


class TestGroupWordsByY:
    def test_basic_grouping_two_distinct_y_values(self):
        """Words with different top values produce separate groups."""
        words = [
            _word("A", 10, 350.0),
            _word("B", 60, 370.0),
        ]
        result = group_words_by_y(words)
        assert 350.0 in result
        assert 370.0 in result
        assert len(result[350.0]) == 1
        assert result[350.0][0]["text"] == "A"
        assert len(result[370.0]) == 1
        assert result[370.0][0]["text"] == "B"

    def test_fractional_tops_round_to_integer_key(self):
        """Words with top values that round to the same integer produce one group.

        round(100.3, 0) == 100.0 and round(100.4, 0) == 100.0 → one group.
        Note: round(100.7, 0) == 101.0 (banker's rounding), producing a separate
        group.  The implementation uses Python's built-in round(top, 0).
        """
        words = [
            _word("A", 10, 100.3),
            _word("B", 60, 100.4),
        ]
        result = group_words_by_y(words)
        assert len(result) == 1
        assert 100.0 in result
        assert len(result[100.0]) == 2

    def test_tolerance_parameter_accepted(self):
        """tolerance parameter is accepted without raising TypeError."""
        words = [_word("A", 10, 200.0)]
        # Should not raise even though tolerance does not change behaviour
        result = group_words_by_y(words, tolerance=5.0)
        assert 200.0 in result

    def test_tolerance_does_not_change_grouping(self):
        """Grouping is by round(top, 0) regardless of tolerance value."""
        words = [
            _word("A", 10, 100.3),
            _word("B", 60, 100.4),
        ]
        result_default = group_words_by_y(words)
        result_large_tolerance = group_words_by_y(words, tolerance=50.0)
        assert set(result_default.keys()) == set(result_large_tolerance.keys())

    def test_no_table_top_y_filtering(self):
        """Words with any top value are included -- no table_top_y minimum."""
        words = [
            _word("A", 10, 0.0),
            _word("B", 60, 5.0),
            _word("C", 60, 999.0),
        ]
        result = group_words_by_y(words)
        assert len(result) == 3

    def test_empty_list_returns_empty_dict(self):
        """Empty word list produces an empty dict."""
        result = group_words_by_y([])
        assert result == {}

    def test_multiple_words_same_y_grouped_together(self):
        """Multiple words at the same rounded Y appear in one group."""
        words = [
            _word("01/01", 5, 320.0),
            _word("Tesco", 60, 320.0),
            _word("12.50", 210, 320.0),
        ]
        result = group_words_by_y(words)
        assert len(result) == 1
        assert len(result[320.0]) == 3

    def test_returned_dict_keys_are_float(self):
        """All keys in the returned dict are floats (not ints)."""
        words = [_word("A", 10, 200.0)]
        result = group_words_by_y(words)
        for key in result:
            assert isinstance(key, float), f"Expected float key, got {type(key)}"


# ---------------------------------------------------------------------------
# TestAssignWordsToColumns
# ---------------------------------------------------------------------------


class TestAssignWordsToColumns:
    def test_relaxed_check_by_default(self):
        """With strict_rightmost=False (default), all columns use xmin <= x0 < xmax."""
        words = [_word("Hello", 60, 320.0, x1=90)]
        result = assign_words_to_columns(words, COLUMNS)
        assert result["Details"] == "Hello"

    def test_all_columns_have_empty_string_keys(self):
        """Returned dict contains all column names, even those without data."""
        result = assign_words_to_columns([], COLUMNS)
        assert set(result.keys()) == set(COLUMNS.keys())
        for val in result.values():
            assert val == ""

    def test_empty_words_returns_empty_row(self):
        """Empty words list returns dict with all column keys mapped to empty string."""
        result = assign_words_to_columns([], COLUMNS)
        assert result == {col: "" for col in COLUMNS}

    def test_strict_rightmost_false_accepts_word_extending_beyond_rightmost(self):
        """Without strict_rightmost, a word whose x1 extends past xmax is still placed."""
        # x0=310 is inside Balance (300-350), x1=360 extends beyond xmax=350
        # relaxed check: xmin(300) <= x0(310) < xmax(350) → placed
        words = [_word("1234.56", 310, 320.0, x1=360)]
        result = assign_words_to_columns(words, COLUMNS)
        assert result["Balance"] == "1234.56"

    def test_strict_rightmost_true_rejects_word_extending_beyond_rightmost(self):
        """With strict_rightmost=True, a word whose x1 > xmax of rightmost is rejected."""
        # x0=310 inside Balance (300-350), x1=360 extends beyond xmax=350
        # strict check: xmin(300) <= x0(310) AND x1(360) <= xmax(350) → FAILS
        words = [_word("1234.56", 310, 320.0, x1=360)]
        result = assign_words_to_columns(words, COLUMNS, strict_rightmost=True)
        assert result["Balance"] == ""

    def test_strict_rightmost_true_accepts_word_contained_in_rightmost(self):
        """With strict_rightmost=True, a word fully within rightmost column is accepted."""
        # x0=310, x1=345 both within Balance (300-350)
        words = [_word("100.00", 310, 320.0, x1=345)]
        result = assign_words_to_columns(words, COLUMNS, strict_rightmost=True)
        assert result["Balance"] == "100.00"

    def test_strict_rightmost_does_not_affect_non_rightmost_columns(self):
        """With strict_rightmost=True, non-rightmost columns still use relaxed check."""
        # Details word x0=60 x1=999 (way beyond Details xmax=200)
        # relaxed check: xmin(50) <= x0(60) < xmax(200) → placed (x1 ignored)
        words = [_word("Tesco", 60, 320.0, x1=999)]
        result = assign_words_to_columns(words, COLUMNS, strict_rightmost=True)
        assert result["Details"] == "Tesco"

    def test_x1_fallback_when_key_missing(self):
        """When x1 key is absent, fallback x1 = x0 + max(len(text)*3, 10) is used."""
        # "Hi" has len=2; fallback: x0(60) + max(2*3, 10) = 60 + 10 = 70
        # With strict_rightmost=True, Balance (300-350): x0=310, x1=320 (both inside) → placed
        words = [{"text": "Hi", "x0": 310, "top": 320.0}]  # no x1 key
        result = assign_words_to_columns(words, COLUMNS, strict_rightmost=True)
        # fallback x1 = 310 + max(len("Hi")*3, 10) = 310 + 10 = 320 <= 350 → accepted
        assert result["Balance"] == "Hi"

    def test_x1_fallback_strict_rightmost_rejects_with_long_text(self):
        """Long text without x1 causes large fallback x1, which fails strict check."""
        # "LongTextHere" has len=12; fallback: x0(310) + max(12*3, 10) = 310 + 36 = 346 <= 350
        # Actually 346 <= 350 passes. Use a very long text.
        # "AReallylongtextstring" has len=21; fallback: 310 + max(21*3, 10) = 310 + 63 = 373 > 350 → rejected
        long_text = "AReallylongtextstring"  # len=21
        words = [{"text": long_text, "x0": 310, "top": 320.0}]  # no x1
        result = assign_words_to_columns(words, COLUMNS, strict_rightmost=True)
        assert result["Balance"] == ""

    def test_multiple_words_concatenated_with_space(self):
        """Multiple words in the same column are concatenated with space, then stripped."""
        words = [
            _word("John", 60, 320.0, x1=90),
            _word("Smith", 95, 320.0, x1=130),
        ]
        result = assign_words_to_columns(words, COLUMNS)
        assert result["Details"] == "John Smith"

    def test_values_are_stripped(self):
        """Final values have leading/trailing whitespace stripped."""
        words = [_word("Hi", 60, 320.0, x1=90)]
        result = assign_words_to_columns(words, COLUMNS)
        assert result["Details"] == "Hi"
        assert not result["Details"].endswith(" ")

    def test_word_outside_all_columns_not_assigned(self):
        """A word whose x0 falls outside every column boundary is not placed anywhere."""
        # x0=500 is beyond all column boundaries (max xmax=350)
        words = [_word("Orphan", 500, 320.0, x1=530)]
        result = assign_words_to_columns(words, COLUMNS)
        for val in result.values():
            assert val == ""


# ---------------------------------------------------------------------------
# TestCalculateColumnCoverage
# ---------------------------------------------------------------------------


class TestCalculateColumnCoverage:
    def test_all_columns_have_data_returns_one(self):
        """When every column has data in at least one row, coverage is 1.0."""
        rows = [
            {
                "Date": "01/01",
                "Details": "Tesco",
                "Debit": "12.50",
                "Credit": "",
                "Balance": "100.00",
            },
            {
                "Date": "",
                "Details": "AIB",
                "Debit": "",
                "Credit": "50.00",
                "Balance": "",
            },
        ]
        result = calculate_column_coverage(rows, COLUMNS)
        assert result == 1.0

    def test_partial_coverage(self):
        """2 of 4 columns having data returns 0.5."""
        two_col_columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit": (200, 250),
            "Credit": (250, 300),
        }
        rows = [
            {"Date": "01/01", "Details": "Tesco", "Debit": "", "Credit": ""},
        ]
        result = calculate_column_coverage(rows, two_col_columns)
        assert result == 0.5

    def test_empty_rows_returns_zero(self):
        """No rows means no coverage."""
        result = calculate_column_coverage([], COLUMNS)
        assert result == 0.0

    def test_empty_columns_returns_zero(self):
        """No columns means no coverage."""
        rows = [{"Date": "01/01"}]
        result = calculate_column_coverage(rows, {})
        assert result == 0.0

    def test_whitespace_only_values_not_counted(self):
        """Values that are only whitespace are not counted as data."""
        rows = [
            {"Date": "   ", "Details": "\t", "Debit": "", "Credit": "", "Balance": ""},
        ]
        result = calculate_column_coverage(rows, COLUMNS)
        assert result == 0.0

    def test_single_row_single_column_has_data(self):
        """1 of 5 columns having data in one row returns 0.2."""
        rows = [
            {"Date": "", "Details": "Tesco", "Debit": "", "Credit": "", "Balance": ""}
        ]
        result = calculate_column_coverage(rows, COLUMNS)
        assert result == pytest.approx(0.2)

    def test_same_column_in_multiple_rows_counts_once(self):
        """The same column name is counted once even if it has data in multiple rows."""
        rows = [
            {"Date": "01/01", "Details": "", "Debit": "", "Credit": "", "Balance": ""},
            {"Date": "02/01", "Details": "", "Debit": "", "Credit": "", "Balance": ""},
        ]
        result = calculate_column_coverage(rows, COLUMNS)
        assert result == pytest.approx(0.2)
