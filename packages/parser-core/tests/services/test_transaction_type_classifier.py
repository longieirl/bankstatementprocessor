"""Tests for transaction type classification using Chain of Responsibility pattern."""

from __future__ import annotations

import pytest

from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.transaction_type_classifier import (
    AmountBasedClassifier,
    BankStatementPatternClassifier,
    CashClassifier,
    CreditCardPatternClassifier,
    DefaultClassifier,
    TemplateKeywordClassifier,
    create_transaction_type_classifier_chain,
)
from bankstatements_core.templates.template_model import BankTemplate

# ---- Fixtures ----


@pytest.fixture
def credit_card_template():
    """Template with credit card transaction type keywords."""
    from dataclasses import replace

    from bankstatements_core.templates.template_model import (
        TemplateDetectionConfig,
        TemplateExtractionConfig,
    )

    template = BankTemplate(
        id="test_cc",
        name="Test Credit Card",
        enabled=True,
        detection=TemplateDetectionConfig(filename_patterns=["*.pdf"]),
        extraction=TemplateExtractionConfig(
            table_top_y=100, table_bottom_y=700, columns={"Date": (0, 100)}
        ),
        document_type="credit_card_statement",
    )

    template.processing = replace(
        template.processing,
        transaction_types={
            "expense": ["POS", "CONTACTLESS", "ONLINE", "ANNUAL FEE", "LATE FEE"],
            "transfer": ["PAYMENT RECEIVED", "DIRECT DEBIT"],
            "refund": ["REFUND", "CREDIT"],
        },
    )

    return template


@pytest.fixture
def bank_template():
    """Template with bank statement transaction type keywords."""
    from dataclasses import replace

    from bankstatements_core.templates.template_model import (
        TemplateDetectionConfig,
        TemplateExtractionConfig,
    )

    template = BankTemplate(
        id="test_bank",
        name="Test Bank",
        enabled=True,
        detection=TemplateDetectionConfig(filename_patterns=["*.pdf"]),
        extraction=TemplateExtractionConfig(
            table_top_y=100, table_bottom_y=700, columns={"Date": (0, 100)}
        ),
        document_type="bank_statement",
    )

    template.processing = replace(
        template.processing,
        transaction_types={
            "transfer": ["SEPA", "TRANSFER"],
            "expense": ["DIRECT DEBIT", "STANDING ORDER"],
            "income": ["INTEREST CREDIT"],
        },
    )

    return template


# ---- TemplateKeywordClassifier Tests ----


class TestTemplateKeywordClassifier:
    """Test template-based classification with keyword matching."""

    def test_classify_expense_with_template_keyword(self, credit_card_template):
        """Should classify as expense when Details contains template POS keyword."""
        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {"Date": "01/12/2023", "Details": "POS TESCO STORES", "Debit_AMT": "45.23"}
        )

        result = classifier.classify(transaction, credit_card_template)

        assert result == "expense"

    def test_classify_refund_with_template_keywords(self, credit_card_template):
        """Should classify as refund when Details contains refund keyword."""
        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "10/12/2023",
                "Details": "REFUND AMAZON.COM",
                "Credit_AMT": "15.00",
            }
        )

        result = classifier.classify(transaction, credit_card_template)

        assert result == "refund"

    def test_case_insensitive_matching(self, credit_card_template):
        """Should match keywords case-insensitively."""
        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "contactless payment at shop",
                "Debit_AMT": "12.50",
            }
        )

        result = classifier.classify(transaction, credit_card_template)

        assert result == "expense"

    def test_returns_none_when_no_match(self, credit_card_template):
        """Should return None when no keyword matches."""
        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "UNKNOWN TRANSACTION TYPE",
                "Debit_AMT": "10.00",
            }
        )

        result = classifier._do_classify(transaction, credit_card_template)

        assert result is None

    def test_returns_none_when_no_template(self):
        """Should return None when no template provided."""
        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {"Date": "01/12/2023", "Details": "POS TESCO", "Debit_AMT": "45.23"}
        )

        result = classifier._do_classify(transaction, None)

        assert result is None

    def test_returns_none_when_template_has_no_keywords(self):
        """Should return None when template has no transaction_types."""
        from bankstatements_core.templates.template_model import (
            TemplateDetectionConfig,
            TemplateExtractionConfig,
        )

        template = BankTemplate(
            id="test",
            name="Test",
            enabled=True,
            detection=TemplateDetectionConfig(filename_patterns=["*.pdf"]),
            extraction=TemplateExtractionConfig(
                table_top_y=100, table_bottom_y=700, columns={"Date": (0, 100)}
            ),
        )

        classifier = TemplateKeywordClassifier()
        transaction = Transaction.from_dict(
            {"Date": "01/12/2023", "Details": "POS TESCO", "Debit_AMT": "45.23"}
        )

        result = classifier._do_classify(transaction, template)

        assert result is None


