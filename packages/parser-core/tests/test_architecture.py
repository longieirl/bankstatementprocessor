"""Architecture enforcement tests.

These tests enforce structural constraints on the codebase that cannot be
expressed purely through type-checking or linting.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_no_production_shim_imports():
    """Production source must not import from the pdf_table_extractor shim.

    bankstatements_core.pdf_table_extractor is a backward-compatibility shim
    for external callers only. Internal production code must import directly
    from the real facades:
      - bankstatements_core.extraction.extraction_facade
      - bankstatements_core.extraction.validation_facade
      - bankstatements_core.extraction.row_classification_facade
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
        "Use bankstatements_core.extraction.extraction_facade, "
        "validation_facade, or row_classification_facade instead.\n\n"
        "Violations:\n" + "\n".join(violations)
    )
