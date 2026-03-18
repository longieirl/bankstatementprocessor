"""Tests for bounding box utilities."""

import pytest

from bankstatements_core.analysis.bbox_utils import (
    BBox,
    bbox_from_words,
    bbox_intersection,
    calculate_overlap_ratio,
    expand_bbox,
    merge_bboxes,
    overlaps,
)


class TestBBox:
    """Tests for BBox dataclass."""

    def test_bbox_creation(self):
        """Test basic bbox creation."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 200

    def test_bbox_width(self):
        """Test width calculation."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.width == 90

    def test_bbox_height(self):
        """Test height calculation."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.height == 180

    def test_bbox_area(self):
        """Test area calculation."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.area == 90 * 180

    def test_contains_point_inside(self):
        """Test point containment for point inside bbox."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.contains_point(50, 100)

    def test_contains_point_on_edge(self):
        """Test point containment for point on bbox edge."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert bbox.contains_point(10, 20)
        assert bbox.contains_point(100, 200)

    def test_contains_point_outside(self):
        """Test point containment for point outside bbox."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        assert not bbox.contains_point(5, 100)
        assert not bbox.contains_point(50, 10)
        assert not bbox.contains_point(150, 100)
        assert not bbox.contains_point(50, 250)

    def test_bbox_repr(self):
        """Test string representation."""
        bbox = BBox(x0=10.5, y0=20.7, x1=100.3, y1=200.9)
        repr_str = repr(bbox)
        assert "10.5" in repr_str
        assert "20.7" in repr_str
        assert "100.3" in repr_str
        assert "200.9" in repr_str


class TestOverlaps:
    """Tests for overlaps function."""

    def test_overlaps_no_intersection(self):
        """Test bboxes that don't overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=20, x1=30, y1=30)
        assert not overlaps(bbox1, bbox2)

    def test_overlaps_partial_intersection(self):
        """Test bboxes with partial overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=5, y0=5, x1=15, y1=15)
        assert overlaps(bbox1, bbox2)

    def test_overlaps_complete_containment(self):
        """Test bbox completely inside another."""
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BBox(x0=10, y0=10, x1=20, y1=20)
        assert overlaps(bbox1, bbox2)

    def test_overlaps_edge_touching(self):
        """Test bboxes touching at edge (counts as overlap in pdfplumber coords)."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=10, y0=0, x1=20, y1=10)
        # Edges touching - in PDF coordinates this is considered overlapping
        # because the check uses < not <=, but coordinates at exactly 10
        # means bbox1.x1 == bbox2.x0, so bbox1.x1 < bbox2.x0 is False
        # This means they ARE overlapping according to the logic
        assert overlaps(bbox1, bbox2)

    def test_overlaps_with_threshold_zero(self):
        """Test overlaps with threshold=0 (any overlap counts)."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=9, y0=9, x1=15, y1=15)
        assert overlaps(bbox1, bbox2, threshold=0.0)

    def test_overlaps_with_threshold_high(self):
        """Test overlaps with high threshold (requires significant overlap)."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=9, y0=9, x1=15, y1=15)
        # Small overlap, won't meet 0.5 threshold
        assert not overlaps(bbox1, bbox2, threshold=0.5)

    def test_overlaps_with_threshold_met(self):
        """Test overlaps with threshold that is met."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=0, y0=0, x1=10, y1=10)  # Identical
        assert overlaps(bbox1, bbox2, threshold=1.0)

    def test_overlaps_horizontal_separation(self):
        """Test horizontally separated bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=0, x1=30, y1=10)
        assert not overlaps(bbox1, bbox2)

    def test_overlaps_vertical_separation(self):
        """Test vertically separated bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=0, y0=20, x1=10, y1=30)
        assert not overlaps(bbox1, bbox2)


class TestCalculateOverlapRatio:
    """Tests for calculate_overlap_ratio function."""

    def test_no_overlap(self):
        """Test overlap ratio for non-overlapping bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=20, x1=30, y1=30)
        assert calculate_overlap_ratio(bbox1, bbox2) == 0.0

    def test_complete_overlap_identical(self):
        """Test overlap ratio for identical bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=0, y0=0, x1=10, y1=10)
        assert calculate_overlap_ratio(bbox1, bbox2) == 1.0

    def test_complete_containment(self):
        """Test overlap ratio when small bbox inside large bbox."""
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)  # Large
        bbox2 = BBox(x0=10, y0=10, x1=20, y1=20)  # Small inside
        # Small bbox is completely contained, ratio should be 1.0
        assert calculate_overlap_ratio(bbox1, bbox2) == 1.0

    def test_partial_overlap(self):
        """Test overlap ratio for partial overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)  # Area = 100
        bbox2 = BBox(x0=5, y0=5, x1=15, y1=15)  # Area = 100
        # Overlap area = 5x5 = 25, smaller bbox = 100, ratio = 0.25
        ratio = calculate_overlap_ratio(bbox1, bbox2)
        assert ratio == 0.25

    def test_half_overlap(self):
        """Test overlap ratio for 50% overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)  # Area = 100
        bbox2 = BBox(x0=5, y0=0, x1=15, y1=10)  # Area = 100
        # Overlap area = 5x10 = 50, smaller bbox = 100, ratio = 0.5
        ratio = calculate_overlap_ratio(bbox1, bbox2)
        assert ratio == 0.5

    def test_zero_area_bbox(self):
        """Test overlap ratio with zero-area bbox."""
        bbox1 = BBox(x0=0, y0=0, x1=0, y1=0)  # Zero area
        bbox2 = BBox(x0=0, y0=0, x1=10, y1=10)
        assert calculate_overlap_ratio(bbox1, bbox2) == 0.0

    def test_overlap_ratio_symmetry(self):
        """Test that overlap ratio is symmetric."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=5, y0=5, x1=15, y1=15)
        ratio1 = calculate_overlap_ratio(bbox1, bbox2)
        ratio2 = calculate_overlap_ratio(bbox2, bbox1)
        assert ratio1 == ratio2


