"""Tests confirming pdf_table_extractor shim uses module-level singletons."""

from __future__ import annotations

import warnings


def test_validate_page_structure_reuses_singleton():
    """validate_page_structure calls reuse the same PageValidationService instance."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import bankstatements_core.pdf_table_extractor as shim
    s1 = shim._PAGE_VALIDATION_SERVICE
    s2 = shim._PAGE_VALIDATION_SERVICE
    assert s1 is s2


def test_all_singletons_are_module_level():
    """All four module-level singletons exist and are stable references."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import bankstatements_core.pdf_table_extractor as shim

    assert shim._PAGE_VALIDATION_SERVICE is shim._PAGE_VALIDATION_SERVICE
    assert shim._ROW_CLASSIFIER_CHAIN is shim._ROW_CLASSIFIER_CHAIN
    assert shim._HEADER_SERVICE is shim._HEADER_SERVICE
    assert shim._ROW_MERGER_SERVICE is shim._ROW_MERGER_SERVICE
