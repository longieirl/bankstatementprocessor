"""Template detector that orchestrates multi-signal detection."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from pdfplumber.page import Page

from bankstatements_core.templates.detectors import (
    BaseDetector,
    CardNumberDetector,
    ColumnHeaderDetector,
    DetectionResult,
    ExclusionDetector,
    FilenameDetector,
    HeaderDetector,
    IBANDetector,
    LoanReferenceDetector,
)
from bankstatements_core.templates.template_model import BankTemplate
from bankstatements_core.templates.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)

# Detector weights for Phase 2 aggregated scoring
# Higher weight = more reliable/specific detector
DETECTOR_WEIGHTS = {
    "IBAN": 2.0,  # Most reliable for bank statements (IBAN is unique)
    "CardNumber": 2.0,  # NEW: Most reliable for credit card statements
    "LoanReference": 2.0,  # NEW: Most reliable for loan statements
    "ColumnHeader": 1.5,  # Strong indicator of template structure
    "Header": 1.0,  # Baseline weight
    "Filename": 0.8,  # Less reliable (users can rename files)
    "Exclusion": 0.0,  # Binary filter, not used in scoring
}

# Minimum aggregate confidence required to select a template
# Prevents weak matches from being selected
# Threshold of 0.6 allows single detector matches (e.g., Filename @ 0.85 * 0.8 = 0.68)
# while rejecting very weak matches (< 0.6)
MIN_CONFIDENCE_THRESHOLD = 0.6


class TemplateDetector:
    """Orchestrates multi-signal template detection using confidence-based scoring."""

    def __init__(self, registry: TemplateRegistry):
        """Initialize detector with template registry.

        Args:
            registry: TemplateRegistry containing available templates
        """
        self.registry = registry

        # Initialize detector chain
        # ExclusionDetector runs FIRST to filter out excluded templates
        # All detectors now return scored results
        self.detectors: list[BaseDetector] = [
            ExclusionDetector(),  # Run first to filter exclusions
            IBANDetector(),  # Bank statements
            CardNumberDetector(),  # NEW: Credit card statements
            LoanReferenceDetector(),  # NEW: Loan statements
            FilenameDetector(),
            HeaderDetector(),
            ColumnHeaderDetector(),
        ]

    def _classify_document_type(self, first_page: Page) -> str | None:
        """Classify document type based on content signals.

        This pre-classification helps narrow down templates before running
        full detection, improving accuracy and performance.

        Detection signals (in priority order):
        1. Card numbers (e.g., "**** **** **** 1234") → credit_card_statement
        2. Loan references (e.g., "Loan Ref:", "Mortgage Account:") → loan_statement
        3. IBAN patterns (e.g., "IBAN: IE29...") → bank_statement
        4. Header keywords ("Credit Card", "Loan Statement") → respective types

        Args:
            first_page: First page of the PDF

        Returns:
            Document type string if classification succeeds, None if uncertain.
            Possible values: "bank_statement", "credit_card_statement", "loan_statement"
        """
        try:
            # Extract text from header area (top 400 PDF points)
            header_bbox = (0, 0, first_page.width, 400)
            text = first_page.crop(header_bbox).extract_text()
        except (AttributeError, ValueError, TypeError):
            # Fallback to full page if cropping fails
            text = first_page.extract_text()

        if not text:
            logger.debug("No text found for document type classification")
            return None

        text_lower = text.lower()

        # Priority 1: Check for card number patterns (most specific)
        card_patterns = [
            r"\*{4}\s*\*{4}\s*\*{4}\s*[0-9]{4}",  # Masked: **** **** **** 1234
            r"card\s*(?:number|no\.?):\s*\*+\s*[0-9]{4}",  # Card Number: ****1234
        ]
        for pattern in card_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(
                    "Document classified as credit_card_statement (card number found)"
                )
                return "credit_card_statement"

        # Priority 2: Check for loan references
        loan_patterns = [
            r"loan\s*(?:ref|reference|no|number):\s*[A-Z0-9-]+",
            r"mortgage\s*(?:account|ref|no):\s*[A-Z0-9-]+",
        ]
        for pattern in loan_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(
                    "Document classified as loan_statement (loan reference found)"
                )
                return "loan_statement"

        # Priority 3: Check for IBAN (indicates bank statement)
        if re.search(r"iban:\s*[A-Z]{2}[0-9]{2}", text, re.IGNORECASE):
            logger.info("Document classified as bank_statement (IBAN found)")
            return "bank_statement"

        # Priority 4: Check header keywords
        if any(
            keyword in text_lower
            for keyword in ["credit card statement", "card statement"]
        ):
            logger.info("Document classified as credit_card_statement (header keyword)")
            return "credit_card_statement"

        if any(
            keyword in text_lower
            for keyword in ["loan statement", "mortgage statement"]
        ):
            logger.info("Document classified as loan_statement (header keyword)")
            return "loan_statement"

        # Uncertain - let detector scoring decide
        logger.debug("Document type classification uncertain")
        return None

    def detect_template(self, pdf_path: Path, first_page: Page) -> BankTemplate:
        """Detect template using document type classification and aggregated scoring.

        Phase 2 enhancements:
        - Pre-classifies document type before template matching
        - Filters templates by document_type if classification succeeds
        - Adds new detector types (CardNumber, LoanReference) to chain
        - Falls back to all templates if classification uncertain
        - Aggregates confidence scores from ALL detectors per template
        - Applies detector-specific weights (IBAN/CardNumber/LoanRef=2.0x, ColumnHeader=1.5x, etc.)
        - Enforces minimum confidence threshold (0.6)
        - Implements tie-breaking logic (prefer IBAN > max confidence > alphabetical)

        Args:
            pdf_path: Path to the PDF file
            first_page: First page of the PDF

        Returns:
            Detected BankTemplate with highest aggregate score or default template
        """
        logger.debug(f"Starting template detection for: {pdf_path.name}")

        # Phase 2: Try to classify document type first
        document_type = self._classify_document_type(first_page)

        # Get templates, optionally filtered by type
        if document_type:
            logger.info(f"Filtering templates for document_type='{document_type}'")
            templates = self.registry.get_templates_by_type(document_type)

            if not templates:
                logger.warning(
                    f"No templates found for document_type='{document_type}', "
                    f"using all templates"
                )
                templates = self.registry.get_all_templates()
        else:
            logger.debug("Document type uncertain, using all templates")
            templates = self.registry.get_all_templates()

        if not templates:
            logger.warning("No enabled templates found, using default")
            return self.registry.get_default_template()

        # Phase 2: Aggregate scores from all detectors
        template_scores: dict[str, float] = defaultdict(float)
        template_details: dict[str, list[DetectionResult]] = defaultdict(list)
        excluded_templates: set[str] = set()

        for detector in self.detectors:
            try:
                results = detector.detect(pdf_path, first_page, templates)
                if results:
                    for result in results:
                        # Skip excluded templates (confidence = 0.0)
                        if result.confidence == 0.0:
                            logger.debug(
                                f"Template '{result.template.id}' excluded by "
                                f"{result.detector_name}"
                            )
                            # Mark as excluded
                            excluded_templates.add(result.template.id)
                            continue

                        # Skip templates that were already excluded
                        if result.template.id in excluded_templates:
                            continue

                        # Apply detector-specific weight
                        weight = DETECTOR_WEIGHTS.get(result.detector_name, 1.0)
                        weighted_score = result.confidence * weight

                        template_scores[result.template.id] += weighted_score
                        template_details[result.template.id].append(result)

            except (AttributeError, ValueError, TypeError, OSError) as e:
                # Expected errors: PDF access issues, text extraction failures, type errors
                logger.error(
                    f"Error in {detector.name} detector for {pdf_path.name}: {e}"
                )
            # Let unexpected errors bubble up

        # Remove excluded templates
        valid_scores = {
            tid: score
            for tid, score in template_scores.items()
            if tid not in excluded_templates and score > 0.0
        }

        if not valid_scores:
            # No valid matches - use document-type-specific default
            if document_type:
                default = self.registry.get_default_for_type(document_type)
                logger.info(
                    f"No templates matched, using default for {document_type}: "
                    f"{default.name} for {pdf_path.name}"
                )
            else:
                default = self.registry.get_default_template()
                logger.info(
                    f"No templates matched, using global default: {default.name} "
                    f"for {pdf_path.name}"
                )
            return default

        # Enhanced logging: Show all candidates with detector breakdown
        logger.info(f"Template detection results for {pdf_path.name}:")
        for template_id in sorted(
            valid_scores, key=lambda x: valid_scores[x], reverse=True
        ):
            score = valid_scores[template_id]
            details = template_details[template_id]
            detector_breakdown = ", ".join(
                f"{d.detector_name}={d.confidence:.2f}"
                for d in sorted(details, key=lambda x: x.confidence, reverse=True)
            )
            logger.info(f"  {template_id}: {score:.2f} ({detector_breakdown})")

        # Find best template
        best_template_id = max(valid_scores, key=lambda x: valid_scores[x])
        best_score = valid_scores[best_template_id]

        # Phase 2: Check minimum confidence threshold
        if best_score < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(
                f"Best match '{best_template_id}' has confidence {best_score:.2f}, "
                f"below threshold {MIN_CONFIDENCE_THRESHOLD}. Using default template."
            )
            if document_type:
                return self.registry.get_default_for_type(document_type)
            return self.registry.get_default_template()

        # Phase 2: Handle ties with deterministic tie-breaking
        tied_templates = [
            tid for tid, score in valid_scores.items() if score == best_score
        ]

        if len(tied_templates) > 1:
            logger.info(f"Tie detected between: {', '.join(tied_templates)}")
            best_template_id = self._break_tie(tied_templates, template_details)
            logger.info(f"Tie-breaker selected: {best_template_id}")

        # Get the selected template
        best_template = self.registry.get_template(best_template_id)
        if not best_template:
            # Shouldn't happen, but handle gracefully
            logger.error(
                f"Selected template '{best_template_id}' not found in registry"
            )
            if document_type:
                return self.registry.get_default_for_type(document_type)
            return self.registry.get_default_template()

        logger.info(
            f"Selected template: {best_template.name} "
            f"(aggregate confidence={best_score:.2f}) for {pdf_path.name}"
        )
        return best_template

    def _break_tie(
        self,
        tied_templates: list[str],
        template_details: dict[str, list[DetectionResult]],
    ) -> str:
        """Break ties using secondary criteria.

        Tie-breaking rules (in order):
        1. Prefer template with IBAN match (most specific)
        2. Prefer template with highest max confidence from any detector
        3. Prefer alphabetically first (deterministic fallback)

        Args:
            tied_templates: List of template IDs with equal aggregate scores
            template_details: Mapping of template IDs to their detection results

        Returns:
            Template ID that wins the tie-break
        """
        # Rule 1: Prefer template with IBAN match
        for template_id in tied_templates:
            details = template_details[template_id]
            if any(d.detector_name == "IBAN" for d in details):
                logger.debug(f"Tie-breaker: {template_id} has IBAN match")
                return template_id

        # Rule 2: Prefer template with highest max confidence
        max_confidences = {
            tid: max(d.confidence for d in template_details[tid])
            for tid in tied_templates
        }
        best_by_max_conf = max(max_confidences, key=lambda x: max_confidences[x])
        if max_confidences[best_by_max_conf] > max(
            c for tid, c in max_confidences.items() if tid != best_by_max_conf
        ):
            logger.debug(
                f"Tie-breaker: {best_by_max_conf} has highest max confidence "
                f"({max_confidences[best_by_max_conf]:.2f})"
            )
            return best_by_max_conf

        # Rule 3: Alphabetical fallback (deterministic)
        alphabetical_first = sorted(tied_templates)[0]
        logger.debug(f"Tie-breaker: {alphabetical_first} (alphabetically first)")
        return alphabetical_first

    def force_template(self, template_id: str) -> BankTemplate | None:
        """Force use of specific template by ID.

        Args:
            template_id: Template identifier to force

        Returns:
            BankTemplate if found and enabled, None otherwise
        """
        template = self.registry.get_template(template_id)

        if template:
            logger.info(f"Forced template: {template.name}")
        else:
            logger.warning(f"Forced template '{template_id}' not found or disabled")

        return template
