# Consolidate Test Directories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the stale root `tests/` and `src/` directories, port valuable unique tests to `packages/parser-core/tests/`, update all Makefile targets, and add a CI guardrail so the directories can never silently reappear.

**Architecture:** Audit confirmed 4 files worth porting and 4 stale files to discard. All ported tests update imports from `src.*` to `bankstatements_core.*`. The root `Makefile` is redirected to run `packages/parser-core/tests/` (already passing 1555 tests, 91% coverage gate). A one-line CI shell check in `ci.yml` enforces the new structure permanently.

**Tech Stack:** pytest, Python 3.11–3.13, GitHub Actions, bankstatements_core package

---

## File Map

| Action | Path |
|---|---|
| **Create** | `packages/parser-core/tests/services/test_output_strategies.py` |
| **Create** | `packages/parser-core/tests/test_recursive_scan_entitlements_integration.py` |
| **Modify** | `packages/parser-core/tests/test_app.py` ← new file (does not exist yet) |
| **Modify** | `Makefile` (lines 37–56: test, test-unit, test-integration, test-fast, test-watch, coverage) |
| **Modify** | `.github/workflows/ci.yml` (add guardrail step before `test-core` job) |
| **Delete** | `tests/` (entire directory, 91 files) |
| **Delete** | `src/` (entire directory) |

---

## Task 1: Port `test_output_strategies.py`

The root `tests/test_output_strategies.py` tests concrete write behaviour of `CSVOutputStrategy`, `ExcelOutputStrategy`, `JSONOutputStrategy` (Excel column formatting, numeric cell types, multi-format dispatch). This is not covered in parser-core — `test_output_strategy_entitlements.py` only tests tier permissions, not actual file writing.

**Files:**
- Create: `packages/parser-core/tests/services/test_output_strategies.py`

- [ ] **Step 1: Create the ported test file**