# ---- CashClassifier Tests ----


class TestCashClassifier:
    """Test ATM and cash deposit/lodgement classification."""

    def test_atm_withdrawal_classified_as_cash_withdrawal(self):
        """Should classify ATM WITHDRAWAL as cash_withdrawal."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "ATM WITHDRAWAL O CONNELL ST",
                "Debit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "cash_withdrawal"

    def test_cash_machine_classified_as_cash_withdrawal(self):
        """Should classify CASH MACHINE as cash_withdrawal."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "CASH MACHINE DAME STREET",
                "Debit_AMT": "50.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "cash_withdrawal"

    def test_lodgement_classified_as_cash_deposit(self):
        """Should classify LODGEMENT as cash_deposit."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "LODGEMENT BRANCH",
                "Credit_AMT": "200.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "cash_deposit"

    def test_cash_deposit_classified_as_cash_deposit(self):
        """Should classify CASH DEPOSIT as cash_deposit."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "05/12/2023",
                "Details": "CASH DEPOSIT ATM",
                "Credit_AMT": "150.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "cash_deposit"

    def test_non_cash_returns_none(self):
        """Should return None for regular transactions."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "TESCO STORES",
                "Debit_AMT": "45.23",
                "document_type": "bank_statement",
            }
        )

        result = classifier._do_classify(transaction, None)

        assert result is None

    def test_cashpoint_classified_as_cash_withdrawal(self):
        """Should classify CASHPOINT as cash_withdrawal."""
        classifier = CashClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "02/12/2023",
                "Details": "CASHPOINT GRAFTON ST",
                "Debit_AMT": "60.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "cash_withdrawal"


# ---- CreditCardPatternClassifier Tests ----


class TestCreditCardPatternClassifier:
    """Test credit card specific pattern classification."""

    def test_classify_pos_as_expense(self):
        """Should classify POS transactions as expense."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO STORES",
                "Debit_AMT": "45.23",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_online_as_expense(self):
        """Should classify ONLINE transactions as expense."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "ONLINE AMAZON.COM",
                "Debit_AMT": "25.99",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_payment_received_as_transfer(self):
        """Should classify payment received as transfer."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "05/12/2023",
                "Details": "PAYMENT RECEIVED THANK YOU",
                "Credit_AMT": "500.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "transfer"

    def test_classify_annual_fee_as_expense(self):
        """Should classify annual fee as expense."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/01/2024",
                "Details": "ANNUAL FEE",
                "Debit_AMT": "12.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_refund(self):
        """Should classify refund transactions as refund."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "10/12/2023",
                "Details": "REFUND AMAZON.COM",
                "Credit_AMT": "15.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "refund"

    def test_classify_reversal_as_refund(self):
        """Should classify REVERSAL as refund."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "12/12/2023",
                "Details": "REVERSAL CHARGE",
                "Credit_AMT": "30.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "refund"

    def test_only_runs_for_credit_card_statements(self):
        """Should not classify non-credit card statements."""
        classifier = CreditCardPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO STORES",
                "Debit_AMT": "45.23",
                "document_type": "bank_statement",
            }
        )

        result = classifier._do_classify(transaction, None)

        assert result is None


# ---- BankStatementPatternClassifier Tests ----


class TestBankStatementPatternClassifier:
    """Test bank statement specific pattern classification."""

    def test_classify_sepa_as_transfer(self):
        """Should classify SEPA transactions as transfer."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "SEPA CREDIT FROM JOHN DOE",
                "Credit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "transfer"

    def test_classify_direct_debit_as_expense(self):
        """Should classify direct debit as expense."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "05/12/2023",
                "Details": "DIRECT DEBIT ELECTRICITY COMPANY",
                "Debit_AMT": "75.50",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_standing_order_as_expense(self):
        """Should classify standing order as expense."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "STANDING ORDER RENT",
                "Debit_AMT": "1200.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_interest_credit_as_income(self):
        """Should classify interest credit as income."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "31/12/2023",
                "Details": "INTEREST CREDIT",
                "Credit_AMT": "2.50",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "income"

    def test_classify_overdraft_interest_as_expense(self):
        """Should classify overdraft interest as expense."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "31/12/2023",
                "Details": "OVERDRAFT INTEREST",
                "Debit_AMT": "5.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_classify_salary_as_income(self):
        """Should classify SALARY credit as income."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "28/12/2023",
                "Details": "SALARY ACME CORP",
                "Credit_AMT": "3500.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "income"

    def test_classify_wages_as_income(self):
        """Should classify WAGES credit as income."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "28/12/2023",
                "Details": "WAGES WEEKLY",
                "Credit_AMT": "800.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "income"

    def test_classify_dividend_as_income(self):
        """Should classify DIVIDEND credit as income."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "15/12/2023",
                "Details": "DIVIDEND PAYMENT SHARES",
                "Credit_AMT": "120.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "income"

    def test_classify_refund_as_refund(self):
        """Should classify REFUND credit as refund."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "10/12/2023",
                "Details": "REFUND ONLINE SHOP",
                "Credit_AMT": "25.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "refund"

    def test_only_runs_for_bank_statements(self):
        """Should not classify non-bank statements."""
        classifier = BankStatementPatternClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "SEPA CREDIT",
                "Credit_AMT": "100.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier._do_classify(transaction, None)

        assert result is None


