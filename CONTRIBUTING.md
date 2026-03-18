# Contributing to bankstatementprocessor

Thank you for your interest in contributing! This is a monorepo — all shared PDF parsing logic lives in `packages/parser-core/` and is published to PyPI as `bankstatements-core`.

## Repository Structure

```
bankstatementprocessor/
├── packages/
│   ├── parser-core/      bankstatements-core — the shared parsing library
│   └── parser-free/      bankstatements-free — thin free-tier CLI wrapper
├── templates/            shared bank template JSON files
└── docs/
```

**Contributions to parsing logic, services, extraction, or templates belong in `packages/parser-core/`.** The `parser-free` package is intentionally minimal — it only wires `bankstatements-core` to a CLI entry point.

---

## Getting Started

### Prerequisites

- Python 3.11, 3.12, or 3.13
- Git
- `poppler-utils` (for PDF processing — `brew install poppler` on macOS, `apt install poppler-utils` on Linux)

### Local Development Setup

```bash
git clone https://github.com/longieirl/bankstatementprocessor.git
cd bankstatementprocessor

# Install parser-core in editable mode (includes all parsing deps)
pip install -e "packages/parser-core[dev,test]"

# Install parser-free in editable mode (depends on parser-core above)
pip install -e "packages/parser-free[test]"
```

### Verify Setup

```bash
# Core tests with coverage
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91

# Free CLI smoke test
bankstatements --version
bankstatements --init
```

---

## Making Changes

### Branch Naming

- `feature/descriptive-name` — new features
- `fix/descriptive-name` — bug fixes
- `docs/descriptive-name` — documentation updates

### Workflow

1. Fork the repository and create a branch
2. Make changes following the code standards below
3. **Write tests** — 91% coverage on `bankstatements-core` is enforced by CI
4. Run quality checks:
   ```bash
   # From packages/parser-core/
   black src tests
   isort src tests
   flake8 src tests --max-line-length=88 --extend-ignore=E203,W503
   mypy src --ignore-missing-imports
   pytest tests/ --cov=bankstatements_core --cov-fail-under=91
   ```
5. Submit a PR — CI must pass (lint, boundary check, tests)

---

## Code Standards

### Formatting

- **Line length:** 88 characters (Black default)
- **Imports:** organised by isort (stdlib → third-party → local)

### Type Hints

All public functions must have type hints:

```python
def process_transaction(amount: Decimal, date: datetime) -> Transaction:
    ...
```

### Naming Conventions

- **Classes:** PascalCase (`BankStatementProcessor`)
- **Functions/Variables:** snake_case (`parse_date`)
- **Constants:** UPPER_SNAKE_CASE (`TABLE_TOP_Y`)
- **Private members:** `_leading_underscore`

### Design Patterns

`bankstatements-core` uses Strategy, Repository, Factory, Chain of Responsibility, Builder, and Facade patterns. Follow existing patterns when adding new features.

---

## Testing

### Coverage Requirement

**91% minimum on `bankstatements-core`** — enforced by CI. PRs that drop below this threshold will not be merged.

### Running Tests

```bash
# All tests with coverage
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91 -v

# Specific file or test
pytest packages/parser-core/tests/services/test_my_service.py -v
pytest packages/parser-core/tests/ -k "test_function_name"

# Parallel execution
pytest packages/parser-core/tests/ -n auto

# Free CLI tests
pytest packages/parser-free/tests/ -v
```

### Test Organisation

```
packages/parser-core/tests/
├── test_processor.py
├── test_app.py
├── services/
├── extraction/
├── domain/
└── templates/
```

---

## Adding a New Bank Template

Templates live in `packages/parser-core/src/bankstatements_core/templates/`. See [docs/ADDING_NEW_TEMPLATES.md](docs/ADDING_NEW_TEMPLATES.md) for the full guide.

Quick summary:
1. Copy an existing template JSON and adjust column bounds and IBAN pattern
2. Add a detector class in `bankstatements_core/templates/` if the bank needs filename/header matching
3. Add tests in `packages/parser-core/tests/templates/`

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass with 91%+ coverage
- [ ] Code is formatted (Black + isort)
- [ ] Linting passes (Flake8, MyPy)
- [ ] New functionality has tests
- [ ] No regressions in existing tests

### CI Checks

Your PR must pass:

- **lint-core** — Black, isort, Flake8, MyPy on `parser-core`
- **lint-free** — Black, isort, Flake8 on `parser-free`
- **test-core** — pytest with 91%+ coverage on `bankstatements-core`
- **test-free** — pytest on `parser-free`
- **boundary-check** — CI fails if `parser-free` imports `bankstatements_premium` or `src.licensing`
- **security** — Bandit on both packages

### Review Process

1. Automated CI checks run on your PR
2. Maintainer review (typically within 48 hours)
3. Address any requested changes
4. Approval and merge by maintainers

---

## Reporting Bugs

1. Check [existing issues](https://github.com/longieirl/bankstatementprocessor/issues) first
2. Reproduce with a minimal test case
3. Open an issue with:
   - OS and Python version
   - `bankstatements --version` output
   - Steps to reproduce
   - Expected vs actual behaviour
   - Relevant log output

---

## Feature Requests

1. Check [existing issues](https://github.com/longieirl/bankstatementprocessor/issues) first
2. Open an issue with label `enhancement`
3. Describe the use case and expected behaviour

---

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
