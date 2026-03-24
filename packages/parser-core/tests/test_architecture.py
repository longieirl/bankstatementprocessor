"""Architecture enforcement tests.

These tests enforce structural constraints on the codebase that cannot be
expressed purely through type-checking or linting.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest


def test_no_production_shim_imports():
    """Production source must not import from the pdf_table_extractor shim.

    bankstatements_core.pdf_table_extractor is a backward-compatibility shim
    for external callers only. Internal production code must import directly
    from bankstatements_core.extraction.extraction_facade or
    bankstatements_core.services instead.
    """
    src_root = Path(__file__).parent.parent / "src"
    pattern = re.compile(
        r"from\s+bankstatements_core\.pdf_table_extractor\s+import"
        r"|import\s+bankstatements_core\.pdf_table_extractor"
    )
    violations = []
    for py_file in src_root.rglob("*.py"):
        # Skip the shim itself — it may reference its own module name in docstrings
        if py_file.name == "pdf_table_extractor.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    f"{py_file.relative_to(src_root)}:{i}: {line.strip()}"
                )
    assert not violations, (
        "Production source imports from deprecated shim "
        "(bankstatements_core.pdf_table_extractor).\n"
        "Use bankstatements_core.extraction.extraction_facade or "
        "bankstatements_core.services instead.\n\n"
        "Violations:\n" + "\n".join(violations)
    )


def test_facade_modules_deleted():
    """Confirm the three thin facade pass-throughs are gone."""
    for module in [
        "bankstatements_core.extraction.content_analysis_facade",
        "bankstatements_core.extraction.validation_facade",
        "bankstatements_core.extraction.row_classification_facade",
    ]:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)


def test_extraction_result_defined_in_domain_models():
    """ExtractionResult must be defined in domain/models/, not extraction/ or services/."""
    src_root = Path(__file__).parent.parent / "src"
    wrong_dirs = [
        src_root / "bankstatements_core" / "extraction",
        src_root / "bankstatements_core" / "services",
    ]
    pattern = re.compile(r"^class ExtractionResult")
    violations = []
    for wrong_dir in wrong_dirs:
        for py_file in wrong_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    violations.append(
                        f"{py_file.relative_to(src_root)}:{i}: {line.strip()}"
                    )
    assert not violations, (
        "ExtractionResult must be defined in domain/models/, not extraction/ or services/.\n\n"
        "Violations:\n" + "\n".join(violations)
    )
