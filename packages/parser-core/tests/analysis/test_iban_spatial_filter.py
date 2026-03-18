"""Tests for IBAN spatial filtering."""

from unittest.mock import MagicMock, patch

import pytest

from bankstatements_core.analysis.bbox_utils import BBox
from bankstatements_core.analysis.iban_spatial_filter import (
    IBANCandidate,
    IBANSpatialFilter,
)


class TestIBANCandidate:
    """Tests for IBANCandidate dataclass."""

    def test_iban_candidate_creation(self):
        """Test creating IBAN candidate."""
        bbox = BBox(x0=100, y0=50, x1=200, y1=60)
        candidate = IBANCandidate(
            iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox
        )

        assert candidate.iban == "IE29AIBK93115212345678"
        assert candidate.masked == "IE29****5678"
        assert candidate.bbox == bbox
        assert candidate.confidence_score == 0.0
        assert candidate.rejection_reason is None

    def test_iban_candidate_with_score(self):
        """Test IBAN candidate with confidence score."""
        bbox = BBox(x0=100, y0=50, x1=200, y1=60)
        candidate = IBANCandidate(
            iban="IE29AIBK93115212345678",
            masked="IE29****5678",
            bbox=bbox,
            confidence_score=85.5,
        )

        assert candidate.confidence_score == 85.5


