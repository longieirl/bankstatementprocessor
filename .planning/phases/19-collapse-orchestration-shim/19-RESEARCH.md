# Phase 19: Collapse Redundant Orchestration Layers / Retire pdf_table_extractor Shim - Research

**Researched:** 2026-03-24
**Domain:** Python refactoring — dead code removal, shim deprecation, import cleanup
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Shim cleanup scope
- Fix **only the two files explicitly named in the RFC**: `extraction_orchestrator.py` and `pdf_extractor.py`
- The 4 additional production files that also import from the shim (`processing_facade.py`, `content_density.py`, `page_validation.py`, `row_merger.py`) are **out of scope** for this phase — left for RFC #20/#21
- Do not delete the shim — external callers may depend on it

#### CSV writing methods
- `_write_csv_with_totals` and `_append_totals_to_csv` are considered **dead code** and must be removed from `BankStatementProcessor`
- `OutputOrchestrator.write_output_files()` at line 703 already handles this; no verification step needed

#### Shim deprecation annotation
- Add a **runtime `DeprecationWarning`** at module import time in `pdf_table_extractor.py`
- External callers will receive a warning; no silent failure
- Style: `warnings.warn("...", DeprecationWarning, stacklevel=2)` at module level

#### CI guard for shim imports
- Add a **pytest test** in the existing test suite that greps `packages/*/src/` for imports from `bankstatements_core.pdf_table_extractor` and fails if any are found
- This enforces the "shim is external-use-only" contract going forward

### Claude's Discretion
- Exact placement of the pytest shim-import guard (which test file, fixture structure)
- Wording of the DeprecationWarning message
- Whether `_filter_rows` (the private helper used by the three filter methods) is moved to `TransactionFilterService` or simply deleted along with its callers

### Deferred Ideas (OUT OF SCOPE)
- Move remaining 4 production shim importers (`processing_facade.py`, `content_density.py`, `page_validation.py`, `row_merger.py`) — RFC #20
- Remove `enrich_with_document_type` defensive re-enrichment — explicitly deferred until RFC #16 (`ExtractionResult` boundary) is implemented (noted in RFC #19 as Issue D)
</user_constraints>

---

## Summary

Phase 19 is a pure refactoring phase with no behaviour change. Four distinct tasks make up the work: (1) remove nine dead private methods from `BankStatementProcessor` (the IBAN grouper, all filter helpers, and both CSV writing helpers); (2) inline `PDFProcessingOrchestrator._process_single_pdf` — a 3-line passthrough that adds no value; (3) redirect the two named production importers (`extraction_orchestrator.py`, `pdf_extractor.py`) off the backward-compat shim to the real facades; and (4) add a `DeprecationWarning` to the shim and a pytest guard that will catch any future accidental shim imports in production code.

The codebase is already well-prepared for every change. `TransactionFilterService` already has `filter_empty_rows`, `filter_header_rows`, and `filter_invalid_dates` — none of the private methods on `BankStatementProcessor` need to be moved anywhere. `OutputOrchestrator.write_output_files()` already owns CSV-with-totals logic. `extraction_facade.py` and `validation_facade.py` already export exactly the symbols that the shim currently re-exports, and `pdf_extractor.py` already uses inline local imports, so the replacement style is already established.

The shim guard pytest test is the only net-new code (aside from the `warnings.warn` call and dead-code deletions). The existing test for `extraction_orchestrator.py` patches `bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf` — that patch target string must be updated when the import moves from the shim to `extraction_facade`. Three test files (`test_pdf_table_extractor.py`, `test_env_parsing_logging.py`, `tests/templates/test_template_integration.py`) currently import from the shim and will trigger the new `DeprecationWarning`; those test-level shim imports are legitimate and must be exempted from the guard (or the guard must search only `src/`, not `tests/`).

**Primary recommendation:** Work in five atomic commits — dead-code removal, `_process_single_pdf` inline, `extraction_orchestrator.py` import switch, `pdf_extractor.py` import switch, then shim deprecation + guard — so each commit is independently green and revertable.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `warnings` stdlib | 3.11+ | Runtime deprecation notices | Built-in; no dependency needed |
| `pytest` | >=7.0.0 (project) | Test suite | Already the project's test framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-cov` | >=4.0.0 (project) | Coverage enforcement (91% threshold) | Runs with every `pytest` invocation via pyproject addopts |

No new libraries required. All changes use existing project infrastructure.

**Test run command:**
```bash
cd packages/parser-core && python -m pytest tests/ -x -q
```

---

## Architecture Patterns

