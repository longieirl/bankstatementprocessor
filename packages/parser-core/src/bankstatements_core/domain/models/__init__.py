"""Domain models for bank statement entities."""

from __future__ import annotations

from bankstatements_core.domain.models.extraction_result import ExtractionResult
from bankstatements_core.domain.models.transaction import Transaction

__all__ = ["Transaction", "ExtractionResult"]
