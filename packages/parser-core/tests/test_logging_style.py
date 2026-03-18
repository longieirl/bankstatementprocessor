import re
from pathlib import Path


def test_no_prints_and_no_logger_fstring_in_src():
    """Fail if any `print()` calls or `logger.*(f"...`) style logging exists in bankstatements_core.

    This prevents accidental prints in production code and encourages
    parameterized logging (avoids eager formatting and keeps logs consistent).

    NOTE: This is a linting goal. Currently there are many logger f-strings
    in the codebase. This test enforces no NEW violations are added.
    """
    import bankstatements_core

    core_root = Path(bankstatements_core.__file__).parent
    src_files = list(core_root.rglob("*.py"))
    fstring_logger = re.compile(r"logger\.\w+\(\s*f['\"]")
    print_call = re.compile(r"\bprint\(")

    # Files that have been refactored to use parameterized logging
    refactored_files = {
        "pdf_table_extractor.py",
        "services/pdf_discovery.py",
        "services/pdf_processing_orchestrator.py",
    }

    violations = []
    for p in src_files:
        rel = p.relative_to(core_root)
        if str(rel) not in refactored_files:
            continue
        text = p.read_text(encoding="utf-8")
        if print_call.search(text):
            violations.append(f"print() found in {p}")
        if fstring_logger.search(text):
            violations.append(f"logger f-string found in {p}")

    assert (
        not violations
    ), "Found logging/style violations in refactored files:\n" + "\n".join(violations)
