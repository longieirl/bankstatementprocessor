"""ServiceRegistry — single wiring point for transaction processing services.

Centralises construction of duplicate detection, sorting, IBAN grouping, and
the enrichment/classification pipeline.

Usage (primary path)::

    registry = ServiceRegistry.from_config(processor_config, entitlements)
    unique, dupes = registry.process_transaction_group(rows, template)
    grouped = registry.group_by_iban(rows, pdf_ibans)

Escape hatches are available for callers that need individual services::

    detector = registry.get_duplicate_detector()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bankstatements_core.config.processor_config import ProcessorConfig
    from bankstatements_core.domain.protocols.services import (
        IDuplicateDetector,
        IIBANGrouping,
        ITransactionSorting,
    )
    from bankstatements_core.entitlements import Entitlements
    from bankstatements_core.templates.template_model import BankTemplate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ServiceContext:
    """Shared dependencies passed once to ServiceRegistry at construction time.

    This is an internal dataclass — never exposed to callers.
    """

    column_names: list[str]
    debit_columns: list[str]
    credit_columns: list[str]
    entitlements: Any  # Entitlements | None


class ServiceRegistry:
    """Single wiring point for all transaction processing services.

    Callers use the primary methods for the common case.
    Individual services are accessible via get_*() escape hatches for tests
    or specialised callers.
    """

    def __init__(
        self,
        context: _ServiceContext,
        duplicate_detector: "IDuplicateDetector",
        sorting_service: "ITransactionSorting",
        grouping_service: "IIBANGrouping",
    ) -> None:
        self._context = context
        self._duplicate_detector = duplicate_detector
        self._sorting_service = sorting_service
        self._grouping_service = grouping_service

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        config: "ProcessorConfig",
        entitlements: "Entitlements | None" = None,
        duplicate_detector: "IDuplicateDetector | None" = None,
        sorting_service: "ITransactionSorting | None" = None,
        grouping_service: "IIBANGrouping | None" = None,
    ) -> "ServiceRegistry":
        """Build a ServiceRegistry from a ProcessorConfig.

        Args:
            config: Processor configuration carrying column, sorting, and
                processing settings.
            entitlements: Optional tier-based entitlements.
            duplicate_detector: Override duplicate detector (default: AllFields).
            sorting_service: Override sorting service (default: chronological
                if config.processing.sort_by_date, else no-sort).
            grouping_service: Override IBAN grouping service (default: suffix-4).

        Returns:
            Fully wired ServiceRegistry instance.
        """
        from bankstatements_core.config.column_config import get_column_names
        from bankstatements_core.patterns.strategies import AllFieldsDuplicateStrategy
        from bankstatements_core.processor import find_matching_columns
        from bankstatements_core.services.duplicate_detector import (
            DuplicateDetectionService,
        )
        from bankstatements_core.services.iban_grouping import IBANGroupingService
        from bankstatements_core.services.sorting_service import (
            ChronologicalSortingStrategy,
            NoSortingStrategy,
            TransactionSortingService,
        )

        column_names = (
            get_column_names(config.extraction.columns)
            if config.extraction.columns
            else []
        )
        debit_columns = find_matching_columns(column_names, ["debit"])
        credit_columns = find_matching_columns(column_names, ["credit"])

        context = _ServiceContext(
            column_names=column_names,
            debit_columns=debit_columns,
            credit_columns=credit_columns,
            entitlements=entitlements,
        )

        if duplicate_detector is None:
            duplicate_detector = DuplicateDetectionService(AllFieldsDuplicateStrategy())

        if sorting_service is None:
            sort_strategy = (
                ChronologicalSortingStrategy()
                if config.processing.sort_by_date
                else NoSortingStrategy()
            )
            sorting_service = TransactionSortingService(sort_strategy)

        if grouping_service is None:
            grouping_service = IBANGroupingService()

        return cls(context, duplicate_detector, sorting_service, grouping_service)

    # ------------------------------------------------------------------
    # Primary methods (80 % case)
    # ------------------------------------------------------------------

    def process_transaction_group(
        self,
        transactions: list[dict],
        template: "BankTemplate | None" = None,
    ) -> tuple[list[dict], list[dict]]:
        """Enrich → classify → deduplicate → sort a group of transactions.

        Args:
            transactions: List of transaction dicts for a single IBAN group.
            template: Optional bank template used for transaction type keywords.

        Returns:
            Tuple of (unique_transactions, duplicate_transactions).
        """
        enriched = self._enrich_with_filename(transactions)
        enriched = self._enrich_with_document_type(enriched)
        enriched = self._classify_transaction_types(enriched, template)

        unique_rows, duplicate_rows = self._duplicate_detector.detect_and_separate(
            enriched
        )
        logger.info(
            "Duplicate detection: %d unique, %d duplicates",
            len(unique_rows),
            len(duplicate_rows),
        )

        sorted_rows = self._sorting_service.sort(unique_rows)
        return sorted_rows, duplicate_rows

    def group_by_iban(
        self,
        transactions: list[dict],
        pdf_ibans: dict[str, str],
    ) -> dict[str, list[dict]]:
        """Group transactions by IBAN suffix.

        Args:
            transactions: Flat list of all transaction dicts.
            pdf_ibans: Mapping of PDF filename → IBAN string.

        Returns:
            Dict of IBAN suffix → list of transaction dicts.
        """
        return self._grouping_service.group_by_iban(transactions, pdf_ibans)

    # ------------------------------------------------------------------
    # Escape hatches (20 % case)
    # ------------------------------------------------------------------

    def get_duplicate_detector(self) -> "IDuplicateDetector":
        return self._duplicate_detector

    def get_sorting_service(self) -> "ITransactionSorting":
        return self._sorting_service

    def get_grouping_service(self) -> "IIBANGrouping":
        return self._grouping_service

    # ------------------------------------------------------------------
    # Internal enrichment helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enrich_with_filename(transactions: list[dict]) -> list[dict]:
        """Set Filename key from source_pdf if not already present."""
        for row in transactions:
            if "Filename" not in row:
                row["Filename"] = row.get("source_pdf", "")
        return transactions

    @staticmethod
    def _enrich_with_document_type(
        transactions: list[dict], default_type: str = "bank_statement"
    ) -> list[dict]:
        """Set document_type if not already present."""
        for row in transactions:
            if "document_type" not in row:
                row["document_type"] = default_type
        return transactions

    @staticmethod
    def _classify_transaction_types(
        transactions: list[dict],
        template: "BankTemplate | None" = None,
    ) -> list[dict]:
        """Classify each transaction using Chain of Responsibility."""
        from bankstatements_core.services.transaction_type_classifier import (
            create_transaction_type_classifier_chain,
        )

        if not transactions:
            return transactions

        document_type = transactions[0].get("document_type")
        classifier = create_transaction_type_classifier_chain(document_type)

        for transaction in transactions:
            transaction["transaction_type"] = classifier.classify(transaction, template)

        logger.info(
            "Transaction type classification: %d transactions classified",
            len(transactions),
        )
        return transactions
