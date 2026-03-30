"""Boundary tests for ServiceRegistry.

Covers:
- from_config builds a fully wired registry
- process_transaction_group runs enrich → classify → dedup → sort
- group_by_iban delegates to grouping service
- escape hatches return the injected services
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

from bankstatements_core.config.processor_config import (
    ExtractionConfig,
    OutputConfig,
    ProcessingConfig,
    ProcessorConfig,
)
from bankstatements_core.domain.models.transaction import Transaction
from bankstatements_core.services.duplicate_detector import DuplicateDetectionService
from bankstatements_core.services.iban_grouping import IBANGroupingService
from bankstatements_core.services.service_registry import ServiceRegistry
from bankstatements_core.services.sorting_service import TransactionSortingService


def _minimal_config(sort_by_date: bool = True) -> ProcessorConfig:
    tmp = Path(tempfile.mkdtemp())
    return ProcessorConfig(
        input_dir=tmp,
        output_dir=tmp,
        extraction=ExtractionConfig(),
        processing=ProcessingConfig(sort_by_date=sort_by_date),
        output=OutputConfig(),
    )


class TestFromConfig:
    def test_builds_registry_with_default_services(self):
        config = _minimal_config()
        registry = ServiceRegistry.from_config(config)
        assert isinstance(registry.get_duplicate_detector(), DuplicateDetectionService)
        assert isinstance(registry.get_sorting_service(), TransactionSortingService)
        assert isinstance(registry.get_grouping_service(), IBANGroupingService)

    def test_injected_services_override_defaults(self):
        config = _minimal_config()
        mock_dedup = Mock()
        mock_sort = Mock()
        mock_group = Mock()
        registry = ServiceRegistry.from_config(
            config,
            duplicate_detector=mock_dedup,
            sorting_service=mock_sort,
            grouping_service=mock_group,
        )
        assert registry.get_duplicate_detector() is mock_dedup
        assert registry.get_sorting_service() is mock_sort
        assert registry.get_grouping_service() is mock_group


class TestProcessTransactionGroup:
    def test_enriches_classifies_deduplicates_and_sorts(self):
        config = _minimal_config()
        transactions = [
            Transaction.from_dict(
                {"Date": "01/01/2024", "Details": "Test", "source_pdf": "a.pdf"}
            ),
        ]

        mock_dedup = Mock()
        mock_dedup.detect_and_separate.return_value = (transactions, [])
        mock_sort = Mock()
        mock_sort.sort.side_effect = lambda x: x

        registry = ServiceRegistry.from_config(
            config,
            duplicate_detector=mock_dedup,
            sorting_service=mock_sort,
        )

        unique, dupes = registry.process_transaction_group(transactions)

        # Enrichment happened before dedup
        called_with = mock_dedup.detect_and_separate.call_args[0][0]
        assert called_with[0].filename == "a.pdf"
        assert called_with[0].document_type == "bank_statement"
        assert called_with[0].transaction_type != ""

        # Sort was called and result returned
        mock_sort.sort.assert_called_once()
        assert unique == transactions
        assert dupes == []

    def test_returns_unique_and_duplicate_lists(self):
        config = _minimal_config()
        tx1 = Transaction.from_dict(
            {"Date": "01/01/2024", "Details": "A", "source_pdf": "x.pdf"}
        )
        tx2 = Transaction.from_dict(
            {"Date": "01/01/2024", "Details": "A", "source_pdf": "x.pdf"}
        )

        mock_dedup = Mock()
        mock_dedup.detect_and_separate.return_value = ([tx1], [tx2])
        mock_sort = Mock()
        mock_sort.sort.side_effect = lambda x: x

        registry = ServiceRegistry.from_config(
            config,
            duplicate_detector=mock_dedup,
            sorting_service=mock_sort,
        )

        unique, dupes = registry.process_transaction_group([tx1, tx2])
        assert len(unique) == 1
        assert len(dupes) == 1


class TestGroupByIban:
    def test_delegates_to_grouping_service(self):
        config = _minimal_config()
        mock_group = Mock()
        mock_group.group_by_iban.return_value = {"1234": []}

        registry = ServiceRegistry.from_config(config, grouping_service=mock_group)
        transactions = [Transaction.from_dict({"Date": "01/01/2024"})]
        pdf_ibans = {"a.pdf": "IE001234"}

        result = registry.group_by_iban(transactions, pdf_ibans)

        mock_group.group_by_iban.assert_called_once_with(transactions, pdf_ibans)
        assert result == {"1234": []}


class TestEscapeHatches:
    def test_get_duplicate_detector_returns_injected(self):
        config = _minimal_config()
        mock_dedup = Mock()
        registry = ServiceRegistry.from_config(config, duplicate_detector=mock_dedup)
        assert registry.get_duplicate_detector() is mock_dedup

    def test_get_sorting_service_returns_injected(self):
        config = _minimal_config()
        mock_sort = Mock()
        registry = ServiceRegistry.from_config(config, sorting_service=mock_sort)
        assert registry.get_sorting_service() is mock_sort

    def test_get_grouping_service_returns_injected(self):
        config = _minimal_config()
        mock_group = Mock()
        registry = ServiceRegistry.from_config(config, grouping_service=mock_group)
        assert registry.get_grouping_service() is mock_group
