"""Transaction type classification using Chain of Responsibility pattern.

This module provides transaction type classification (purchase, payment, fee, refund, etc.)
by applying a chain of specialized classifiers. Each classifier handles one specific
classification strategy and can pass to the next classifier if it doesn't match.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from bankstatements_core.utils import to_float

if TYPE_CHECKING:
    from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class TransactionTypeClassifier(ABC):
    """Base class for transaction type classification.

    Uses Chain of Responsibility pattern to allow multiple classification
    strategies to be applied in sequence until one succeeds.
    """

    def __init__(self) -> None:
        """Initialize classifier with no next classifier."""
        self._next_classifier: TransactionTypeClassifier | None = None

    def set_next(
        self, classifier: "TransactionTypeClassifier"
    ) -> "TransactionTypeClassifier":
        """Set the next classifier in the chain.

        Args:
            classifier: The next classifier to call if this one doesn't match

        Returns:
            The classifier that was set (for fluent interface)
        """
        self._next_classifier = classifier
        return classifier

    def classify(
        self, transaction: dict, template: "BankTemplate | None" = None
    ) -> str:
        """Classify transaction type, delegating to next classifier if needed.

        Args:
            transaction: Transaction dictionary
            template: Optional bank template with transaction type keywords

        Returns:
            Transaction type string: "purchase", "payment", "fee", "refund",
            "transfer", "interest", "other"
        """
        result = self._do_classify(transaction, template)
        if result:
            return result

        if self._next_classifier:
            return self._next_classifier.classify(transaction, template)

        return "other"  # Default fallback

    @abstractmethod
    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Attempt to classify the transaction.

        Returns:
            Transaction type if this classifier can classify the transaction,
            None if it should pass to the next classifier
        """
        pass


class TemplateKeywordClassifier(TransactionTypeClassifier):
    """Classifier that uses template-defined transaction type keywords.

    This classifier has highest priority as it uses bank-specific patterns
    defined in the template configuration.
    """

    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Classify using template transaction_types keyword mappings."""
        if not template or not template.processing.transaction_types:
            return None

        details = transaction.get("Details", "").upper()
        if not details:
            return None

        # Check each transaction type's keywords
        for txn_type, keywords in template.processing.transaction_types.items():
            for keyword in keywords:
                if keyword.upper() in details:
                    logger.debug(f"Template keyword match: '{keyword}' -> {txn_type}")
                    return txn_type

        return None


class CreditCardPatternClassifier(TransactionTypeClassifier):
    """Classifier for credit card specific transaction patterns.

    Only runs when document_type is "credit_card_statement".
    """

    # Credit card transaction patterns
    PURCHASE_PATTERNS = [
        "PURCHASE",
        "SALE",
        "POS",
        "CONTACTLESS",
        "ONLINE",
        "RECURRING PAYMENT",
        "SUBSCRIPTION",
        "E-COMMERCE",
    ]

    PAYMENT_PATTERNS = [
        "PAYMENT",
        "PAYMENT RECEIVED",
        "DIRECT DEBIT",
        "PAYMENT THANK YOU",
        "AUTOPAY",
    ]

    FEE_PATTERNS = [
        "FEE",
        "CHARGE",
        "INTEREST",
        "ANNUAL FEE",
        "LATE FEE",
        "FOREIGN TRANSACTION FEE",
        "CASH ADVANCE FEE",
        "OVERLIMIT FEE",
    ]

    REFUND_PATTERNS = [
        "REFUND",
        "REVERSAL",
        "CREDIT",
        "CHARGEBACK",
    ]

    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Classify credit card transactions."""
        # Only run for credit card statements
        document_type = transaction.get("document_type", "")
        if document_type != "credit_card_statement":
            return None

        details = transaction.get("Details", "").upper()
        if not details:
            return None

        # Check patterns in priority order
        if any(pattern in details for pattern in self.PURCHASE_PATTERNS):
            return "purchase"

        if any(pattern in details for pattern in self.PAYMENT_PATTERNS):
            return "payment"

        if any(pattern in details for pattern in self.FEE_PATTERNS):
            return "fee"

        if any(pattern in details for pattern in self.REFUND_PATTERNS):
            return "refund"

        return None


