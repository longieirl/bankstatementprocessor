"""Tests for PDF table extraction orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bankstatements_core.domain import ExtractionResult
from bankstatements_core.extraction.pdf_extractor import PDFTableExtractor
from bankstatements_core.extraction.row_post_processor import (
    RowPostProcessor,
    extract_filename_date,
)

# Test columns configuration
TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


class TestPDFTableExtractor:
    """Tests for PDFTableExtractor class."""

    def test_initialization_defaults(self):
        """Test extractor initialization with defaults."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        assert extractor.columns == TEST_COLUMNS
        assert extractor.table_top_y == 300
        assert extractor.table_bottom_y == 720
        assert extractor.enable_dynamic_boundary is False

    def test_initialization_custom_values(self):
        """Test extractor initialization with custom values."""
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            table_top_y=250,
            table_bottom_y=800,
            enable_dynamic_boundary=True,
            enable_page_validation=True,
        )
        assert extractor.table_top_y == 250
        assert extractor.table_bottom_y == 800
        assert extractor.enable_dynamic_boundary is True
        assert extractor.page_validation_enabled is True

    def test_extract_filename_date_valid(self):
        """Test extracting date from filename with valid pattern."""
        assert extract_filename_date("statement_20230115.pdf") == "15 Jan 2023"

    def test_extract_filename_date_no_pattern(self):
        """Test extracting date from filename without date pattern."""
        assert extract_filename_date("statement.pdf") == ""

    def test_extract_filename_date_invalid_date(self):
        """Test extracting invalid date from filename."""
        assert extract_filename_date("statement_99999999.pdf") == ""

    def test_extract_rows_from_words(self):
        """Test extracting rows from word list."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        words = [
            # Row 1: Transaction (all words at same rounded Y)
            {"text": "01", "x0": 30, "x1": 40, "top": 350.0},
            {"text": "Jan", "x0": 35, "x1": 50, "top": 350.0},
            {"text": "Purchase", "x0": 60, "x1": 110, "top": 350.0},
            {"text": "50.00", "x0": 210, "x1": 240, "top": 350.0},
            # Row 2: Another transaction
            {"text": "02", "x0": 30, "x1": 40, "top": 370.0},
            {"text": "Jan", "x0": 35, "x1": 50, "top": 370.0},
            {"text": "Sale", "x0": 60, "x1": 90, "top": 370.0},
            {"text": "25.00", "x0": 260, "x1": 290, "top": 370.0},
        ]
        rows = extractor._row_builder.build_rows(words)
        assert len(rows) == 2
        assert "01 Jan" in rows[0]["Date"]
        assert "Purchase" in rows[0]["Details"]
        assert "50.00" in rows[0]["Debit €"]

    def test_extract_rows_from_words_filters_non_transactions(self):
        """Test that non-transaction rows are filtered."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        words = [
            # Transaction
            {"text": "01", "x0": 30, "x1": 40, "top": 350},
            {"text": "Jan", "x0": 35, "x1": 50, "top": 350},
            {"text": "Purchase", "x0": 60, "x1": 110, "top": 350},
            {"text": "50.00", "x0": 210, "x1": 240, "top": 350},
            # Header row (will be classified as metadata)
            {"text": "Date", "x0": 30, "x1": 60, "top": 370},
            {"text": "Details", "x0": 60, "x1": 110, "top": 370},
        ]
        rows = extractor._row_builder.build_rows(words)
        # Should only have the transaction, not the header
        assert len(rows) == 1

    def test_process_row_with_date(self):
        """Test processing row with date present."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        proc = RowPostProcessor(
            columns=TEST_COLUMNS,
            row_classifier=extractor._row_classifier,
            template=None,
            filename_date="",
            filename="test.pdf",
        )
        row = {
            "Date": "01 Jan 2023",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Credit €": "",
            "Balance €": "100.00",
        }
        current_date = proc.process(row, current_date="")
        assert current_date == "01 Jan 2023"
        assert row["Filename"] == "test.pdf"

    def test_process_row_without_date_uses_current(self):
        """Test processing row without date uses current date."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        proc = RowPostProcessor(
            columns=TEST_COLUMNS,
            row_classifier=extractor._row_classifier,
            template=None,
            filename_date="",
            filename="test.pdf",
        )
        row = {
            "Date": "",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Credit €": "",
            "Balance €": "100.00",
        }
        current_date = proc.process(row, current_date="31 Dec 2022")
        assert row["Date"] == "31 Dec 2022"
        assert current_date == "31 Dec 2022"

    def test_process_row_without_date_uses_filename_date(self):
        """Test processing row without date uses filename date."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS)
        proc = RowPostProcessor(
            columns=TEST_COLUMNS,
            row_classifier=extractor._row_classifier,
            template=None,
            filename_date="15 Jan 2023",
            filename="test.pdf",
        )
        row = {
            "Date": "",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Credit €": "",
            "Balance €": "100.00",
        }
        current_date = proc.process(row, current_date="")
        assert row["Date"] == "15 Jan 2023"
        assert current_date == "15 Jan 2023"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_basic_flow(self, mock_pdfplumber):
        """Test basic extraction flow with mocked PDF."""
        # Setup mock
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Mock words that form a transaction
        mock_words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "2023", "x0": 40, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        # Extract - pass parameters directly instead of using environment variables
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert isinstance(result, ExtractionResult)
        assert result.page_count == 1
        assert len(result.transactions) == 1
        assert result.transactions[0].filename == "test.pdf"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_with_dynamic_boundary(self, mock_pdfplumber):
        """Test extraction with dynamic boundary enabled."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600
        mock_page.height = 800

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        mock_words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "2023", "x0": 40, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_dynamic_boundary=True,
            enable_page_validation=False,
            enable_header_check=False,
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1
        # Crop is called for: credit card check (header), table extraction (initial + final)
        assert mock_page.crop.call_count >= 2  # At least initial + final for table

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_with_page_validation_failure(self, mock_pdfplumber):
        """Test extraction with page validation that fails."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        # Mock words that don't form valid transactions
        mock_words = [
            {"text": "Invalid", "x0": 60, "top": 350},
            {"text": "Row", "x0": 80, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(columns=TEST_COLUMNS, enable_page_validation=True)
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1
        # No valid transactions, so rows should be empty
        assert len(result.transactions) == 0

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_multiple_pages(self, mock_pdfplumber):
        """Test extraction with multiple pages."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped1 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_words1 = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped1.extract_words.return_value = mock_words1

        mock_cropped2 = MagicMock()
        mock_page2.crop.return_value = mock_cropped2
        mock_words2 = [
            {"text": "02", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Sale", "x0": 60, "top": 350},
            {"text": "25.00", "x0": 260, "top": 350},
        ]
        mock_cropped2.extract_words.return_value = mock_words2

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 2
        assert len(result.transactions) == 2

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_date_propagation_across_rows(self, mock_pdfplumber):
        """Test that dates propagate correctly across rows."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.width = 595  # Standard A4 width in points
        mock_page.height = 842  # Standard A4 height in points
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_cropped = MagicMock()
        mock_cropped.width = 595
        mock_cropped.height = 842
        mock_page.crop.return_value = mock_cropped

        # First row has date, second doesn't
        # Date column: [0, 50], Details: [50, 200], Debit: [200, 250], Credit: [250, 300], Balance: [300, 350]
        mock_words = [
            # Row 1 with date (all date components must fit within [0, 50])
            {"text": "01", "x0": 5, "x1": 15, "top": 350},
            {"text": "Jan", "x0": 16, "x1": 30, "top": 350},
            {"text": "2023", "x0": 31, "x1": 49, "top": 350},
            {"text": "Purchase", "x0": 60, "x1": 110, "top": 350},
            {"text": "50.00", "x0": 210, "x1": 240, "top": 350},
            # Row 2 without date
            {"text": "Sale", "x0": 60, "x1": 90, "top": 370},
            {"text": "25.00", "x0": 260, "x1": 290, "top": 370},
        ]
        mock_cropped.extract_words.return_value = mock_words

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
        )
        result = extractor.extract(Path("/tmp/test.pdf"))

        assert len(result.transactions) == 2
        # Both rows should have the same date (2023 is captured if x1 is provided for all words)
        assert "01 Jan 2023" in result.transactions[0].date
        assert "01 Jan 2023" in result.transactions[1].date

    def test_page_validation_constructor_parameter(self):
        """Test page validation setting via constructor parameter."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS, enable_page_validation=True)
        assert extractor.page_validation_enabled is True

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS, enable_page_validation=False
        )
        assert extractor.page_validation_enabled is False

    def test_header_check_constructor_parameter(self):
        """Test header check setting via constructor parameter."""
        extractor = PDFTableExtractor(columns=TEST_COLUMNS, enable_header_check=True)
        assert extractor.header_check_enabled is True

        extractor = PDFTableExtractor(columns=TEST_COLUMNS, enable_header_check=False)
        assert extractor.header_check_enabled is False

    def test_extraction_config_parameter(self):
        """Test that extraction_config parameter is stored correctly."""
        from bankstatements_core.templates.template_model import (
            PerPageBoundaries,
            TemplateExtractionConfig,
        )

        extraction_config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns=TEST_COLUMNS,
            per_page_overrides={1: PerPageBoundaries(table_top_y=490)},
        )

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS, extraction_config=extraction_config
        )

        assert extractor.extraction_config is not None
        assert extractor.extraction_config == extraction_config

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_per_page_boundaries_applied_correctly(self, mock_pdfplumber):
        """Test that per-page boundaries are applied to correct pages."""
        from bankstatements_core.templates.template_model import (
            PerPageBoundaries,
            TemplateExtractionConfig,
        )

        # Create extraction config with per-page overrides
        extraction_config = TemplateExtractionConfig(
            table_top_y=140,  # Default for pages 2+
            table_bottom_y=735,
            columns=TEST_COLUMNS,
            per_page_overrides={1: PerPageBoundaries(table_top_y=490)},  # Page 1
        )

        # Setup mocks for 2 pages
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value = mock_pdf

        mock_page1.width = 600
        mock_page2.width = 600

        # Mock crop for both pages
        mock_cropped1 = MagicMock()
        mock_cropped2 = MagicMock()
        mock_page1.crop.return_value = mock_cropped1
        mock_page2.crop.return_value = mock_cropped2

        # Mock words for both pages
        mock_words1 = [
            {"text": "01", "x0": 30, "top": 500},
            {"text": "Jan", "x0": 35, "top": 500},
            {"text": "Purchase", "x0": 60, "top": 500},
            {"text": "50.00", "x0": 210, "top": 500},
        ]
        mock_words2 = [
            {"text": "02", "x0": 30, "top": 150},
            {"text": "Feb", "x0": 35, "top": 150},
            {"text": "Sale", "x0": 60, "top": 150},
            {"text": "25.00", "x0": 260, "top": 150},
        ]
        mock_cropped1.extract_words.return_value = mock_words1
        mock_cropped2.extract_words.return_value = mock_words2

        # Create extractor with extraction_config
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            extraction_config=extraction_config,
            enable_page_validation=False,
            enable_header_check=False,
        )

        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 2
        assert len(result.transactions) == 2

        # Verify crop was called with correct boundaries
        # Page 1 should use override (490)
        page1_crop_calls = [
            call for call in mock_page1.crop.call_args_list if call[0][0][1] == 490
        ]
        assert len(page1_crop_calls) > 0, "Page 1 should use table_top_y=490"

        # Page 2 should use default (140)
        page2_crop_calls = [
            call for call in mock_page2.crop.call_args_list if call[0][0][1] == 140
        ]
        assert len(page2_crop_calls) > 0, "Page 2 should use table_top_y=140"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_per_page_boundaries_without_extraction_config(self, mock_pdfplumber):
        """Test that extraction works without extraction_config (uses instance defaults)."""
        # Setup mocks
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        mock_words = [
            {"text": "01", "x0": 30, "top": 350},
            {"text": "Jan", "x0": 35, "top": 350},
            {"text": "Purchase", "x0": 60, "top": 350},
            {"text": "50.00", "x0": 210, "top": 350},
        ]
        mock_cropped.extract_words.return_value = mock_words

        # Create extractor WITHOUT extraction_config (should use instance defaults)
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            table_top_y=300,
            table_bottom_y=720,
            enable_page_validation=False,
            enable_header_check=False,
        )

        result = extractor.extract(Path("/tmp/test.pdf"))

        assert result.page_count == 1
        assert len(result.transactions) == 1

        # Verify crop was called with instance defaults (300)
        crop_calls = [
            call for call in mock_page.crop.call_args_list if call[0][0][1] == 300
        ]
        assert len(crop_calls) > 0, "Should use instance default table_top_y=300"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_per_page_header_check_top_y_override(self, mock_pdfplumber):
        """Test that per-page header_check_top_y override is applied."""
        from bankstatements_core.templates.template_model import (
            PerPageBoundaries,
            TemplateExtractionConfig,
        )

        # Create extraction config with header_check_top_y override for page 1
        extraction_config = TemplateExtractionConfig(
            table_top_y=140,
            table_bottom_y=735,
            columns=TEST_COLUMNS,
            header_check_top_y=100,  # Default
            per_page_overrides={1: PerPageBoundaries(header_check_top_y=450)},
        )

        # Setup mocks
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600

        mock_cropped = MagicMock()
        mock_page.crop.return_value = mock_cropped

        mock_words = [
            {"text": "Date", "x0": 30, "top": 460},  # Header
            {"text": "Details", "x0": 60, "top": 460},
            {"text": "01", "x0": 30, "top": 500},  # Transaction
            {"text": "Jan", "x0": 35, "top": 500},
        ]
        mock_cropped.extract_words.return_value = mock_words

        # Create extractor with header check enabled
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            extraction_config=extraction_config,
            enable_page_validation=False,
            enable_header_check=True,  # Enable header check
        )

        extractor.extract(Path("/tmp/test.pdf"))

        # Verify header area crop was called with override value (450)
        header_crop_calls = [
            call for call in mock_page.crop.call_args_list if call[0][0][1] == 450
        ]
        assert (
            len(header_crop_calls) > 0
        ), "Header check should use header_check_top_y=450 for page 1"


