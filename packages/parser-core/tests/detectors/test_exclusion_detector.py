"""Tests for ExclusionDetector."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bankstatements_core.templates.detectors.exclusion_detector import ExclusionDetector
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
)


def make_page(
    text: str | None, crop_raises: type[Exception] | None = None
) -> MagicMock:
    """Create a mock pdfplumber Page.

    Args:
        text: Text returned by extract_text() (full page and cropped).
        crop_raises: If set, page.crop() raises this exception type.
    """
    page = MagicMock()
    page.width = 800
    if crop_raises is not None:
        page.crop.side_effect = crop_raises("crop failed")
    else:
        cropped = MagicMock()
        cropped.extract_text.return_value = text
        page.crop.return_value = cropped
    page.extract_text.return_value = text
    return page


def make_template(
    template_id: str = "cc_test",
    name: str = "Test CC",
    exclude_keywords: list[str] | None = None,
) -> BankTemplate:
    """Create a BankTemplate with configurable exclude_keywords."""
    return BankTemplate(
        id=template_id,
        name=name,
        enabled=True,
        document_type="credit_card_statement",
        detection=TemplateDetectionConfig(
            header_keywords=["Credit Card"],
            exclude_keywords=exclude_keywords or [],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (29, 78)},
        ),
    )


class TestExclusionDetector:
    """Tests for ExclusionDetector."""

    def test_name(self):
        """name property returns 'Exclusion'."""
        detector = ExclusionDetector()
        assert detector.name == "Exclusion"

    def test_no_exclude_keywords_returns_empty(self):
        """Template with no exclude_keywords is skipped — returns empty list."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=[])
        page = make_page("IBAN: IE29AIBK93115212345678")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert results == []

    def test_keyword_found_excludes_template(self):
        """Keyword present in header text → confidence=0.0 with match_details populated."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("IBAN: IE29AIBK93115212345678")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert len(results) == 1
        assert results[0].template == template
        assert results[0].confidence == 0.0
        assert results[0].detector_name == "Exclusion"
        assert results[0].match_details["excluded"] is True
        assert "IBAN" in results[0].match_details["matched_keywords"]

    def test_keyword_not_found_allows_template(self):
        """Keyword absent from header → empty result (template allowed)."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("Credit Card Statement\nCard Number: **** **** **** 1234")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert results == []

    def test_multiple_templates_mixed_excluded_and_allowed(self):
        """Multiple templates: only excluded ones appear in results."""
        detector = ExclusionDetector()
        excluded_template = make_template(
            "cc1", "CC With IBAN Exclusion", exclude_keywords=["IBAN"]
        )
        allowed_template = make_template(
            "cc2", "CC Without Exclusion Match", exclude_keywords=["SWIFT"]
        )
        no_rules_template = make_template("cc3", "CC No Rules", exclude_keywords=[])
        page = make_page("IBAN: IE29AIBK93115212345678 Bank Statement")

        results = detector.detect(
            Path("test.pdf"),
            page,
            [excluded_template, allowed_template, no_rules_template],
        )

        assert len(results) == 1
        assert results[0].template == excluded_template

    def test_crop_raises_attribute_error_falls_back_to_full_page(self):
        """AttributeError from crop() → falls back to first_page.extract_text()."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("IBAN: IE29AIBK93115212345678", crop_raises=AttributeError)

        results = detector.detect(Path("test.pdf"), page, [template])

        assert len(results) == 1
        assert results[0].confidence == 0.0

    def test_crop_raises_value_error_falls_back_to_full_page(self):
        """ValueError from crop() → falls back to first_page.extract_text()."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("IBAN: IE29AIBK93115212345678", crop_raises=ValueError)

        results = detector.detect(Path("test.pdf"), page, [template])

        assert len(results) == 1
        assert results[0].confidence == 0.0

    def test_no_text_in_header_returns_empty(self):
        """extract_text() returns None → no exclusions possible, returns empty list."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page(None)

        results = detector.detect(Path("test.pdf"), page, [template])

        assert results == []

    def test_empty_string_text_returns_empty(self):
        """extract_text() returns empty string → no exclusions possible, returns empty list."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert results == []

    def test_case_insensitive_keyword_matching(self):
        """Keyword 'IBAN' matches lowercase 'iban' in text."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN"])
        page = make_page("iban: ie29aibk93115212345678")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert len(results) == 1
        assert results[0].confidence == 0.0

    def test_multiple_keywords_only_matched_in_details(self):
        """Multiple exclude keywords: only the matched one appears in matched_keywords."""
        detector = ExclusionDetector()
        template = make_template(exclude_keywords=["IBAN", "Sort Code"])
        page = make_page("IBAN: IE29AIBK93115212345678")

        results = detector.detect(Path("test.pdf"), page, [template])

        assert len(results) == 1
        matched = results[0].match_details["matched_keywords"]
        assert "IBAN" in matched
        assert "Sort Code" not in matched