### Recommended File Layout (unchanged — refactoring only)
```
packages/parser-core/src/bankstatements_core/
├── processor.py                     # Remove 9 private methods
├── pdf_table_extractor.py           # Add DeprecationWarning at top
├── services/
│   ├── extraction_orchestrator.py   # Switch shim → extraction_facade
│   └── pdf_processing_orchestrator.py  # Inline _process_single_pdf
└── extraction/
    └── pdf_extractor.py             # Switch 5 inline shim imports → validation_facade / extraction_facade
```

### Pattern 1: Dead Method Removal
**What:** Delete private methods from `BankStatementProcessor` that are already superseded by injected services.
**When to use:** When a private method is never called by `run()` or `_process_transaction_group()` through the class's own callsite (confirmed by grep).
**Verification:** After deletion, run `grep -rn "_filter_rows\|_has_row_data\|_filter_empty_rows\|_is_header_row\|_filter_header_rows\|_has_valid_transaction_date\|_filter_invalid_date_rows\|_group_rows_by_iban\|_write_csv_with_totals\|_append_totals_to_csv" packages/parser-core/src/` — must return zero hits.

Current state of `processor.py`:
- `run()` at line 609 calls `self._transaction_orchestrator.group_by_iban(...)` — the orchestrator's version, NOT the private `_group_rows_by_iban`.
- `_process_transaction_group()` at lines 691-692 calls `self._filter_service.filter_empty_rows(...)` and `self._filter_service.filter_header_rows(...)` — the service's versions.
- `_write_csv_with_totals` and `_append_totals_to_csv` have **no callers** anywhere in `src/`.
- All nine private methods are therefore safe to delete.

**Note on `_filter_rows`:** This is only called by `_filter_empty_rows`, `_filter_header_rows`, and `_filter_invalid_date_rows` on `BankStatementProcessor`. Since all three callers are being deleted, `_filter_rows` itself is deleted too. No move to `TransactionFilterService` needed.

### Pattern 2: Method Inlining
**What:** Replace a single-line method call with its body, then delete the method.
**When to use:** When a method contains nothing but a delegation to another object with no pre/post logic.

`PDFProcessingOrchestrator._process_single_pdf` (lines 185-200):
```python
# BEFORE — in process_all_pdfs:
result = self._process_single_pdf(pdf)

# _process_single_pdf body:
rows, page_count, iban = self.extraction_orchestrator.extract_from_pdf(pdf)
return rows, page_count, iban

# AFTER — inlined at the call site:
rows, page_count, iban = self.extraction_orchestrator.extract_from_pdf(pdf)
```
The `result = self._process_single_pdf(pdf)` line plus the subsequent `rows, page_count, iban = result` unpack collapse to a single direct call.

### Pattern 3: Import Target Redirect (extraction_orchestrator.py)
**What:** Replace the shim import with the direct facade import.

```python
# BEFORE (line 16):
from bankstatements_core.pdf_table_extractor import extract_tables_from_pdf

# AFTER:
from bankstatements_core.extraction.extraction_facade import extract_tables_from_pdf
```

The function signature and behaviour are identical — `extraction_facade.extract_tables_from_pdf` is exactly what the shim re-exports. The existing test patches `bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf` — this patch target remains valid after the redirect because it patches the name in the module's namespace, which is what changes.

### Pattern 4: Inline Import Redirect (pdf_extractor.py)
**What:** Replace 5 separate inline (inside-method) shim imports with direct facade imports.

Current shim imports in `pdf_extractor.py` and their direct replacements:

| Shim import | Direct import |
|-------------|---------------|
| `from bankstatements_core.pdf_table_extractor import validate_page_structure` | `from bankstatements_core.extraction.validation_facade import validate_page_structure` |
| `from bankstatements_core.pdf_table_extractor import merge_continuation_lines` | `from bankstatements_core.extraction.validation_facade import merge_continuation_lines` |
| `from bankstatements_core.pdf_table_extractor import detect_table_headers` (×2 occurrences) | `from bankstatements_core.extraction.validation_facade import detect_table_headers` |
| `from bankstatements_core.pdf_table_extractor import detect_table_end_boundary_smart` | `from bankstatements_core.extraction.extraction_facade import detect_table_end_boundary_smart` |

Decision: keep them as inline imports (matching existing style) OR hoist all five to top-level. Either is acceptable — the existing code already uses inline imports, so matching that style is lower risk. This is within Claude's Discretion.

### Pattern 5: Module-Level DeprecationWarning
**What:** Emit a warning when the shim module is imported.

