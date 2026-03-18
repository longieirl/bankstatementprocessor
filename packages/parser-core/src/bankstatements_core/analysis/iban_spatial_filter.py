"""IBAN spatial filtering for PDF analysis.

This module extracts IBAN candidates from PDF pages and filters them based on
spatial location to exclude IBANs that overlap with transaction tables.

IMPORTANT: Only processes first page for IBAN extraction.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, List, Optional

from bankstatements_core.analysis.bbox_utils import BBox, overlaps
from bankstatements_core.extraction.iban_extractor import IBANExtractor

logger = logging.getLogger(__name__)


@dataclass
class IBANCandidate:
    """IBAN candidate with spatial information.

    Attributes:
        iban: The full IBAN string
        masked: Masked IBAN for logging (e.g., IE29****5678)
        bbox: Bounding box of the IBAN location
        confidence_score: Score based on location and context (0-100)
        rejection_reason: Optional reason if candidate was rejected
    """

    iban: str
    masked: str
    bbox: BBox
    confidence_score: float = 0.0
    rejection_reason: Optional[str] = None


class IBANSpatialFilter:
    """Extract and filter IBANs based on spatial location.

    IMPORTANT: Only extracts IBAN from first page, ignores all other pages.
    """

    def __init__(self) -> None:
        """Initialize IBAN spatial filter."""
        self.iban_extractor = IBANExtractor()

    def extract_iban_candidates(self, page: Any) -> List[IBANCandidate]:
        """Extract IBAN candidates with spatial coordinates from page.

        Uses two strategies:
        1. Word-based spatial extraction (precise coordinates)
        2. Text-based extraction with approximate coordinates (fallback)

        IMPORTANT: Should only be called on first page.

        Args:
            page: pdfplumber page object (should be first page)

        Returns:
            List of IBANCandidate objects with bounding boxes
        """
        page_num = page.page_number
        if page_num != 1:
            logger.warning(
                f"⚠️  IBAN extraction called on page {page_num} - "
                "should only process first page!"
            )

        logger.debug(f"Extracting IBAN candidates from page {page_num}")

        # Extract all words with coordinates
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

        if not words:
            logger.debug("No words found on page")
            return []

        logger.debug(f"Extracted {len(words)} words from page")

        # Group nearby words into potential IBAN sequences
        candidates = []

        # Try to find IBANs in text
        for i, word in enumerate(words):
            text = word["text"]

            # Look for potential IBAN patterns (starts with 2 letters + 2 digits)
            if not re.match(r"^[A-Z]{2}\d{2}", text):
                continue

            # Try to build IBAN from this word and nearby words
            iban_text = text
            word_bbox = BBox(
                x0=word["x0"], y0=word["top"], x1=word["x1"], y1=word["bottom"]
            )

            # Look ahead for continuation (same line, within 10 pixels)
            for j in range(i + 1, min(i + 10, len(words))):
                next_word = words[j]

                # Check if on same line (within 3 pixels vertically)
                if abs(next_word["top"] - word["top"]) > 3:
                    break

                # Check if close horizontally (within 10 pixels)
                if next_word["x0"] - word_bbox.x1 > 10:
                    break

                # Add to IBAN text
                iban_text += next_word["text"]
                word_bbox = BBox(
                    x0=word_bbox.x0,
                    y0=min(word_bbox.y0, next_word["top"]),
                    x1=next_word["x1"],
                    y1=max(word_bbox.y1, next_word["bottom"]),
                )

            # Remove spaces and validate
            iban_clean = iban_text.replace(" ", "").replace("\xa0", "").upper()

            # Use IBANExtractor to validate
            if self.iban_extractor.is_valid_iban(iban_clean):
                masked = self.iban_extractor._mask_iban(iban_clean)

                candidate = IBANCandidate(
                    iban=iban_clean, masked=masked, bbox=word_bbox
                )

                candidates.append(candidate)
                logger.debug(f"Found IBAN candidate: {masked} at {word_bbox}")

        # Fallback: If no candidates found with word-based approach,
        # try text-based extraction with approximate coordinates
        if not candidates:
            logger.debug(
                "No IBANs found with word-based extraction, trying text-based fallback"
            )
            page_text = page.extract_text()
            if page_text:
                # Use IBANExtractor to find IBAN in full page text
                iban = self.iban_extractor.extract_iban(page_text)
                if iban:
                    masked = self.iban_extractor._mask_iban(iban)
                    logger.info(f"✓ Found IBAN using text-based fallback: {masked}")

                    # Create approximate bounding box (page header area)
                    # Most IBANs are in the top 1/3 of the page
                    page_height = page.height
                    page_width = page.width
                    approx_bbox = BBox(
                        x0=0,
                        y0=0,
                        x1=page_width,
                        y1=page_height / 3,  # Top third of page
                    )

                    candidate = IBANCandidate(
                        iban=iban, masked=masked, bbox=approx_bbox
                    )
                    candidates.append(candidate)
                    logger.debug(
                        f"Using approximate bounding box for fallback IBAN: {approx_bbox}"
                    )

        logger.info(f"Found {len(candidates)} IBAN candidates on page {page_num}")
        return candidates

    def filter_by_table_overlap(
        self,
        candidates: List[IBANCandidate],
        table_regions: List[BBox],
        overlap_threshold: float = 0.0,
    ) -> List[IBANCandidate]:
        """Filter out IBANs that overlap with table regions.

        Args:
            candidates: List of IBAN candidates
            table_regions: List of table bounding boxes (may be expanded)
            overlap_threshold: Overlap ratio threshold (0.0 = any overlap filters out)

        Returns:
            Filtered list of IBAN candidates (non-overlapping only)
        """
        if not table_regions:
            logger.debug("No table regions provided, returning all candidates")
            return candidates

        filtered = []
        rejected = []

        for candidate in candidates:
            # Check overlap with each table region
            overlaps_table = False
            for table_bbox in table_regions:
                if overlaps(candidate.bbox, table_bbox, threshold=overlap_threshold):
                    overlaps_table = True
                    candidate.rejection_reason = f"Overlaps with table {table_bbox}"
                    logger.debug(
                        f"REJECTED: {candidate.masked} overlaps table {table_bbox}"
                    )
                    break

            if overlaps_table:
                rejected.append(candidate)
            else:
                filtered.append(candidate)
                logger.debug(f"ACCEPTED: {candidate.masked} does not overlap tables")

        logger.info(
            f"Filtered IBANs: {len(filtered)} accepted, {len(rejected)} rejected "
            f"(table overlap)"
        )

        return filtered

    def score_candidates(
        self, candidates: List[IBANCandidate], page_height: float
    ) -> List[IBANCandidate]:
        """Score IBAN candidates based on location and context.

        Higher scores are given to:
        - IBANs in header area (top 25% of page) = +50 points
        - IBANs higher on the page = +0 to +30 points based on Y position
        - IBANs near "IBAN" label (future enhancement) = +20 points

        Args:
            candidates: List of IBAN candidates
            page_height: Height of page in points

        Returns:
            Same list with confidence_score populated, sorted by score (highest first)
        """
        header_boundary = page_height * 0.25  # Top 25% of page

        for candidate in candidates:
            score = 0.0

            # Score 1: Header area preference (+50 points)
            if candidate.bbox.y0 <= header_boundary:
                score += 50.0
                logger.debug(f"{candidate.masked}: +50 (header area)")

            # Score 2: Y-position preference (+0 to +30 points, higher = better)
            # Normalize Y position (0 = top, 1 = bottom)
            y_ratio = candidate.bbox.y0 / page_height
            position_score = 30.0 * (1.0 - y_ratio)  # Invert so top gets high score
            score += position_score
            logger.debug(
                f"{candidate.masked}: +{position_score:.1f} "
                f"(Y-position {candidate.bbox.y0:.1f}/{page_height:.1f})"
            )

            # Score 3: Near "IBAN" label (future enhancement)
            # TODO: Look for "IBAN" text nearby

            candidate.confidence_score = score
            logger.debug(f"{candidate.masked}: Total score = {score:.1f}")

        # Sort by score (highest first)
        candidates_sorted = sorted(
            candidates, key=lambda c: c.confidence_score, reverse=True
        )

        return candidates_sorted

    def select_best_iban(
        self, candidates: List[IBANCandidate]
    ) -> Optional[IBANCandidate]:
        """Select the best IBAN from scored candidates.

        Args:
            candidates: List of scored IBAN candidates (should be sorted)

        Returns:
            Best IBANCandidate, or None if no candidates
        """
        if not candidates:
            logger.info("No IBAN candidates available")
            return None

        best = candidates[0]
        logger.info(
            f"Selected IBAN: {best.masked} (score: {best.confidence_score:.1f}, "
            f"location: {best.bbox})"
        )

        return best
