"""Tests for TransactionProcessingOrchestrator.

This module tests the transaction processing orchestration including
duplicate detection, sorting, and metadata enrichment.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bankstatements_core.services.transaction_processing_orchestrator import (
    TransactionProcessingOrchestrator,
)


@pytest.fixture
def mock_duplicate_detector():
    """Create a mock duplicate detector."""
    detector = Mock()
    detector.detect_and_separate.return_value = ([], [])  # (unique, duplicates)
    return detector


@pytest.fixture
def mock_sorting_service():
    """Create a mock sorting service."""
    sorter = Mock()
    sorter.sort.side_effect = lambda x: x  # Pass through
    return sorter


@pytest.fixture
def orchestrator(mock_duplicate_detector, mock_sorting_service):
    """Create a TransactionProcessingOrchestrator instance."""
    return TransactionProcessingOrchestrator(
        duplicate_detector=mock_duplicate_detector,
        sorting_service=mock_sorting_service,
    )


class TestEnrichWithFilename:
    """Test filename enrichment."""

    def test_adds_filename_when_missing(self, orchestrator):
        """Test that Filename is added when not present."""
        transactions = [
            {"Date": "01/12/2023", "Details": "Test", "source_pdf": "test.pdf"},
            {"Date": "02/12/2023", "Details": "Test2", "source_pdf": "test2.pdf"},
        ]

        enriched = orchestrator.enrich_with_filename(transactions)

        assert enriched[0]["Filename"] == "test.pdf"
        assert enriched[1]["Filename"] == "test2.pdf"

    def test_preserves_existing_filename(self, orchestrator):
        """Test that existing Filename is preserved."""
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "Test",
                "Filename": "existing.pdf",
                "source_pdf": "other.pdf",
            }
        ]

        enriched = orchestrator.enrich_with_filename(transactions)

        # Should keep existing Filename
        assert enriched[0]["Filename"] == "existing.pdf"

    def test_handles_missing_source_pdf(self, orchestrator):
        """Test handling when source_pdf is missing."""
        transactions = [{"Date": "01/12/2023", "Details": "Test"}]

        enriched = orchestrator.enrich_with_filename(transactions)

        # Should add empty Filename
        assert enriched[0]["Filename"] == ""


class TestEnrichWithDocumentType:
    """Test document type enrichment."""

    def test_adds_document_type_when_missing(self, orchestrator):
        """Test that document_type is added when not present."""
        transactions = [
            {"Date": "01/12/2023", "Details": "Test1"},
            {"Date": "02/12/2023", "Details": "Test2"},
        ]

        enriched = orchestrator.enrich_with_document_type(transactions)

        # Should add default document_type
        assert enriched[0]["document_type"] == "bank_statement"
        assert enriched[1]["document_type"] == "bank_statement"

    def test_preserves_existing_document_type(self, orchestrator):
        """Test that existing document_type is preserved."""
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "Card Purchase",
                "document_type": "credit_card_statement",
            },
            {
                "Date": "02/12/2023",
                "Details": "Loan Payment",
                "document_type": "loan_statement",
            },
        ]

        enriched = orchestrator.enrich_with_document_type(transactions)

        # Should preserve existing types
        assert enriched[0]["document_type"] == "credit_card_statement"
        assert enriched[1]["document_type"] == "loan_statement"

    def test_custom_default_type(self, orchestrator):
        """Test using custom default document type."""
        transactions = [{"Date": "01/12/2023", "Details": "Test"}]

        enriched = orchestrator.enrich_with_document_type(
            transactions, default_type="credit_card_statement"
        )

        assert enriched[0]["document_type"] == "credit_card_statement"

    def test_mixed_existing_and_missing(self, orchestrator):
        """Test handling mix of transactions with and without document_type."""
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "Has Type",
                "document_type": "credit_card_statement",
            },
            {"Date": "02/12/2023", "Details": "No Type"},
            {
                "Date": "03/12/2023",
                "Details": "Has Type",
                "document_type": "loan_statement",
            },
        ]

        enriched = orchestrator.enrich_with_document_type(transactions)

        # Should preserve existing and add default for missing
        assert enriched[0]["document_type"] == "credit_card_statement"
        assert enriched[1]["document_type"] == "bank_statement"  # Default added
        assert enriched[2]["document_type"] == "loan_statement"


class TestProcessTransactionGroup:
    """Test transaction group processing."""

    def test_enriches_before_duplicate_detection(
        self, mock_duplicate_detector, mock_sorting_service
    ):
        """Test that enrichment happens before duplicate detection."""
        transactions = [
            {"Date": "01/12/2023", "Details": "Test", "source_pdf": "test.pdf"}
        ]

        # Setup mock to capture what's passed to detect_and_separate
        captured_input = []

        def capture_input(txns):
            captured_input.extend(txns)
            return (txns, [])  # Return as unique, no duplicates

        mock_duplicate_detector.detect_and_separate.side_effect = capture_input

        orchestrator = TransactionProcessingOrchestrator(
            duplicate_detector=mock_duplicate_detector,
            sorting_service=mock_sorting_service,
        )

        orchestrator.process_transaction_group(transactions)

        # Verify enrichment happened before duplicate detection
        assert len(captured_input) > 0
        assert "Filename" in captured_input[0]
        assert "document_type" in captured_input[0]

    def test_enrichment_includes_both_fields(
        self, mock_duplicate_detector, mock_sorting_service
    ):
        """Test that both Filename and document_type are added."""
        transactions = [
            {"Date": "01/12/2023", "Details": "Test", "source_pdf": "test.pdf"}
        ]

        captured_input = []

        def capture_input(txns):
            captured_input.extend(txns)
            return (txns, [])

        mock_duplicate_detector.detect_and_separate.side_effect = capture_input

        orchestrator = TransactionProcessingOrchestrator(
            duplicate_detector=mock_duplicate_detector,
            sorting_service=mock_sorting_service,
        )

        orchestrator.process_transaction_group(transactions)

        # Both fields should be present
        assert captured_input[0]["Filename"] == "test.pdf"
        assert captured_input[0]["document_type"] == "bank_statement"

    def test_enrichment_preserves_existing_document_type(
        self, mock_duplicate_detector, mock_sorting_service
    ):
        """Test that existing document_type from extraction is preserved."""
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "Card Purchase",
                "Filename": "card.pdf",
                "document_type": "credit_card_statement",  # Already set by extractor
            }
        ]

        captured_input = []

        def capture_input(txns):
            captured_input.extend(txns)
            return (txns, [])

        mock_duplicate_detector.detect_and_separate.side_effect = capture_input

        orchestrator = TransactionProcessingOrchestrator(
            duplicate_detector=mock_duplicate_detector,
            sorting_service=mock_sorting_service,
        )

        orchestrator.process_transaction_group(transactions)

        # Should preserve credit_card_statement, not override with default
        assert captured_input[0]["document_type"] == "credit_card_statement"


class TestGroupByIBAN:
    """Test IBAN grouping."""

    def test_delegates_to_grouping_service(self, orchestrator):
        """Test that group_by_iban delegates to grouping service."""
        transactions = [
            {"Date": "01/12/2023", "Details": "Test", "Filename": "test1.pdf"},
            {"Date": "02/12/2023", "Details": "Test2", "Filename": "test2.pdf"},
        ]
        pdf_ibans = {"test1.pdf": "IE12345", "test2.pdf": "IE67890"}

        # Mock the grouping service
        orchestrator.grouping_service = Mock()
        orchestrator.grouping_service.group_by_iban.return_value = {
            "IE12345": [transactions[0]],
            "IE67890": [transactions[1]],
        }

        result = orchestrator.group_by_iban(transactions, pdf_ibans)

        # Verify delegation
        orchestrator.grouping_service.group_by_iban.assert_called_once_with(
            transactions, pdf_ibans
        )
        assert "IE12345" in result
        assert "IE67890" in result


class TestEnrichmentIntegration:
    """Integration tests for enrichment in processing pipeline."""

    def test_full_pipeline_with_document_types(
        self, mock_duplicate_detector, mock_sorting_service
    ):
        """Test full processing pipeline preserves document types."""
        transactions = [
            {
                "Date": "01/12/2023",
                "Details": "Bank",
                "source_pdf": "bank.pdf",
                "document_type": "bank_statement",
            },
            {
                "Date": "02/12/2023",
                "Details": "Card",
                "source_pdf": "card.pdf",
                "document_type": "credit_card_statement",
            },
        ]

        # Setup mocks to pass through
        mock_duplicate_detector.detect_and_separate.return_value = (transactions, [])
        mock_sorting_service.sort.side_effect = lambda x: x

        orchestrator = TransactionProcessingOrchestrator(
            duplicate_detector=mock_duplicate_detector,
            sorting_service=mock_sorting_service,
        )

        unique, duplicates = orchestrator.process_transaction_group(transactions)

        # Verify document types preserved through pipeline
        assert unique[0]["document_type"] == "bank_statement"
        assert unique[1]["document_type"] == "credit_card_statement"
