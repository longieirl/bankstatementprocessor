# bankstatementprocessor

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
| `packages/parser-free/` | `bankstatements-free` | Free-tier CLI — thin wrapper around `bankstatements-core` |

---

## Quick Start

```bash
pip install bankstatements-free

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
- Transaction type classification (purchase, payment, refund, fee, transfer)
- Monthly transaction summaries and expense analysis
- IBAN extraction and grouping
- Multi-document type support (bank statements, credit cards, loans)
- GDPR-compliant local processing — no data leaves your machine
- Template-based statement detection (AIB Ireland, Revolut, and more)

**Premium features** (available in the private `bankstatements-premium` distribution):
- Credit card and loan statement support (no IBAN required)
- Process templates without IBAN patterns

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
│   └── parser-free/          bankstatements-free (free-tier CLI)
│       ├── src/bankstatements_free/
│       └── tests/
├── templates/                shared bank template JSON files
├── docs/                     documentation
└── .github/workflows/
    ├── ci.yml                lint + test both packages
    ├── boundary-check.yml    enforce parser-free cannot import premium code
    └── release-core.yml      publish bankstatements-core to PyPI on core-v* tags
```

---

## Development

**Setup:**

```bash
# Install parser-core in editable mode
pip install -e packages/parser-core[dev,test]

# Install parser-free in editable mode (depends on parser-core)
pip install -e packages/parser-free[test]
```

**Common commands:**

```bash
# Run tests (from packages/parser-core/)
pytest packages/parser-core/tests/ --cov=bankstatements_core --cov-fail-under=91

# Run tests (from packages/parser-free/)
pytest packages/parser-free/tests/

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