```python
# Add near the top of pdf_table_extractor.py, after the existing imports:
import warnings
warnings.warn(
    "bankstatements_core.pdf_table_extractor is a backward-compatibility shim "
    "and will be removed in a future version. "
    "Import directly from bankstatements_core.extraction.extraction_facade, "
    "bankstatements_core.extraction.validation_facade, or "
    "bankstatements_core.extraction.row_classification_facade instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

`stacklevel=2` is correct for a module-level `warnings.warn` call — it causes the warning to point to the caller's import statement rather than to this file.

**Impact on existing tests:** Three test files import from the shim:
- `tests/test_pdf_table_extractor.py`
- `tests/test_env_parsing_logging.py`
- `tests/templates/test_template_integration.py`

These will now emit `DeprecationWarning` during test collection. The project's `pyproject.toml` `filterwarnings` section currently only silences one `RuntimeWarning`. Options:
1. Add `"ignore::DeprecationWarning:bankstatements_core.pdf_table_extractor"` to `filterwarnings` in `pyproject.toml` — keeps test output clean.
2. Add `pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")` in each affected test file.
3. Do nothing — the warning will appear in test output but tests will still pass.

Recommended: add to `pyproject.toml` filterwarnings so the warning is suppressed for the test files that legitimately use the shim. The shim guard (see below) will catch production code separately.

### Pattern 6: CI Shim Import Guard (pytest test)
**What:** A pytest test that scans `packages/*/src/` for import statements referencing `bankstatements_core.pdf_table_extractor` and fails if any are found. This enforces the contract that the shim is external-use-only.

```python
# Placement recommendation: tests/test_architecture.py (new file) or
# append to an existing architecture/style test such as tests/test_logging_style.py

import re
from pathlib import Path


def test_no_production_shim_imports():
    """Production source must not import from pdf_table_extractor shim."""
    src_root = Path(__file__).parent.parent / "src"
    pattern = re.compile(
        r"from\s+bankstatements_core\.pdf_table_extractor\s+import"
        r"|import\s+bankstatements_core\.pdf_table_extractor"
    )
    violations = []
    for py_file in src_root.rglob("*.py"):
        # Skip the shim itself
        if py_file.name == "pdf_table_extractor.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{py_file.relative_to(src_root)}:{i}: {line.strip()}")
    assert not violations, (
        "Production source imports from deprecated shim:\n" + "\n".join(violations)
    )
```

