"""Extraction scoring configuration for Transaction.confidence_score computation.

Holds the per-signal penalty weights used by RowPostProcessor to reduce
a transaction's confidence score when extraction anomalies are detected.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionScoringConfig:
    """Injectable penalty weights for Transaction.confidence_score.

    All weights must be non-negative. The score starts at 1.0 and is
    decremented by each applicable penalty, then clamped to [0.0, 1.0].

    Attributes:
        penalty_date_propagated: Applied when a date is filled in from a
            prior row or the filename rather than read directly from the row.
        penalty_missing_balance: Applied when the balance field is absent or
            empty for a transaction row.

    Examples:
        >>> cfg = ExtractionScoringConfig.default()
        >>> cfg.penalty_date_propagated
        0.1
        >>> cfg.penalty_missing_balance
        0.2
    """

    penalty_date_propagated: float = 0.1
    penalty_missing_balance: float = 0.2

    def __post_init__(self) -> None:
        for name, val in [
            ("penalty_date_propagated", self.penalty_date_propagated),
            ("penalty_missing_balance", self.penalty_missing_balance),
        ]:
            if val < 0.0:
                raise ValueError(f"{name} must be >= 0.0, got {val}")

    @classmethod
    def default(cls) -> "ExtractionScoringConfig":
        """Return the default production scoring configuration."""
        return cls()
