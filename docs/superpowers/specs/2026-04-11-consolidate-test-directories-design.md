# Design: Consolidate Test Directories

**Date:** 2026-04-11
**Status:** Approved

## Problem

Two test directories exist with diverging content:

- `tests/` — 91 files, last meaningfully updated Jan–Mar 2026, imports via `src.*`, **143 failing tests**
- `packages/parser-core/tests/` — 105 files, actively maintained, imports via `bankstatements_core.*`, **1555 passing, 0 failing**

`tests/` is a stale mirror that no longer matches the production source code. The `src/` directory it imports from reflects an older API where service methods accepted raw dicts; the codebase has since migrated to `list[Transaction]`. The root `Makefile`'s `make test` target runs `tests/` — meaning the project's primary test command is currently red.

## Goal

Single canonical test location (`packages/parser-core/tests/`), zero test failures, and a structural guardrail that prevents the root `tests/` from silently reappearing.

## Approach: Big-bang migration (Option A)

One PR that:

1. Audits `tests/` for genuinely valuable tests not covered in `packages/parser-core/tests/`
2. Ports those tests (updating imports from `src.*` to `bankstatements_core.*`)
3. Deletes `tests/`, `src/`
4. Updates `Makefile` targets to run `packages/parser-core/tests/`
5. Adds a CI guardrail that fails if `tests/` or `src/` reappears

## Audit Results

### Files to delete (stale — API no longer exists)

| File | Reason |
|---|---|
| `tests/services/test_transaction_processing_orchestrator.py` | `TransactionProcessingOrchestrator` deleted in PR #46; `ServiceRegistry` (already tested) replaced it |
| `tests/test_iban_grouping.py` | Tests `BankStatementProcessor._group_rows_by_iban` which no longer exists; `packages/parser-core/tests/services/test_iban_grouping.py` is a superset |
| `tests/test_empty_row_filtering.py` | Tests `BankStatementProcessor._filter_empty_rows` which was refactored away; covered via `services/test_header_detection.py` |
| `tests/test_header_row_filtering.py` | Tests `BankStatementProcessor._is_header_row` / `_filter_header_rows` — removed from processor; covered elsewhere |

### Files to port (valuable, not covered in parser-core)

| File | What to port | Target location |
|---|---|---|
| `tests/test_output_strategies.py` | All 19 tests — concrete write behaviour of `CSVOutputStrategy`, `ExcelOutputStrategy`, `JSONOutputStrategy` (Excel column formatting, numeric types, multi-format dispatch). Not covered by parser-core's output tests which only test entitlements. | `packages/parser-core/tests/services/test_output_strategies.py` |
| `tests/test_app.py` | All tests — `main()` error path integration (`ConfigurationError`, `FileNotFoundError`, `PermissionError`, `KeyboardInterrupt`). Parser-core has `test_app_config.py` but nothing testing `main()` itself. | `packages/parser-core/tests/test_app.py` |
| `tests/test_coverage_improvements.py` | 5 tests only — `main()` error paths and `AppConfig.from_env` generic exception handling. The remaining 17 are already covered in `test_processor.py`, `test_utils.py`, `services/test_column_analysis.py` and are discarded. | Add the 5 unique tests into `packages/parser-core/tests/test_app.py` alongside the `test_app.py` port above |
| `tests/test_recursive_scan_entitlements_integration.py` | All tests — entitlement enforcement for PAID tier features via `BankStatementProcessingFacade` end-to-end. `test_tier_feature_parity.py` covers the same topic at unit level, not facade level. | `packages/parser-core/tests/test_recursive_scan_entitlements_integration.py` |

### Files with no unique value (already fully covered)

`tests/adapters/`, `tests/analysis/`, `tests/builders/`, `tests/commands/`, `tests/config/`, `tests/domain/`, `tests/extraction/`, `tests/facades/`, `tests/patterns/`, `tests/services/` (except the TPO file above), and all remaining top-level test files — each has a counterpart in `packages/parser-core/tests/` that is more up-to-date.

## Makefile Changes

| Target | Current | New |
|---|---|---|
| `test` | `pytest tests/ --cov=src` | `pytest packages/parser-core/tests/ --cov=bankstatements_core` (mirrors what `cd packages/parser-core && pytest` does) |
| `test-unit` | `pytest tests/ -m unit --cov=src` | Same path swap |
| `test-integration` | `pytest tests/ -m integration --cov=src` | `pytest packages/parser-core/tests/ -m integration --cov=bankstatements_core` |
| `test-fast` | `pytest tests/ -n auto` | Same path swap |

## CI Guardrail

Add a step to `.github/workflows/ci.yml` (or a new `test-structure.yml`) that runs:

```bash
if [ -d "tests/" ] || [ -d "src/" ]; then
  echo "ERROR: root tests/ or src/ directory must not exist. Use packages/parser-core/tests/ instead."
  exit 1
fi
```

This is a shell check — no dependencies, runs in under a second.

## Import Updates (porting rule)

All ported tests change:
- `from src.X import Y` → `from bankstatements_core.X import Y`
- `from src.patterns.repositories import reset_config_singleton` → `from bankstatements_core.patterns.repositories import reset_config_singleton`
- `from src.app import ...` → `from bankstatements_core.app import ...`

## Error Handling

- If a ported test fails due to a genuine API mismatch (not just import path), it is updated to match the current API — not skipped.
- The 91% coverage gate in `packages/parser-core/pyproject.toml` acts as a regression backstop.

## Success Criteria

- `make test` exits 0
- `packages/parser-core/tests/` has all valuable behavioural coverage from root `tests/`
- `tests/` and `src/` are deleted
- CI fails loudly if either directory reappears
- Coverage stays at or above 91%