class BankStatementPatternClassifier(TransactionTypeClassifier):
    """Classifier for bank statement specific transaction patterns.

    Only runs when document_type is "bank_statement".
    """

    # Bank statement transaction patterns
    TRANSFER_PATTERNS = [
        "TRANSFER",
        "TRF",
        "SEPA",
        "SEPA CREDIT",
        "SEPA DEBIT",
        "WIRE",
        "ONLINE TRANSFER",
        "MOBILE TRANSFER",
    ]

    PAYMENT_PATTERNS = [
        "STANDING ORDER",
        "DIRECT DEBIT",
        "DD",
        "SO",
        "BILL PAYMENT",
    ]

    INTEREST_PATTERNS = [
        "INTEREST",
        "INT CREDIT",
        "INTEREST CREDIT",
        "INTEREST PAID",
    ]

    FEE_PATTERNS = [
        "CHARGE",
        "FEE",
        "MAINTENANCE FEE",
        "TRANSACTION FEE",
        "ATM FEE",
        "OVERDRAFT FEE",
    ]

    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Classify bank statement transactions."""
        # Only run for bank statements
        document_type = transaction.get("document_type", "")
        if document_type != "bank_statement":
            return None

        details = transaction.get("Details", "").upper()
        if not details:
            return None

        # Check patterns in priority order
        if any(pattern in details for pattern in self.TRANSFER_PATTERNS):
            return "transfer"

        if any(pattern in details for pattern in self.PAYMENT_PATTERNS):
            return "payment"

        if any(pattern in details for pattern in self.INTEREST_PATTERNS):
            return "interest"

        if any(pattern in details for pattern in self.FEE_PATTERNS):
            return "fee"

        return None


class AmountBasedClassifier(TransactionTypeClassifier):
    """Classifier using amount patterns as heuristics.

    This is a lower priority classifier that uses debit/credit patterns
    when keywords don't match.
    """

    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Classify based on amount patterns."""
        debit = transaction.get("Debit_EUR")
        credit = transaction.get("Credit_EUR")

        debit_amount = to_float(str(debit)) if debit else None
        credit_amount = to_float(str(credit)) if credit else None

        # Credit only (money in) - likely refund or transfer
        if credit_amount and credit_amount > 0 and not debit_amount:
            # Could be refund or incoming transfer
            # Without keywords, default to transfer for bank statements
            document_type = transaction.get("document_type", "")
            if document_type == "credit_card_statement":
                return "refund"  # Credits on credit cards are usually refunds
            return "transfer"  # Credits on bank accounts are usually transfers

        # Debit only (money out) - likely purchase or payment
        if debit_amount and debit_amount > 0 and not credit_amount:
            # Could be purchase or outgoing payment
            document_type = transaction.get("document_type", "")
            if document_type == "credit_card_statement":
                return "purchase"  # Debits on credit cards are usually purchases
            return "payment"  # Debits on bank accounts are usually payments

        # Zero or no amount - likely fee or interest
        if (not debit_amount or debit_amount == 0) and (
            not credit_amount or credit_amount == 0
        ):
            return "fee"

        return None


class DefaultClassifier(TransactionTypeClassifier):
    """Default classifier that returns 'other' for unclassifiable transactions.

    This should be the last classifier in the chain.
    """

    def _do_classify(
        self, transaction: dict, template: "BankTemplate | None"
    ) -> str | None:
        """Always return 'other' as default classification."""
        return "other"


def create_transaction_type_classifier_chain(
    document_type: str | None = None,
) -> TransactionTypeClassifier:
    """Build classifier chain based on document type.

    The chain is built in priority order:
    1. TemplateKeywordClassifier (highest priority - bank-specific)
    2. Document-specific classifier (CreditCard or BankStatement)
    3. AmountBasedClassifier (heuristic fallback)
    4. DefaultClassifier (catch-all)

    Args:
        document_type: Type of document ("credit_card_statement", "bank_statement", etc.)

    Returns:
        The head of the classifier chain
    """
    # Start with template classifier (highest priority)
    template_classifier = TemplateKeywordClassifier()

    # Add document-specific classifier
    document_classifier: TransactionTypeClassifier | None
    if document_type == "credit_card_statement":
        document_classifier = CreditCardPatternClassifier()
    elif document_type == "bank_statement":
        document_classifier = BankStatementPatternClassifier()
    else:
        # No document-specific classifier for unknown types
        document_classifier = None

    # Build chain
    if document_classifier:
        template_classifier.set_next(document_classifier)
        document_classifier.set_next(AmountBasedClassifier()).set_next(
            DefaultClassifier()
        )
    else:
        template_classifier.set_next(AmountBasedClassifier()).set_next(
            DefaultClassifier()
        )

    return template_classifier
