"""Transaction Processing Orchestrator for bank statements.

This module orchestrates IBAN grouping. Enrichment, classification, duplicate
detection and sorting have moved to ServiceRegistry.

Note: This class is retained for backward compatibility. A follow-up issue will
track its complete removal once all callers migrate to ServiceRegistry.
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

logger = logging.getLogger(__name__)


class TransactionProcessingOrchestrator:
    """Orchestrates IBAN grouping for transaction processing.

    Note: enrichment and classification logic has moved to ServiceRegistry.
    This class is retained for backward compatibility and will be removed in a
    follow-up.
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
        """
        return self.grouping_service.group_by_iban(transactions, pdf_ibans)
