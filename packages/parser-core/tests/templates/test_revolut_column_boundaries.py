"""Tests for Revolut template column boundary accuracy.

Regression tests to prevent balance extraction issues caused by
column boundary misalignment (e.g., boundary at X=526 missing text at X=525.6).
"""

from __future__ import annotations

import pytest

from bankstatements_core.templates.template_registry import TemplateRegistry


class TestRevolutColumnBoundaries:
    """Test Revolut template column boundaries match PDF structure."""

    def test_revolut_balance_column_starts_before_526(self):
        """Test Revolut Balance € column starts at X=525 (not 526).

        Regression test for issue where balance values at X=525.6 were
        excluded because column boundary started at X=526.

        Related: REVOLUT_BALANCE_ISSUE.md
        """
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert revolut is not None
        assert "Balance €" in revolut.extraction.columns

        balance_col = revolut.extraction.columns["Balance €"]
        start_x, end_x = balance_col

        # Must start at or before 525 to capture balance values at X=525.6
        assert start_x <= 525, (
            f"Balance column starts at X={start_x}, but actual balance values "
            f"appear at X=525.6. This will cause data loss!"
        )

        # Reasonable end boundary
        assert end_x >= 556, "Balance column should extend to at least X=556"

    def test_revolut_column_boundaries_contiguous(self):
        """Test Revolut columns are contiguous with no gaps."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        columns = revolut.extraction.columns
        column_list = list(columns.items())

        # Check adjacent columns for gaps
        for i in range(len(column_list) - 1):
            col1_name, (_, col1_end) = column_list[i]
            col2_name, (col2_start, _) = column_list[i + 1]

            # Allow up to 10 pixels gap for realistic column spacing
            gap = col2_start - col1_end
            assert abs(gap) <= 10, (
                f"Gap of {gap} pixels between {col1_name} "
                f"(ends at {col1_end}) and {col2_name} (starts at {col2_start})"
            )

    def test_revolut_column_order_logical(self):
        """Test Revolut columns are in logical left-to-right order."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        columns = revolut.extraction.columns
        expected_order = ["Date", "Details", "Debit €", "Credit €", "Balance €"]

        actual_order = list(columns.keys())
        assert actual_order == expected_order, (
            f"Column order mismatch. Expected: {expected_order}, Got: {actual_order}"
        )

    def test_revolut_column_widths_reasonable(self):
        """Test Revolut column widths are reasonable for content."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        columns = revolut.extraction.columns

        # Date column should be narrow (dates are short)
        date_width = columns["Date"][1] - columns["Date"][0]
        assert 50 <= date_width <= 100, f"Date column width {date_width} seems unusual"

        # Details column should be widest (transaction descriptions)
        details_width = columns["Details"][1] - columns["Details"][0]
        assert details_width >= 150, (
            f"Details column width {details_width} seems too narrow"
        )

        # Amount columns should be similar width
        debit_width = columns["Debit €"][1] - columns["Debit €"][0]
        credit_width = columns["Credit €"][1] - columns["Credit €"][0]
        balance_width = columns["Balance €"][1] - columns["Balance €"][0]

        # All amount columns should be between 20-120 pixels
        for col_name, width in [
            ("Debit €", debit_width),
            ("Credit €", credit_width),
            ("Balance €", balance_width),
        ]:
            assert 20 <= width <= 120, (
                f"{col_name} width {width} is outside reasonable range (20-120)"
            )


class TestRevolutBalanceExtraction:
    """Test Revolut balance extraction scenarios."""

    def test_revolut_balance_column_defined(self):
        """Test Revolut template has Balance € column defined."""
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert "Balance €" in revolut.extraction.columns, (
            "Revolut template must have Balance € column"
        )

    def test_revolut_supports_multiline(self):
        """Test Revolut template supports multiline transactions.

        Revolut has continuation lines like:
        Line 1: 12 Jan 2025 Apple Pay top-up by *5801 €112.50 €137.70
        Line 2: From: *5801

        Balance (€137.70) is on Line 1, not Line 2.
        """
        registry = TemplateRegistry.from_default_config()
        revolut = registry.get_template("revolut")

        assert revolut.processing.supports_multiline is True, (
            "Revolut template must support multiline transactions"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
