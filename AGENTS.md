# Bank Statements Processor

## Repo Overview

This is the **free-tier** open-source repo. The private `bankstatements-premium` repo holds the paid-tier Docker image published to GHCR. Do not conflate the two.

- **Local Docker image name:** `bankstatementsprocessor` (built from `Dockerfile`)
- **Production image:** `ghcr.io/longieirl/bankstatements-premium:latest` (private repo only)
- Legitimate references to `ghcr.io/longieirl/bankstatements` belong only in `.env.remote`, `Makefile docker-push`, and `.github/workflows/`.

Current version: **0.1.6**

---

## Package Layout

```
packages/
  parser-core/    bankstatements-core (PyPI) — PDF extraction, services, templates
  parser-free/    bankstatements-free (free-tier CLI) — thin wrapper around parser-core
templates/        shared bank template JSON files
custom_templates/ user-overridable templates
skills/           Claude Code agent skills
```

**Source of truth for Docker:** `packages/parser-core/` and `packages/parser-free/`.
`src/` at the repo root is a mirror/symlink for local test running only — never edit it.

Real source: `packages/parser-core/src/bankstatements_core/`

### Module structure (`bankstatements_core`)

```
adapters/        pdfplumber adapter
analysis/        bbox utils, column/table analysis, template generator
builders/        ProcessorBuilder
commands/        CLI commands (analyze-pdf, init)
config/          AppConfig, ProcessorConfig, EnvironmentParser
domain/          models, protocols, services, converters, currency
extraction/      PDFExtractor, IBANExtractor, RowBuilder, WordUtils
facades/         ProcessingFacade
patterns/        factories, repositories, strategies
services/        all business logic services
templates/       bank JSON templates + detectors
entitlements.py
processor.py
pdf_table_extractor.py  # legacy shim — delegates to extraction/, treat as deprecated
```

---

## Development Setup

```bash
pip install -e packages/parser-core[dev,test]
pip install -e packages/parser-free[test]
```

---

## Running Tests

```bash
# parser-core (run from repo root)
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91

# parser-free
pytest packages/parser-free/tests/

# integration (run from repo root)
python -m pytest packages/parser-core/tests/integration/ -m integration --no-cov

# re-baseline integration snapshot
pytest packages/parser-core/tests/integration/ -m integration --snapshot-update --no-cov

# parallel (faster)
pytest packages/parser-core/tests/ -n auto
```

Tests default to `not integration` — run integration tests explicitly with `-m integration`.
Coverage minimum: **91%** on `bankstatements-core`.

---

## Linting & Formatting

Run these together before every push (CI checks all four):

```bash
black packages/parser-core/src packages/parser-core/tests
isort packages/parser-core/src packages/parser-core/tests
ruff check packages/parser-core/src packages/parser-core/tests
mypy packages/parser-core/src
```

For `parser-free`, run isort **from within `packages/parser-free/`** — CI sort order differs from root.

**Black gotcha:** Black collapses multi-line `raise`/`return` onto one line if it fits in 88 chars. Always write them as single lines:
- `raise ValueError(f"...")` not a multi-line form
- `raise TypeError(f"...")` not a multi-line form

**Logging:** use `%`-formatting, not f-strings — enforced by ruff rule G004.

---

## Make Targets

```bash
make docker-local        # build from source + run
make docker-remote       # pull production image + run
make docker-build        # build only
make docker-integration  # snapshot-based Docker integration test
make docker-scan-trivy   # trivy HIGH/CRITICAL scan
make docker-secure-run   # network-isolated (GDPR mode)
```

---

## Version Bumping

Three files must always match — CI compares them and fails on mismatch:

1. `packages/parser-core/pyproject.toml` → `version = "x.y.z"`
2. `packages/parser-core/src/bankstatements_core/__version__.py`
3. `packages/parser-free/pyproject.toml` → `version = "x.y.z"`

```bash
make version-bump-patch   # bump x.x.N
make version-bump-minor   # bump x.N.0
make version-bump-major   # bump N.0.0
```

---

## Git Conventions

Commit format: `type: description`

Types: `feat` | `fix` | `chore` | `docs` | `refactor` | `test` | `perf` | `sec`

Branch naming: `type/short-description`
If working from a GitHub issue: `type/123-short-description`

**Never push directly to `main`.** Always create a feature branch, push the branch, and open a PR. Branch protection requires CI to pass before merge.

```bash
git checkout -b <branch-name>
git push -u origin <branch-name>
```

Always use `.github/PULL_REQUEST_TEMPLATE.md`. Pass `--assignee @me` on `gh pr create` — `gh pr edit` lacks the required token scope.

```bash
gh pr create --assignee @me --title "..." --body "$(cat <<'EOF'
...populated template...
EOF
)"
```

---

## Key Architecture Notes

- `ExtractionResult.card_number: str | None` — `None` = bank statement, string = credit card (last-4 suffix)
- `BankTemplate.column_aliases` — renames template keys to canonical column names; `RowPostProcessor._apply_column_aliases()` is the sole owner
- `CCGroupingService` in `services/card_grouping.py` — groups CC results by last-4 card suffix
- `processor.run()` splits on `card_number is None`: bank → `group_by_iban`, CC → `group_by_card`
- `PDFProcessingOrchestrator.process_all_pdfs()` returns `tuple[list[ExtractionResult], int, int]` → `(results, pdf_count, pages_read)`
- `ServiceRegistry.from_config(ProcessorConfig, Entitlements)` is the primary factory
- Credit card support is **paid tier only** via `require_iban=False` in `Entitlements.paid_tier()`
- Service layer uses `list[Transaction]` throughout — no dict round-trips internally; conversion at output boundary via `transactions_to_dicts()`
- Architecture test (`test_architecture.py`) enforces module placement and bans circular imports

---

## CI Workflows

| Workflow | File | Trigger |
|---|---|---|
| Main CI | `ci.yml` | push/PR to main |
| Release (root) | `release.yml` | tag push |
| Release (core) | `release-core.yml` | tag push |
| Security scan | `security-scan.yml` | schedule + push |
| Boundary check | `boundary-check.yml` | push/PR |
| PR labeler | `pr-labeler.yml` | PR open/sync |

CI enforces: ruff, black, mypy, pylint design gates (Xenon), bandit, pip-audit, trivy (0 critical), coverage ≥ 91%.

**Security:** workflows use quoted shell variables and avoid `${{ github.* }}` interpolation directly in `run:` steps to prevent shell injection (hardened in PRs #168–#171). Production image runs `apt-get upgrade -y` on every build to pull latest Debian patches.

---

## Open Issues

- **#59** — Docker integration CI job (blocked — needs fake PDFs; local tooling done in PR #70)

---

## Gitignored Files (never commit)

- `HANDOFF.md`, `MEMORY.md`
- `.env.local` (may contain tokens)
- `logs/processing_activity.jsonl`
- `input/`, `output/` contents
