"""ExtractionResult domain model for bank statement PDF extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bankstatements_core.domain.models.extraction_warning import ExtractionWarning
from bankstatements_core.domain.models.transaction import Transaction


@dataclass
class ExtractionResult:
    """Document-level result container for a single PDF extraction.

    Attributes:
        transactions: Promoted Transaction objects extracted from the PDF
        page_count: Total number of pages in the source PDF
        iban: IBAN found in the document header, or None if not detected
        source_file: Path to the source PDF file
        warnings: Document-level non-fatal events (e.g. credit card detected,
            skipped). Distinct from per-row Transaction.extraction_warnings.
            In-memory only — not written to output files.
    """

    transactions: list[Transaction]
    page_count: int
    iban: str | None
    source_file: Path
    warnings: list[ExtractionWarning] = field(default_factory=list)
