"""Tests for IBAN-based file grouping functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.processor import BankStatementProcessor


class TestIBANGrouping:
    """Test cases for grouping transactions by IBAN."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a processor instance for testing."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        config = ProcessorConfig(input_dir=input_dir, output_dir=output_dir)
        processor = BankStatementProcessor(config=config)
        return processor

    def test_group_rows_by_iban_single_iban(self, processor):
        """Test grouping with single IBAN."""
        all_rows = [
            {"Filename": "statement1.pdf", "Date": "01/01/2024"},
            {"Filename": "statement2.pdf", "Date": "02/01/2024"},
        ]

        pdf_ibans = {
            "statement1.pdf": "IE29AIBK93115212345678",
            "statement2.pdf": "IE29AIBK93115212345678",
        }

        result = processor._group_rows_by_iban(all_rows, pdf_ibans)

        assert len(result) == 1
        assert "5678" in result
        assert len(result["5678"]) == 2

    def test_group_rows_by_iban_multiple_ibans(self, processor):
        """Test grouping with multiple IBANs."""
        all_rows = [
            {"Filename": "statement1.pdf", "Date": "01/01/2024"},
            {"Filename": "statement2.pdf", "Date": "02/01/2024"},
            {"Filename": "statement3.pdf", "Date": "03/01/2024"},
        ]

        pdf_ibans = {
            "statement1.pdf": "IE29AIBK93115212345678",  # ends in 5678
            "statement2.pdf": "IE29AIBK93115212349015",  # ends in 9015
            "statement3.pdf": "IE29AIBK93115212345678",  # ends in 5678
        }

        result = processor._group_rows_by_iban(all_rows, pdf_ibans)

        assert len(result) == 2
        assert "5678" in result
        assert "9015" in result
        assert len(result["5678"]) == 2  # statement1 and statement3
        assert len(result["9015"]) == 1  # statement2

    def test_group_rows_by_iban_no_iban_found(self, processor):
        """Test grouping when no IBAN found for some PDFs."""
        all_rows = [
            {"Filename": "statement1.pdf", "Date": "01/01/2024"},
            {"Filename": "statement2.pdf", "Date": "02/01/2024"},
        ]

        pdf_ibans = {
            "statement1.pdf": "IE29AIBK93115212345678",
            # statement2.pdf has no IBAN
        }

        result = processor._group_rows_by_iban(all_rows, pdf_ibans)

        assert len(result) == 2
        assert "5678" in result
        assert "unknown" in result
        assert len(result["5678"]) == 1
        assert len(result["unknown"]) == 1

    def test_group_rows_by_iban_all_unknown(self, processor):
        """Test grouping when no IBANs found at all."""
        all_rows = [
            {"Filename": "statement1.pdf", "Date": "01/01/2024"},
            {"Filename": "statement2.pdf", "Date": "02/01/2024"},
        ]

        pdf_ibans = {}  # No IBANs found

        result = processor._group_rows_by_iban(all_rows, pdf_ibans)

        assert len(result) == 1
        assert "unknown" in result
        assert len(result["unknown"]) == 2

    def test_iban_suffix_in_filename(self, processor):
        """Test that IBAN suffix is correctly used in output filenames."""
        # This is more of an integration test
        # We can check the filename generation logic

        unique_rows = [{"Date": "01/01/2024", "Details": "Test"}]
        duplicate_rows = []

        import pandas as pd

        df_unique = pd.DataFrame(unique_rows, columns=["Date", "Details"])

        # Write with IBAN suffix using orchestrator
        output_paths = processor._output_orchestrator.write_output_files(
            unique_rows, duplicate_rows, df_unique, iban_suffix="5678"
        )

        # Check that filenames contain the IBAN suffix
        for path in output_paths.values():
            assert "_5678" in path, f"IBAN suffix not in path: {path}"

    def test_no_iban_suffix_in_filename(self, processor):
        """Test that filenames work without IBAN suffix."""
        unique_rows = [{"Date": "01/01/2024", "Details": "Test"}]
        duplicate_rows = []

        import pandas as pd

        df_unique = pd.DataFrame(unique_rows, columns=["Date", "Details"])

        # Write without IBAN suffix using orchestrator
        output_paths = processor._output_orchestrator.write_output_files(
            unique_rows, duplicate_rows, df_unique, iban_suffix=None
        )

        # Check that filenames don't have unexpected suffixes
        for path in output_paths.values():
            # Should have normal names without suffix
            assert (
                "bank_statements" in path
                or "duplicates" in path
                or "monthly_summary" in path
                or "expense_analysis" in path
            )

    def test_different_iban_suffixes(self, processor):
        """Test various IBAN suffix formats."""
        test_cases = [
            ("IE29AIBK93115212345678", "5678"),
            ("DE89370400440532013000", "3000"),
            ("GB29NWBK60161331926819", "6819"),
            ("FR1420041010050500013M02606", "2606"),
        ]

        for full_iban, expected_suffix in test_cases:
            all_rows = [{"Filename": "test.pdf", "Date": "01/01/2024"}]
            pdf_ibans = {"test.pdf": full_iban}

            result = processor._group_rows_by_iban(all_rows, pdf_ibans)

            assert expected_suffix in result
            assert len(result[expected_suffix]) == 1

    def test_grouping_preserves_row_data(self, processor):
        """Test that grouping doesn't modify row data."""
        original_rows = [
            {
                "Filename": "statement1.pdf",
                "Date": "01/01/2024",
                "Details": "Transaction 1",
                "Amount": "100.00",
            },
            {
                "Filename": "statement2.pdf",
                "Date": "02/01/2024",
                "Details": "Transaction 2",
                "Amount": "200.00",
            },
        ]

        pdf_ibans = {
            "statement1.pdf": "IE29AIBK93115212345678",
            "statement2.pdf": "IE29AIBK93115212349015",
        }

        result = processor._group_rows_by_iban(original_rows, pdf_ibans)

        # Check that all fields are preserved
        grouped_row_1 = result["5678"][0]
        assert grouped_row_1["Date"] == "01/01/2024"
        assert grouped_row_1["Details"] == "Transaction 1"
        assert grouped_row_1["Amount"] == "100.00"

        grouped_row_2 = result["9015"][0]
        assert grouped_row_2["Date"] == "02/01/2024"
        assert grouped_row_2["Details"] == "Transaction 2"
        assert grouped_row_2["Amount"] == "200.00"
