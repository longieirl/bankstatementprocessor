"""Tests for duplicate detection service."""

from __future__ import annotations

import pytest

from bankstatements_core.patterns.strategies import (
    AllFieldsDuplicateStrategy,
    DateAmountDuplicateStrategy,
)
from bankstatements_core.services.duplicate_detector import DuplicateDetectionService


class TestDuplicateDetectionService:
    """Tests for DuplicateDetectionService."""

    def test_initialization(self):
        """Test service initialization with strategy."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)
        assert service.strategy == strategy

    def test_detect_and_separate_no_duplicates(self):
        """Test detection when there are no duplicates."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase 1",
                "Debit €": "50.00",
                "Filename": "file1.pdf",
            },
            {
                "Date": "02 Jan 2023",
                "Details": "Purchase 2",
                "Debit €": "25.00",
                "Filename": "file1.pdf",
            },
        ]

        unique, duplicates = service.detect_and_separate(transactions)
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_detect_and_separate_with_duplicates(self):
        """Test detection when there are duplicates across files."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase 1",
                "Debit €": "50.00",
                "Filename": "file1.pdf",
            },
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase 1",
                "Debit €": "50.00",
                "Filename": "file2.pdf",  # Same transaction, different file
            },
        ]

        unique, duplicates = service.detect_and_separate(transactions)
        assert len(unique) == 1
        assert len(duplicates) == 1
        assert unique[0]["Filename"] == "file1.pdf"
        assert duplicates[0]["Filename"] == "file2.pdf"

    def test_detect_and_separate_same_file_same_transaction(self):
        """Test that same transaction in same file is not marked as duplicate."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase 1",
                "Debit €": "50.00",
                "Filename": "file1.pdf",
            },
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase 1",
                "Debit €": "50.00",
                "Filename": "file1.pdf",  # Same file
            },
        ]

        unique, duplicates = service.detect_and_separate(transactions)
        # Both should be kept as unique (same file)
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_detect_and_separate_with_date_amount_strategy(self):
        """Test detection with DateAmountDuplicateStrategy."""
        strategy = DateAmountDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        transactions = [
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase at Store A",
                "Debit €": "50.00",
                "Filename": "file1.pdf",
            },
            {
                "Date": "01 Jan 2023",
                "Details": "Purchase at Store B",  # Different details
                "Debit €": "50.00",  # Same amount and date
                "Filename": "file2.pdf",
            },
        ]

        unique, duplicates = service.detect_and_separate(transactions)
        # Should detect as duplicate (same date and amount, different files)
        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_detect_and_separate_empty_list(self):
        """Test detection with empty transaction list."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        unique, duplicates = service.detect_and_separate([])
        assert len(unique) == 0
        assert len(duplicates) == 0

    def test_get_statistics_no_duplicates(self):
        """Test statistics when there are no duplicates."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        unique = [{"id": 1}, {"id": 2}, {"id": 3}]
        duplicates = []

        stats = service.get_statistics(unique, duplicates)
        assert stats["total"] == 3
        assert stats["unique"] == 3
        assert stats["duplicates"] == 0
        assert stats["duplicate_rate_percent"] == 0.0

    def test_get_statistics_with_duplicates(self):
        """Test statistics when there are duplicates."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        unique = [{"id": 1}, {"id": 2}]
        duplicates = [{"id": 3}, {"id": 4}]

        stats = service.get_statistics(unique, duplicates)
        assert stats["total"] == 4
        assert stats["unique"] == 2
        assert stats["duplicates"] == 2
        assert stats["duplicate_rate_percent"] == 50.0

    def test_get_statistics_high_duplicate_rate(self):
        """Test statistics with high duplicate rate."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        unique = [{"id": 1}]
        duplicates = [{"id": 2}, {"id": 3}, {"id": 4}]

        stats = service.get_statistics(unique, duplicates)
        assert stats["total"] == 4
        assert stats["unique"] == 1
        assert stats["duplicates"] == 3
        assert stats["duplicate_rate_percent"] == 75.0

    def test_get_statistics_empty_lists(self):
        """Test statistics with empty lists."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        stats = service.get_statistics([], [])
        assert stats["total"] == 0
        assert stats["unique"] == 0
        assert stats["duplicates"] == 0
        assert stats["duplicate_rate_percent"] == 0.0

    def test_detect_multiple_files_complex_scenario(self):
        """Test complex scenario with multiple files and duplicates."""
        strategy = AllFieldsDuplicateStrategy()
        service = DuplicateDetectionService(strategy)

        transactions = [
            # Transaction 1 appears in file1 and file2 (duplicate in file2)
            {
                "Date": "01 Jan 2023",
                "Details": "Txn1",
                "Debit €": "50.00",
                "Filename": "file1.pdf",
            },
            {
                "Date": "01 Jan 2023",
                "Details": "Txn1",
                "Debit €": "50.00",
                "Filename": "file2.pdf",
            },
            # Transaction 2 only in file1 (unique)
            {
                "Date": "02 Jan 2023",
                "Details": "Txn2",
                "Debit €": "25.00",
                "Filename": "file1.pdf",
            },
            # Transaction 3 appears in file2 and file3 (duplicate in file3)
            {
                "Date": "03 Jan 2023",
                "Details": "Txn3",
                "Debit €": "75.00",
                "Filename": "file2.pdf",
            },
            {
                "Date": "03 Jan 2023",
                "Details": "Txn3",
                "Debit €": "75.00",
                "Filename": "file3.pdf",
            },
        ]

        unique, duplicates = service.detect_and_separate(transactions)
        assert len(unique) == 3  # Txn1 from file1, Txn2 from file1, Txn3 from file2
        assert len(duplicates) == 2  # Txn1 from file2, Txn3 from file3

        stats = service.get_statistics(unique, duplicates)
        assert stats["total"] == 5
        assert stats["duplicate_rate_percent"] == 40.0