class TestPDFTableExtractorCardNumber:
    """Tests for card number extraction in PDFTableExtractor (CC-07)."""

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_card_number_paid_tier(self, mock_pdfplumber):
        """Paid tier CC PDF: card_number extracted from template patterns."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600

        # Cropped header returns text with masked card number
        mock_header_cropped = MagicMock()
        mock_header_cropped.extract_text.return_value = (
            "Account Statement\n**** **** **** 1234\nSome other text"
        )
        # Table crop returns empty (no transactions)
        mock_table_cropped = MagicMock()
        mock_table_cropped.extract_words.return_value = []

        def crop_side_effect(bbox):
            # header crop (0, 0, width, 400)
            if bbox[1] == 0 and bbox[3] == 400:
                return mock_header_cropped
            return mock_table_cropped

        mock_page.crop.side_effect = crop_side_effect

        # Template with card_number_patterns
        mock_template = MagicMock()
        mock_template.detection.get_card_number_patterns.return_value = [
            r"\*{4}\s*\*{4}\s*\*{4}\s*[0-9]{4}",
        ]

        # Paid tier entitlements
        mock_entitlements = MagicMock()
        mock_entitlements.require_iban = False

        # Header analyser: IS a CC statement
        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
            template=mock_template,
            entitlements=mock_entitlements,
        )
        extractor._header_analyser = MagicMock()
        extractor._header_analyser.is_credit_card_statement.return_value = True
        extractor._header_analyser.extract_iban.return_value = None

        result = extractor.extract(Path("/tmp/cc.pdf"))

        assert result.card_number == "**** **** **** 1234"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_card_number_no_template(self, mock_pdfplumber):
        """Paid tier CC PDF with no template: card_number == 'unknown'."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600
        mock_cropped = MagicMock()
        mock_cropped.extract_words.return_value = []
        mock_page.crop.return_value = mock_cropped

        mock_entitlements = MagicMock()
        mock_entitlements.require_iban = False

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
            template=None,
            entitlements=mock_entitlements,
        )
        extractor._header_analyser = MagicMock()
        extractor._header_analyser.is_credit_card_statement.return_value = True
        extractor._header_analyser.extract_iban.return_value = None

        result = extractor.extract(Path("/tmp/cc_no_template.pdf"))

        assert result.card_number == "unknown"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_card_number_no_match_falls_back_to_unknown(self, mock_pdfplumber):
        """Paid tier CC PDF where pattern doesn't match: card_number == 'unknown'."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600

        # Header returns text WITHOUT matching card number
        mock_header_cropped = MagicMock()
        mock_header_cropped.extract_text.return_value = "Account Statement\nNo card number here"
        mock_table_cropped = MagicMock()
        mock_table_cropped.extract_words.return_value = []

        def crop_side_effect(bbox):
            if bbox[1] == 0 and bbox[3] == 400:
                return mock_header_cropped
            return mock_table_cropped

        mock_page.crop.side_effect = crop_side_effect

        mock_template = MagicMock()
        mock_template.detection.get_card_number_patterns.return_value = [
            r"\*{4}\s*\*{4}\s*\*{4}\s*[0-9]{4}",
        ]

        mock_entitlements = MagicMock()
        mock_entitlements.require_iban = False

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
            template=mock_template,
            entitlements=mock_entitlements,
        )
        extractor._header_analyser = MagicMock()
        extractor._header_analyser.is_credit_card_statement.return_value = True
        extractor._header_analyser.extract_iban.return_value = None

        result = extractor.extract(Path("/tmp/cc_no_match.pdf"))

        assert result.card_number == "unknown"

    @patch("bankstatements_core.adapters.pdfplumber_adapter.pdfplumber.open")
    def test_extract_card_number_free_tier_returns_early(self, mock_pdfplumber):
        """Free tier CC PDF: early return with CODE_CREDIT_CARD_SKIPPED, card_number is None."""
        from bankstatements_core.domain.models.extraction_warning import (
            CODE_CREDIT_CARD_SKIPPED,
        )

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.return_value = mock_pdf

        mock_page.width = 600
        mock_cropped = MagicMock()
        mock_cropped.extract_words.return_value = []
        mock_page.crop.return_value = mock_cropped

        # Free tier: require_iban=True
        mock_entitlements = MagicMock()
        mock_entitlements.require_iban = True

        extractor = PDFTableExtractor(
            columns=TEST_COLUMNS,
            enable_page_validation=False,
            enable_header_check=False,
            entitlements=mock_entitlements,
        )
        extractor._header_analyser = MagicMock()
        extractor._header_analyser.is_credit_card_statement.return_value = True

        result = extractor.extract(Path("/tmp/cc_free_tier.pdf"))

        assert result.card_number is None
        assert any(w.code == CODE_CREDIT_CARD_SKIPPED for w in result.warnings)
