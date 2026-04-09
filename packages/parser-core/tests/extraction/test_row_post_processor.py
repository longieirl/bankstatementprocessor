"""Tests for RowPostProcessor and extract_filename_date."""

from __future__ import annotations

from unittest.mock import Mock

from bankstatements_core.extraction.row_post_processor import (
    RowPostProcessor,
    extract_filename_date,
)

TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


def _make_classifier(row_type="transaction"):
    c = Mock()
    c.classify.return_value = row_type
    return c


def _make_processor(
    filename="statement.pdf", filename_date="", template=None, row_type="transaction"
):
    return RowPostProcessor(
        columns=TEST_COLUMNS,
        row_classifier=_make_classifier(row_type),
        template=template,
        filename_date=filename_date,
        filename=filename,
    )


class TestExtractFilenameDate:
    def test_valid_date_extracted(self):
        assert extract_filename_date("statement_20250202.pdf") == "02 Feb 2025"

    def test_no_date_returns_empty(self):
        assert extract_filename_date("statement.pdf") == ""

    def test_invalid_date_returns_empty(self):
        assert extract_filename_date("file_99991399.pdf") == ""

    def test_date_at_start(self):
        assert extract_filename_date("20240101_bank.pdf") == "01 Jan 2024"


class TestRowPostProcessor:
    def test_date_propagated_from_row(self):
        proc = _make_processor()
        row = {
            "Date": "01/01/2024",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "")
        assert updated == "01/01/2024"

    def test_current_date_propagated_to_dateless_row(self):
        proc = _make_processor()
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "01/01/2024")
        assert row["Date"] == "01/01/2024"
        assert updated == "01/01/2024"

    def test_filename_date_used_when_no_current_date(self):
        proc = _make_processor(filename_date="15 Mar 2025")
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "")
        assert row["Date"] == "15 Mar 2025"
        assert updated == "15 Mar 2025"

    def test_filename_tagged(self):
        proc = _make_processor(filename="my_statement.pdf")
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["Filename"] == "my_statement.pdf"

    def test_default_document_type_when_no_template(self):
        proc = _make_processor(template=None)
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "bank_statement"
        assert row["template_id"] is None

    def test_template_document_type_and_id(self):
        template = Mock()
        template.document_type = "current_account"
        template.id = "aib_current"
        template.column_aliases = {}
        proc = _make_processor(template=template)
        row = {
            "Date": "01/01",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "current_account"
        assert row["template_id"] == "aib_current"

    def test_non_transaction_row_not_modified(self):
        proc = _make_processor(row_type="metadata")
        row = {
            "Date": "",
            "Details": "Opening Balance",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "05/01/2024")
        assert "Filename" not in row
        assert updated == "05/01/2024"

    def test_current_date_not_overwritten_by_filename_date(self):
        """filename_date should only be used when current_date is also empty."""
        proc = _make_processor(filename_date="01 Jan 2025")
        row = {
            "Date": "",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        updated = proc.process(row, "15/03/2025")
        assert row["Date"] == "15/03/2025"  # current_date wins over filename_date
        assert updated == "15/03/2025"


class TestStatefulPageRowProcessor:
    def test_date_persists_across_pages(self):
        """Date seen on page 1 is used to fill rows on page 2."""
        from bankstatements_core.extraction.row_post_processor import (
            StatefulPageRowProcessor,
        )

        proc = _make_processor()
        wrapper = StatefulPageRowProcessor(proc)

        page1 = [
            {
                "Date": "01/01/2024",
                "Details": "A",
                "Debit €": "",
                "Credit €": "",
                "Balance €": "",
            }
        ]
        page2 = [
            {"Date": "", "Details": "B", "Debit €": "", "Credit €": "", "Balance €": ""}
        ]

        wrapper.process_page(page1)
        result = wrapper.process_page(page2)

        assert result[0]["Date"] == "01/01/2024"
        assert wrapper.current_date() == "01/01/2024"

    def test_skipped_page_preserves_date(self):
        """process_page(None) is a no-op — date state is unchanged."""
        from bankstatements_core.extraction.row_post_processor import (
            StatefulPageRowProcessor,
        )

        proc = _make_processor()
        wrapper = StatefulPageRowProcessor(proc)

        wrapper.process_page(
            [
                {
                    "Date": "05/05/2024",
                    "Details": "X",
                    "Debit €": "",
                    "Credit €": "",
                    "Balance €": "",
                }
            ]
        )
        assert wrapper.current_date() == "05/05/2024"

        rows = wrapper.process_page(None)
        assert rows == []
        assert wrapper.current_date() == "05/05/2024"  # state preserved

    def test_last_date_source_row(self):
        """last_date_source() returns 'row' when date came from the row."""
        from bankstatements_core.extraction.row_post_processor import (
            StatefulPageRowProcessor,
        )

        proc = _make_processor()
        wrapper = StatefulPageRowProcessor(proc)
        wrapper.process_page(
            [
                {
                    "Date": "01/01/2024",
                    "Details": "A",
                    "Debit €": "",
                    "Credit €": "",
                    "Balance €": "",
                }
            ]
        )
        assert wrapper.last_date_source() == "row"

    def test_reset_clears_state(self):
        """reset() clears current_date and last_date_source."""
        from bankstatements_core.extraction.row_post_processor import (
            StatefulPageRowProcessor,
        )

        proc = _make_processor()
        wrapper = StatefulPageRowProcessor(proc)
        wrapper.process_page(
            [
                {
                    "Date": "01/01/2024",
                    "Details": "A",
                    "Debit €": "",
                    "Credit €": "",
                    "Balance €": "",
                }
            ]
        )
        wrapper.reset()
        assert wrapper.current_date() == ""
        assert wrapper.last_date_source() == ""


class TestColumnAliasesNormalisation:
    """Tests for column_aliases row dict normalisation (CC-05)."""

    def test_aliases_rename_row_keys(self):
        """Row keys matching column_aliases are renamed to canonical names."""
        template = Mock()
        template.document_type = "credit_card_statement"
        template.id = "aib_credit_card"
        template.column_aliases = {
            "Transaction Details": "Details",
            "Debit €": "Debit",
            "Credit €": "Credit",
        }
        cc_columns = {
            "Date": (0, 50),
            "Transaction Details": (50, 200),
            "Debit €": (200, 300),
            "Credit €": (300, 400),
        }
        proc = RowPostProcessor(
            columns=cc_columns,
            row_classifier=_make_classifier("transaction"),
            template=template,
            filename_date="",
            filename="cc_statement.pdf",
        )
        row = {
            "Date": "01 Jan 2025",
            "Transaction Details": "TESCO STORE",
            "Debit €": "42.50",
            "Credit €": "",
        }
        proc.process(row, "")
        assert row.get("Details") == "TESCO STORE"
        assert "Transaction Details" not in row
        assert row.get("Debit") == "42.50"
        assert "Debit €" not in row
        assert row.get("Credit") == ""
        assert "Credit €" not in row

    def test_empty_aliases_no_rename(self):
        """Empty column_aliases dict is a no-op — row keys unchanged."""
        template = Mock()
        template.document_type = "bank_statement"
        template.id = "aib_bank"
        template.column_aliases = {}
        proc = _make_processor(template=template)
        row = {
            "Date": "01/01/2024",
            "Details": "Tesco",
            "Debit €": "10.00",
            "Credit €": "",
            "Balance €": "100.00",
        }
        proc.process(row, "")
        # Keys unchanged — "Details" still "Details", not renamed
        assert "Details" in row
        assert row["Details"] == "Tesco"

    def test_no_template_no_alias_attempt(self):
        """When template is None, no alias normalisation is attempted."""
        proc = _make_processor(template=None)
        row = {
            "Date": "01/01/2024",
            "Details": "Tesco",
            "Debit €": "10.00",
            "Credit €": "",
            "Balance €": "100.00",
        }
        proc.process(row, "")
        assert "Details" in row
        assert row["document_type"] == "bank_statement"

    def test_cc_document_type_stamped(self):
        """CC-06: CC template stamps document_type=credit_card_statement."""
        template = Mock()
        template.document_type = "credit_card_statement"
        template.id = "aib_credit_card"
        template.column_aliases = {"Transaction Details": "Details"}
        cc_columns = {
            "Date": (0, 50),
            "Transaction Details": (50, 200),
            "Debit €": (200, 300),
            "Credit €": (300, 400),
        }
        proc = RowPostProcessor(
            columns=cc_columns,
            row_classifier=_make_classifier("transaction"),
            template=template,
            filename_date="",
            filename="cc.pdf",
        )
        row = {
            "Date": "01/01/2025",
            "Transaction Details": "Shop",
            "Debit €": "",
            "Credit €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "credit_card_statement"
        assert row["template_id"] == "aib_credit_card"

    def test_bank_statement_document_type_unchanged(self):
        """CC-06 no regression: bank statement template stamps document_type=bank_statement."""
        template = Mock()
        template.document_type = "bank_statement"
        template.id = "aib_bank"
        template.column_aliases = {}
        proc = _make_processor(template=template)
        row = {
            "Date": "01/01/2024",
            "Details": "Tesco",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["document_type"] == "bank_statement"

    def test_statement_year_stamped_on_transaction_row(self):
        """statement_year is stamped as a string on each transaction row when provided."""
        proc = RowPostProcessor(
            columns=TEST_COLUMNS,
            row_classifier=_make_classifier("transaction"),
            template=None,
            filename_date="",
            filename="statement.pdf",
            statement_year=2026,
        )
        row = {
            "Date": "3 Feb",
            "Details": "Purchase",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert row["statement_year"] == "2026"

    def test_statement_year_not_stamped_when_none(self):
        """statement_year key absent from row when not provided."""
        proc = _make_processor()
        row = {
            "Date": "3 Feb",
            "Details": "Purchase",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert "statement_year" not in row

    def test_statement_year_only_on_transaction_rows(self):
        """statement_year is not stamped on non-transaction rows."""
        proc = RowPostProcessor(
            columns=TEST_COLUMNS,
            row_classifier=_make_classifier("header"),
            template=None,
            filename_date="",
            filename="statement.pdf",
            statement_year=2026,
        )
        row = {
            "Date": "",
            "Details": "Date Details Debit Credit Balance",
            "Debit €": "",
            "Credit €": "",
            "Balance €": "",
        }
        proc.process(row, "")
        assert "statement_year" not in row


class TestCRAmountRerouting:
    """Tests for CR-suffix rerouting in RowPostProcessor (issue #131)."""

    def _make_cc_processor(self) -> RowPostProcessor:
        template = Mock()
        template.document_type = "credit_card_statement"
        template.id = "aib_credit_card"
        template.column_aliases = {"Amount": "Debit"}
        cc_columns = {
            "Date": (0, 50),
            "Details": (50, 200),
            "Debit": (200, 300),
            "Credit": (300, 400),
        }
        return RowPostProcessor(
            columns=cc_columns,
            row_classifier=_make_classifier("transaction"),
            template=template,
            filename_date="",
            filename="cc_statement.pdf",
        )

    def test_cr_amount_rerouted_to_credit(self):
        """300.00CR in Debit is moved to Credit and Debit is cleared after process()."""
        proc = self._make_cc_processor()
        row = {
            "Date": "3 Feb",
            "Details": "PAYMENT THANK YOU",
            "Debit": "300.00CR",
            "Credit": "",
        }
        proc.process(row, "")
        assert row["Credit"] == "300.00"
        assert row["Debit"] == ""

    def test_plain_debit_unchanged(self):
        """A plain debit amount (no CR suffix) stays in Debit after process()."""
        proc = self._make_cc_processor()
        row = {
            "Date": "3 Feb",
            "Details": "TESCO STORE",
            "Debit": "42.50",
            "Credit": "",
        }
        proc.process(row, "")
        assert row["Debit"] == "42.50"
        assert row["Credit"] == ""
