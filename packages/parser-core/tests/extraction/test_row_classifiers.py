"""Tests for row classifier chain."""

from __future__ import annotations

import pytest

from bankstatements_core.extraction.row_classifiers import (
    AdministrativeClassifier,
    ClassifierRegistry,
    DefaultMetadataClassifier,
    FXContinuationClassifier,
    HeaderMetadataClassifier,
    RefContinuationClassifier,
    ReferenceCodeClassifier,
    RowClassifier,
    TimestampMetadataClassifier,
    TransactionClassifier,
    create_row_classifier_chain,
)

# Test columns configuration
TEST_COLUMNS = {
    "Date": (0, 50),
    "Details": (50, 200),
    "Debit €": (200, 250),
    "Credit €": (250, 300),
    "Balance €": (300, 350),
}


class TestHeaderMetadataClassifier:
    """Tests for HeaderMetadataClassifier."""

    def test_detect_txndate_header(self):
        """Test detection of TxnDate header pattern."""
        classifier = HeaderMetadataClassifier()
        row = {"Date": "'TxnDate'(transactiondate)", "Details": "", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_detect_field_name_pattern(self):
        """Test detection of field name patterns."""
        classifier = HeaderMetadataClassifier()
        row = {"Date": "field name", "Details": "", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_detect_simple_header(self):
        """Test detection of simple column headers."""
        classifier = HeaderMetadataClassifier()
        row = {"Date": "date", "Details": "details", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_non_header_row(self):
        """Test that non-header rows are not classified."""
        classifier = HeaderMetadataClassifier()
        row = {"Date": "01/01/2023", "Details": "Purchase", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestAdministrativeClassifier:
    """Tests for AdministrativeClassifier."""

    def test_detect_lending_strict(self):
        """Test detection of strict administrative pattern."""
        classifier = AdministrativeClassifier()
        row = {
            "Date": "",
            "Details": "Lending @ 5%",
            "Balance €": "100.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "administrative"

    def test_balance_forward_without_balance(self):
        """Test BALANCE FORWARD classified as admin when no balance amount."""
        classifier = AdministrativeClassifier()
        row = {"Date": "", "Details": "BALANCE FORWARD", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "administrative"

    def test_balance_forward_with_balance(self):
        """Test BALANCE FORWARD not classified as admin when balance present."""
        classifier = AdministrativeClassifier()
        row = {
            "Date": "01/01/2023",
            "Details": "BALANCE FORWARD",
            "Balance €": "1000.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None  # Should pass to next classifier

    def test_interest_rate_without_amounts(self):
        """Test Interest Rate classified as admin when no monetary data."""
        classifier = AdministrativeClassifier()
        row = {"Date": "", "Details": "Interest Rate", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "administrative"

    def test_interest_rate_with_amounts(self):
        """Test Interest Rate not classified as admin when amounts present."""
        classifier = AdministrativeClassifier()
        row = {
            "Date": "01/01/2023",
            "Details": "Interest Rate",
            "Debit €": "5.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestReferenceCodeClassifier:
    """Tests for ReferenceCodeClassifier."""

    def test_detect_ie_reference_code(self):
        """Test detection of IE reference codes."""
        classifier = ReferenceCodeClassifier()
        row = {"Date": "", "Details": "IE123456", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "reference"

    def test_non_reference_code(self):
        """Test that non-reference codes are not classified."""
        classifier = ReferenceCodeClassifier()
        row = {"Date": "", "Details": "Regular transaction", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestFXContinuationClassifier:
    """Tests for FXContinuationClassifier."""

    def test_detect_gbp_rate_pattern(self):
        """Test detection of GBP rate pattern."""
        classifier = FXContinuationClassifier()
        row = {"Date": "", "Details": "8.99 GBP@", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_detect_exchange_rate(self):
        """Test detection of exchange rate pattern."""
        classifier = FXContinuationClassifier()
        row = {"Date": "", "Details": "0.828571", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_detect_fx_fee(self):
        """Test detection of FX fee pattern."""
        classifier = FXContinuationClassifier()
        row = {"Date": "", "Details": "INCL FX FEE E0.45", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_detect_quantity_spec(self):
        """Test detection of quantity specification."""
        classifier = FXContinuationClassifier()
        row = {"Date": "", "Details": "1@ 0.50 EACH", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_fx_pattern_with_amounts_not_continuation(self):
        """Test FX pattern with debit/credit not classified as continuation."""
        classifier = FXContinuationClassifier()
        row = {
            "Date": "",
            "Details": "8.99 GBP@",
            "Debit €": "10.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestTimestampMetadataClassifier:
    """Tests for TimestampMetadataClassifier."""

    def test_detect_timestamp_pattern(self):
        """Test detection of timestamp patterns."""
        classifier = TimestampMetadataClassifier()
        row = {"Date": "", "Details": "01JAN2023 TIME 14:30", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_non_timestamp_pattern(self):
        """Test that non-timestamp patterns are not classified."""
        classifier = TimestampMetadataClassifier()
        row = {"Date": "01/01/2023", "Details": "Purchase", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestTransactionClassifier:
    """Tests for TransactionClassifier."""

    def test_detect_transaction_with_debit(self):
        """Test detection of transaction with debit amount."""
        classifier = TransactionClassifier()
        row = {
            "Date": "01/01/2023",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_detect_transaction_with_credit(self):
        """Test detection of transaction with credit amount."""
        classifier = TransactionClassifier()
        row = {
            "Date": "01/01/2023",
            "Details": "Deposit",
            "Credit €": "100.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_detect_transaction_with_prefix(self):
        """Test detection of transaction with known prefix."""
        classifier = TransactionClassifier()
        row = {"Date": "01/01/2023", "Details": "VDC-12345", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_detect_transaction_with_date(self):
        """Test detection of transaction with meaningful date."""
        classifier = TransactionClassifier()
        row = {
            "Date": "01/01/2023",
            "Details": "Some transaction",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_detect_transaction_with_balance(self):
        """Test detection of transaction with balance."""
        classifier = TransactionClassifier()
        row = {
            "Date": "",
            "Details": "Balance",
            "Balance €": "1000.00",
            "Filename": "test",
        }
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_non_transaction(self):
        """Test that rows without transaction indicators are not classified."""
        classifier = TransactionClassifier()
        row = {"Date": "", "Details": "Random text", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestRefContinuationClassifier:
    """Tests for RefContinuationClassifier (AIB CC reference continuation lines)."""

    @pytest.fixture
    def classifier(self):
        return RefContinuationClassifier()

    @pytest.fixture
    def cc_columns(self):
        """CC-style columns (no amount col named 'Debit €')."""
        return {
            "Transaction Date": (29, 80),
            "Posting Date": (80, 118),
            "Transaction Details": (118, 370),
            "Amount": (370, 430),
        }

    def test_ref_colon_digits_classified_as_continuation(self, classifier, cc_columns):
        """Ref: <digits> with no amount is continuation."""
        row = {
            "Transaction Date": "4 Feb",
            "Posting Date": "",
            "Transaction Details": "Ref: 1234567890",
            "Amount": "",
        }
        result = classifier._do_classify(row, cc_columns)
        assert result == "continuation"

    def test_ref_no_space_classified_as_continuation(self, classifier, cc_columns):
        """Ref:<digits> (no space after colon) is also continuation."""
        row = {
            "Transaction Date": "4 Feb",
            "Transaction Details": "Ref:9876543",
            "Amount": "",
        }
        result = classifier._do_classify(row, cc_columns)
        assert result == "continuation"

    def test_ref_with_amount_still_continuation(self, classifier, cc_columns):
        """Ref: pattern always classified as continuation regardless of amount.

        The 'Amount' column on CC templates doesn't map to a typed debit/credit column,
        so we match purely on the description pattern — Ref: <digits> is always a
        reference continuation line in practice.
        """
        row = {
            "Transaction Date": "4 Feb",
            "Transaction Details": "Ref: 1234567890",
            "Amount": "50.00",
        }
        result = classifier._do_classify(row, cc_columns)
        assert result == "continuation"

    def test_regular_transaction_not_matched(self, classifier):
        """Normal transaction description not affected."""
        row = {"Date": "4 Feb", "Details": "PAYPAL *CLEVERBRIDG", "Debit €": "84.54"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None

    def test_reference_word_in_middle_not_matched(self, classifier):
        """'Ref:' in the middle of a description is not matched (anchored to start)."""
        row = {"Date": "", "Details": "Payment Ref: 123 extra", "Debit €": ""}
        # Pattern requires digits immediately after Ref: with no other text
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result is None


class TestDefaultMetadataClassifier:
    """Tests for DefaultMetadataClassifier."""

    def test_always_returns_metadata(self):
        """Test that default classifier always returns metadata."""
        classifier = DefaultMetadataClassifier()
        row = {"Date": "", "Details": "Anything", "Filename": "test"}
        result = classifier._do_classify(row, TEST_COLUMNS)
        assert result == "metadata"


class TestChainOfResponsibility:
    """Tests for the complete chain of classifiers."""

    def test_chain_classifies_header(self):
        """Test chain correctly classifies header row."""
        chain = create_row_classifier_chain()
        row = {"Date": "date", "Details": "details", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_chain_classifies_administrative(self):
        """Test chain correctly classifies administrative row."""
        chain = create_row_classifier_chain()
        row = {"Date": "", "Details": "Lending @ 5%", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "administrative"

    def test_chain_classifies_reference(self):
        """Test chain correctly classifies reference code."""
        chain = create_row_classifier_chain()
        row = {"Date": "", "Details": "IE123456", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "reference"

    def test_chain_classifies_ref_continuation(self):
        """Test chain classifies AIB CC Ref: line as continuation (not transaction)."""
        chain = create_row_classifier_chain()
        # AIB CC: date repeats on the Ref line — without this classifier,
        # TransactionClassifier would see the date and emit a phantom empty row.
        row = {"Date": "4 Feb", "Details": "Ref: 1234567890", "Debit €": "", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_chain_classifies_fx_continuation(self):
        """Test chain correctly classifies FX continuation."""
        chain = create_row_classifier_chain()
        row = {"Date": "", "Details": "0.828571", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "continuation"

    def test_chain_classifies_timestamp(self):
        """Test chain correctly classifies timestamp."""
        chain = create_row_classifier_chain()
        row = {"Date": "", "Details": "01JAN2023 TIME 14:30", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_chain_classifies_transaction(self):
        """Test chain correctly classifies transaction."""
        chain = create_row_classifier_chain()
        row = {
            "Date": "01/01/2023",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Filename": "test",
        }
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "transaction"

    def test_chain_classifies_unknown_as_metadata(self):
        """Test chain falls back to metadata for unknown rows."""
        chain = create_row_classifier_chain()
        row = {"Date": "", "Details": "Unknown content", "Filename": "test"}
        result = chain.classify(row, TEST_COLUMNS)
        assert result == "metadata"

    def test_chain_order_matters(self):
        """Test that chain order affects classification priority."""
        # Headers should be classified before transactions
        chain = create_row_classifier_chain()
        row = {
            "Date": "date",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Filename": "test",
        }
        result = chain.classify(row, TEST_COLUMNS)
        # Should be classified as header (metadata), not transaction
        assert result == "metadata"


class TestRowClassifierHelpers:
    """Tests for helper methods in RowClassifier."""

    def test_get_row_values_filters_filename(self):
        """Test that _get_row_values filters out Filename."""
        row = {"Date": "01/01/2023", "Details": "Test", "Filename": "test.pdf"}
        result = RowClassifier._get_row_values(row)
        assert "Filename" not in result
        assert "Date" in result
        assert "Details" in result

    def test_get_row_values_filters_empty(self):
        """Test that _get_row_values filters out empty values."""
        row = {"Date": "01/01/2023", "Details": "  ", "Debit €": "", "Filename": "test"}
        result = RowClassifier._get_row_values(row)
        assert "Date" in result
        assert "Details" not in result  # Whitespace only
        assert "Debit €" not in result  # Empty

    def test_get_description_text(self):
        """Test _get_description_text extracts description."""
        row = {"Date": "01/01/2023", "Details": "Purchase", "Filename": "test"}
        result = RowClassifier._get_description_text(row, TEST_COLUMNS)
        assert result == "Purchase"

    def test_get_amount_and_balance_info(self):
        """Test _get_amount_and_balance_info detects amounts and balances."""
        row = {
            "Date": "01/01/2023",
            "Details": "Purchase",
            "Debit €": "50.00",
            "Balance €": "950.00",
            "Filename": "test",
        }
        has_amount, has_balance = RowClassifier._get_amount_and_balance_info(
            row, TEST_COLUMNS
        )
        assert has_amount is True
        assert has_balance is True

    def test_looks_like_date(self):
        """Test _looks_like_date recognizes date patterns."""
        classifier = TransactionClassifier()
        assert classifier._looks_like_date("01/01/2023") is True
        assert classifier._looks_like_date("01-01-2023") is True
        assert classifier._looks_like_date("01 Jan 2023") is True
        assert classifier._looks_like_date("01 Jan") is True  # Date without year
        assert classifier._looks_like_date("15 December") is True  # Full month name
        assert classifier._looks_like_date("01JAN2023") is True
        assert classifier._looks_like_date("Not a date") is False


class TestClassifierRegistry:
    """Tests for ClassifierRegistry."""

    def test_classifier_priority_order(self):
        """get_priority_order() reflects the declared priority sequence."""
        registry = ClassifierRegistry(
            [
                (0, HeaderMetadataClassifier),
                (1, AdministrativeClassifier),
                (2, ReferenceCodeClassifier),
                (3, FXContinuationClassifier),
                (4, TimestampMetadataClassifier),
                (5, TransactionClassifier),
                (6, DefaultMetadataClassifier),
            ]
        )
        order = registry.get_priority_order()
        assert order[0] == (0, "HeaderMetadataClassifier")
        assert order[5] == (5, "TransactionClassifier")
        assert order[6] == (6, "DefaultMetadataClassifier")

    def test_duplicate_priority_raises(self):
        """Duplicate priorities raise ValueError at construction time."""
        with pytest.raises(ValueError, match="priority 0 already assigned"):
            ClassifierRegistry(
                [
                    (0, HeaderMetadataClassifier),
                    (0, TransactionClassifier),
                ]
            )

    def test_non_classifier_subclass_raises(self):
        """Passing a non-RowClassifier class raises TypeError."""
        with pytest.raises(TypeError):
            ClassifierRegistry([(0, object)])  # type: ignore[list-item]

    def test_build_chain_returns_head(self):
        """build_chain() returns a RowClassifier instance."""
        registry = ClassifierRegistry(
            [
                (0, HeaderMetadataClassifier),
                (1, DefaultMetadataClassifier),
            ]
        )
        head = registry.build_chain()
        assert isinstance(head, RowClassifier)
        assert isinstance(head, HeaderMetadataClassifier)

    def test_priorities_sorted_regardless_of_input_order(self):
        """Registry sorts by priority even if input is unordered."""
        registry = ClassifierRegistry(
            [
                (5, TransactionClassifier),
                (0, HeaderMetadataClassifier),
                (6, DefaultMetadataClassifier),
            ]
        )
        order = registry.get_priority_order()
        assert order[0] == (0, "HeaderMetadataClassifier")
        assert order[1] == (5, "TransactionClassifier")
        assert order[2] == (6, "DefaultMetadataClassifier")

    @pytest.mark.parametrize(
        "row,expected,reason",
        [
            (
                {"Date": "date", "Details": "Purchase", "Debit €": "50.00"},
                "metadata",
                "HeaderMetadata (0) beats Transaction (5) for header-like date value",
            ),
            (
                {
                    "Date": "",
                    "Details": "BALANCE FORWARD",
                    "Debit €": "",
                    "Credit €": "",
                    "Balance €": "",
                },
                "administrative",
                "Administrative (1) beats Transaction (5) for BALANCE FORWARD with no balance",
            ),
            (
                {"Date": "", "Details": "0.828571", "Debit €": "", "Credit €": ""},
                "continuation",
                "FXContinuation (3) beats Transaction (5) for exchange-rate-only rows",
            ),
        ],
    )
    def test_ambiguous_row_priority(self, row, expected, reason):
        """Ambiguous rows resolve to the highest-priority (lowest number) classifier."""
        chain = create_row_classifier_chain()
        assert chain.classify(row, TEST_COLUMNS) == expected, reason

    def test_wrong_order_produces_wrong_result(self):
        """Documents that priority order is not arbitrary — regression guard."""
        wrong_order_chain = ClassifierRegistry(
            [
                (0, TransactionClassifier),
                (1, HeaderMetadataClassifier),
                (2, AdministrativeClassifier),
                (3, ReferenceCodeClassifier),
                (4, FXContinuationClassifier),
                (5, TimestampMetadataClassifier),
                (6, DefaultMetadataClassifier),
            ]
        ).build_chain()

        ambiguous = {"Date": "date", "Details": "Purchase", "Debit €": "50.00"}
        # With Transaction first, it wins over Header
        assert wrong_order_chain.classify(ambiguous, TEST_COLUMNS) == "transaction"
        # Confirms the correct chain must put HeaderMetadata first
        correct_chain = create_row_classifier_chain()
        assert correct_chain.classify(ambiguous, TEST_COLUMNS) == "metadata"
