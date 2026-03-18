"""Bounding box utilities for spatial analysis of PDF content.

This module provides core geometric operations for working with bounding boxes
in PDF coordinate space.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class BBox:
    """Represents a bounding box in PDF coordinate space.

    Attributes:
        x0: Left edge X coordinate
        y0: Top edge Y coordinate
        x1: Right edge X coordinate
        y1: Bottom edge Y coordinate
    """

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """Calculate width of bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Calculate height of bounding box."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Calculate area of bounding box."""
        return self.width * self.height

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is contained within this bounding box.

        Args:
            x: X coordinate of point
            y: Y coordinate of point

        Returns:
            True if point is inside bbox, False otherwise
        """
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def __repr__(self) -> str:
        """String representation of bounding box."""
        return f"BBox(x0={self.x0:.1f}, y0={self.y0:.1f}, x1={self.x1:.1f}, y1={self.y1:.1f})"


def overlaps(bbox1: BBox, bbox2: BBox, threshold: float = 0.0) -> bool:
    """Check if two bounding boxes overlap.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        threshold: Minimum overlap ratio (0.0-1.0) to consider as overlapping.
                  0.0 means any overlap counts, 1.0 means complete overlap required.

    Returns:
        True if bboxes overlap above threshold, False otherwise
    """
    # Check if there's any intersection
    if bbox1.x1 < bbox2.x0 or bbox2.x1 < bbox1.x0:
        return False
    if bbox1.y1 < bbox2.y0 or bbox2.y1 < bbox1.y0:
        return False

    # If threshold is 0, any overlap is sufficient
    if threshold == 0.0:
        return True

    # Calculate overlap ratio
    overlap_ratio = calculate_overlap_ratio(bbox1, bbox2)
    return overlap_ratio >= threshold


def calculate_overlap_ratio(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate the ratio of overlap area to the smaller bbox area.

    This uses the smaller bbox as the denominator, so if a small bbox
    is completely inside a large bbox, the ratio will be 1.0.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box

    Returns:
        Overlap ratio (0.0-1.0), where 0.0 is no overlap and 1.0 is complete
        overlap of the smaller bbox
    """
    # Calculate intersection
    x_overlap = max(0, min(bbox1.x1, bbox2.x1) - max(bbox1.x0, bbox2.x0))
    y_overlap = max(0, min(bbox1.y1, bbox2.y1) - max(bbox1.y0, bbox2.y0))

    if x_overlap == 0 or y_overlap == 0:
        return 0.0

    overlap_area = x_overlap * y_overlap

    # Use the smaller bbox area as denominator
    smaller_area = min(bbox1.area, bbox2.area)

    if smaller_area == 0:
        return 0.0

    return overlap_area / smaller_area


def expand_bbox(bbox: BBox, margin: float) -> BBox:
    """Create an expanded bounding box with added margin on all sides.

    Args:
        bbox: Original bounding box
        margin: Pixels to add on each side (can be negative to shrink)

    Returns:
        New expanded BBox
    """
    return BBox(
        x0=bbox.x0 - margin,
        y0=bbox.y0 - margin,
        x1=bbox.x1 + margin,
        y1=bbox.y1 + margin,
    )


def merge_bboxes(bboxes: List[BBox]) -> BBox:
    """Merge multiple bounding boxes into a single container bbox.

    Args:
        bboxes: List of bounding boxes to merge

    Returns:
        Single BBox that contains all input bboxes

    Raises:
        ValueError: If bboxes list is empty
    """
    if not bboxes:
        raise ValueError("Cannot merge empty list of bounding boxes")

    min_x0 = min(bbox.x0 for bbox in bboxes)
    min_y0 = min(bbox.y0 for bbox in bboxes)
    max_x1 = max(bbox.x1 for bbox in bboxes)
    max_y1 = max(bbox.y1 for bbox in bboxes)

    return BBox(x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1)


def bbox_from_words(words: List[dict]) -> BBox:
    """Create a bounding box that contains all given words.

    Args:
        words: List of word dictionaries with keys: x0, top, x1, bottom

    Returns:
        BBox containing all words

    Raises:
        ValueError: If words list is empty
    """
    if not words:
        raise ValueError("Cannot create bbox from empty word list")

    min_x0 = min(word["x0"] for word in words)
    min_y0 = min(word["top"] for word in words)
    max_x1 = max(word["x1"] for word in words)
    max_y1 = max(word["bottom"] for word in words)

    return BBox(x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1)


def bbox_intersection(bbox1: BBox, bbox2: BBox) -> Tuple[float, float]:
    """Calculate the intersection dimensions of two bounding boxes.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box

    Returns:
        Tuple of (width, height) of intersection. Returns (0, 0) if no intersection.
    """
    x_overlap = max(0, min(bbox1.x1, bbox2.x1) - max(bbox1.x0, bbox2.x0))
    y_overlap = max(0, min(bbox1.y1, bbox2.y1) - max(bbox1.y0, bbox2.y0))

    return (x_overlap, y_overlap)
