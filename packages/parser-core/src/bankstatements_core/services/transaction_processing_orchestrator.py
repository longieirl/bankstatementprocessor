"""Transaction Processing Orchestrator for bank statements.

This module orchestrates transaction-level processing including:
- IBAN grouping
- Duplicate detection
- Sorting
- Filename enrichment
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bankstatements_core.domain.protocols.services import (
        IDuplicateDetector,
        IIBANGrouping,
        ITransactionSorting,
    )
    from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


class TransactionProcessingOrchestrator:
    """Orchestrates transaction processing pipeline.

    Handles:
    - Grouping transactions by IBAN
    - Duplicate detection and removal
    - Transaction sorting (chronological or none)
    - Enrichment with source filename
    """

    def __init__(
        self,
        duplicate_detector: "IDuplicateDetector",
        sorting_service: "ITransactionSorting",
        grouping_service: "IIBANGrouping | None" = None,
    ):
        """Initialize transaction processing orchestrator.

        Args:
            duplicate_detector: Service for detecting duplicates
            sorting_service: Service for sorting transactions
            grouping_service: Service for grouping by IBAN (optional, creates default if None)
        """
        from bankstatements_core.services.iban_grouping import IBANGroupingService

        self.duplicate_detector = duplicate_detector
        self.sorting_service = sorting_service
        self.grouping_service = grouping_service or IBANGroupingService()

    def group_by_iban(
        self, transactions: list[dict], pdf_ibans: dict[str, str]
    ) -> dict[str, list[dict]]:
        """Group transactions by their source IBAN.

        Args:
            transactions: List of transaction dictionaries
            pdf_ibans: Dictionary mapping PDF filenames to IBANs

        Returns:
            Dictionary mapping IBANs to their transactions

        Examples:
            >>> orchestrator = TransactionProcessingOrchestrator(detector, sorter)
            >>> grouped = orchestrator.group_by_iban(transactions, ibans)
            >>> for iban, txns in grouped.items():
            ...     print(f"IBAN {iban}: {len(txns)} transactions")
        """
        return self.grouping_service.group_by_iban(transactions, pdf_ibans)

    def process_transaction_group(
        self, transactions: list[dict], template: "BankTemplate | None" = None
    ) -> tuple[list[dict], list[dict]]:
        """Process a group of transactions (detect duplicates, sort, enrich).

        Args:
            transactions: List of transaction dictionaries
            template: Optional bank template with transaction type keywords

        Returns:
            Tuple of (unique_transactions, duplicate_transactions)

        Examples:
            >>> orchestrator = TransactionProcessingOrchestrator(detector, sorter)
            >>> unique, dupes = orchestrator.process_transaction_group(transactions)
            >>> total = len(unique) + len(dupes)
            >>> print(f"Found {len(dupes)} duplicates in {total} transactions")
        """
        # 0. Enrich with metadata (filename, document_type, transaction_type)
        enriched = self.enrich_with_filename(transactions)
        enriched = self.enrich_with_document_type(enriched)
        enriched = self.classify_transaction_types(enriched, template)

        # 1. Detect duplicates (now with transaction_type available)
        unique_rows, duplicate_rows = self.duplicate_detector.detect_and_separate(
            enriched
        )

        logger.info(
            "Duplicate detection: %d unique, %d duplicates",
            len(unique_rows),
            len(duplicate_rows),
        )

        # 2. Sort transactions if configured
        sorted_rows = self.sorting_service.sort(unique_rows)

        return sorted_rows, duplicate_rows

    def enrich_with_filename(self, transactions: list[dict]) -> list[dict]:
        """Add 'Filename' column to transactions if not present.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Transactions with 'Filename' column added

        Examples:
            >>> orchestrator = TransactionProcessingOrchestrator(detector, sorter)
            >>> enriched = orchestrator.enrich_with_filename(transactions)
            >>> all('Filename' in txn for txn in enriched)
            True
        """
        for row in transactions:
            if "Filename" not in row:
                row["Filename"] = row.get("source_pdf", "")

        return transactions

    def enrich_with_document_type(
        self, transactions: list[dict], default_type: str = "bank_statement"
    ) -> list[dict]:
        """Add 'document_type' column to transactions if not present.

        Args:
            transactions: List of transaction dictionaries
            default_type: Default document type if missing (default: "bank_statement")

        Returns:
            Transactions with document_type field

        Examples:
            >>> orchestrator = TransactionProcessingOrchestrator(detector, sorter)
            >>> enriched = orchestrator.enrich_with_document_type(transactions)
            >>> all('document_type' in txn for txn in enriched)
            True
        """
        for row in transactions:
            if "document_type" not in row:
                row["document_type"] = default_type

        return transactions

    def classify_transaction_types(
        self, transactions: list[dict], template: "BankTemplate | None" = None
    ) -> list[dict]:
        """Classify transaction type for each transaction.

        Uses Chain of Responsibility pattern to apply multiple classification
        strategies in sequence until one succeeds.

        Args:
            transactions: List of transaction dictionaries
            template: Optional bank template with transaction type keywords

        Returns:
            Transactions with transaction_type field added

        Examples:
            >>> orchestrator = TransactionProcessingOrchestrator(detector, sorter)
            >>> enriched = orchestrator.classify_transaction_types(transactions, template)
            >>> all('transaction_type' in txn for txn in enriched)
            True
        """
        from bankstatements_core.services.transaction_type_classifier import (
            create_transaction_type_classifier_chain,
        )

        if not transactions:
            return transactions

        # Get document type from first transaction (all in group have same type)
        document_type = transactions[0].get("document_type")

        # Create classifier chain appropriate for document type
        classifier = create_transaction_type_classifier_chain(document_type)

        # Classify each transaction
        for transaction in transactions:
            transaction["transaction_type"] = classifier.classify(transaction, template)

        logger.info(
            "Transaction type classification: %d transactions classified",
            len(transactions),
        )

        return transactions
