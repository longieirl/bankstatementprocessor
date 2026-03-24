---
phase: 19-collapse-orchestration-shim
plan: "01"
subsystem: api
tags: [python, refactor, dead-code, processor, orchestrator]

# Dependency graph
requires: []
provides:
  - "BankStatementProcessor without 10 dead private methods (_write_csv_with_totals, _append_totals_to_csv, _filter_rows, _has_row_data, _filter_empty_rows, _is_header_row, _filter_header_rows, _has_valid_transaction_date, _filter_invalid_date_rows, _group_rows_by_iban)"
  - "PDFProcessingOrchestrator with _process_single_pdf inlined into process_all_pdfs"
affects: [20-delete-facade-passthroughs, 21-unify-word-utils]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dead code purge: private methods superseded by injected services are deleted outright, not kept as wrappers"
    - "Inline passthrough: single-statement forwarding methods are inlined at call site"

key-files:
  created: []
  modified:
    - packages/parser-core/src/bankstatements_core/processor.py
    - packages/parser-core/src/bankstatements_core/services/pdf_processing_orchestrator.py
    - packages/parser-core/tests/test_repository_integration.py

key-decisions:
  - "Deleted 10 dead private methods from BankStatementProcessor; logic already owned by injected TransactionFilterService, TransactionProcessingOrchestrator, and OutputOrchestrator"
  - "Inlined PDFProcessingOrchestrator._process_single_pdf (3-line passthrough with no logic) directly at its single call site in process_all_pdfs"
  - "Deleted test_iban_grouping.py, test_empty_row_filtering.py, test_header_row_filtering.py (tested only dead methods)"
  - "Removed test_append_totals_uses_repository and appended_csv tracking from MockTransactionRepository (only used by that deleted test)"
  - "test_architecture.py failure (row_merger.py shim import) is pre-existing and out of scope for this plan"

patterns-established:
  - "Injected service owns logic: when a service is injected for a concern, the processor must NOT duplicate that logic as private methods"

requirements-completed:
  - RFC-19-dead-code
  - RFC-19-inline-passthrough

# Metrics
duration: 5min
completed: 2026-03-24
---

# Phase 19 Plan 01: Delete Dead Private Methods and Inline Passthrough Summary

**Deleted 10 dead private methods from BankStatementProcessor and inlined the 3-line PDFProcessingOrchestrator._process_single_pdf passthrough; 3 test files removed, coverage at 92.35%**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T15:31:18Z
- **Completed:** 2026-03-24T15:36:23Z
- **Tasks:** 2
- **Files modified:** 4 (1 deleted test file group + 2 src files + 1 test file)

## Accomplishments
- Removed 10 dead private methods from `processor.py`: `_write_csv_with_totals`, `_append_totals_to_csv`, `_filter_rows`, `_has_row_data`, `_filter_empty_rows`, `_is_header_row`, `_filter_header_rows`, `_has_valid_transaction_date`, `_filter_invalid_date_rows`, `_group_rows_by_iban`
- Inlined `PDFProcessingOrchestrator._process_single_pdf` at its single call site (`process_all_pdfs`), eliminating a pure-indirection wrapper
- Deleted 3 test files (`test_iban_grouping.py`, `test_empty_row_filtering.py`, `test_header_row_filtering.py`) that tested only the deleted dead methods
- Removed `test_append_totals_uses_repository` and `appended_csv` tracking from `test_repository_integration.py`
- Test suite: 1301 passed, 9 skipped, 92.35% coverage (threshold 91%)

## Task Commits

1. **Task 1: Delete 10 dead private methods from BankStatementProcessor** - `2cd7c23` (refactor)
2. **Task 2: Inline PDFProcessingOrchestrator._process_single_pdf** - `7752df7` (refactor)

## Files Created/Modified
- `packages/parser-core/src/bankstatements_core/processor.py` - Removed 10 dead private methods and unused `Callable` import
- `packages/parser-core/src/bankstatements_core/services/pdf_processing_orchestrator.py` - Inlined `_process_single_pdf`; deleted method definition
- `packages/parser-core/tests/test_repository_integration.py` - Removed `test_append_totals_uses_repository` test and `appended_csv` tracking from mock
- `packages/parser-core/tests/test_iban_grouping.py` - Deleted entirely
- `packages/parser-core/tests/test_empty_row_filtering.py` - Deleted entirely
- `packages/parser-core/tests/test_header_row_filtering.py` - Deleted entirely

## Decisions Made
- Deleted `Callable` import from `processor.py` as it was only used by the now-deleted `_filter_rows` method
- Preserved `_sort_transactions_by_date` in `processor.py` — it is NOT in the 10 dead methods list and is tested by `test_processor_refactored_methods.py`
- `transaction_filter.py` references to `_is_header_row` and similar are the canonical owners, not violations
- Pre-existing `test_architecture.py` failure (`row_merger.py` shim import) is out of scope; logged to deferred items

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `test_architecture.py::test_no_production_shim_imports` was failing before this plan's changes (4 violations pre-existing, reduced to 1 violation by earlier `feat(19-02)` commit). The remaining `row_merger.py` violation is pre-existing and out of scope. All 1301 non-architecture tests pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `processor.py` and `pdf_processing_orchestrator.py` are clean of dead code
- Ready for phase 20 (delete thin facade pass-throughs) and phase 21 (unify word utils)
- The pre-existing `row_merger.py` shim import violation should be addressed in a follow-up plan

---
*Phase: 19-collapse-orchestration-shim*
*Completed: 2026-03-24*
