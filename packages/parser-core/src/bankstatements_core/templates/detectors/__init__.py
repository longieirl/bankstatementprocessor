"""Template detectors for identifying bank statement format."""

from __future__ import annotations

from bankstatements_core.templates.detectors.base import BaseDetector, DetectionResult
from bankstatements_core.templates.detectors.card_number_detector import (
    CardNumberDetector,
)
from bankstatements_core.templates.detectors.column_header_detector import (
    ColumnHeaderDetector,
)
from bankstatements_core.templates.detectors.exclusion_detector import ExclusionDetector
from bankstatements_core.templates.detectors.filename_detector import FilenameDetector
from bankstatements_core.templates.detectors.header_detector import HeaderDetector
from bankstatements_core.templates.detectors.iban_detector import IBANDetector
from bankstatements_core.templates.detectors.loan_reference_detector import (
    LoanReferenceDetector,
)

__all__ = [
    "BaseDetector",
    "CardNumberDetector",
    "ColumnHeaderDetector",
    "DetectionResult",
    "ExclusionDetector",
    "FilenameDetector",
    "HeaderDetector",
    "IBANDetector",
    "LoanReferenceDetector",
]
