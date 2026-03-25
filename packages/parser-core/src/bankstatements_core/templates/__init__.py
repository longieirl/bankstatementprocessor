"""Template system for multi-bank PDF statement support."""

from __future__ import annotations

from bankstatements_core.templates.template_detector import (
    DetectionExplanation,
    ScoringConfig,
    TemplateDetector,
)
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
    TemplateProcessingConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry

__all__ = [
    "BankTemplate",
    "DetectionExplanation",
    "ScoringConfig",
    "TemplateDetectionConfig",
    "TemplateExtractionConfig",
    "TemplateProcessingConfig",
    "TemplateRegistry",
    "TemplateDetector",
]
