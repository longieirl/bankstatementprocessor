---
phase: 19-collapse-orchestration-shim
plan: "02"
subsystem: extraction
tags: [pdf-extraction, shim, deprecation, architecture-guard, pytest]

# Dependency graph
requires: []
provides:
  - "extraction_orchestrator.py imports extract_tables_from_pdf directly from extraction_facade"
  - "pdf_extractor.py has 0 shim imports; 5 inline imports from validation_facade/extraction_facade"
  - "processing_facade.py, content_density.py, page_validation.py, row_merger.py redirected off shim"
  - "pdf_table_extractor.py emits DeprecationWarning at module import time"
  - "tests/test_architecture.py CI guard enforcing no production shim imports"
affects: [20-delete-thin-facades, 21-word-utils]

# Tech tracking
tech-stack:
  added: []
  patterns: [architecture-guard-test, deprecation-warning-on-shim-import]

key-files:
  created:
    - packages/parser-core/tests/test_architecture.py
  modified:
    - packages/parser-core/src/bankstatements_core/services/extraction_orchestrator.py
    - packages/parser-core/src/bankstatements_core/extraction/pdf_extractor.py
    - packages/parser-core/src/bankstatements_core/pdf_table_extractor.py
    - packages/parser-core/src/bankstatements_core/facades/processing_facade.py
    - packages/parser-core/src/bankstatements_core/services/content_density.py
    - packages/parser-core/src/bankstatements_core/services/page_validation.py
    - packages/parser-core/src/bankstatements_core/services/row_merger.py
    - packages/parser-core/pyproject.toml

key-decisions:
  - "Redirect all 9 production shim imports (7 files) to real facades in same commit batch"
  - "Architecture guard scans src/ only (not tests/) and skips the shim file itself"
  - "DeprecationWarning uses stacklevel=2 so the warning points to the caller, not the shim"
  - "pyproject.toml filterwarnings suppresses the DeprecationWarning for the 3 legitimate test shim importers"

patterns-established:
  - "Architecture enforcement: use test_architecture.py to lock structural contracts via failing tests"
  - "Shim deprecation: warnings.warn with DeprecationWarning+stacklevel=2 at module level"

requirements-completed: [RFC-19-shim-redirect, RFC-19-deprecation-warning, RFC-19-ci-guard]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 19 Plan 02: Collapse Orchestration Shim Summary

**Shim retired from all 9 production call sites across 7 files, DeprecationWarning added, and architecture guard CI test locks the contract**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T14:31:28Z
- **Completed:** 2026-03-24T14:34:57Z
- **Tasks:** 2
- **Files modified:** 9 (7 src + 1 test + 1 config)

## Accomplishments
- Redirected extraction_orchestrator.py and pdf_extractor.py (5 inline imports) off the shim to real facades
- Discovered and auto-fixed 4 additional shim imports in processing_facade, content_density, page_validation, row_merger
- Annotated pdf_table_extractor.py with DeprecationWarning at module import (stacklevel=2, points at caller)
- Created tests/test_architecture.py with test_no_production_shim_imports that CI-guards against regressions
- Full test suite: 1302 passed, 9 skipped, 92.36% coverage (threshold 91%)

## Task Commits

Each task was committed atomically:

1. **Task 1: Redirect production shim imports and annotate shim** - `2fe63ca` (feat)
2. **Task 2: Add architecture guard and redirect remaining shim imports** - `8fb31ca` (feat)

## Files Created/Modified
- `packages/parser-core/tests/test_architecture.py` - New CI guard: scans src/ for shim imports, fails with violation list
- `packages/parser-core/src/bankstatements_core/services/extraction_orchestrator.py` - Line 16: import from extraction_facade
- `packages/parser-core/src/bankstatements_core/extraction/pdf_extractor.py` - 5 inline shim imports redirected to validation_facade/extraction_facade
- `packages/parser-core/src/bankstatements_core/pdf_table_extractor.py` - warnings.warn DeprecationWarning at module level
- `packages/parser-core/src/bankstatements_core/facades/processing_facade.py` - get_columns_config from config.column_config
- `packages/parser-core/src/bankstatements_core/services/content_density.py` - classify_row_type from row_classification_facade
- `packages/parser-core/src/bankstatements_core/services/page_validation.py` - classify_row_type from row_classification_facade
- `packages/parser-core/src/bankstatements_core/services/row_merger.py` - classify_row_type from row_classification_facade
- `packages/parser-core/pyproject.toml` - filterwarnings entry to suppress DeprecationWarning from shim for legitimate test imports

## Decisions Made
- Redirect all 9 production shim imports (7 files) to real facades — the guard test discovered 4 files the plan hadn't listed
- Architecture guard scans only `src/`, skips `pdf_table_extractor.py` itself, uses regex matching both `from ... import` and bare `import` forms
- DeprecationWarning uses `stacklevel=2` so pytest output points at the importing file, not the shim
- pyproject.toml filterwarnings set per-module (`bankstatements_core.pdf_table_extractor`) to suppress only the expected shim warning in tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Redirected 4 additional shim imports not listed in plan**
- **Found during:** Task 2 (architecture guard test execution)
- **Issue:** test_no_production_shim_imports caught 4 more production shim imports not mentioned in 19-02-PLAN.md: `processing_facade.py` (get_columns_config), `content_density.py` (classify_row_type), `page_validation.py` (classify_row_type), `row_merger.py` (classify_row_type)
- **Fix:** Redirected each to its real facade: column_config, row_classification_facade
- **Files modified:** facades/processing_facade.py, services/content_density.py, services/page_validation.py, services/row_merger.py
- **Verification:** Architecture guard passes (0 violations); full test suite 1302 passed, 92.36% coverage
- **Committed in:** 8fb31ca (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical redirects)
**Impact on plan:** Required for architecture guard to pass. No scope creep — all fixes are in-scope shim redirects matching the plan's stated goal.

## Issues Encountered
- Stale Python bytecode (.pyc) cached the old imports and caused the architecture test to fail even after edits. Cleared cache with `find ... -name "*.pyc" -delete`. Re-run passed immediately.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All production code now imports from real facades; shim is external-use-only
- Architecture guard in CI ensures no regression to shim imports
- RFC #19 production-import requirement fulfilled; ready for RFC #20 (delete thin facade pass-throughs)

---
*Phase: 19-collapse-orchestration-shim*
*Completed: 2026-03-24*

## Self-Check: PASSED

- FOUND: packages/parser-core/tests/test_architecture.py
- FOUND: packages/parser-core/src/bankstatements_core/services/extraction_orchestrator.py (redirected)
- FOUND: packages/parser-core/src/bankstatements_core/pdf_table_extractor.py (annotated)
- FOUND: .planning/phases/19-collapse-orchestration-shim/19-02-SUMMARY.md
- FOUND commit 2fe63ca: feat(19-02): redirect production shim imports to real facades
- FOUND commit 8fb31ca: feat(19-02): add architecture guard and redirect remaining shim imports
