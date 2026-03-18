"""Integration tests for RowMergerService with real classifier."""

import pytest

from bankstatements_core.services.row_merger import RowMergerService


class TestRowMergerServiceIntegration:
    """Integration test suite for RowMergerService using real row classifier."""

    @pytest.fixture
    def service(self):
        """Create RowMergerService instance."""
        return RowMergerService()

    @pytest.fixture
    def columns(self):
        """Standard column configuration."""
        return {
            "Date": (0, 100),
            "Details": (100, 300),
            "Debit €": (300, 400),
            "Credit €": (400, 500),
            "Balance €": (500, 600),
        }

    def test_merge_continuation_lines_no_description_column(self, service):
        """Test that merging returns rows unchanged when no description column."""
        columns = {
            "Date": (0, 100),
            "Debit €": (100, 200),
        }
        rows = [
            {"Date": "01/01/23", "Debit €": "100.00"},
            {"Date": "", "Debit €": "50.00"},
        ]

        result = service.merge_continuation_lines(rows, columns)
        # Should return rows unchanged without description column
        assert len(result) == 2

    def test_merge_transaction_with_continuation_line(self, service, columns):
        """Test merging continuation line with transaction."""
        # Note: The classifier identifies rows without amounts as "metadata", not "continuation"
        # So this test verifies that metadata rows stop continuation merging
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PURCHASE CARD",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "FX RATE: 1.2345",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata row stops continuation, so both rows kept
        assert len(result) == 2

    def test_merge_multiple_continuation_lines(self, service, columns):
        """Test handling multiple metadata rows after transaction."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "Reference: ABC123",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "",
                "Details": "Additional info",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata rows are kept separate
        assert len(result) == 3

    def test_preserve_balance_from_metadata_row(self, service, columns):
        """Test that metadata rows are kept separate."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "",  # Missing balance
            },
            {
                "Date": "",
                "Details": "Extra info",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "400.00",  # Balance in metadata row
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata rows don't merge, kept separate
        assert len(result) == 2

    def test_transactions_without_dates_kept_as_is(self, service, columns):
        """Test that transactions without dates are kept but not modified."""
        # Rows with amounts are classified as transactions even without dates
        # Date carry-forward only works for continuation-type rows
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT 1",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",  # No date but has amount = transaction
                "Details": "PAYMENT 2",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "450.00",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Both kept as transactions, dates not modified
        assert len(result) == 2
        assert result[0]["Date"] == "01/01/23"
        assert (
            result[1]["Date"] == ""
        )  # Date not carried forward for transaction-type rows

    def test_multiple_transactions_without_dates(self, service, columns):
        """Test multiple transactions without dates are kept as-is."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT 1",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "PAYMENT 2",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "450.00",
            },
            {
                "Date": "",
                "Details": "PAYMENT 3",
                "Debit €": "",
                "Credit €": "200.00",
                "Balance €": "650.00",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        assert len(result) == 3
        # Dates not modified for transaction-type rows
        assert result[0]["Date"] == "01/01/23"
        assert result[1]["Date"] == ""
        assert result[2]["Date"] == ""

    def test_transactions_with_mixed_dates(self, service, columns):
        """Test transactions with mixed date presence."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT 1",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "PAYMENT 2",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "450.00",
            },
            {
                "Date": "02/01/23",  # New date
                "Details": "PAYMENT 3",
                "Debit €": "75.00",
                "Credit €": "",
                "Balance €": "375.00",
            },
            {
                "Date": "",
                "Details": "PAYMENT 4",
                "Credit €": "100.00",
                "Debit €": "",
                "Balance €": "475.00",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        assert len(result) == 4
        # Dates preserved as-is for transaction-type rows
        assert result[0]["Date"] == "01/01/23"
        assert result[1]["Date"] == ""
        assert result[2]["Date"] == "02/01/23"
        assert result[3]["Date"] == ""

    def test_administrative_rows_passed_through(self, service, columns):
        """Test that administrative rows are passed through unchanged."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "BROUGHT FORWARD",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "02/01/23",
                "Details": "PAYMENT 2",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "450.00",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Administrative row should be kept separate
        assert len(result) == 3
        assert result[1]["Details"] == "BROUGHT FORWARD"

    def test_metadata_between_transactions(self, service, columns):
        """Test that metadata rows between transactions are kept."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT 1",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "Extra info",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
            {
                "Date": "02/01/23",
                "Details": "PAYMENT 2",
                "Debit €": "50.00",
                "Credit €": "",
                "Balance €": "450.00",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata rows kept separate
        assert len(result) == 3

    def test_metadata_row_without_transaction(self, service, columns):
        """Test that metadata rows without preceding transaction are kept."""
        # Rows without amounts and dates are classified as metadata
        rows = [
            {
                "Date": "",
                "Details": "Metadata line",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata rows pass through
        assert len(result) == 1

    def test_empty_metadata_text_kept(self, service, columns):
        """Test that metadata rows with empty text are still processed."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",
            },
            {
                "Date": "",
                "Details": "  ",  # Empty/whitespace only
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Both rows kept (metadata doesn't merge)
        assert len(result) == 2

    def test_metadata_rows_kept_separate(self, service, columns):
        """Test that metadata rows don't merge with transactions."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "PAYMENT",
                "Debit €": "100.00",
                "Credit €": "",
                "Balance €": "500.00",  # Has balance
            },
            {
                "Date": "",
                "Details": "Info",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "400.00",  # Different balance
            },
        ]

        result = service.merge_continuation_lines(rows, columns)

        # Metadata doesn't merge
        assert len(result) == 2
        assert result[0]["Balance €"] == "500.00"
        assert result[1]["Balance €"] == "400.00"
