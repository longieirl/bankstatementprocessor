"""Row post-processing: date propagation and metadata tagging.

Encapsulates the per-row logic that runs after word-to-row conversion:
filling in missing dates and stamping each row with filename/document_type/template_id.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from bankstatements_core.domain.currency import reroute_cr_suffix
from bankstatements_core.domain.models.extraction_scoring_config import (
    ExtractionScoringConfig,
)
from bankstatements_core.domain.models.extraction_warning import (
    CODE_DATE_PROPAGATED,
    CODE_MISSING_BALANCE,
    ExtractionWarning,
)
from bankstatements_core.extraction.column_identifier import ColumnTypeIdentifier

if TYPE_CHECKING:
    from bankstatements_core.extraction.row_classifiers import RowClassifier
    from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


def extract_filename_date(filename: str) -> str:
    """Extract date from filename using YYYYMMDD pattern.

    Args:
        filename: Filename to extract date from

    Returns:
        Formatted date string (e.g., "02 Feb 2025"), or empty string if no date found
    """
    date_match = re.search(r"(\d{8})", filename)
    if not date_match:
        return ""
    try:
        return datetime.strptime(date_match.group(1), "%Y%m%d").strftime("%d %b %Y")
    except ValueError:
        return ""


class RowPostProcessor:
    """Tags rows with metadata and propagates dates to dateless transaction rows."""

    def __init__(  # noqa: PLR0913
        self,
        columns: dict[str, tuple[int | float, int | float]],
        row_classifier: RowClassifier,
        template: BankTemplate | None,
        filename_date: str,
        filename: str,
        scoring_config: ExtractionScoringConfig | None = None,
        statement_year: int | None = None,
    ) -> None:
        self._columns = columns
        self._row_classifier = row_classifier
        self._template = template
        self._filename_date = filename_date
        self._filename = filename
        self._scoring_config = (
            scoring_config
            if scoring_config is not None
            else ExtractionScoringConfig.default()
        )
        self._statement_year = statement_year
        self._date_col = ColumnTypeIdentifier.find_first_column_of_type(columns, "date")
        self._balance_col = ColumnTypeIdentifier.find_first_column_of_type(
            columns, "balance"
        )
        self._last_source: str = ""

    def _reroute_cr_amounts(self, row: dict) -> None:
        """Reroute CR-suffixed debit amounts to the Credit column."""
        reroute_cr_suffix(row)

    def _apply_column_aliases(self, row: dict) -> None:
        """Rename non-canonical row keys to canonical names using template.column_aliases.

        Modifies the row dict in-place. Must be called before row classification
        so the classifier sees canonical column names.

        Args:
            row: Row dictionary to normalise (modified in-place)
        """
        if self._template and self._template.column_aliases:
            for old_key, new_key in self._template.column_aliases.items():
                if old_key in row:
                    row[new_key] = row.pop(old_key)

    def process(self, row: dict, current_date: str) -> str:
        """Tag row with metadata and propagate date. Returns updated current_date.

        Only processes rows classified as 'transaction'; others are left unchanged.

        Sets self._last_source to indicate where the returned date came from:
        "row" if taken from the row itself, "propagated" if filled in from
        current_date or filename_date, "" if no date column or non-transaction row.

        Args:
            row: Row dictionary (modified in-place)
            current_date: Most recently seen date

        Returns:
            Updated current_date
        """
        self._last_source = ""
        self._apply_column_aliases(row)
        self._reroute_cr_amounts(row)
        if self._row_classifier.classify(row, self._columns) != "transaction":
            return current_date

        score = 1.0
        warnings: list[dict] = []

        # Date propagation
        if self._date_col and row.get(self._date_col):
            current_date = row[self._date_col]
            self._last_source = "row"
        elif self._date_col and (current_date or self._filename_date):
            fallback_date = current_date or self._filename_date
            row[self._date_col] = fallback_date
            if not current_date:
                current_date = fallback_date
            self._last_source = "propagated"
            score -= self._scoring_config.penalty_date_propagated
            warnings.append(
                ExtractionWarning(
                    code=CODE_DATE_PROPAGATED,
                    message=f"date propagated from previous row ('{fallback_date}')",
                ).to_dict()
            )

        # Missing balance
        if self._balance_col and not row.get(self._balance_col, "").strip():
            score -= self._scoring_config.penalty_missing_balance
            warnings.append(
                ExtractionWarning(
                    code=CODE_MISSING_BALANCE,
                    message="balance field is missing or empty",
                ).to_dict()
            )

        row["confidence_score"] = str(max(0.0, min(1.0, score)))
        if warnings:
            row["extraction_warnings"] = json.dumps(warnings)

        # Metadata tagging
        row["Filename"] = self._filename
        if self._statement_year is not None:
            row["statement_year"] = str(self._statement_year)
        if self._template:
            row["document_type"] = self._template.document_type
            row["template_id"] = self._template.id
        else:
            row["document_type"] = "bank_statement"
            row["template_id"] = None

        return current_date


class StatefulPageRowProcessor:
    """Wraps RowPostProcessor to own the current_date state across pages.

    Removes the need for callers to thread a current_date variable through
    their page loop. A skipped page (page_rows is None) is handled explicitly
    rather than being invisible — state is preserved but the skip is visible
    via last_date_source().

    Usage::

        wrapper = StatefulPageRowProcessor(post_processor)
        for page_rows in pages:
            rows = wrapper.process_page(page_rows)  # None = skipped page
    """

    def __init__(self, post_processor: RowPostProcessor) -> None:
        self._post_processor = post_processor
        self._current_date: str = ""
        self._last_source: str = ""

    def process_page(self, page_rows: list[dict] | None) -> list[dict]:
        """Process all rows on a page, maintaining date state.

        Args:
            page_rows: Rows extracted from one page, or None if the page was
                       skipped (table structure not found). A None value is a
                       no-op — date state is preserved unchanged.

        Returns:
            Non-empty processed rows, or [] if page_rows is None/empty.
        """
        if page_rows is None:
            return []

        result: list[dict] = []
        for row in page_rows:
            self._current_date = self._post_processor.process(row, self._current_date)
            self._last_source = self._post_processor._last_source
            if row:
                result.append(row)
        return result

    def current_date(self) -> str:
        """Return the most recently seen date across all processed pages."""
        return self._current_date

    def last_date_source(self) -> str:
        """Return where the last date update came from: 'row', 'propagated', or ''."""
        return self._last_source

    def reset(self) -> None:
        """Reset date state — useful when reusing the wrapper for a new PDF."""
        self._current_date = ""
        self._last_source = ""
