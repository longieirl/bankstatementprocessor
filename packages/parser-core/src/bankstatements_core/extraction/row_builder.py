"""Word-to-row conversion and classification filtering.

Encapsulates grouping PDF words by Y position, assigning them to columns,
and filtering to only transaction/continuation rows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bankstatements_core.extraction.word_utils import (
    assign_words_to_columns,
    group_words_by_y,
)

if TYPE_CHECKING:
    from bankstatements_core.extraction.row_classifiers import RowClassifier

logger = logging.getLogger(__name__)


class RowBuilder:
    """Converts a flat list of PDF words into classified row dictionaries.

    Boundary strategy:
    - Rightmost column: STRICT check (word must be fully contained) to prevent
      footer text bleeding into the balance column.
    - All other columns: RELAXED check (word's left edge within bounds).
    """

    def __init__(
        self,
        columns: dict[str, tuple[int | float, int | float]],
        row_classifier: RowClassifier,
    ) -> None:
        self._columns = columns
        self._row_classifier = row_classifier

    def build_rows(self, words: list[dict]) -> list[dict]:
        """Group words by Y position, assign to columns, return transaction/continuation rows.

        Args:
            words: List of word dictionaries from pdfplumber

        Returns:
            List of row dictionaries classified as 'transaction' or 'continuation'
        """
        lines = group_words_by_y(words)
        page_rows = []
        for _, line_words in sorted(lines.items()):
            row = assign_words_to_columns(
                line_words, self._columns, strict_rightmost=True
            )
            if any(row.values()):
                row_type = self._row_classifier.classify(row, self._columns)
                if row_type in ["transaction", "continuation"]:
                    page_rows.append(row)
        return page_rows
