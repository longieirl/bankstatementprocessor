"""Tests for PageValidationService."""

import pytest

from bankstatements_core.services.page_validation import PageValidationService


class TestPageValidationService:
    """Test suite for PageValidationService."""

    @pytest.fixture
    def service(self):
        """Create PageValidationService instance with default settings."""
        return PageValidationService()

    @pytest.fixture
    def columns(self):
        """Standard column configuration."""
        return {
            "Date": (0, 100),
            "Details": (100, 300),
            "Debit €": (300, 400),
            "Balance €": (400, 500),
        }

    def test_validate_page_structure_low_column_coverage(self, columns):
        """Test page rejection when column coverage is too low."""
        # Service with strict column coverage requirement
        service = PageValidationService(min_column_coverage=0.8)

        # Only 1 out of 4 columns has data (25% coverage < 80%)
        rows = [
            {"Date": "01/01/23", "Details": "", "Debit €": "", "Balance €": ""},
        ]

        assert service.validate_page_structure(rows, columns) is False

    def test_validate_page_structure_missing_date_column(self):
        """Test page rejection when required date column is missing."""
        service = PageValidationService(require_date_column=True)

        columns = {
            "Details": (100, 300),
            "Debit €": (300, 400),
        }

        rows = [
            {"Details": "Payment", "Debit €": "100.00"},
        ]

        assert service.validate_page_structure(rows, columns) is False

    def test_validate_page_structure_missing_amount_columns(self):
        """Test page rejection when required amount columns are missing."""
        service = PageValidationService(require_amount_column=True)

        columns = {
            "Date": (0, 100),
            "Details": (100, 300),
        }

        rows = [
            {"Date": "01/01/23", "Details": "Payment"},
        ]

        assert service.validate_page_structure(rows, columns) is False

    def test_validate_page_structure_sufficient_coverage(self, service, columns):
        """Test page acceptance when coverage is sufficient."""
        rows = [
            {
                "Date": "01/01/23",
                "Details": "Payment 1",
                "Debit €": "100.00",
                "Balance €": "500.00",
            },
            {
                "Date": "02/01/23",
                "Details": "Payment 2",
                "Debit €": "50.00",
                "Balance €": "450.00",
            },
        ]

        assert service.validate_page_structure(rows, columns) is True
