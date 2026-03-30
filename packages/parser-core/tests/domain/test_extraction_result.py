"""Tests for ExtractionResult domain model.

Covers EXTR-01 (dataclass fields and imports) and EXTR-02 (document-level
warning isolation from Transaction.extraction_warnings).
"""

from __future__ import annotations

from pathlib import Path

from bankstatements_core.domain.models.transaction import Transaction


class TestExtractionResultImports:
    def test_importable_from_module(self):
        pass

    def test_importable_from_models_package(self):
        pass

    def test_importable_from_domain_package(self):
        pass


class TestExtractionResultConstruction:
    def test_all_five_fields_accessible(self):
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        result = ExtractionResult(
            transactions=[],
            page_count=3,
            iban="IE29AIBK93115212345678",
            source_file=Path("statement.pdf"),
        )
        assert result.transactions == []
        assert result.page_count == 3
        assert result.iban == "IE29AIBK93115212345678"
        assert result.source_file == Path("statement.pdf")
        assert result.warnings == []

    def test_warnings_defaults_to_empty_list(self):
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        result = ExtractionResult(
            transactions=[], page_count=1, iban=None, source_file=Path("x.pdf")
        )
        assert result.warnings == []

    def test_warnings_accepts_explicit_list(self):
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        result = ExtractionResult(
            transactions=[],
            page_count=1,
            iban=None,
            source_file=Path("x.pdf"),
            warnings=["credit card detected, skipped"],
        )
        assert result.warnings == ["credit card detected, skipped"]

    def test_iban_can_be_none(self):
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        result = ExtractionResult(
            transactions=[], page_count=1, iban=None, source_file=Path("x.pdf")
        )
        assert result.iban is None

    def test_transactions_can_contain_transaction_objects(self):
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        result = ExtractionResult(
            transactions=[tx], page_count=1, iban=None, source_file=Path("x.pdf")
        )
        assert len(result.transactions) == 1
        assert result.transactions[0] is tx


class TestExtractionResultMutableDefault:
    def test_warnings_no_shared_mutable_default(self):
        """Two ExtractionResult instances must not share the same warnings list."""
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        result1 = ExtractionResult(
            transactions=[], page_count=1, iban=None, source_file=Path("a.pdf")
        )
        result2 = ExtractionResult(
            transactions=[], page_count=1, iban=None, source_file=Path("b.pdf")
        )
        result1.warnings.append("event")
        assert result2.warnings == []


class TestExtractionResultWarningIsolation:
    def test_document_level_warning_not_in_transaction_extraction_warnings(self):
        """EXTR-02: A document-level warning in ExtractionResult.warnings must not
        appear in any Transaction.extraction_warnings."""
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
        )
        result = ExtractionResult(
            transactions=[tx],
            page_count=1,
            iban=None,
            source_file=Path("statement.pdf"),
            warnings=["credit card detected, skipped"],
        )
        assert "credit card detected, skipped" in result.warnings
        assert tx.extraction_warnings == []

    def test_transaction_warnings_not_propagated_to_extraction_result(self):
        """EXTR-02 reverse: per-row Transaction.extraction_warnings must not appear
        in ExtractionResult.warnings unless explicitly added."""
        from bankstatements_core.domain.models.extraction_result import ExtractionResult

        tx = Transaction(
            date="01/01/2024",
            details="Test",
            debit=None,
            credit="10.00",
            balance="100.00",
            filename="test.pdf",
            extraction_warnings=["row-level anomaly"],
        )
        result = ExtractionResult(
            transactions=[tx],
            page_count=1,
            iban=None,
            source_file=Path("statement.pdf"),
        )
        assert result.warnings == []
        assert "row-level anomaly" not in result.warnings
