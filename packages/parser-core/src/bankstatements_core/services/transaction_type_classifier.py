"""Transaction type classification using Chain of Responsibility pattern.

This module classifies transactions into one of six types:
  income, expense, transfer, refund, cash_withdrawal, cash_deposit

Classification chain (highest to lowest priority):
  1. TemplateKeywordClassifier  — bank-specific keyword overrides
  2. CashClassifier             — ATM / cash deposit patterns
  3. Document-specific          — CreditCardPatternClassifier or BankStatementPatternClassifier
  4. AmountBasedClassifier      — heuristic fallback
  5. DefaultClassifier          — catch-all
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from bankstatements_core.utils import to_float

if TYPE_CHECKING:
    from bankstatements_core.domain.models.transaction import Transaction
    from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class TransactionTypeClassifier(ABC):
    """Base class for transaction type classification.

    Uses Chain of Responsibility pattern to allow multiple classification
    strategies to be applied in sequence until one succeeds.
    """

    def __init__(self) -> None:
        self._next_classifier: TransactionTypeClassifier | None = None

    def set_next(
        self, classifier: TransactionTypeClassifier
    ) -> TransactionTypeClassifier:
        """Set the next classifier in the chain and return it (fluent interface)."""
        self._next_classifier = classifier
        return classifier

    def classify(
        self, transaction: Transaction, template: BankTemplate | None = None
    ) -> str:
        """Classify transaction type, delegating to next classifier if needed.

        Returns one of: income, expense, transfer, refund, cash_withdrawal,
        cash_deposit, or expense as the final fallback.
        """
        result = self._do_classify(transaction, template)
        if result:
            return result

        if self._next_classifier:
            return self._next_classifier.classify(transaction, template)

        return "expense"

    @abstractmethod
    def _do_classify(
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        """Attempt to classify the transaction.

        Returns the type string if matched, None to pass to the next classifier.
        """
        pass


class TemplateKeywordClassifier(TransactionTypeClassifier):
    """Classifies using template-defined transaction type keywords (highest priority)."""

    def _do_classify(
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        if not template or not template.processing.transaction_types:
            return None

        details = transaction.details.upper()
        if not details:
            return None

        for txn_type, keywords in template.processing.transaction_types.items():
            for keyword in keywords:
                if keyword.upper() in details:
                    logger.debug(
                        "Template keyword match: '%s' -> %s", keyword, txn_type
                    )
                    return txn_type

        return None


class CashClassifier(TransactionTypeClassifier):
    """Classifies ATM withdrawals and cash deposits/lodgements."""

    WITHDRAWAL_PATTERNS = [  # noqa: RUF012
        "ATM WITHDRAWAL",
        "CASH WITHDRAWAL",
        "CASHPOINT",
        "WITHDRAWAL ATM",
        "CASH MACHINE",
        "AUTOMATED TELLER",
    ]

    DEPOSIT_PATTERNS = [  # noqa: RUF012
        "LODGEMENT",
        "LODGMENT",
        "CASH DEPOSIT",
        "CASH LODGEMENT",
        "DEPOSIT ATM",
        "CASH IN",
    ]

    def _do_classify(
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        details = transaction.details.upper()
        if not details:
            return None

        # Check deposits first — "CASH DEPOSIT ATM" must not match ATM-withdrawal patterns
        if any(pattern in details for pattern in self.DEPOSIT_PATTERNS):
            return "cash_deposit"

        if any(pattern in details for pattern in self.WITHDRAWAL_PATTERNS):
            return "cash_withdrawal"

        return None


class CreditCardPatternClassifier(TransactionTypeClassifier):
    """Classifies credit card specific transaction patterns.

    Only runs when document_type is "credit_card_statement".
    """

    REFUND_PATTERNS = [  # noqa: RUF012
        "REFUND",
        "REVERSAL",
        "CHARGEBACK",
    ]

    PURCHASE_PATTERNS = [  # noqa: RUF012
        "PURCHASE",
        "SALE",
        "POS",
        "CONTACTLESS",
        "ONLINE",
        "RECURRING PAYMENT",
        "SUBSCRIPTION",
        "E-COMMERCE",
    ]

    PAYMENT_PATTERNS = [  # noqa: RUF012
        "PAYMENT RECEIVED",
        "PAYMENT THANK YOU",
        "AUTOPAY",
        "DIRECT DEBIT",
    ]

    FEE_PATTERNS = [  # noqa: RUF012
        "ANNUAL FEE",
        "LATE FEE",
        "FOREIGN TRANSACTION FEE",
        "CASH ADVANCE FEE",
        "OVERLIMIT FEE",
        "INTEREST CHARGED",
        "FINANCE CHARGE",
    ]

    def _do_classify(  # noqa: PLR0911
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        if transaction.document_type != "credit_card_statement":
            return None

        details = transaction.details.upper()
        if not details:
            return None

        if any(pattern in details for pattern in self.REFUND_PATTERNS):
            return "refund"

        if any(pattern in details for pattern in self.PURCHASE_PATTERNS):
            return "expense"

        if any(pattern in details for pattern in self.PAYMENT_PATTERNS):
            return "transfer"

        if any(pattern in details for pattern in self.FEE_PATTERNS):
            return "expense"

        return None


class BankStatementPatternClassifier(TransactionTypeClassifier):
    """Classifies bank statement specific transaction patterns.

    Only runs when document_type is "bank_statement".
    """

    REFUND_PATTERNS = [  # noqa: RUF012
        "REFUND",
        "REVERSAL",
        "CHARGEBACK",
    ]

    INCOME_PATTERNS = [  # noqa: RUF012
        "SALARY",
        "WAGES",
        "PAYROLL",
        "DIVIDEND",
        "BONUS",
        "PENSION",
        "WELFARE",
        "BURSARY",
        "GRANT",
    ]

    TRANSFER_PATTERNS = [  # noqa: RUF012
        "TRANSFER",
        "TRF",
        "SEPA",
        "WIRE",
        "ONLINE TRANSFER",
        "MOBILE TRANSFER",
    ]

    EXPENSE_PATTERNS = [  # noqa: RUF012
        "STANDING ORDER",
        "DIRECT DEBIT",
        "BILL PAYMENT",
        "MAINTENANCE FEE",
        "TRANSACTION FEE",
        "ATM FEE",
        "OVERDRAFT FEE",
        "ACCOUNT FEE",
        "SERVICE CHARGE",
    ]

    INTEREST_INCOME_PATTERNS = [  # noqa: RUF012
        "INTEREST CREDIT",
        "INT CREDIT",
        "INTEREST PAID",
    ]

    INTEREST_EXPENSE_PATTERNS = [  # noqa: RUF012
        "OVERDRAFT INTEREST",
        "INTEREST CHARGED",
        "DEBIT INTEREST",
    ]

    def _do_classify(  # noqa: PLR0911  # pylint: disable=too-many-return-statements
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        if transaction.document_type != "bank_statement":
            return None

        details = transaction.details.upper()
        if not details:
            return None

        if any(pattern in details for pattern in self.REFUND_PATTERNS):
            return "refund"

        if any(pattern in details for pattern in self.INCOME_PATTERNS):
            return "income"

        if any(pattern in details for pattern in self.TRANSFER_PATTERNS):
            return "transfer"

        if any(pattern in details for pattern in self.INTEREST_INCOME_PATTERNS):
            return "income"

        if any(pattern in details for pattern in self.INTEREST_EXPENSE_PATTERNS):
            return "expense"

        if any(pattern in details for pattern in self.EXPENSE_PATTERNS):
            return "expense"

        return None


class AmountBasedClassifier(TransactionTypeClassifier):
    """Classifies using debit/credit direction as a last-resort heuristic.

    By the time this classifier runs, explicit patterns for transfer, refund,
    cash, and income have already been checked. Unmatched credits are treated
    as income; unmatched debits as expenses.
    """

    def _do_classify(
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        debit_amount = to_float(str(transaction.debit)) if transaction.debit else None
        credit_amount = (
            to_float(str(transaction.credit)) if transaction.credit else None
        )

        if credit_amount and credit_amount > 0 and not debit_amount:
            if transaction.document_type == "credit_card_statement":
                return "refund"
            return "income"

        if debit_amount and debit_amount > 0 and not credit_amount:
            return "expense"

        return None


class DefaultClassifier(TransactionTypeClassifier):
    """Catch-all classifier — returns 'expense' for any unclassified transaction."""

    def _do_classify(
        self, transaction: Transaction, template: BankTemplate | None
    ) -> str | None:
        return "expense"


def create_transaction_type_classifier_chain(
    document_type: str | None = None,
) -> TransactionTypeClassifier:
    """Build classifier chain based on document type.

    Chain (in priority order):
      1. TemplateKeywordClassifier  — bank-specific overrides
      2. CashClassifier             — ATM / lodgement patterns
      3. CreditCardPatternClassifier or BankStatementPatternClassifier
      4. AmountBasedClassifier      — direction heuristic
      5. DefaultClassifier          — catch-all

    Args:
        document_type: "credit_card_statement", "bank_statement", or other/None

    Returns:
        Head of the classifier chain
    """
    template_classifier = TemplateKeywordClassifier()
    cash_classifier = CashClassifier()
    amount_classifier = AmountBasedClassifier()
    default_classifier = DefaultClassifier()

    template_classifier.set_next(cash_classifier)

    if document_type == "credit_card_statement":
        doc_classifier: TransactionTypeClassifier = CreditCardPatternClassifier()
        cash_classifier.set_next(doc_classifier)
        doc_classifier.set_next(amount_classifier)
    elif document_type == "bank_statement":
        doc_classifier = BankStatementPatternClassifier()
        cash_classifier.set_next(doc_classifier)
        doc_classifier.set_next(amount_classifier)
    else:
        cash_classifier.set_next(amount_classifier)

    amount_classifier.set_next(default_classifier)

    return template_classifier
