# Plan: Remove Entitlements (PR 1 of 2)

**Spec:** `docs/superpowers/specs/2026-10-05-remove-entitlements-design.md`
**Branch:** `worktree-feat+remove-entitlements`
**Scope:** Entitlements removal + CC always-on. Package rename is PR 2 (separate branch).

## Global Constraints

- Touch only what you must. Match existing style.
- No new abstractions.
- Run `pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91` — must pass.
- Run `pytest packages/parser-free/tests/` — must pass.
- Run `black packages/parser-core/src packages/parser-core/tests`, `isort packages/parser-core/src packages/parser-core/tests`, `ruff check packages/parser-core/src packages/parser-core/tests`, `mypy packages/parser-core/src` — all must pass.
- All commits on branch `worktree-feat+remove-entitlements`.
- Commit format: `type: description` (feat/fix/chore/docs/refactor/test).
- Never push. Never create a PR.
- Source of truth: `packages/parser-core/src/bankstatements_core/` (not `src/` at repo root).

---

## Task 1: Delete entitlements.py and update all source files

Remove the entitlements system from all production source files.

### Delete
- `packages/parser-core/src/bankstatements_core/entitlements.py`

### Modify (remove entitlements params, imports, and calls)

**`processor.py`**
- Drop `entitlements` param from `__init__`, remove `self.entitlements` storage
- Remove `is_paid_tier` guard and the `group_by_card` conditional — always call `group_by_card()` when `cc_results` is non-empty
- Remove `entitlements=self.entitlements` from all downstream instantiation calls

**`services/service_registry.py`**
- Drop `entitlements` param from `from_config()` and `_ServiceContext`

**`services/extraction_orchestrator.py`**
- Drop `_entitlements` param
- Remove `require_iban` branch in `_initialize_template_system()` — always load CC-capable templates

**`services/pdf_processing_orchestrator.py`**
- Drop `entitlements` param

**`services/pdf_discovery.py`**
- Remove `check_recursive_scan()` call and `EntitlementError` import

**`services/expense_analysis.py`**
- Remove `check_expense_analysis()` call and `EntitlementError` import

**`services/monthly_summary.py`**
- Remove `entitlements` param and the `check_monthly_summary()` defense-in-depth call

**`facades/processing_facade.py`**
- Remove `Entitlements` import, `EntitlementError` import
- Remove `free_tier()` default, all four `check_*` calls and their `except EntitlementError` blocks
- Remove `entitlements` param from `__init__` and `from_environment()`

**`patterns/strategies.py`**
- Remove `TYPE_CHECKING` import of `Entitlements`
- Change `create_output_strategy(format_name, entitlements)` → `create_output_strategy(format_name)` — remove `entitlements` param, `check_output_format()` call, and tier-logging line

**`patterns/factories.py`**
- Remove `entitlements` params from all functions
- Remove `builder.with_entitlements(entitlements)` call

**`builders/processor_builder.py`**
- Delete `with_entitlements()` method and `self._entitlements` field
- Remove `entitlements=self._entitlements` from all build calls

**`extraction/pdf_extractor.py`**
- Remove `self._entitlements = opts.entitlements` storage
- Remove early-return guard `if self._entitlements is None or self._entitlements.require_iban:` — always extract card number on page 1

**`extraction/extraction_facade.py`**
- Remove `entitlements` param

**`extraction/extraction_params.py`**
- Remove `entitlements: Any | None = None` field

**`utils.py`**
- Change `discover_pdfs(input_dir, recursive, entitlements)` → `discover_pdfs(input_dir, recursive)` — remove `entitlements` param and update `PDFDiscoveryService(entitlements)` call → `PDFDiscoveryService()`

**`exceptions.py`**
- Delete `EntitlementError` class entirely (class definition + its entry in `__all__`)
- Remove `EntitlementError` from the exception hierarchy comment at the top of the file

**`commands/analyze_pdf.py`**
- Remove comments referencing the entitlement system:
  - Module-level comment "NO PAID FEATURES: Does not use ProcessorFactory or any entitlement-restricted features"
  - User-facing warning "operates outside entitlement system (no paid features)"
  - Inline comments "no TemplateRegistry to avoid entitlement checks" and "This bypasses entitlement system"

