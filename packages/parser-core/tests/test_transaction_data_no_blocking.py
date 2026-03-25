"""Tests to verify transaction line data does not block PDF processing."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bankstatements_core.config.processor_config import ProcessorConfig
from bankstatements_core.domain import ExtractionResult
from bankstatements_core.domain.converters import dicts_to_transactions


def create_test_processor(input_dir, output_dir):
    """Helper to create processor with test configuration."""
    from bankstatements_core.processor import BankStatementProcessor

    config = ProcessorConfig(input_dir=input_dir, output_dir=output_dir)
    return BankStatementProcessor(config=config)


class TestTransactionDataNoBlocking:
    """Verify transaction data cannot cause PDFs to be blocked."""

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_visa_in_transaction_does_not_block(self, mock_pdfplumber):
        """Test that VISA in transaction description does not block processing."""
        from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 612
        mock_page.height = 792

        # Mock header area (no credit card indicators)
        mock_header = MagicMock()
        mock_header.extract_text.return_value = """
        Personal Bank Account
        Statement of Account
        IBAN: IE48 AIBK 9340 8921 4590 15
        Date Details Debit € Credit €
        """
        mock_header.extract_words.return_value = [
            {"text": "IBAN:", "x0": 10, "top": 100},
            {"text": "IE48", "x0": 50, "top": 100},
        ]

        # Mock cropped area for table extraction
        mock_table = MagicMock()
        mock_table.extract_words.return_value = [
            {"text": "11", "x0": 30, "top": 350},
            {"text": "Aug", "x0": 35, "top": 350},
            {"text": "MOBI", "x0": 60, "top": 350},
            {"text": "CLICK", "x0": 80, "top": 350},
            {"text": "VISA", "x0": 100, "top": 350},  # VISA in transaction
            {"text": "100.00", "x0": 210, "top": 350},
        ]

        def crop_side_effect(bbox):
            # Header area (y <= 350 for IBAN extraction)
            if bbox[3] <= 350:
                return mock_header
            # Table area
            return mock_table

        mock_page.crop.side_effect = crop_side_effect

        extractor = PDFTableExtractor(
            columns={
                "Date": (0, 50),
                "Details": (50, 200),
                "Debit €": (200, 250),
                "Credit €": (250, 300),
            }
        )

        result = extractor.extract(Path("/tmp/test.pdf"))

        # Should NOT be detected as credit card (VISA only in transaction)
        assert result.iban == "IE48AIBK93408921459015"
        assert result.page_count == 1
        # PDF should be processed, not blocked

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_mastercard_in_transaction_does_not_block(self, mock_pdfplumber):
        """Test that Mastercard in transaction description does not block processing."""
        from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 612
        mock_page.height = 792

        # Mock header area (no credit card indicators)
        mock_header = MagicMock()
        mock_header.extract_text.return_value = """
        Bank Statement
        IBAN: IE29 AIBK 9311 5212 3456 78
        """
        mock_header.extract_words.return_value = []

        mock_table = MagicMock()
        mock_table.extract_words.return_value = [
            {"text": "Payment", "x0": 60, "top": 350},
            {"text": "via", "x0": 80, "top": 350},
            {"text": "Mastercard", "x0": 100, "top": 350},  # Mastercard in transaction
        ]

        def crop_side_effect(bbox):
            if bbox[3] <= 350:
                return mock_header
            return mock_table

        mock_page.crop.side_effect = crop_side_effect

        extractor = PDFTableExtractor(
            columns={
                "Date": (0, 50),
                "Details": (50, 200),
                "Debit €": (200, 250),
            }
        )

        result = extractor.extract(Path("/tmp/test.pdf"))

        # Should NOT be detected as credit card
        assert result.iban == "IE29AIBK93115212345678"
        assert result.page_count == 1

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_iban_in_transaction_does_not_override_header_iban(self, mock_pdfplumber):
        """Test that IBAN in transaction doesn't override header IBAN."""
        from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 612
        mock_page.height = 792

        # Header has account IBAN
        mock_header = MagicMock()
        mock_header.extract_text.return_value = """
        Account Statement
        IBAN: IE48 AIBK 9340 8921 4590 15
        """
        mock_header.extract_words.return_value = []

        # Transaction has different IBAN (bank transfer recipient)
        mock_table = MagicMock()
        mock_table.extract_words.return_value = [
            {"text": "Transfer", "x0": 60, "top": 350},
            {"text": "to", "x0": 80, "top": 350},
            {"text": "IE29AIBK93115212345678", "x0": 100, "top": 350},  # Different IBAN
        ]

        def crop_side_effect(bbox):
            if bbox[3] <= 350:
                return mock_header
            return mock_table

        mock_page.crop.side_effect = crop_side_effect

        extractor = PDFTableExtractor(
            columns={
                "Date": (0, 50),
                "Details": (50, 200),
            }
        )

        result = extractor.extract(Path("/tmp/test.pdf"))

        # Should return header IBAN, not transaction IBAN
        assert result.iban == "IE48AIBK93408921459015"  # Normalized without spaces
        assert result.page_count == 1

    def test_processor_does_not_use_transaction_data_for_exclusion(self):
        """Test that processor only uses header data for exclusion decisions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            test_pdf = input_dir / "test.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Mock: PDF has IBAN (from header) but transactions mention VISA
            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                # Returns: ExtractionResult with VISA in transactions, IBAN from header
                mock_extract.return_value = ExtractionResult(
                    transactions=dicts_to_transactions(
                        [
                            {
                                "Date": "11 Aug",
                                "Details": "MOBI CLICK VISA",
                                "Debit €": "100.00",
                            }
                        ]
                    ),
                    page_count=1,
                    iban="IE48AIBK93408921459015",
                    source_file=Path("test.pdf"),
                )

                processor = create_test_processor(input_dir, output_dir)
                result = processor.run()

                # Should NOT be excluded (has IBAN from header)
                excluded_path = output_dir / "excluded_files.json"
                assert not excluded_path.exists()

                # Should process transactions
                assert result["transactions"] == 1

    def test_all_card_brands_in_transactions_allowed(self):
        """Test that all card brand names in transactions don't block processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            test_pdf = input_dir / "test.pdf"
            test_pdf.write_bytes(b"%PDF-1.4\nTest PDF")

            # Transactions contain all card brands
            transaction_details = [
                "VISA Payment",
                "Mastercard Transaction",
                "American Express",
                "Discover Card",
            ]

            with patch(
                "bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf"
            ) as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    transactions=dicts_to_transactions(
                        [
                            {"Date": "11 Aug", "Details": detail}
                            for detail in transaction_details
                        ]
                    ),
                    page_count=1,
                    iban="IE48AIBK93408921459015",
                    source_file=Path("test.pdf"),
                )

                processor = create_test_processor(input_dir, output_dir)
                result = processor.run()

                # Should NOT be excluded
                excluded_path = output_dir / "excluded_files.json"
                assert not excluded_path.exists()

                # All transactions processed
                assert result["transactions"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
