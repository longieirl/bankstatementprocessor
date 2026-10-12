# Bank Statement Processor

[![CI](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml/badge.svg)](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

> Parse PDF bank statements into structured CSV, JSON, and Excel — locally, with no cloud services.

**Lead Maintainer:** [J Long](https://github.com/longieirl)

---

## Packages

| Package | PyPI | Description |
|---|---|---|
| `packages/parser-core/` | `bankstatements-core` | Shared parsing library — PDF extraction, services, templates |
| `packages/parser-cli/` | `bankstatements-cli` | CLI — thin wrapper around `bankstatements-core` |

---

## Quick Start

```bash
pip install bankstatements-cli

# Place PDF statements in an input directory
bankstatements --input ./input --output ./output
```

**Output formats:**

```bash
bankstatements --input ./input --output ./output --output-formats csv,json,excel
```

---

## Features

- PDF extraction with configurable table boundaries
- CSV, JSON, and Excel export
- Batch processing with recursive directory scanning
- SHA-256 duplicate detection
- Transaction type classification (income, expense, refund, transfer, cash_withdrawal, cash_deposit)
- Monthly transaction summaries and expense analysis
- IBAN extraction and grouping
- Credit card statement support
- GDPR-compliant local processing — no data leaves your machine
- Template-based statement detection (AIB Ireland, Revolut, and more)

---

## Supported Banks

| Bank | Template |
|---|---|
| AIB Ireland | `aib_ireland.json` |
| Revolut | `revolut.json` |
| Generic fallback | `default.json` |

Custom templates can be added — see [docs/CUSTOM_TEMPLATES.md](docs/CUSTOM_TEMPLATES.md).

---

## Repository Structure

```
bankstatementprocessor/
├── packages/
│   ├── parser-core/          bankstatements-core (PyPI library)
│   │   ├── src/bankstatements_core/
│   │   └── tests/
│   └── parser-cli/          bankstatements-cli (CLI)
│       ├── src/bankstatements_cli/
│       └── tests/
├── templates/                shared bank template JSON files
├── docs/                     documentation
└── .github/workflows/
    ├── ci.yml                lint + test both packages
    ├── boundary-check.yml    enforce parser-cli only imports bankstatements-core
    └── release-core.yml      publish bankstatements-core to PyPI on core-v* tags
```

---

## Docker

### Build from source (development)

A `Dockerfile` and `docker-compose.yml` build both `bankstatements-core` and `bankstatements-cli` from source.

```bash
git clone https://github.com/longieirl/bankstatementprocessor.git
cd bankstatementprocessor

docker-compose up --build
```

Place PDFs in `./input/` before running. Results are written to `./output/`.

### Run via Docker (no clone)

The image is published to the GitHub Container Registry — pull and run it directly, no clone required. Both bank statements and credit-card statements are processed; no license is needed.

```bash
docker pull ghcr.io/longieirl/bankstatements:latest
```

```bash
docker run --rm \
  --network none \
  -v "/path/to/your/pdfs:/app/input:ro" \
  -v "/path/to/your/output:/app/output" \
  -e EXIT_AFTER_PROCESSING=true \
  -e OUTPUT_FORMATS=csv,json,excel \
  ghcr.io/longieirl/bankstatements:latest
```

Mount your PDF folder at `/app/input` (read-only) and an output folder at `/app/output`. `--network none` runs fully offline (drop it if you don't need isolation).

Optional: set `-e FILTER_YEAR=2025` (or a range like `2024-2026`) to restrict output to specific years; omit it to include all years. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

---

## Development

**Setup:**

```bash
# Install parser-core in editable mode
pip install -e packages/parser-core[dev,test]

# Install parser-cli in editable mode (depends on parser-core)
pip install -e packages/parser-cli[test]
```

**Common commands:**

```bash
# Run tests (from packages/parser-core/)
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91

# Run tests (from packages/parser-cli/)
pytest packages/parser-cli/tests/

# Format + lint
black src tests
isort src tests
flake8 src tests
```

**Coverage requirement:** 91% minimum on `bankstatements-core`.

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a branch: `git checkout -b feat/my-feature`
3. Make changes and add tests (91%+ coverage required)
4. Submit a PR — CI must pass (lint, tests, boundary check)

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## License

**Apache License 2.0** — free for commercial use with modifications allowed.

See [LICENSE](LICENSE) and [NOTICE](NOTICE).
