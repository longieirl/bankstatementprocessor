"""Tests for Transaction.confidence_score computation in RowPostProcessor."""

from __future__ import annotations

import dataclasses
import json
from unittest.mock import Mock

import pytest

from bankstatements_core.domain.models.extraction_scoring_config import (
    ExtractionScoringConfig,
)
from bankstatements_core.domain.models.extraction_warning import (
    CODE_DATE_PROPAGATED,
    CODE_MISSING_BALANCE,
)
from bankstatements_core.extraction.row_post_processor import RowPostProcessor

TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


def _make_classifier(row_type="transaction"):
    c = Mock()
    c.classify.return_value = row_type
    return c


def _make_processor(
    filename="statement.pdf",
    filename_date="",
    template=None,
    row_type="transaction",
    scoring_config=None,
):
    return RowPostProcessor(
        columns=TEST_COLUMNS,
        row_classifier=_make_classifier(row_type),
        template=template,
        filename_date=filename_date,
        filename=filename,
        scoring_config=scoring_config,
    )


def _clean_row(balance="1234.56"):
    return {
        "Date": "01/01/2024",
        "Details": "Tesco",
        "Debit €": "10.00",
        "Credit €": "",
        "Balance €": balance,
    }


class TestExtractionScoringConfig:
    def test_default_weights(self):
        cfg = ExtractionScoringConfig.default()
        assert cfg.penalty_date_propagated == 0.1
        assert cfg.penalty_missing_balance == 0.2

    def test_custom_weights(self):
        cfg = ExtractionScoringConfig(
            penalty_date_propagated=0.3, penalty_missing_balance=0.4
        )
        assert cfg.penalty_date_propagated == 0.3
        assert cfg.penalty_missing_balance == 0.4

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="penalty_date_propagated"):
            ExtractionScoringConfig(penalty_date_propagated=-0.1)

    def test_negative_missing_balance_raises(self):
        with pytest.raises(ValueError, match="penalty_missing_balance"):
            ExtractionScoringConfig(penalty_missing_balance=-0.5)

    def test_frozen(self):
        cfg = ExtractionScoringConfig.default()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.penalty_date_propagated = 0.9  # type: ignore[misc]


class TestFullConfidenceRow:
    def test_clean_row_scores_1_0(self):
        proc = _make_processor()
        row = _clean_row()
        proc.process(row, "")
        assert float(row["confidence_score"]) == 1.0

    def test_no_warnings_on_clean_row(self):
        proc = _make_processor()
        row = _clean_row()
        proc.process(row, "")
        warnings = json.loads(row.get("extraction_warnings", "[]"))
        assert warnings == []


class TestDatePropagatedPenalty:
    def test_date_propagated_reduces_score(self):
        proc = _make_processor()
        row = _clean_row()
        row["Date"] = ""  # no date — will be propagated from current_date
        proc.process(row, "05/01/2024")
        assert float(row["confidence_score"]) == pytest.approx(0.9)

    def test_date_propagated_warning_code_present(self):
        proc = _make_processor()
        row = _clean_row()
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        warnings = json.loads(row["extraction_warnings"])
        codes = [w["code"] for w in warnings]
        assert CODE_DATE_PROPAGATED in codes

    def test_date_propagated_from_filename_reduces_score(self):
        proc = _make_processor(filename_date="01 Jan 2024")
        row = _clean_row()
        row["Date"] = ""
        proc.process(row, "")
        assert float(row["confidence_score"]) == pytest.approx(0.9)


class TestMissingBalancePenalty:
    def test_missing_balance_reduces_score(self):
        proc = _make_processor()
        row = _clean_row(balance="")
        proc.process(row, "")
        assert float(row["confidence_score"]) == pytest.approx(0.8)

    def test_missing_balance_warning_code_present(self):
        proc = _make_processor()
        row = _clean_row(balance="")
        proc.process(row, "")
        warnings = json.loads(row["extraction_warnings"])
        codes = [w["code"] for w in warnings]
        assert CODE_MISSING_BALANCE in codes


class TestBothPenalties:
    def test_both_penalties_cumulative(self):
        proc = _make_processor()
        row = _clean_row(balance="")
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        # 1.0 - 0.1 (date) - 0.2 (balance) = 0.7
        assert float(row["confidence_score"]) == pytest.approx(0.7)

    def test_both_warnings_present(self):
        proc = _make_processor()
        row = _clean_row(balance="")
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        warnings = json.loads(row["extraction_warnings"])
        codes = {w["code"] for w in warnings}
        assert CODE_DATE_PROPAGATED in codes
        assert CODE_MISSING_BALANCE in codes


class TestScoreClamping:
    def test_score_clamped_to_zero(self):
        cfg = ExtractionScoringConfig(
            penalty_date_propagated=0.6, penalty_missing_balance=0.6
        )
        proc = _make_processor(scoring_config=cfg)
        row = _clean_row(balance="")
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        assert float(row["confidence_score"]) == 0.0

    def test_score_never_negative(self):
        cfg = ExtractionScoringConfig(
            penalty_date_propagated=1.0, penalty_missing_balance=1.0
        )
        proc = _make_processor(scoring_config=cfg)
        row = _clean_row(balance="")
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        assert float(row["confidence_score"]) >= 0.0


class TestInjectableScoringConfig:
    def test_custom_config_honoured(self):
        cfg = ExtractionScoringConfig(
            penalty_date_propagated=0.3, penalty_missing_balance=0.0
        )
        proc = _make_processor(scoring_config=cfg)
        row = _clean_row()
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        assert float(row["confidence_score"]) == pytest.approx(0.7)

    def test_zero_penalties_leaves_score_at_1(self):
        cfg = ExtractionScoringConfig(
            penalty_date_propagated=0.0, penalty_missing_balance=0.0
        )
        proc = _make_processor(scoring_config=cfg)
        row = _clean_row(balance="")
        row["Date"] = ""
        proc.process(row, "05/01/2024")
        assert float(row["confidence_score"]) == pytest.approx(1.0)


class TestNonTransactionRowNotScored:
    def test_non_transaction_row_has_no_confidence_score(self):
        proc = _make_processor(row_type="metadata")
        row = {
            "Date": "",
            "Details": "Opening Balance",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert "confidence_score" not in row
