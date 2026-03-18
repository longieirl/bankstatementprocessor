"""Base detector interface for template detection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pdfplumber.page import Page

from bankstatements_core.templates.template_model import BankTemplate


@dataclass
class DetectionResult:
    """Result of template detection with confidence score.

    Attributes:
        template: The matched template
        confidence: Confidence score (0.0 to 1.0)
                   0.0 = excluded/rejected
                   1.0 = perfect match
        detector_name: Name of detector that produced this result
        match_details: Additional debug information about the match
    """

    template: BankTemplate
    confidence: float
    detector_name: str
    match_details: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


class BaseDetector(ABC):
    """Abstract base class for template detectors.

    Detectors now return scored results instead of binary yes/no.
    This enables confidence-based template selection.
    """

    @abstractmethod
    def detect(
        self, pdf_path: Path, first_page: Page, templates: list[BankTemplate]
    ) -> list[DetectionResult]:
        """Attempt to detect which templates match the PDF.

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF (for content analysis)
            templates: List of templates to check

        Returns:
            List of DetectionResult objects with confidence scores.
            Empty list if no matches found.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the detector name for logging.

        Returns:
            Detector name
        """
        pass
