"""Word-to-row conversion and classification filtering.

Encapsulates grouping PDF words by Y position, assigning them to columns,
and filtering to only transaction/continuation rows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
        row_classifier: "RowClassifier",
    ) -> None:
        self._columns = columns
        self._row_classifier = row_classifier
        self._column_names = list(columns.keys())
        self._rightmost_column = self._column_names[-1] if self._column_names else None

    def build_rows(self, words: list[dict]) -> list[dict]:
        """Group words by Y position, assign to columns, return transaction/continuation rows.

        Args:
            words: List of word dictionaries from pdfplumber

        Returns:
            List of row dictionaries classified as 'transaction' or 'continuation'
        """
        lines: dict[float, list[dict]] = {}
        for w in words:
            y_key = round(w["top"], 0)
            lines.setdefault(y_key, []).append(w)

        page_rows = []
        for _, line_words in sorted(lines.items()):
            row = dict.fromkeys(self._columns, "")

            for w in line_words:
                x0 = w["x0"]
                x1 = w.get("x1", x0 + max(len(w["text"]) * 3, 10))
                text = w["text"]

                for col, (xmin, xmax) in self._columns.items():
                    if col == self._rightmost_column:
                        if xmin <= x0 and x1 <= xmax:
                            row[col] += text + " "
                            break
                    else:
                        if xmin <= x0 < xmax:
                            row[col] += text + " "
                            break

            row = {k: v.strip() for k, v in row.items()}

            if any(row.values()):
                row_type = self._row_classifier.classify(row, self._columns)
                if row_type in ["transaction", "continuation"]:
                    page_rows.append(row)

        return page_rows