class TestExpandBBox:
    """Tests for expand_bbox function."""

    def test_expand_positive_margin(self):
        """Test expanding bbox with positive margin."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        expanded = expand_bbox(bbox, margin=5)
        assert expanded.x0 == 5
        assert expanded.y0 == 15
        assert expanded.x1 == 105
        assert expanded.y1 == 205

    def test_expand_negative_margin(self):
        """Test shrinking bbox with negative margin."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        shrunk = expand_bbox(bbox, margin=-5)
        assert shrunk.x0 == 15
        assert shrunk.y0 == 25
        assert shrunk.x1 == 95
        assert shrunk.y1 == 195

    def test_expand_zero_margin(self):
        """Test expanding bbox with zero margin."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        same = expand_bbox(bbox, margin=0)
        assert same.x0 == bbox.x0
        assert same.y0 == bbox.y0
        assert same.x1 == bbox.x1
        assert same.y1 == bbox.y1

    def test_expand_creates_new_bbox(self):
        """Test that expand_bbox returns a new object."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        expanded = expand_bbox(bbox, margin=5)
        assert expanded is not bbox


class TestMergeBBoxes:
    """Tests for merge_bboxes function."""

    def test_merge_two_bboxes(self):
        """Test merging two bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=20, x1=30, y1=30)
        merged = merge_bboxes([bbox1, bbox2])
        assert merged.x0 == 0
        assert merged.y0 == 0
        assert merged.x1 == 30
        assert merged.y1 == 30

    def test_merge_overlapping_bboxes(self):
        """Test merging overlapping bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=15, y1=15)
        bbox2 = BBox(x0=10, y0=10, x1=25, y1=25)
        merged = merge_bboxes([bbox1, bbox2])
        assert merged.x0 == 0
        assert merged.y0 == 0
        assert merged.x1 == 25
        assert merged.y1 == 25

    def test_merge_single_bbox(self):
        """Test merging single bbox returns equivalent bbox."""
        bbox = BBox(x0=10, y0=20, x1=100, y1=200)
        merged = merge_bboxes([bbox])
        assert merged.x0 == bbox.x0
        assert merged.y0 == bbox.y0
        assert merged.x1 == bbox.x1
        assert merged.y1 == bbox.y1

    def test_merge_multiple_bboxes(self):
        """Test merging multiple bboxes."""
        bboxes = [
            BBox(x0=0, y0=0, x1=10, y1=10),
            BBox(x0=50, y0=50, x1=60, y1=60),
            BBox(x0=100, y0=100, x1=110, y1=110),
        ]
        merged = merge_bboxes(bboxes)
        assert merged.x0 == 0
        assert merged.y0 == 0
        assert merged.x1 == 110
        assert merged.y1 == 110

    def test_merge_empty_list_raises_error(self):
        """Test that merging empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot merge empty list"):
            merge_bboxes([])


class TestBBoxFromWords:
    """Tests for bbox_from_words function."""

    def test_bbox_from_single_word(self):
        """Test creating bbox from single word."""
        words = [{"x0": 10, "top": 20, "x1": 50, "bottom": 30}]
        bbox = bbox_from_words(words)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 50
        assert bbox.y1 == 30

    def test_bbox_from_multiple_words(self):
        """Test creating bbox from multiple words."""
        words = [
            {"x0": 10, "top": 20, "x1": 50, "bottom": 30},
            {"x0": 60, "top": 20, "x1": 100, "bottom": 30},
            {"x0": 10, "top": 40, "x1": 100, "bottom": 50},
        ]
        bbox = bbox_from_words(words)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 50

    def test_bbox_from_words_scattered(self):
        """Test creating bbox from scattered words."""
        words = [
            {"x0": 50, "top": 100, "x1": 60, "bottom": 110},
            {"x0": 0, "top": 0, "x1": 10, "bottom": 10},
            {"x0": 200, "top": 200, "x1": 210, "bottom": 210},
        ]
        bbox = bbox_from_words(words)
        assert bbox.x0 == 0
        assert bbox.y0 == 0
        assert bbox.x1 == 210
        assert bbox.y1 == 210

    def test_bbox_from_empty_words_raises_error(self):
        """Test that creating bbox from empty words raises ValueError."""
        with pytest.raises(ValueError, match="Cannot create bbox from empty word list"):
            bbox_from_words([])


class TestBBoxIntersection:
    """Tests for bbox_intersection function."""

    def test_intersection_no_overlap(self):
        """Test intersection of non-overlapping bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=20, x1=30, y1=30)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 0
        assert height == 0

    def test_intersection_partial_overlap(self):
        """Test intersection of partially overlapping bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=5, y0=5, x1=15, y1=15)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 5
        assert height == 5

    def test_intersection_complete_overlap(self):
        """Test intersection of identical bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=0, y0=0, x1=10, y1=10)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 10
        assert height == 10

    def test_intersection_containment(self):
        """Test intersection when one bbox contains another."""
        bbox1 = BBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BBox(x0=10, y0=10, x1=20, y1=20)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 10
        assert height == 10

    def test_intersection_edge_touching(self):
        """Test intersection of edge-touching bboxes."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=10, y0=0, x1=20, y1=10)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 0
        assert height == 10

    def test_intersection_horizontal_overlap_only(self):
        """Test intersection with only horizontal overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=5, y0=20, x1=15, y1=30)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 5
        assert height == 0

    def test_intersection_vertical_overlap_only(self):
        """Test intersection with only vertical overlap."""
        bbox1 = BBox(x0=0, y0=0, x1=10, y1=10)
        bbox2 = BBox(x0=20, y0=5, x1=30, y1=15)
        width, height = bbox_intersection(bbox1, bbox2)
        assert width == 0
        assert height == 5