**Placement decision (Claude's Discretion):** Either a new `tests/test_architecture.py` file (clear intent, easy to find) or appended to the existing `tests/test_logging_style.py` (which already tests code style properties). A new `test_architecture.py` is preferred for discoverability.

### Anti-Patterns to Avoid
- **Grepping tests/ as well as src/:** The guard must exclude `tests/` — test files that exercise shim backward compatibility are legitimate.
- **Moving `_filter_rows` to `TransactionFilterService`:** It is used nowhere except the three callers being deleted. Deleting it is simpler and cleaner.
- **Hoisting inline imports in pdf_extractor.py to top-level in the same commit as the redirect:** These are two independent concerns. If hoisting is desired, do it in a separate follow-up commit so diffs are clear.
- **Deleting shim:** Out of scope — external callers must not be broken.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import-scanning guard | Custom AST parser | `Path.rglob` + `re.compile` | Simple regex on text is sufficient for import-pattern detection; no AST overhead needed |
| DeprecationWarning emission | Custom warning class | `warnings.warn(..., DeprecationWarning, stacklevel=2)` | Standard Python pattern; `stacklevel=2` correctly attributes the warning to the caller |

**Key insight:** Every capability needed for this phase already exists in the stdlib or the project's existing services. The phase is entirely deletions + redirects + a small new test.

---

## Common Pitfalls

### Pitfall 1: Stale Patch Targets in Tests
**What goes wrong:** After redirecting `extraction_orchestrator.py` to import from `extraction_facade`, the mock patch `@patch("bankstatements_core.services.extraction_orchestrator.extract_tables_from_pdf")` may appear to still work — but actually it already patches the name in the module namespace, which is correct. The patch target string does NOT need to change.
**Why it happens:** Confusion between "where the function is defined" vs "where the name lives at patch time."
**How to avoid:** Run `tests/services/test_extraction_orchestrator.py` immediately after the import switch — all 9 tests should pass without modification.
**Warning signs:** If `mock_extract.assert_called_once()` fails, the patch target is wrong.

### Pitfall 2: DeprecationWarning Breaks Test Collection
**What goes wrong:** Adding `warnings.warn(..., DeprecationWarning)` at module import time will cause pytest to emit warnings during collection for any test that imports from the shim. With `--strict-config` enabled (which is set), this does NOT cause failures unless `filterwarnings = "error"` is also set (it is not).
**Why it happens:** Module-level code runs at import time; pytest imports all test modules during collection.
**How to avoid:** Add `"ignore::DeprecationWarning:bankstatements_core"` to the `filterwarnings` list in `pyproject.toml`. Check the three affected test files after adding the warning.
**Warning signs:** Test output suddenly shows many `DeprecationWarning` lines during collection.

### Pitfall 3: Guard Test Fires on the Shim Itself
**What goes wrong:** The regex that scans `src/` for shim imports will match `pdf_table_extractor.py`'s own `__all__` docstring or comments.
**Why it happens:** The shim file itself contains the string `bankstatements_core.pdf_table_extractor` in its module docstring.
**How to avoid:** The guard must `continue` / skip the file `pdf_table_extractor.py` explicitly. Shown in the code example above.

### Pitfall 4: Coverage Drop Below 91% After Deletion
**What goes wrong:** Removing methods that had test coverage lowers the numerator; if the removed methods were well-covered (they are, in `test_processor.py` and `test_processor_refactored_methods.py`) the percentage could change. However since the tests that exercised these methods via the public `run()` path will still exercise the service equivalents, coverage should remain stable.
**Why it happens:** Coverage tool counts lines per file; fewer lines means each uncovered line matters more.
**How to avoid:** Run `python -m pytest tests/ --cov-fail-under=91` after each commit. The project currently has 91.1% coverage.
**Warning signs:** Coverage drops below 91.1%. If it does, check whether any test directly calls the deleted private methods and needs updating.

### Pitfall 5: Inline Import Style Inconsistency
**What goes wrong:** `pdf_extractor.py` currently uses inline (inside-method) imports from the shim. If replacements are made as top-level imports while other imports remain inline, the file becomes inconsistent.
**Why it happens:** Mechanical find-replace without reading the surrounding context.
**How to avoid:** Either replace all five inline imports with inline equivalents (safest, minimal diff) or hoist all of them to top-level in one consistent pass. Do not mix styles in the same commit.

---

## Code Examples

### Example 1: DeprecationWarning at module level (standard Python pattern)
```python
# Source: Python stdlib docs - warnings module
# In pdf_table_extractor.py, after existing imports:
import warnings
warnings.warn(
    "bankstatements_core.pdf_table_extractor is a backward-compatibility shim "
    "and will be removed in a future version. "
    "Import directly from bankstatements_core.extraction.extraction_facade, "
    "bankstatements_core.extraction.validation_facade, or "
    "bankstatements_core.extraction.row_classification_facade instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

### Example 2: pyproject.toml filterwarnings addition
```toml
# In [tool.pytest.ini_options] filterwarnings list:
filterwarnings = [
    "ignore:TestResult has no addDuration method:RuntimeWarning",
    "ignore::DeprecationWarning:bankstatements_core.pdf_table_extractor",
]
```

### Example 3: extraction_orchestrator.py import switch
```python
# BEFORE (line 16):
from bankstatements_core.pdf_table_extractor import extract_tables_from_pdf

# AFTER:
from bankstatements_core.extraction.extraction_facade import extract_tables_from_pdf
```

### Example 4: pdf_extractor.py inline import replacements
```python
# _extract_page method — BEFORE:
from bankstatements_core.pdf_table_extractor import validate_page_structure
from bankstatements_core.pdf_table_extractor import merge_continuation_lines

# _extract_page method — AFTER:
from bankstatements_core.extraction.validation_facade import validate_page_structure
from bankstatements_core.extraction.validation_facade import merge_continuation_lines

# _determine_boundaries_and_extract method — BEFORE:
from bankstatements_core.pdf_table_extractor import detect_table_headers
from bankstatements_core.pdf_table_extractor import detect_table_end_boundary_smart

# _determine_boundaries_and_extract method — AFTER:
from bankstatements_core.extraction.validation_facade import detect_table_headers
from bankstatements_core.extraction.extraction_facade import detect_table_end_boundary_smart
```
Note: `detect_table_headers` appears at two call sites (lines 187 and 228). Both must be updated.

### Example 5: _process_single_pdf inline
```python
# BEFORE — in process_all_pdfs (line 126):
result = self._process_single_pdf(pdf)
rows, page_count, iban = result

# AFTER — inlined:
rows, page_count, iban = self.extraction_orchestrator.extract_from_pdf(pdf)

# Then delete _process_single_pdf method entirely (lines 185-200).
```

### Example 6: Architecture guard test
```python
# tests/test_architecture.py (new file)
import re
from pathlib import Path


def test_no_production_shim_imports():
    """Production source must not import from pdf_table_extractor shim."""
    src_root = Path(__file__).parent.parent / "src"
    pattern = re.compile(
        r"from\s+bankstatements_core\.pdf_table_extractor\s+import"
        r"|import\s+bankstatements_core\.pdf_table_extractor"
    )
    violations = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "pdf_table_extractor.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                violations.append(
                    f"{py_file.relative_to(src_root)}:{i}: {line.strip()}"
                )
    assert not violations, (
        "Production source imports from deprecated shim:\n" + "\n".join(violations)
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `pdf_table_extractor.py` god module | Split into `extraction_facade.py`, `validation_facade.py`, `row_classification_facade.py`, `content_analysis_facade.py`, `extraction_params.py` | RFC #18 (PR #23, merged) | Shim now re-exports from focused modules; this phase removes the last two production callers of the shim |
| Processor owned filter logic (`_filter_empty_rows`, etc.) | `TransactionFilterService` owns filter logic | RFC series | Processor private methods are stale duplicates |
| Processor owned CSV writing | `OutputOrchestrator.write_output_files()` | Earlier RFC | `_write_csv_with_totals`/`_append_totals_to_csv` are dead code |

**Deprecated/outdated after this phase:**
- `BankStatementProcessor._filter_rows`, `_has_row_data`, `_filter_empty_rows`, `_is_header_row`, `_filter_header_rows`, `_has_valid_transaction_date`, `_filter_invalid_date_rows`, `_group_rows_by_iban`, `_write_csv_with_totals`, `_append_totals_to_csv` — removed
- `PDFProcessingOrchestrator._process_single_pdf` — inlined and removed
- `bankstatements_core.pdf_table_extractor` as a production import target — annotated deprecated; still present for external callers

---

## Open Questions

1. **Inline vs top-level imports in pdf_extractor.py**
   - What we know: All 5 shim imports in `pdf_extractor.py` are inline (inside method bodies). The project has no explicit style rule mandating inline or top-level.
   - What's unclear: Whether the team prefers to keep them inline (minimal diff) or hoist them to top-level (cleaner, more conventional).
   - Recommendation: Keep inline to minimise diff noise in this refactoring phase. Hoisting can be a separate cosmetic commit.

2. **Guard test file placement**
   - What we know: `tests/test_logging_style.py` already houses style-enforcement tests. Alternatively, `tests/test_architecture.py` is a new file.
   - What's unclear: Team preference.
   - Recommendation: New `tests/test_architecture.py` — architecture guards are distinct from logging-style guards and deserve a clearly-named home.

3. **TransactionFilterService — `filter_invalid_date_rows` alias**
   - What we know: The RFC mentioned adding `filter_invalid_date_rows` and `has_valid_transaction_date` to `TransactionFilterService`. These names do NOT exist on the service (it has `filter_invalid_dates`, which does the same job).
   - What's unclear: Whether new aliases are needed for the RFC to be complete.
   - Recommendation: No aliases needed. The private methods on `BankStatementProcessor` being deleted are not replaced by anything — they are dead code. `TransactionFilterService.filter_invalid_dates` already exists and already covers this behaviour. The RFC wording about "verify/add" means the verification step is done and the answer is "already exists under a slightly different name."

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection — `processor.py`, `pdf_table_extractor.py`, `extraction_orchestrator.py`, `pdf_extractor.py`, `transaction_filter.py`, `extraction_facade.py`, `validation_facade.py`, `pdf_processing_orchestrator.py`
- `pyproject.toml` — pytest configuration, coverage thresholds, filterwarnings
- `tests/services/test_extraction_orchestrator.py` — existing patch targets
- Test directory scan — confirmed no existing test for shim import guard; confirmed three test files importing from shim

### Secondary (MEDIUM confidence)
- Python stdlib `warnings` module documentation — `stacklevel=2` semantics for module-level `warnings.warn`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Dead code identification: HIGH — confirmed by grep that `_write_csv_with_totals`, `_append_totals_to_csv` have no callers in `src/`; confirmed `_group_rows_by_iban` is never called (only the orchestrator's `group_by_iban` is called); confirmed filter methods are never called on `self` in `run()` or `_process_transaction_group()`
- Import redirect targets: HIGH — `extraction_facade.py` and `validation_facade.py` export exactly the symbols named; no signature changes
- Shim deprecation pattern: HIGH — standard Python stdlib pattern
- Coverage impact: MEDIUM — current coverage is 91.1%, threshold is 91%; deletion of covered methods reduces line count but tests that drove coverage through public API remain; risk is low but should be verified on first run
- Guard test: HIGH — pattern confirmed against actual file contents

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable refactoring domain, no external dependencies involved)