class TestIBANSpatialFilter:
    """Tests for IBANSpatialFilter class."""

    def test_init(self):
        """Test filter initialization."""
        filter = IBANSpatialFilter()
        assert filter.iban_extractor is not None

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_single_word_iban(self, mock_extractor_class):
        """Test extracting IBAN from single word."""
        # Mock IBANExtractor
        mock_extractor = MagicMock()
        mock_extractor.is_valid_iban.return_value = True
        mock_extractor._mask_iban.return_value = "IE29****5678"
        mock_extractor_class.return_value = mock_extractor

        # Mock page
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.extract_words.return_value = [
            {
                "text": "IE29AIBK93115212345678",
                "x0": 100,
                "top": 50,
                "x1": 200,
                "bottom": 60,
            }
        ]

        filter = IBANSpatialFilter()
        filter.iban_extractor = mock_extractor  # Override with mock

        candidates = filter.extract_iban_candidates(mock_page)

        assert len(candidates) == 1
        assert candidates[0].iban == "IE29AIBK93115212345678"
        assert candidates[0].masked == "IE29****5678"
        assert candidates[0].bbox.x0 == 100
        assert candidates[0].bbox.y0 == 50

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_multi_word_iban(self, mock_extractor_class):
        """Test extracting IBAN split across multiple words."""
        mock_extractor = MagicMock()
        mock_extractor.is_valid_iban.return_value = True
        mock_extractor._mask_iban.return_value = "IE29****5678"
        mock_extractor_class.return_value = mock_extractor

        # Mock page with IBAN split into parts
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.extract_words.return_value = [
            {"text": "IE29", "x0": 100, "top": 50, "x1": 120, "bottom": 60},
            {"text": "AIBK", "x0": 125, "top": 50, "x1": 145, "bottom": 60},
            {"text": "9311", "x0": 150, "top": 50, "x1": 170, "bottom": 60},
            {"text": "5212345678", "x0": 175, "top": 50, "x1": 220, "bottom": 60},
        ]

        filter = IBANSpatialFilter()
        filter.iban_extractor = mock_extractor

        candidates = filter.extract_iban_candidates(mock_page)

        assert len(candidates) >= 1
        # Should combine into full IBAN
        assert any(c.iban == "IE29AIBK93115212345678" for c in candidates)

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_no_iban(self, mock_extractor_class):
        """Test extracting when no IBAN present (both word-based and text-based fail)."""
        mock_extractor = MagicMock()
        mock_extractor.is_valid_iban.return_value = False  # Word-based fails
        mock_extractor.extract_iban.return_value = None  # Text-based also fails
        mock_extractor_class.return_value = mock_extractor

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.extract_words.return_value = [
            {"text": "Some", "x0": 100, "top": 50, "x1": 120, "bottom": 60},
            {"text": "random", "x0": 125, "top": 50, "x1": 145, "bottom": 60},
            {"text": "text", "x0": 150, "top": 50, "x1": 170, "bottom": 60},
        ]
        mock_page.extract_text.return_value = "Some random text without IBAN"

        filter = IBANSpatialFilter()
        filter.iban_extractor = mock_extractor

        candidates = filter.extract_iban_candidates(mock_page)

        assert len(candidates) == 0
        # Verify fallback was attempted
        mock_page.extract_text.assert_called_once()
        mock_extractor.extract_iban.assert_called_once()

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_page_not_first_warning(self, mock_extractor_class):
        """Test warning when extracting from non-first page."""
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor

        mock_page = MagicMock()
        mock_page.page_number = 2  # Not first page
        mock_page.extract_words.return_value = []

        filter = IBANSpatialFilter()

        with patch(
            "bankstatements_core.analysis.iban_spatial_filter.logger"
        ) as mock_logger:
            _ = filter.extract_iban_candidates(mock_page)
            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "should only process first page" in str(
                mock_logger.warning.call_args
            )

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_empty_page(self, mock_extractor_class):
        """Test extracting from page with no words."""
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.extract_words.return_value = []

        filter = IBANSpatialFilter()

        candidates = filter.extract_iban_candidates(mock_page)

        assert len(candidates) == 0

    def test_filter_by_table_overlap_no_overlap(self):
        """Test filtering IBANs with no table overlap."""
        bbox_iban = BBox(x0=100, y0=50, x1=200, y1=60)
        bbox_table = BBox(x0=50, y0=300, x1=550, y1=700)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_iban
            )
        ]

        table_regions = [bbox_table]

        filter = IBANSpatialFilter()
        filtered = filter.filter_by_table_overlap(candidates, table_regions)

        # IBAN should not be filtered (no overlap)
        assert len(filtered) == 1
        assert filtered[0].iban == "IE29AIBK93115212345678"

    def test_filter_by_table_overlap_with_overlap(self):
        """Test filtering IBANs that overlap with table."""
        # IBAN inside table region
        bbox_iban = BBox(x0=100, y0=350, x1=200, y1=360)
        bbox_table = BBox(x0=50, y0=300, x1=550, y1=700)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_iban
            )
        ]

        table_regions = [bbox_table]

        filter = IBANSpatialFilter()
        filtered = filter.filter_by_table_overlap(candidates, table_regions)

        # IBAN should be filtered out (overlaps table)
        assert len(filtered) == 0

    def test_filter_by_table_overlap_multiple_candidates(self):
        """Test filtering with multiple IBAN candidates."""
        bbox_iban1 = BBox(x0=100, y0=50, x1=200, y1=60)  # Above table
        bbox_iban2 = BBox(x0=100, y0=350, x1=200, y1=360)  # Inside table
        bbox_table = BBox(x0=50, y0=300, x1=550, y1=700)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_iban1
            ),
            IBANCandidate(
                iban="IE29AIBK93115212345679", masked="IE29****5679", bbox=bbox_iban2
            ),
        ]

        table_regions = [bbox_table]

        filter = IBANSpatialFilter()
        filtered = filter.filter_by_table_overlap(candidates, table_regions)

        # Only first IBAN should remain
        assert len(filtered) == 1
        assert filtered[0].iban == "IE29AIBK93115212345678"

    def test_filter_by_table_overlap_no_tables(self):
        """Test filtering with no table regions."""
        bbox_iban = BBox(x0=100, y0=50, x1=200, y1=60)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_iban
            )
        ]

        table_regions = []

        filter = IBANSpatialFilter()
        filtered = filter.filter_by_table_overlap(candidates, table_regions)

        # All candidates should remain
        assert len(filtered) == 1

    def test_filter_by_table_overlap_threshold(self):
        """Test filtering with overlap threshold."""
        # Partial overlap
        bbox_iban = BBox(x0=540, y0=290, x1=600, y1=310)
        bbox_table = BBox(x0=50, y0=300, x1=550, y1=700)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_iban
            )
        ]

        table_regions = [bbox_table]

        filter = IBANSpatialFilter()

        # With threshold 0.0, any overlap filters out
        filtered_strict = filter.filter_by_table_overlap(
            candidates, table_regions, overlap_threshold=0.0
        )
        assert len(filtered_strict) == 0

        # With threshold 0.5, small overlap might not filter
        _ = filter.filter_by_table_overlap(
            candidates, table_regions, overlap_threshold=0.5
        )
        # Depends on overlap ratio calculation

    def test_score_candidates_header_area(self):
        """Test scoring with IBAN in header area."""
        page_height = 842.0
        _ = page_height * 0.25  # 210.5 - header_boundary not used

        # IBAN in header
        bbox_header = BBox(x0=100, y0=50, x1=200, y1=60)
        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678", masked="IE29****5678", bbox=bbox_header
            )
        ]

        filter = IBANSpatialFilter()
        scored = filter.score_candidates(candidates, page_height)

        # Should get header bonus (+50) plus Y-position bonus
        assert scored[0].confidence_score >= 50.0

    def test_score_candidates_non_header_area(self):
        """Test scoring with IBAN outside header area."""
        page_height = 842.0

        # IBAN below header
        bbox_non_header = BBox(x0=100, y0=400, x1=200, y1=410)
        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678",
                masked="IE29****5678",
                bbox=bbox_non_header,
            )
        ]

        filter = IBANSpatialFilter()
        scored = filter.score_candidates(candidates, page_height)

        # Should not get header bonus
        assert scored[0].confidence_score < 50.0

    def test_score_candidates_sorting(self):
        """Test that candidates are sorted by score."""
        page_height = 842.0

        # Multiple candidates at different Y positions
        bbox1 = BBox(x0=100, y0=50, x1=200, y1=60)  # Top (high score)
        bbox2 = BBox(x0=100, y0=400, x1=200, y1=410)  # Middle (medium score)
        bbox3 = BBox(x0=100, y0=750, x1=200, y1=760)  # Bottom (low score)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345671", masked="IE29****5671", bbox=bbox2
            ),
            IBANCandidate(
                iban="IE29AIBK93115212345672", masked="IE29****5672", bbox=bbox3
            ),
            IBANCandidate(
                iban="IE29AIBK93115212345673", masked="IE29****5673", bbox=bbox1
            ),
        ]

        filter = IBANSpatialFilter()
        scored = filter.score_candidates(candidates, page_height)

        # Should be sorted highest to lowest
        assert scored[0].bbox.y0 == 50  # Top candidate first
        assert scored[1].bbox.y0 == 400  # Middle candidate second
        assert scored[2].bbox.y0 == 750  # Bottom candidate last

    def test_score_candidates_y_position_preference(self):
        """Test that higher Y positions get better scores."""
        page_height = 842.0

        bbox_top = BBox(x0=100, y0=100, x1=200, y1=110)
        bbox_bottom = BBox(x0=100, y0=700, x1=200, y1=710)

        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345671", masked="IE29****5671", bbox=bbox_top
            ),
            IBANCandidate(
                iban="IE29AIBK93115212345672", masked="IE29****5672", bbox=bbox_bottom
            ),
        ]

        filter = IBANSpatialFilter()
        scored = filter.score_candidates(candidates, page_height)

        # Top IBAN should have higher score
        assert scored[0].confidence_score > scored[1].confidence_score

    def test_select_best_iban_single_candidate(self):
        """Test selecting best IBAN with single candidate."""
        bbox = BBox(x0=100, y0=50, x1=200, y1=60)
        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345678",
                masked="IE29****5678",
                bbox=bbox,
                confidence_score=80.0,
            )
        ]

        filter = IBANSpatialFilter()
        best = filter.select_best_iban(candidates)

        assert best is not None
        assert best.iban == "IE29AIBK93115212345678"
        assert best.confidence_score == 80.0

    def test_select_best_iban_multiple_candidates(self):
        """Test selecting best IBAN with multiple candidates."""
        bbox1 = BBox(x0=100, y0=50, x1=200, y1=60)
        bbox2 = BBox(x0=100, y0=400, x1=200, y1=410)

        # Note: select_best_iban expects candidates already sorted by score
        # (which is what score_candidates does)
        candidates = [
            IBANCandidate(
                iban="IE29AIBK93115212345672",
                masked="IE29****5672",
                bbox=bbox1,
                confidence_score=80.0,
            ),
            IBANCandidate(
                iban="IE29AIBK93115212345671",
                masked="IE29****5671",
                bbox=bbox2,
                confidence_score=30.0,
            ),
        ]

        filter = IBANSpatialFilter()
        best = filter.select_best_iban(candidates)

        # Should select first candidate (highest score)
        assert best.confidence_score == 80.0
        assert best.iban == "IE29AIBK93115212345672"

    def test_select_best_iban_no_candidates(self):
        """Test selecting best IBAN with no candidates."""
        filter = IBANSpatialFilter()
        best = filter.select_best_iban([])

        assert best is None

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_text_fallback(self, mock_extractor_class):
        """Test text-based fallback when word-based extraction fails.

        This happens when IBAN is formatted in a way that word extraction
        doesn't capture (e.g., unusual spacing, OCR artifacts).
        """
        mock_extractor = MagicMock()
        mock_extractor.is_valid_iban.return_value = False  # Word-based fails
        mock_extractor.extract_iban.return_value = (
            "IE29AIBK93115212345678"  # Text succeeds
        )
        mock_extractor._mask_iban.return_value = "IE29****5678"
        mock_extractor_class.return_value = mock_extractor

        # Mock page with words that don't match IBAN pattern
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.height = 842
        mock_page.width = 595
        mock_page.extract_words.return_value = [
            {"text": "Account", "x0": 100, "top": 50, "x1": 150, "bottom": 60},
            {"text": "Number:", "x0": 155, "top": 50, "x1": 200, "bottom": 60},
        ]
        mock_page.extract_text.return_value = (
            "Account Number: IE29 AIBK 9311 5212 3456 78"
        )

        filter = IBANSpatialFilter()
        filter.iban_extractor = mock_extractor

        candidates = filter.extract_iban_candidates(mock_page)

        # Should have found IBAN via text fallback
        assert len(candidates) == 1
        assert candidates[0].iban == "IE29AIBK93115212345678"
        assert candidates[0].masked == "IE29****5678"

        # Should have approximate bounding box (top third of page)
        assert candidates[0].bbox.x0 == 0
        assert candidates[0].bbox.y0 == 0
        assert candidates[0].bbox.x1 == 595
        assert candidates[0].bbox.y1 == pytest.approx(842 / 3, rel=0.01)

        # Verify text extraction was called as fallback
        mock_page.extract_text.assert_called_once()
        mock_extractor.extract_iban.assert_called_once_with(
            "Account Number: IE29 AIBK 9311 5212 3456 78"
        )

    @patch("bankstatements_core.analysis.iban_spatial_filter.IBANExtractor")
    def test_extract_iban_candidates_no_fallback_if_word_based_succeeds(
        self, mock_extractor_class
    ):
        """Test that text fallback is not used if word-based extraction succeeds."""
        mock_extractor = MagicMock()
        mock_extractor.is_valid_iban.return_value = True  # Word-based succeeds
        mock_extractor._mask_iban.return_value = "IE29****5678"
        mock_extractor_class.return_value = mock_extractor

        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.extract_words.return_value = [
            {
                "text": "IE29AIBK93115212345678",
                "x0": 100,
                "top": 50,
                "x1": 200,
                "bottom": 60,
            }
        ]
        mock_page.extract_text.return_value = "Some text IE29AIBK93115212345678"

        filter = IBANSpatialFilter()
        filter.iban_extractor = mock_extractor

        candidates = filter.extract_iban_candidates(mock_page)

        # Should have found via word-based method
        assert len(candidates) == 1

        # Text extraction should NOT have been called
        mock_page.extract_text.assert_not_called()