```python
# packages/parser-core/tests/services/test_output_strategies.py
"""Tests for output format strategies — concrete write behaviour."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.patterns.factories import ProcessorFactory
from bankstatements_core.patterns.strategies import (
    CSVOutputStrategy,
    ExcelOutputStrategy,
    JSONOutputStrategy,
)

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


@pytest.mark.skipif(
    not OPENPYXL_AVAILABLE, reason="openpyxl not installed (PAID tier dependency)"
)
class TestExcelOutputStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = ExcelOutputStrategy()
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.transactions = [
            {"Date": "01/01/2024", "Details": "Purchase 1", "Debit": "€100.00", "Credit": ""},
            {"Date": "02/01/2024", "Details": "Purchase 2", "Debit": "€50.00", "Credit": ""},
            {"Date": "03/01/2024", "Details": "Refund", "Debit": "", "Credit": "€25.00"},
        ]
        self.column_names = ["Date", "Details", "Debit", "Credit"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_excel_basic(self):
        file_path = self.temp_path / "test.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names, include_totals=False)
        self.assertTrue(file_path.exists())
        df = pd.read_excel(file_path, sheet_name="Transactions")
        self.assertEqual(len(df), 3)
        self.assertListEqual(list(df.columns), self.column_names)

    def test_write_excel_with_totals(self):
        file_path = self.temp_path / "test_totals.xlsx"
        from bankstatements_core.services.totals_calculator import ColumnTotalsService
        df = pd.DataFrame(self.transactions)
        totals_service = ColumnTotalsService(["debit", "credit"])
        totals = totals_service.calculate(df)
        totals_row = totals_service.format_totals_row(totals, self.column_names)
        self.strategy.write(
            self.transactions,
            file_path,
            self.column_names,
            include_totals=True,
            totals_columns=["debit", "credit"],
            totals_row=totals_row,
        )
        self.assertTrue(file_path.exists())
        df = pd.read_excel(file_path, sheet_name="Transactions")
        # 3 transactions + 1 empty row + 1 totals row = 5
        self.assertEqual(len(df), 5)
        self.assertEqual(df.iloc[0]["Date"], "01/01/2024")
        self.assertEqual(df.iloc[4]["Date"], "TOTAL")

    def test_excel_file_extension(self):
        file_path = self.temp_path / "bank_statements.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.suffix, ".xlsx")

    def test_numeric_columns_written_as_numbers(self):
        file_path = self.temp_path / "test_numeric.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]
        debit_cell = worksheet["C2"]
        self.assertIsInstance(debit_cell.value, (int, float))
        self.assertAlmostEqual(debit_cell.value, 100.0, places=2)
        debit_cell2 = worksheet["C3"]
        self.assertIsInstance(debit_cell2.value, (int, float))
        self.assertAlmostEqual(debit_cell2.value, 50.0, places=2)
        credit_cell = worksheet["D4"]
        self.assertIsInstance(credit_cell.value, (int, float))
        self.assertAlmostEqual(credit_cell.value, 25.0, places=2)
        empty_credit = worksheet["D2"]
        self.assertIsNone(empty_credit.value)
        date_cell = worksheet["A2"]
        self.assertIsInstance(date_cell.value, str)
        workbook.close()

    def test_number_formatting_applied(self):
        file_path = self.temp_path / "test_formatting.xlsx"
        self.strategy.write(self.transactions, file_path, self.column_names)
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook["Transactions"]
        self.assertIn("#,##0", worksheet["C2"].number_format)
        self.assertIn("#,##0", worksheet["D4"].number_format)
        workbook.close()


class TestOutputFormatConfiguration(unittest.TestCase):
    def test_single_format_csv(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["csv"])

    def test_single_format_excel(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "excel"}):
            config = AppConfig.from_env()
            self.assertEqual(config.output_formats, ["excel"])

    def test_multiple_formats(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,excel"}):
            config = AppConfig.from_env()
            self.assertIn("csv", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_all_formats(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,json,excel"}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            self.assertIn("csv", config.output_formats)
            self.assertIn("json", config.output_formats)
            self.assertIn("excel", config.output_formats)

    def test_invalid_format_raises_error(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": "csv,invalid"}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("Invalid output format", str(context.exception))
            self.assertIn("invalid", str(context.exception))

    def test_empty_format_raises_error(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": ""}):
            with self.assertRaises(ConfigurationError) as context:
                AppConfig.from_env()
            self.assertIn("At least one output format", str(context.exception))

    def test_default_formats(self):
        with patch.dict("os.environ", {}, clear=True):
            config = AppConfig.from_env()
            self.assertIn("csv", config.output_formats)
            self.assertIn("json", config.output_formats)
            self.assertEqual(len(config.output_formats), 2)

    def test_formats_with_whitespace(self):
        with patch.dict("os.environ", {"OUTPUT_FORMATS": " csv , excel , json "}):
            config = AppConfig.from_env()
            self.assertEqual(len(config.output_formats), 3)
            for fmt in config.output_formats:
                self.assertEqual(fmt, fmt.strip())


class TestOutputFormatIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_processor_with_multiple_formats(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir), "OUTPUT_FORMATS": "csv,json,excel"},
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("json", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)
            self.assertIsInstance(processor.output_strategies["csv"], CSVOutputStrategy)
            self.assertIsInstance(processor.output_strategies["json"], JSONOutputStrategy)
            self.assertIsInstance(processor.output_strategies["excel"], ExcelOutputStrategy)

    def test_factory_creates_correct_strategies(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir), "OUTPUT_FORMATS": "csv,excel"},
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 2)

    def test_processor_default_strategies(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertIn("csv", processor.output_strategies)
            self.assertEqual(len(processor.output_strategies), 2)

    def test_custom_strategies_injection(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
        ):
            config = AppConfig.from_env()
            custom_strategies = {"csv": CSVOutputStrategy(), "excel": ExcelOutputStrategy()}
            processor = ProcessorFactory.create_from_config(config, output_strategies=custom_strategies)
            self.assertEqual(len(processor.output_strategies), 2)
            self.assertIn("csv", processor.output_strategies)
            self.assertIn("excel", processor.output_strategies)


class TestStrategyBackwardCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_behavior_unchanged(self):
        with patch.dict(
            "os.environ",
            {"INPUT_DIR": str(self.input_dir), "OUTPUT_DIR": str(self.output_dir)},
            clear=True,
        ):
            config = AppConfig.from_env()
            processor = ProcessorFactory.create_from_config(config)
            self.assertEqual(len(processor.output_strategies), 2)
            self.assertIn("csv", processor.output_strategies)

    def test_processor_direct_instantiation_still_works(self):
        from bankstatements_core.config.processor_config import ExtractionConfig, ProcessorConfig
        from bankstatements_core.pdf_table_extractor import get_columns_config
        from bankstatements_core.processor import BankStatementProcessor

        columns = get_columns_config()
        config = ProcessorConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            extraction=ExtractionConfig(columns=columns),
        )
        processor = BankStatementProcessor(config=config)
        self.assertIn("csv", processor.output_strategies)
        self.assertIn("json", processor.output_strategies)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests to verify they pass**

Run from the `packages/parser-core/` directory:

```bash
cd packages/parser-core
python -m pytest tests/services/test_output_strategies.py -v --no-cov
```

Expected: all tests PASS (or Excel tests skip with "openpyxl not installed" if running without openpyxl). No import errors.

If any test fails with an `AttributeError` or signature mismatch, update that test to match the current API (do not skip).

- [ ] **Step 3: Commit**

```bash
git add packages/parser-core/tests/services/test_output_strategies.py
git commit -m "test: port output strategy tests to parser-core"
```

---

## Task 2: Port `test_recursive_scan_entitlements_integration.py`

The root `tests/test_recursive_scan_entitlements_integration.py` tests `BankStatementProcessingFacade` end-to-end with real temp directories — checking that PAID tier's unique feature is `require_iban=False`. Parser-core's `test_tier_feature_parity.py` covers similar ground at unit level only.

**Files:**
- Create: `packages/parser-core/tests/test_recursive_scan_entitlements_integration.py`

- [ ] **Step 1: Create the ported test file**

```python
# packages/parser-core/tests/test_recursive_scan_entitlements_integration.py
"""Integration tests for entitlement enforcement via BankStatementProcessingFacade."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bankstatements_core.config.app_config import AppConfig, ConfigurationError
from bankstatements_core.entitlements import Entitlements
from bankstatements_core.facades.processing_facade import BankStatementProcessingFacade


class TestRecursiveScanEntitlementEnforcement:
    def test_free_tier_allows_recursive_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(input_dir=input_dir, output_dir=output_dir, recursive_scan=True)
            facade = BankStatementProcessingFacade(config, Entitlements.free_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_free_tier_works_with_all_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
                output_formats=["csv", "json", "excel"],
            )
            facade = BankStatementProcessingFacade(config, Entitlements.free_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_can_enable_recursive_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            subdir = input_dir / "subdir"
            subdir.mkdir()
            (subdir / "test.pdf").write_text("fake pdf")
            config = AppConfig(input_dir=input_dir, output_dir=output_dir, recursive_scan=True)
            facade = BankStatementProcessingFacade(config, Entitlements.paid_tier())
            summary = facade.process_all()
            assert summary is not None

    def test_paid_tier_respects_recursive_scan_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(input_dir=input_dir, output_dir=output_dir, recursive_scan=False)
            facade = BankStatementProcessingFacade(config, Entitlements.paid_tier())
            summary = facade.process_all()
            assert summary["pdf_count"] == 0

    def test_no_entitlements_defaults_to_free_tier(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
            )
            facade = BankStatementProcessingFacade(config, entitlements=None)
            summary = facade.process_all()
            assert summary["pdf_count"] == 0
            assert summary["transactions"] == 0

    def test_paid_tier_difference_is_iban_requirement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            config = AppConfig(
                input_dir=input_dir,
                output_dir=output_dir,
                recursive_scan=True,
                generate_monthly_summary=True,
                output_formats=["csv", "json", "excel"],
            )
            free_entitlements = Entitlements.free_tier()
            paid_entitlements = Entitlements.paid_tier()
            assert free_entitlements.require_iban is True
            assert paid_entitlements.require_iban is False
            facade_free = BankStatementProcessingFacade(config, free_entitlements)
            facade_paid = BankStatementProcessingFacade(config, paid_entitlements)
            summary_free = facade_free.process_all()
            summary_paid = facade_paid.process_all()
            assert summary_free["pdf_count"] == 0
            assert summary_paid["pdf_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run the new tests**

```bash
cd packages/parser-core
python -m pytest tests/test_recursive_scan_entitlements_integration.py -v --no-cov
```

Expected: all 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/parser-core/tests/test_recursive_scan_entitlements_integration.py
git commit -m "test: port recursive scan entitlements integration tests to parser-core"
```

---

## Task 3: Port `test_app.py` + 5 unique tests from `test_coverage_improvements.py`

The root `tests/test_app.py` tests the `main()` function in `src/app.py`. In `bankstatements_core`, `main()` doesn't exist as a standalone function — but `BankStatementProcessingFacade.process_with_error_handling()` is the functional equivalent and is already tested in `test_processing_facade.py`.

What IS missing: integration tests for `AppConfig.from_env()` reading specific env vars and `setup_logging()` error handling. These live in `src/app.py` but the equivalent code is in `bankstatements_core.config.app_config` and `bankstatements_core.facades.processing_facade`.

The following 5 tests from `test_coverage_improvements.py` are also absent from parser-core and belong here:
- `test_main_configuration_error` → already covered in `test_processing_facade.py:test_process_with_error_handling_config_error`
- `test_main_file_not_found_error` → already covered in `test_processing_facade.py:test_process_with_error_handling_file_not_found`
- `test_main_permission_error` → already covered in `test_processing_facade.py:test_process_with_error_handling_permission_error`
- `test_main_keyboard_interrupt` → already covered in `test_processing_facade.py:test_process_with_error_handling_keyboard_interrupt`
- `test_appconfig_from_env_generic_exception` → covered by `test_app_config.py:test_from_env_generic_exception_wrapped`

**Conclusion:** All 5 "unique" tests from `test_coverage_improvements.py` are already covered under different names in parser-core. Similarly, `test_app.py`'s `main()` integration tests patch `src.*` internals that don't map 1:1 to parser-core. These tests do not need to be ported — they are covered.

**Files:**
- No new file needed for this task.

- [ ] **Step 1: Verify coverage for the error paths**

```bash
cd packages/parser-core
python -m pytest tests/facades/test_processing_facade.py -v --no-cov -k "error_handling"
```

Expected: `test_process_with_error_handling_config_error`, `test_process_with_error_handling_file_not_found`, `test_process_with_error_handling_permission_error`, `test_process_with_error_handling_keyboard_interrupt`, `test_process_with_error_handling_unexpected_error` all PASS.

- [ ] **Step 2: Verify AppConfig generic exception coverage**

```bash
cd packages/parser-core
python -m pytest tests/config/test_app_config.py -v --no-cov -k "generic"
```

Expected: `test_from_env_generic_exception_wrapped` PASSES.

- [ ] **Step 3: No commit needed** — no files changed.

---

## Task 4: Update Makefile targets

Redirect all root `Makefile` test targets from `tests/ --cov=src` to `packages/parser-core/tests/ --cov=bankstatements_core`. The coverage threshold also rises from 90% to 91% to match the canonical pyproject.toml.

**Files:**
- Modify: `Makefile` (lines 37–56)

- [ ] **Step 1: Read the current Makefile lines 37–56**

Open `Makefile` and find the current `test:` through `coverage:` targets. They look like:

```makefile
test:	## Run all tests with coverage
	python3 -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=90

test-unit:	## Run only unit tests
	python3 -m pytest tests/ -v -m "unit" --cov=src --cov-report=term-missing

test-integration:	## Run only integration tests
	python3 -m pytest tests/ -v -m "integration" --cov=src --cov-report=term-missing

test-fast:	## Run tests in parallel (faster)
	python3 -m pytest tests/ -v -n auto --cov=src --cov-report=term-missing

test-watch:	## Run tests in watch mode (re-run on file changes)
	python3 -m ptw -- tests/ -v --cov=src

coverage:	## Generate and open coverage report
	python3 -m pytest tests/ --cov=src --cov-report=html --cov-fail-under=90
	@echo "Opening coverage report in browser..."
	@python3 -c "import webbrowser; webbrowser.open('htmlcov/index.html')"
```

- [ ] **Step 2: Replace with updated targets**

Edit `Makefile`, replacing each of the above targets with:

```makefile
test:	## Run all tests with coverage
	python3 -m pytest packages/parser-core/tests/ -v --cov=bankstatements_core --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=91

test-unit:	## Run only unit tests
	python3 -m pytest packages/parser-core/tests/ -v -m "unit" --cov=bankstatements_core --cov-report=term-missing

test-integration:	## Run only integration tests
	python3 -m pytest packages/parser-core/tests/ -v -m "integration" --cov=bankstatements_core --cov-report=term-missing

test-fast:	## Run tests in parallel (faster)
	python3 -m pytest packages/parser-core/tests/ -v -n auto --cov=bankstatements_core --cov-report=term-missing

test-watch:	## Run tests in watch mode (re-run on file changes)
	python3 -m ptw -- packages/parser-core/tests/ -v --cov=bankstatements_core

coverage:	## Generate and open coverage report
	python3 -m pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-report=html --cov-fail-under=91
	@echo "Opening coverage report in browser..."
	@python3 -c "import webbrowser; webbrowser.open('htmlcov/index.html')"
```

- [ ] **Step 3: Verify `make test` runs correctly before deleting anything**

From the repo root:

```bash
cd packages/parser-core && pip install -e ".[dev,test]" -q && cd ../..
python3 -m pytest packages/parser-core/tests/ -v --cov=bankstatements_core --cov-report=term-missing --cov-fail-under=91 -n auto --tb=short 2>&1 | tail -10
```

Expected last lines:
```
========== X passed, Y skipped in Z.XXs ===========
```
with no failures and coverage ≥ 91%.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "build: redirect Makefile test targets to packages/parser-core/tests/"
```

---

## Task 5: Delete `tests/` and `src/`

With valuable tests ported and Makefile updated, remove the stale mirror directories.

**Files:**
- Delete: `tests/` (entire directory)
- Delete: `src/` (entire directory)

- [ ] **Step 1: Delete `tests/`**

```bash
git rm -r tests/
```

Expected: all files under `tests/` staged for deletion.

- [ ] **Step 2: Delete `src/`**

```bash
git rm -r src/
```

Expected: all files under `src/` staged for deletion.

- [ ] **Step 3: Verify no other files reference `tests/` or `src/` in unexpected ways**

```bash
grep -r "from src\.\|import src\." --include="*.py" . 2>/dev/null | grep -v ".git/" | grep -v "packages/" | grep -v "docs/"
```

Expected: no output (no Python files outside `packages/` import from `src.*`).

```bash
grep -r "pytest tests/" --include="*.yml" --include="*.yaml" --include="Makefile" . 2>/dev/null | grep -v ".git/"
```

Expected: no output (no CI or build files still reference `pytest tests/`).

- [ ] **Step 4: Commit the deletion**

```bash
git commit -m "chore: delete stale root tests/ and src/ directories"
```

---

## Task 6: Add CI guardrail to `ci.yml`

Add a fast shell check that fails the build immediately if `tests/` or `src/` ever reappears at the repo root.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Find the right insertion point in ci.yml**

Open `.github/workflows/ci.yml` and find the `test-core:` job (around line 236). The guardrail should run as a **standalone job** that runs on every push/PR, parallel to `lint-core`, with no dependencies. Find the top-level `jobs:` section and identify a good place to insert before `test-core`.

- [ ] **Step 2: Add the guardrail job**

Insert the following job in `.github/workflows/ci.yml` under the `jobs:` key (before `test-core:`):

```yaml
  check-test-structure:
    name: Verify test directory structure
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
    - uses: actions/checkout@v6
    - name: Fail if root tests/ or src/ exist
      run: |
        if [ -d "tests/" ] || [ -d "src/" ]; then
          echo "ERROR: root tests/ or src/ must not exist."
          echo "Use packages/parser-core/tests/ for all tests."
          exit 1
        fi
        echo "OK: root tests/ and src/ are absent."
```

- [ ] **Step 3: Add `check-test-structure` to the final gate job**

Find the final gate job (around line 433 — the job that `needs: [changes, lint-core, lint-free, security, test-core, test-free, build-docker, workflow-lint]`). Add `check-test-structure` to its `needs:` list:

```yaml
    needs: [changes, lint-core, lint-free, security, test-core, test-free, build-docker, workflow-lint, check-test-structure]
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add guardrail to fail if root tests/ or src/ reappear"
```

---

## Task 7: Final verification

Confirm everything works end-to-end.

- [ ] **Step 1: Run the full test suite via the updated Makefile target**

```bash
make test 2>&1 | tail -15
```

Expected:
```
====== XXXX passed, X skipped in X.XXs ======
```
No failures. Coverage ≥ 91%.

- [ ] **Step 2: Confirm `tests/` and `src/` are gone**

```bash
ls tests/ 2>&1 && echo "FAIL: tests/ exists" || echo "OK: tests/ absent"
ls src/ 2>&1 && echo "FAIL: src/ exists" || echo "OK: src/ absent"
```

Expected: both print `OK`.

- [ ] **Step 3: Verify git status is clean**

```bash
git status
```

Expected: `nothing to commit, working tree clean`

- [ ] **Step 4: Open a PR**

```bash
git push origin HEAD
gh pr create \
  --title "chore: consolidate test directories — delete stale root tests/ and src/" \
  --body "$(cat <<'EOF'
## Summary
- Ports valuable unique tests from root `tests/` to `packages/parser-core/tests/` (`test_output_strategies`, `test_recursive_scan_entitlements_integration`)
- Deletes stale root `tests/` (143 failing) and `src/` directories
- Redirects all Makefile test targets to `packages/parser-core/tests/` with 91% coverage gate
- Adds CI guardrail job that fails if `tests/` or `src/` reappear

## Test plan
- [ ] `make test` exits 0 with ≥ 91% coverage
- [ ] `packages/parser-core/tests/` passes 1555+ tests, 0 failures
- [ ] `tests/` and `src/` directories are absent from the repo
- [ ] CI `check-test-structure` job passes on this PR
EOF
)" \
  --assignee @me
```
