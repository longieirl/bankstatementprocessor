"""Tests for FREE tier template filtering based on IBAN requirements."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from bankstatements_core.entitlements import Entitlements
from bankstatements_core.services.extraction_orchestrator import ExtractionOrchestrator
from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
    TemplateProcessingConfig,
)
from bankstatements_core.templates.template_registry import TemplateRegistry


@pytest.fixture
def template_with_iban():
    """Template with IBAN pattern."""
    return BankTemplate(
        id="with_iban",
        name="Bank with IBAN",
        enabled=True,
        detection=TemplateDetectionConfig(
            iban_patterns=["IE[0-9]{2}TEST[0-9A-Z]+"],
            column_headers=["Date", "Details"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        ),
        processing=TemplateProcessingConfig(
            supports_multiline=False,
            date_format="%d/%m/%Y",
            currency_symbol="€",
            decimal_separator=".",
        ),
    )


@pytest.fixture
def template_without_iban():
    """Template without IBAN pattern (e.g., default template)."""
    return BankTemplate(
        id="without_iban",
        name="Generic Bank",
        enabled=True,
        detection=TemplateDetectionConfig(
            iban_patterns=[],  # No IBAN pattern
            column_headers=["Date", "Details", "Debit", "Credit"],
        ),
        extraction=TemplateExtractionConfig(
            table_top_y=300,
            table_bottom_y=720,
            columns={"Date": (26, 78)},
        ),
        processing=TemplateProcessingConfig(
            supports_multiline=False,
            date_format="%d/%m/%Y",
            currency_symbol="€",
            decimal_separator=".",
        ),
    )


class TestFreeTierTemplateFiltering:
    """Tests for FREE tier template filtering."""

    def test_free_tier_filters_templates_without_iban(
        self, template_with_iban, template_without_iban, caplog
    ):
        """Test that FREE tier filters out templates without IBAN patterns."""
        caplog.set_level(logging.INFO)

        # Create registry with both templates
        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "without_iban": template_without_iban,
            },
            default_template_id="with_iban",
        )

        # Mock the from_default_config to return our registry
        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            # Create orchestrator with FREE tier entitlements
            ExtractionOrchestrator(entitlements=Entitlements.free_tier())

            # Verify warning was logged
            assert "FREE tier requires IBAN patterns" in caplog.text
            assert "Ignoring 1 template(s) without IBAN patterns" in caplog.text
            assert "Generic Bank" in caplog.text

            # Original registry must NOT be mutated — both templates still present
            assert len(registry.list_all()) == 2
            assert registry.list_enabled() == [
                template_with_iban,
                template_without_iban,
            ]

    def test_free_tier_logs_disabled_templates(
        self, template_with_iban, template_without_iban, caplog
    ):
        """Test that skipped templates are logged with a clear warning message."""
        caplog.set_level(logging.WARNING)

        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "without_iban": template_without_iban,
            },
            default_template_id="with_iban",
        )

        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            ExtractionOrchestrator(entitlements=Entitlements.free_tier())

            # Warning lists the skipped template name
            assert "Generic Bank" in caplog.text
            assert "Ignoring 1 template(s)" in caplog.text

    def test_paid_tier_allows_templates_without_iban(
        self, template_with_iban, template_without_iban, caplog
    ):
        """Test that PAID tier allows templates without IBAN patterns."""
        caplog.set_level(logging.INFO)

        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "without_iban": template_without_iban,
            },
            default_template_id="with_iban",
        )

        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            # Create orchestrator with PAID tier entitlements
            ExtractionOrchestrator(entitlements=Entitlements.paid_tier())

            # No warning should be logged about IBAN patterns
            assert "requires IBAN patterns" not in caplog.text

            # Original registry is unchanged — both templates still enabled
            enabled = registry.list_enabled()
            assert len(enabled) == 2
            assert any(t.id == "with_iban" for t in enabled)
            assert any(t.id == "without_iban" for t in enabled)

    def test_no_entitlements_allows_all_templates(
        self, template_with_iban, template_without_iban, caplog
    ):
        """Test that without entitlements, all templates are allowed."""
        caplog.set_level(logging.INFO)

        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "without_iban": template_without_iban,
            },
            default_template_id="with_iban",
        )

        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            # Create orchestrator without entitlements
            ExtractionOrchestrator(entitlements=None)

            # No warning should be logged
            assert "requires IBAN patterns" not in caplog.text

            # Both templates should be enabled
            enabled = registry.list_enabled()
            assert len(enabled) == 2

    def test_multiple_templates_without_iban_logged(
        self, template_with_iban, template_without_iban, caplog
    ):
        """Test that multiple templates without IBAN are all logged."""
        caplog.set_level(logging.INFO)

        # Create a second template without IBAN
        template_without_iban_2 = BankTemplate(
            id="without_iban_2",
            name="Another Generic Bank",
            enabled=True,
            detection=TemplateDetectionConfig(
                iban_patterns=[],
                column_headers=["Date", "Amount"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=250,
                table_bottom_y=700,
                columns={"Date": (20, 80)},
            ),
            processing=TemplateProcessingConfig(
                supports_multiline=False,
                date_format="%d/%m/%Y",
                currency_symbol="€",
                decimal_separator=".",
            ),
        )

        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "without_iban": template_without_iban,
                "without_iban_2": template_without_iban_2,
            },
            default_template_id="with_iban",
        )

        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            ExtractionOrchestrator(entitlements=Entitlements.free_tier())

            # Verify both templates are mentioned
            assert "Ignoring 2 template(s) without IBAN patterns" in caplog.text
            assert "Generic Bank" in caplog.text
            assert "Another Generic Bank" in caplog.text

            # Original registry is unchanged — all 3 templates still present
            assert len(registry.list_all()) == 3

    def test_free_tier_require_iban_flag(self):
        """Test that FREE tier has require_iban=True."""
        free_tier = Entitlements.free_tier()
        assert free_tier.require_iban is True
        assert free_tier.tier == "FREE"

    def test_paid_tier_require_iban_flag(self):
        """Test that PAID tier has require_iban=False."""
        paid_tier = Entitlements.paid_tier()
        assert paid_tier.require_iban is False
        assert paid_tier.tier == "PAID"

    def test_paid_tier_loads_cc_template_with_column_aliases(self, template_with_iban, caplog):
        """D-10: Paid tier with CC template (no IBAN, has column_aliases) keeps CC template in registry."""
        import logging
        caplog.set_level(logging.INFO)

        # Build a CC template: no IBAN patterns, has column_aliases, document_type=credit_card_statement
        cc_template = BankTemplate(
            id="aib_credit_card",
            name="AIB Credit Card Statement",
            enabled=True,
            detection=TemplateDetectionConfig(
                iban_patterns=[],  # No IBAN — would be filtered on free tier
                column_headers=["Date", "Transaction Details"],
            ),
            extraction=TemplateExtractionConfig(
                table_top_y=320,
                table_bottom_y=720,
                columns={"Date": (29, 78), "Transaction Details": (78, 320), "Debit €": (320, 400), "Credit €": (400, 480)},
            ),
            processing=TemplateProcessingConfig(
                supports_multiline=False,
                date_format="%d/%m/%Y",
                currency_symbol="€",
                decimal_separator=".",
            ),
            document_type="credit_card_statement",
            column_aliases={
                "Transaction Details": "Details",
                "Debit €": "Debit",
                "Credit €": "Credit",
            },
        )

        registry = TemplateRegistry(
            templates={
                "with_iban": template_with_iban,
                "aib_credit_card": cc_template,
            },
            default_template_id="with_iban",
        )

        with patch.object(
            TemplateRegistry, "from_default_config", return_value=registry
        ):
            # Paid tier: require_iban=False — IBAN filter should NOT run
            ExtractionOrchestrator(entitlements=Entitlements.paid_tier())

            # No IBAN filtering warning should appear
            assert "requires IBAN patterns" not in caplog.text

            # Original registry still has both templates (CC not stripped)
            all_templates = registry.list_all()
            template_ids = {t.id for t in all_templates}
            assert "aib_credit_card" in template_ids
            assert "with_iban" in template_ids
            assert len(all_templates) == 2

            # Verify the CC template has column_aliases intact
            cc = next(t for t in all_templates if t.id == "aib_credit_card")
            assert cc.column_aliases == {
                "Transaction Details": "Details",
                "Debit €": "Debit",
                "Credit €": "Credit",
            }
            assert cc.document_type == "credit_card_statement"