**`domain/models/extraction_result.py`**
- Update `card_number` docstring line: remove "detected on paid tier" — change to "Set to 'unknown' when CC PDF is detected but no card number pattern matches."

**`packages/parser-free/src/bankstatements_free/app.py`**
- Delete `resolve_entitlements()` function and its import of `Entitlements`
- Remove from `__all__` if present
- Remove the two lines that call `resolve_entitlements()` and pass result to `from_environment()`

### Verification
After all source changes:
```bash
mypy packages/parser-core/src
ruff check packages/parser-core/src
```
Both must pass before committing.

Commit message: `feat: remove entitlements system from all source files`

---

## Task 2: Delete entitlement test files and fix remaining tests

### Delete these files entirely
```
packages/parser-core/tests/test_entitlements.py
packages/parser-core/tests/test_entitlements_consistency.py
packages/parser-core/tests/test_output_strategy_entitlements.py
packages/parser-core/tests/test_pdf_discovery_entitlements.py
packages/parser-core/tests/services/test_monthly_summary_entitlements.py
packages/parser-core/tests/services/test_free_tier_template_filtering.py
packages/parser-core/tests/test_tier_feature_parity.py
packages/parser-free/tests/test_recursive_scan_entitlements_integration.py
```

### Fix remaining tests

In every remaining test file that passes `Entitlements.paid_tier()` or `Entitlements.free_tier()` as a constructor argument:
- Remove the entitlements import
- Drop the `entitlements=...` keyword arg from constructor calls
- Keep the test — it was testing real behavior, not the gate

In `packages/parser-core/tests/commands/test_analyze_pdf.py`:
- Delete `test_entitlement_constraint_no_entitlements_import`
- Keep `test_entitlement_constraint_no_processor_factory` but rename it to `test_analyze_pdf_uses_direct_instantiation`

In `packages/parser-core/tests/extraction/test_pdf_extractor.py`:
- Remove `mock_entitlements = MagicMock()` setup and `mock_entitlements.require_iban = ...` lines
- Remove `entitlements=mock_entitlements` from constructor calls
- Keep the test logic (the CC extraction behavior tests remain meaningful)

In `packages/parser-core/tests/facades/test_processing_facade.py`:
- Remove `Entitlements` import
- Replace `Entitlements.paid_tier()` constructor args with no entitlements arg
- Remove any tests that exist solely to assert entitlement gating raises `EntitlementError`

Apply the same pattern to any other test file with entitlement references.

### Verification
```bash
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91
pytest packages/parser-free/tests/
black packages/parser-core/src packages/parser-core/tests
isort packages/parser-core/src packages/parser-core/tests
ruff check packages/parser-core/src packages/parser-core/tests
mypy packages/parser-core/src
```
All must pass.

Commit message: `test: remove entitlement test files and update remaining tests`

---

## Task 3: CHANGELOG entry and final linting pass

Add a CHANGELOG entry for this PR. In `CHANGELOG.md`, under a new version heading (or an "Unreleased" section if one exists), add:

```
### Breaking changes
- `BankStatementProcessor.__init__()` no longer accepts `entitlements` parameter — `TypeError` on next install for any caller passing it
- `ServiceRegistry.from_config()` no longer accepts `entitlements` parameter
- `ProcessorFactory` functions no longer accept `entitlements` parameter
- `EntitlementError` removed from `exceptions` module
- `create_output_strategy()` no longer accepts `entitlements` parameter

### Changes
- Removed entitlements/tier system — all output formats, CC processing, recursive scanning, monthly summaries, and expense analysis are now unconditionally available
- Credit card PDF processing enabled in open-source repo (previously PAID tier only)
- `entitlements.py` deleted
```

Place the entry at the top of the changelog (most recent first). Match the existing formatting style of the file.

Run final full verification:
```bash
black packages/parser-core/src packages/parser-core/tests
isort packages/parser-core/src packages/parser-core/tests
ruff check packages/parser-core/src packages/parser-core/tests
mypy packages/parser-core/src
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91
pytest packages/parser-free/tests/
```

Commit message: `docs: add CHANGELOG entry for entitlements removal`
