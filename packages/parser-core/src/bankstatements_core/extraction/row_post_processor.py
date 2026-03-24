"""Row post-processing: date propagation and metadata tagging.

Encapsulates the per-row logic that runs after word-to-row conversion:
filling in missing dates and stamping each row with filename/document_type/template_id.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

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

    def __init__(
        self,
        columns: dict[str, tuple[int | float, int | float]],
        row_classifier: "RowClassifier",
        template: "BankTemplate | None",
        filename_date: str,
        filename: str,
    ) -> None:
        self._columns = columns
        self._row_classifier = row_classifier
        self._template = template
        self._filename_date = filename_date
        self._filename = filename
        self._date_col = ColumnTypeIdentifier.find_first_column_of_type(columns, "date")

    def process(self, row: dict, current_date: str) -> str:
        """Tag row with metadata and propagate date. Returns updated current_date.

        Only processes rows classified as 'transaction'; others are left unchanged.

        Args:
            row: Row dictionary (modified in-place)
            current_date: Most recently seen date

        Returns:
            Updated current_date
        """
        if self._row_classifier.classify(row, self._columns) != "transaction":
            return current_date

        # Date propagation
        if self._date_col and row.get(self._date_col):
            current_date = row[self._date_col]
        elif self._date_col and (current_date or self._filename_date):
            fallback_date = current_date or self._filename_date
            row[self._date_col] = fallback_date
            if not current_date:
                current_date = fallback_date

        # Metadata tagging
        row["Filename"] = self._filename
        if self._template:
            row["document_type"] = self._template.document_type
            row["template_id"] = self._template.id
        else:
            row["document_type"] = "bank_statement"
            row["template_id"] = None

        return current_date