# ---- AmountBasedClassifier Tests ----


class TestAmountBasedClassifier:
    """Test amount-based heuristic classification."""

    def test_debit_only_credit_card_classified_as_expense(self):
        """Should classify debit-only credit card transaction as expense."""
        classifier = AmountBasedClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "MERCHANT NAME",
                "Debit_AMT": "50.00",
                "Credit_AMT": None,
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_credit_only_credit_card_classified_as_refund(self):
        """Should classify credit-only credit card transaction as refund."""
        classifier = AmountBasedClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "MERCHANT NAME",
                "Debit_AMT": None,
                "Credit_AMT": "25.00",
                "document_type": "credit_card_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "refund"

    def test_debit_only_bank_statement_classified_as_expense(self):
        """Should classify debit-only bank statement transaction as expense."""
        classifier = AmountBasedClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "MERCHANT NAME",
                "Debit_AMT": "50.00",
                "Credit_AMT": None,
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"

    def test_credit_only_bank_statement_classified_as_income(self):
        """Should classify unmatched bank credit as income (last resort after pattern checks)."""
        classifier = AmountBasedClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "MYSTERY CREDIT",
                "Debit_AMT": None,
                "Credit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        result = classifier.classify(transaction, None)

        assert result == "income"

    def test_zero_amount_falls_through_to_default(self):
        """Zero/no amount should pass through to DefaultClassifier."""
        classifier = AmountBasedClassifier()
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "MONTHLY CHARGE",
                "Debit_AMT": "0.00",
                "Credit_AMT": None,
            }
        )

        result = classifier._do_classify(transaction, None)

        assert result is None


# ---- DefaultClassifier Tests ----


class TestDefaultClassifier:
    """Test default fallback classifier."""

    def test_always_returns_expense(self):
        """Should always return 'expense' as default catch-all."""
        classifier = DefaultClassifier()
        transaction = Transaction.from_dict(
            {"Date": "01/12/2023", "Details": "UNCLASSIFIABLE TRANSACTION"}
        )

        result = classifier.classify(transaction, None)

        assert result == "expense"


