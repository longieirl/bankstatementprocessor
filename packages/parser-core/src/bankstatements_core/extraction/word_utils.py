"""Pure standalone word-processing utility functions for PDF table extraction.

These functions consolidate duplicated private-method logic from:
- extraction/boundary_detector.py (_group_words_by_y, _build_row_from_words,
  _calculate_column_coverage)
- extraction/row_builder.py (inline word-grouping and column-assignment loop)
- services/header_detection.py (_group_words_by_y_coordinate)
- services/page_validation.py (calculate_column_coverage -- canonical version)

This module is intentionally NOT re-exported from extraction/__init__.py.
Callers import directly:
    from bankstatements_core.extraction.word_utils import group_words_by_y
"""

from __future__ import annotations


def group_words_by_y(
    words: list[dict],
    tolerance: float = 1.0,
) -> dict[float, list[dict]]:
    """Group words by Y-coordinate (rounded to the nearest integer).

    Args:
        words: List of word dicts, each containing at least ``"top"`` and
            ``"text"`` keys.
        tolerance: Accepted for API compatibility but the current implementation
            always rounds to 0 decimal places (``round(w["top"], 0)``),
            which is the behaviour used by all original callers.  Changing
            tolerance to a non-zero value does **not** affect the grouping.

    Returns:
        A dict mapping ``float`` Y-coordinate keys to the list of word dicts
        at that rounded Y position.  Keys are the result of
        ``round(w["top"], 0)``, which always produces a ``float`` in Python 3.

    Note:
        This function applies **no** ``table_top_y`` filtering.  Callers that
        need to exclude words above the table boundary should pre-filter the
        word list before calling this function.
    """
    lines: dict[float, list[dict]] = {}
    for w in words:
        y_key = round(w["top"], 0)
        lines.setdefault(y_key, []).append(w)
    return lines


def assign_words_to_columns(
    words: list[dict],
    columns: dict[str, tuple[int | float, int | float]],
    strict_rightmost: bool = False,
) -> dict[str, str]:
    """Assign words to named columns based on their x-position.

    Args:
        words: List of word dicts at a single Y-coordinate.  Each dict must
            contain ``"text"`` and ``"x0"`` keys.  ``"x1"`` is optional; if
            absent the right edge is estimated as
            ``x0 + max(len(text) * 3, 10)``.
        columns: Ordered mapping of column name to ``(xmin, xmax)`` boundary
            tuple.  The last entry is treated as the *rightmost* column when
            ``strict_rightmost=True``.
        strict_rightmost: When ``True``, the rightmost column uses a strict
            containment check (``xmin <= x0 and x1 <= xmax``) to prevent
            footer or overflow text from bleeding into balance/amount columns.
            When ``False`` (default), all columns use a relaxed left-edge
            check (``xmin <= x0 < xmax``).

    Returns:
        A dict mapping every column name to its accumulated text value,
        stripped of leading/trailing whitespace.  Columns with no matching
        words map to an empty string.
    """
    column_names = list(columns.keys())
    rightmost = column_names[-1] if column_names else None
    row: dict[str, str] = dict.fromkeys(columns, "")

    for w in words:
        x0: float = w["x0"]
        text: str = w["text"]
        x1: float = w.get("x1", x0 + max(len(text) * 3, 10))

        for col, (xmin, xmax) in columns.items():
            if strict_rightmost and col == rightmost:
                if xmin <= x0 and x1 <= xmax:
                    row[col] += text + " "
                    break
            else:
                if xmin <= x0 < xmax:
                    row[col] += text + " "
                    break

    return {k: v.strip() for k, v in row.items()}


def calculate_column_coverage(
    rows: list[dict],
    columns: dict[str, tuple[int | float, int | float]],
) -> float:
    """Return the fraction of columns that have non-empty data across all rows.

    A column is counted as having data if at least one row contains a
    non-empty, non-whitespace string for that column name.

    Args:
        rows: List of row dicts, each mapping column names to string values.
        columns: Column definitions mapping name to ``(xmin, xmax)``.  Used
            to determine the full set of column names and the denominator for
            the coverage fraction.

    Returns:
        A float in ``[0.0, 1.0]``.  Returns ``0.0`` when ``rows`` is empty
        or ``columns`` is empty.

    Note:
        Canonical source: ``PageValidationService.calculate_column_coverage``
        in ``services/page_validation.py`` (L116–L133).
    """
    if not rows or not columns:
        return 0.0
    column_names = list(columns.keys())
    columns_with_data: set[str] = set()
    for row in rows:
        for col_name in column_names:
            if row.get(col_name, "").strip():
                columns_with_data.add(col_name)
    return len(columns_with_data) / len(column_names)
