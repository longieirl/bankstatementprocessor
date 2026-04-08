"""Tests for template detector orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bankstatements_core.templates.detectors.base import DetectionResult
from bankstatements_core.templates.template_detector import (
    DetectionExplanation,
    ScoringConfig,
    TemplateDetector,
)
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry


@pytest.fixture
def mock_registry():
    """Create mock template registry."""
    aib_template = BankTemplate(
        id="aib",
        name="Allied Irish Banks",
        enabled=True,
        detection=TemplateDetectionConfig(iban_patterns=["IE[0-9]{2}AIBK.*"]),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        ),
    )

    revolut_template = BankTemplate(
        id="revolut",
        name="Revolut",
        enabled=True,
        detection=TemplateDetectionConfig(iban_patterns=["IE[0-9]{2}REVO.*"]),
        extraction=TemplateExtractionConfig(
            table_top_y=504,
            table_bottom_y=810,
            columns={"Date": (42, 120)},
        ),
    )

    registry = MagicMock(spec=TemplateRegistry)
    registry.get_all_templates.return_value = [aib_template, revolut_template]
    registry.get_templates_by_type.return_value = [
        aib_template,
        revolut_template,
    ]  # NEW
    registry.get_default_template.return_value = aib_template
    registry.get_default_for_type.return_value = aib_template  # NEW
    registry.get_template.side_effect = lambda tid: (
        aib_template
        if tid == "aib"
        else (revolut_template if tid == "revolut" else None)
    )

    return registry


@pytest.fixture
def mock_page():
    """Create mock PDF page."""
    page = MagicMock()
    page.width = 595.28
    page.height = 841.89
    page.extract_text.return_value = ""  # Empty string for classification
    # Mock crop to return a page-like object with extract_text
    cropped = MagicMock()
    cropped.extract_text.return_value = ""
    page.crop.return_value = cropped
    return page


class TestTemplateDetector:
    """Tests for TemplateDetector."""

    def test_initialization(self, mock_registry):
        """Test detector initialization."""
        detector = TemplateDetector(mock_registry)

        assert detector.registry == mock_registry
        assert len(detector.detectors) == 7  # Phase 2: Added CardNumber, LoanReference
        # Exclusion, IBAN, CardNumber, LoanReference, Filename, Header, ColumnHeader

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    def test_detect_by_iban(
        self, mock_iban_detect, mock_exclusion_detect, mock_registry, mock_page
    ):
        """Test template detection by IBAN (highest priority)."""
        aib_template = mock_registry.get_all_templates()[0]
        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=1.0,
                detector_name="IBAN",
                match_details={},
            )
        ]

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == aib_template
        mock_iban_detect.assert_called_once()

    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    def test_detect_by_filename_fallback(
        self,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_header_detect,
        mock_column_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection falls back to filename when IBAN fails (Phase 2)."""
        revolut_template = mock_registry.get_all_templates()[1]
        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []
        mock_filename_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.85,
                detector_name="Filename",
                match_details={},
            )
        ]

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == revolut_template
        mock_iban_detect.assert_called_once()
        mock_filename_detect.assert_called_once()

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_uses_default_when_no_match(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection uses default template when no detector matches."""
        default_template = mock_registry.get_default_template.return_value
        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template
        mock_registry.get_default_template.assert_called()

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    def test_detect_handles_detector_exception(
        self, mock_iban_detect, mock_exclusion_detect, mock_registry, mock_page
    ):
        """Test detection continues when a detector raises exception."""
        mock_exclusion_detect.return_value = []
        mock_iban_detect.side_effect = ValueError("Detector error")
        default_template = mock_registry.get_default_template()

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template

    def test_detect_no_enabled_templates(self, mock_registry, mock_page):
        """Test detection with no enabled templates uses default."""
        mock_registry.get_all_templates.return_value = []
        default_template = mock_registry.get_default_template()

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template

    def test_force_template_valid(self, mock_registry):
        """Test forcing valid template."""
        aib_template = mock_registry.get_template("aib")

        detector = TemplateDetector(mock_registry)
        result = detector.force_template("aib")

        assert result == aib_template

    def test_force_template_invalid(self, mock_registry):
        """Test forcing invalid template returns None."""
        detector = TemplateDetector(mock_registry)
        result = detector.force_template("nonexistent")

        assert result is None

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_below_minimum_threshold(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection falls back to default when confidence is below threshold."""
        revolut_template = mock_registry.get_all_templates()[1]
        default_template = mock_registry.get_default_template()

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []
        # Filename detector returns low confidence (0.5 * 0.8 weight = 0.4 < 0.6 threshold)
        mock_filename_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.5,
                detector_name="Filename",
                match_details={},
            )
        ]

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_tie_breaking_iban_preference(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test tie-breaking prefers template with IBAN match."""
        aib_template = mock_registry.get_all_templates()[0]
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []

        # Create a TRUE TIE: Both templates get same weighted score
        # AIB: ColumnHeader (0.8 * 1.5 = 1.2) + Header (0.3 * 1.0 = 0.3) + IBAN (0.25 * 2.0 = 0.5) = 2.0
        # Revolut: ColumnHeader (0.8 * 1.5 = 1.2) + Header (0.8 * 1.0 = 0.8) = 2.0
        # Tie! But AIB has IBAN, should win
        mock_iban_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.25,  # Low confidence IBAN
                detector_name="IBAN",
                match_details={},
            )
        ]
        mock_header_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.3,
                detector_name="Header",
                match_details={},
            ),
            DetectionResult(
                template=revolut_template,
                confidence=0.8,
                detector_name="Header",
                match_details={},
            ),
        ]
        mock_column_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.8,
                detector_name="ColumnHeader",
                match_details={},
            ),
            DetectionResult(
                template=revolut_template,
                confidence=0.8,
                detector_name="ColumnHeader",
                match_details={},
            ),
        ]
        mock_filename_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # AIB should win the tie because it has IBAN match
        assert result == aib_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_tie_breaking_max_confidence(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test tie-breaking prefers template with highest max confidence (no IBAN)."""
        aib_template = mock_registry.get_all_templates()[0]
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []  # No IBAN matches (skip rule 1)
        # Create tie: both templates have same aggregate score but different max confidence
        # AIB: Header (0.6 * 1.0 = 0.6)
        # Revolut: Filename (0.75 * 0.8 = 0.6)
        # Tie! Revolut has higher max confidence (0.75 > 0.6), should win
        mock_header_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.6,
                detector_name="Header",
                match_details={},
            )
        ]
        mock_filename_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.75,  # Higher max confidence
                detector_name="Filename",
                match_details={},
            )
        ]
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # Revolut wins: same aggregate score but higher max confidence
        assert result == revolut_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_tie_breaking_alphabetical(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test tie-breaking uses alphabetical order as final fallback."""
        aib_template = mock_registry.get_all_templates()[0]
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []  # No IBAN (skip rule 1)
        # Create perfect tie: same aggregate score AND same max confidence
        # AIB: Header (0.75 * 1.0 = 0.75), max conf = 0.75
        # Revolut: Header (0.75 * 1.0 = 0.75), max conf = 0.75
        # Tie on both score and max confidence! Use alphabetical: aib < revolut
        mock_header_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.75,
                detector_name="Header",
                match_details={},
            ),
            DetectionResult(
                template=revolut_template,
                confidence=0.75,
                detector_name="Header",
                match_details={},
            ),
        ]
        mock_filename_detect.return_value = []
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # AIB wins: alphabetically first ("aib" < "revolut")
        assert result == aib_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_template_not_found_in_registry(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection handles case where selected template is not in registry."""
        aib_template = mock_registry.get_all_templates()[0]
        default_template = mock_registry.get_default_template()

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=1.0,
                detector_name="IBAN",
                match_details={},
            )
        ]
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []

        # Mock get_template to return None (template not found)
        mock_registry.get_template.return_value = None

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template

    def test_classify_document_type_credit_card_by_card_number(self, mock_page):
        """Test classification as credit card via card number pattern."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Statement\n**** **** **** 1234"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "credit_card_statement"

    def test_classify_document_type_credit_card_by_header(self, mock_page):
        """Test classification as credit card via header keyword."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Credit Card Statement\nBalance: $100"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "credit_card_statement"

    def test_classify_document_type_loan_by_reference(self, mock_page):
        """Test classification as loan statement via loan reference."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Loan Statement\nLoan Ref: ABC123"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "loan_statement"

    def test_classify_document_type_loan_by_header(self, mock_page):
        """Test classification as loan statement via header keyword."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Mortgage Statement\nAccount details"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "loan_statement"

    def test_classify_document_type_bank_by_iban(self, mock_page):
        """Test classification as bank statement via IBAN."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Bank Statement\nIBAN: IE29AIBK"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "bank_statement"

    def test_classify_document_type_uncertain(self, mock_page):
        """Test classification returns None when uncertain."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Some Generic Document"
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result is None

    def test_classify_document_type_no_text(self, mock_page):
        """Test classification handles missing text gracefully."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = ""
        mock_page.crop.return_value = mock_cropped

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result is None

    def test_classify_document_type_crop_failure_fallback(self, mock_page):
        """Test classification falls back to full page when crop fails."""
        mock_registry = MagicMock()
        mock_page.width = 595.28
        mock_page.height = 841.89
        mock_page.crop.side_effect = AttributeError("Crop failed")
        mock_page.extract_text.return_value = "Credit Card Statement"

        detector = TemplateDetector(mock_registry)
        result = detector._classify_document_type(mock_page)

        assert result == "credit_card_statement"

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_with_document_type_filtered_templates(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection filters templates by document type."""
        credit_card_template = BankTemplate(
            id="cc_default",
            name="Credit Card Default",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                header_keywords=["Credit Card"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        # Mock document type classification
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = (
            "Credit Card Statement\nCard Number: ****1234"
        )
        mock_page.crop.return_value = mock_cropped

        # Mock registry to return credit card template for type filter
        mock_registry.get_templates_by_type.return_value = [credit_card_template]
        mock_registry.get_default_for_type.return_value = credit_card_template

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = [
            DetectionResult(
                template=credit_card_template,
                confidence=0.9,
                detector_name="Header",
                match_details={},
            )
        ]
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # Should call get_templates_by_type with "credit_card_statement"
        mock_registry.get_templates_by_type.assert_called_with("credit_card_statement")
        assert result == credit_card_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_fallback_when_type_filtered_has_no_templates(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection falls back to all templates when type filter returns none."""
        default_template = mock_registry.get_default_template()

        # Mock document type classification returns type but no templates for it
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Credit Card Statement"
        mock_page.crop.return_value = mock_cropped

        mock_registry.get_templates_by_type.return_value = []  # No templates for this type

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # Should fall back to all templates
        mock_registry.get_all_templates.assert_called()
        assert result == default_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_detect_uses_type_specific_default(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Test detection uses document-type-specific default when no match."""
        credit_card_default = BankTemplate(
            id="cc_default",
            name="Credit Card Default",
            document_type="credit_card_statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                header_keywords=["Credit Card"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=300,
                table_bottom_y=720,
                columns={"Date": (26, 78)},
            ),
        )

        # Mock document type classification
        mock_cropped = MagicMock()
        mock_cropped.extract_text.return_value = "Credit Card Statement"
        mock_page.crop.return_value = mock_cropped

        mock_registry.get_templates_by_type.return_value = [credit_card_default]
        mock_registry.get_default_for_type.return_value = credit_card_default

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # Should call get_default_for_type with "credit_card_statement"
        mock_registry.get_default_for_type.assert_called_with("credit_card_statement")
        assert result == credit_card_default

    # -----------------------------------------------------------------------
    # ScoringConfig tests
    # -----------------------------------------------------------------------

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.card_number_detector.CardNumberDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.loan_reference_detector.LoanReferenceDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_threshold_boundary_passes(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_loan_detect,
        mock_card_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Filename score exactly at threshold (0.75 * 0.8 = 0.60 >= 0.60) selects template."""
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_card_detect.return_value = []
        mock_loan_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []
        mock_filename_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.75,  # 0.75 * 0.8 = 0.60 — exactly at threshold
                detector_name="Filename",
                match_details={},
            )
        ]

        scoring = ScoringConfig(
            weights={"Filename": 0.8},
            min_confidence_threshold=0.60,
        )
        detector = TemplateDetector(mock_registry, scoring=scoring)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == revolut_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.card_number_detector.CardNumberDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.loan_reference_detector.LoanReferenceDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_threshold_boundary_fails(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_loan_detect,
        mock_card_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """Filename score just below threshold (0.74 * 0.8 = 0.592 < 0.60) uses default."""
        revolut_template = mock_registry.get_all_templates()[1]
        default_template = mock_registry.get_default_template()

        mock_exclusion_detect.return_value = []
        mock_iban_detect.return_value = []
        mock_card_detect.return_value = []
        mock_loan_detect.return_value = []
        mock_header_detect.return_value = []
        mock_column_detect.return_value = []
        mock_filename_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.74,  # 0.74 * 0.8 = 0.592 — just below threshold
                detector_name="Filename",
                match_details={},
            )
        ]

        scoring = ScoringConfig(
            weights={"Filename": 0.8},
            min_confidence_threshold=0.60,
        )
        detector = TemplateDetector(mock_registry, scoring=scoring)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        assert result == default_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.card_number_detector.CardNumberDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.loan_reference_detector.LoanReferenceDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_weight_ordering_iban_beats_column_header(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_loan_detect,
        mock_card_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """IBAN weight 2.0 (0.5*2.0=1.0) beats ColumnHeader weight 1.5 (0.6*1.5=0.9)."""
        aib_template = mock_registry.get_all_templates()[0]
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []
        mock_card_detect.return_value = []
        mock_loan_detect.return_value = []
        mock_filename_detect.return_value = []
        mock_header_detect.return_value = []
        # AIB scores via IBAN: 0.5 * 2.0 = 1.0
        mock_iban_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.5,
                detector_name="IBAN",
                match_details={},
            )
        ]
        # Revolut scores via ColumnHeader: 0.6 * 1.5 = 0.9
        mock_column_detect.return_value = [
            DetectionResult(
                template=revolut_template,
                confidence=0.6,
                detector_name="ColumnHeader",
                match_details={},
            )
        ]

        scoring = ScoringConfig.default()
        detector = TemplateDetector(mock_registry, scoring=scoring)
        result = detector.detect_template(Path("test.pdf"), mock_page)

        # AIB wins: 1.0 > 0.9
        assert result == aib_template

    @patch(
        "bankstatements_core.templates.detectors.exclusion_detector.ExclusionDetector.detect"
    )
    @patch("bankstatements_core.templates.detectors.iban_detector.IBANDetector.detect")
    @patch(
        "bankstatements_core.templates.detectors.card_number_detector.CardNumberDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.loan_reference_detector.LoanReferenceDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.filename_detector.FilenameDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.header_detector.HeaderDetector.detect"
    )
    @patch(
        "bankstatements_core.templates.detectors.column_header_detector.ColumnHeaderDetector.detect"
    )
    def test_get_detection_explanation_tie_break_reason(
        self,
        mock_column_detect,
        mock_header_detect,
        mock_filename_detect,
        mock_loan_detect,
        mock_card_detect,
        mock_iban_detect,
        mock_exclusion_detect,
        mock_registry,
        mock_page,
    ):
        """get_detection_explanation populates tie_winner_reason when a tie is broken."""
        aib_template = mock_registry.get_all_templates()[0]
        revolut_template = mock_registry.get_all_templates()[1]

        mock_exclusion_detect.return_value = []
        mock_card_detect.return_value = []
        mock_loan_detect.return_value = []
        mock_filename_detect.return_value = []
        # Create a tie: AIB via IBAN (0.25*2.0=0.5) + Header (0.3*1.0=0.3) = 0.8
        #               Revolut via Header (0.8*1.0=0.8)                    = 0.8
        mock_iban_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.25,
                detector_name="IBAN",
                match_details={},
            )
        ]
        mock_header_detect.return_value = [
            DetectionResult(
                template=aib_template,
                confidence=0.3,
                detector_name="Header",
                match_details={},
            ),
            DetectionResult(
                template=revolut_template,
                confidence=0.8,
                detector_name="Header",
                match_details={},
            ),
        ]
        mock_column_detect.return_value = []

        detector = TemplateDetector(mock_registry)
        explanation = detector.get_detection_explanation(Path("test.pdf"), mock_page)

        assert isinstance(explanation, DetectionExplanation)
        assert explanation.tie_broken is True
        assert explanation.tie_winner_reason == "IBAN match"
        assert explanation.selected_template_id == "aib"
        assert explanation.passed_threshold is True
        assert explanation.used_default is False
        assert "aib" in explanation.per_template_scores
        assert "revolut" in explanation.per_template_scores
