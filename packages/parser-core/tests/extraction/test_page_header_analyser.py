"""Tests for PageHeaderAnalyser."""

from __future__ import annotations

from unittest.mock import Mock

from bankstatements_core.extraction.page_header_analyser import PageHeaderAnalyser


def _make_page(header_text: str = "", words: list[dict] | None = None) -> Mock:
    """Build a minimal mock pdfplumber page."""
    page = Mock()
    page.width = 600
    cropped = Mock()
    cropped.extract_text.return_value = header_text
    cropped.extract_words.return_value = words or []
    page.crop.return_value = cropped
    return page


class TestIsCredirCardStatement:
    def _analyser(self) -> PageHeaderAnalyser:
        return PageHeaderAnalyser(Mock())

    def test_card_number_detected(self):
        page = _make_page("Card Number: 1234 5678 9012 3456")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_credit_limit_detected(self):
        page = _make_page("Credit Limit: €5,000")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_credit_card_phrase_detected(self):
        page = _make_page("Your Credit Card Statement")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_visa_detected(self):
        page = _make_page("VISA Debit Statement")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_mastercard_detected(self):
        page = _make_page("Mastercard Gold")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_normal_statement_not_detected(self):
        page = _make_page("Current Account Statement\nIBAN: IE29AIBK93115212345678")
        assert not self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_empty_header_returns_false(self):
        page = _make_page("")
        assert not self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_none_header_text_returns_false(self):
        page = _make_page(None)
        assert not self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_page_exception_returns_false(self):
        page = Mock()
        page.width = 600
        page.crop.side_effect = AttributeError("no crop")
        assert not self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_case_insensitive(self):
        page = _make_page("card number: 0000 1111")
        assert self._analyser().is_credit_card_statement(page, table_top_y=300)

    def test_crops_at_table_top_y(self):
        page = _make_page("Card Number: x")
        analyser = self._analyser()
        analyser.is_credit_card_statement(page, table_top_y=250)
        page.crop.assert_called_once_with((0, 0, page.width, 250))


class TestExtractIban:
    def test_iban_found_in_text(self):
        mock_extractor = Mock()
        mock_extractor.extract_iban.return_value = "IE29AIBK93115212345678"
        mock_extractor.extract_iban_from_pdf_words.return_value = None
        page = _make_page("Account: IE29AIBK93115212345678")
        analyser = PageHeaderAnalyser(mock_extractor)
        assert analyser.extract_iban(page) == "IE29AIBK93115212345678"

    def test_iban_found_in_words_when_text_fails(self):
        mock_extractor = Mock()
        mock_extractor.extract_iban.return_value = None
        mock_extractor.extract_iban_from_pdf_words.return_value = (
            "IE29AIBK93115212345678"
        )
        page = _make_page("", words=[{"text": "IE29AIBK93115212345678"}])
        analyser = PageHeaderAnalyser(mock_extractor)
        assert analyser.extract_iban(page) == "IE29AIBK93115212345678"

    def test_returns_none_when_no_iban(self):
        mock_extractor = Mock()
        mock_extractor.extract_iban.return_value = None
        mock_extractor.extract_iban_from_pdf_words.return_value = None
        page = _make_page("No IBAN here")
        analyser = PageHeaderAnalyser(mock_extractor)
        assert analyser.extract_iban(page) is None

    def test_page_exception_returns_none(self):
        mock_extractor = Mock()
        page = Mock()
        page.width = 600
        page.crop.side_effect = AttributeError("crop failed")
        analyser = PageHeaderAnalyser(mock_extractor)
        assert analyser.extract_iban(page) is None

    def test_crops_at_fixed_350(self):
        mock_extractor = Mock()
        mock_extractor.extract_iban.return_value = None
        mock_extractor.extract_iban_from_pdf_words.return_value = None
        page = _make_page("")
        analyser = PageHeaderAnalyser(mock_extractor)
        analyser.extract_iban(page)
        page.crop.assert_called_once_with((0, 0, page.width, 350))


class TestExtractStatementYear:
    """Tests for PageHeaderAnalyser.extract_statement_year."""

    def _analyser(self) -> PageHeaderAnalyser:
        return PageHeaderAnalyser(Mock())

    def _make_full_page(self, full_text: str) -> Mock:
        """Build a mock page where extract_text() returns full_text (no crop needed)."""
        page = Mock()
        page.extract_text.return_value = full_text
        return page

    def test_payment_due_date_colon(self):
        page = self._make_full_page("Payment Due Date: 20 Feb 2026\nSome other text")
        assert self._analyser().extract_statement_year(page) == 2026

    def test_payment_due_no_colon(self):
        page = self._make_full_page("Payment Due  3 Mar 2026\nBalance: €0.00")
        assert self._analyser().extract_statement_year(page) == 2026

    def test_payment_due_date_different_year(self):
        page = self._make_full_page("Payment Due Date: 1 Jan 2025")
        assert self._analyser().extract_statement_year(page) == 2025

    def test_case_insensitive(self):
        page = self._make_full_page("PAYMENT DUE DATE: 15 Apr 2026")
        assert self._analyser().extract_statement_year(page) == 2026

    def test_returns_none_when_no_payment_due(self):
        page = self._make_full_page("Statement Date: 01 Feb 2026\nBalance: €100.00")
        assert self._analyser().extract_statement_year(page) is None

    def test_returns_none_for_empty_text(self):
        page = self._make_full_page("")
        assert self._analyser().extract_statement_year(page) is None

    def test_returns_none_for_none_text(self):
        page = self._make_full_page(None)
        assert self._analyser().extract_statement_year(page) is None

    def test_returns_none_on_page_exception(self):
        page = Mock()
        page.extract_text.side_effect = AttributeError("no text")
        assert self._analyser().extract_statement_year(page) is None

    def test_payment_due_date_with_extra_whitespace(self):
        page = self._make_full_page("Payment Due Date:  18 Feb 2026")
        assert self._analyser().extract_statement_year(page) == 2026
