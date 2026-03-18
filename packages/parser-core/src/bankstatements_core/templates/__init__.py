"""Template system for multi-bank PDF statement support."""

from __future__ import annotations

from bankstatements_core.templates.template_detector import TemplateDetector
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
    TemplateProcessingConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry

__all__ = [
    "BankTemplate",
    "TemplateDetectionConfig",
    "TemplateExtractionConfig",
    "TemplateProcessingConfig",
    "TemplateRegistry",
    "TemplateDetector",
]