# ---- Chain Integration Tests ----


class TestClassifierChain:
    """Test chain of responsibility integration."""

    def test_chain_stops_at_first_match(self, credit_card_template):
        """Should stop at first classifier that matches."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "POS TESCO STORES",
                "Debit_AMT": "45.23",
                "document_type": "credit_card_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("credit_card_statement")
        result = chain.classify(transaction, credit_card_template)

        assert result == "expense"

    def test_cash_classifier_intercepts_before_document_classifier(self):
        """CashClassifier should intercept ATM withdrawal before document classifier."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "ATM WITHDRAWAL O CONNELL ST",
                "Debit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, None)

        assert result == "cash_withdrawal"

    def test_cash_deposit_classified_correctly(self):
        """Chain should classify lodgement as cash_deposit."""
        transaction = Transaction.from_dict(
            {
                "Date": "03/12/2023",
                "Details": "LODGEMENT BRANCH DUBLIN",
                "Credit_AMT": "500.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, None)

        assert result == "cash_deposit"

    def test_salary_classified_as_income(self):
        """Chain should classify salary as income."""
        transaction = Transaction.from_dict(
            {
                "Date": "28/12/2023",
                "Details": "SALARY ACME CORP LTD",
                "Credit_AMT": "3500.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, None)

        assert result == "income"

    def test_chain_falls_through_to_default(self):
        """Should fall through to default when nothing matches."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "UNKNOWN PATTERN",
                "document_type": "unknown_type",
            }
        )

        chain = create_transaction_type_classifier_chain("unknown_type")
        result = chain.classify(transaction, None)

        assert result == "expense"

    def test_factory_creates_correct_chain_for_credit_cards(self):
        """Should classify CONTACTLESS as expense via CC chain."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "CONTACTLESS PAYMENT",
                "Debit_AMT": "12.50",
                "document_type": "credit_card_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("credit_card_statement")
        result = chain.classify(transaction, None)

        assert result == "expense"

    def test_factory_creates_correct_chain_for_bank_statements(self):
        """Should classify SEPA TRANSFER as transfer via bank statement chain."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "SEPA TRANSFER FROM JOHN",
                "Credit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, None)

        assert result == "transfer"

    def test_chain_without_document_type(self):
        """Should handle None document type gracefully."""
        transaction = Transaction.from_dict(
            {"Date": "01/12/2023", "Details": "SOME TRANSACTION", "Debit_AMT": "50.00"}
        )

        chain = create_transaction_type_classifier_chain(None)
        result = chain.classify(transaction, None)

        assert result in ("expense", "income")

    def test_template_keywords_take_priority_over_patterns(self, bank_template):
        """Template keywords should take priority over generic patterns."""
        transaction = Transaction.from_dict(
            {
                "Date": "01/12/2023",
                "Details": "SEPA CREDIT",
                "Credit_AMT": "100.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, bank_template)

        assert result == "transfer"

    def test_credit_card_payment_classified_as_transfer(self):
        """Paying off CC balance should classify as transfer."""
        transaction = Transaction.from_dict(
            {
                "Date": "15/12/2023",
                "Details": "PAYMENT RECEIVED THANK YOU",
                "Credit_AMT": "800.00",
                "document_type": "credit_card_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("credit_card_statement")
        result = chain.classify(transaction, None)

        assert result == "transfer"

    def test_unmatched_bank_credit_classified_as_income(self):
        """Unmatched bank credit (no transfer/refund/cash pattern) should be income."""
        transaction = Transaction.from_dict(
            {
                "Date": "20/12/2023",
                "Details": "PAYMENT FROM CUSTOMER ABC",
                "Credit_AMT": "500.00",
                "document_type": "bank_statement",
            }
        )

        chain = create_transaction_type_classifier_chain("bank_statement")
        result = chain.classify(transaction, None)

        assert result == "income"
