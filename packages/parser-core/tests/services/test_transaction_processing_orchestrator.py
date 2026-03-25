"""Tests for TransactionProcessingOrchestrator.

The orchestrator now only handles IBAN grouping. Enrichment, classification,
duplicate detection and sorting are tested via test_service_registry.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bankstatements_core.services.transaction_processing_orchestrator import (
    TransactionProcessingOrchestrator,
)


@pytest.fixture
def mock_duplicate_detector():
    detector = Mock()
    detector.detect_and_separate.return_value = ([], [])
    return detector


@pytest.fixture
def mock_sorting_service():
    sorter = Mock()
    sorter.sort.side_effect = lambda x: x
    return sorter


@pytest.fixture
def orchestrator(mock_duplicate_detector, mock_sorting_service):
    return TransactionProcessingOrchestrator(
        duplicate_detector=mock_duplicate_detector,
        sorting_service=mock_sorting_service,
    )


class TestGroupByIBAN:
    def test_delegates_to_grouping_service(self, orchestrator):
        transactions = [
            {"Date": "01/12/2023", "Details": "Test", "Filename": "test1.pdf"},
            {"Date": "02/12/2023", "Details": "Test2", "Filename": "test2.pdf"},
        ]
        pdf_ibans = {"test1.pdf": "IE12345", "test2.pdf": "IE67890"}

        orchestrator.grouping_service = Mock()
        orchestrator.grouping_service.group_by_iban.return_value = {
            "IE12345": [transactions[0]],
            "IE67890": [transactions[1]],
        }

        result = orchestrator.group_by_iban(transactions, pdf_ibans)

        orchestrator.grouping_service.group_by_iban.assert_called_once_with(
            transactions, pdf_ibans
        )
        assert "IE12345" in result
        assert "IE67890" in result
