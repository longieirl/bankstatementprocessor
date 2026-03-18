# bankstatements-free

[![CI](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml/badge.svg)](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bankstatements-free)](https://pypi.org/project/bankstatements-free/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Free-tier CLI for parsing PDF bank statements into structured CSV, JSON, and Excel — locally, with no cloud services.

Built on [`bankstatements-core`](https://pypi.org/project/bankstatements-core/).

---

## Installation

```bash
pip install bankstatements-free
```

## Quick Start

```bash
# Place PDF statements in an input directory
bankstatements --input ./input --output ./output

# Choose output formats
bankstatements --input ./input --output ./output --output-formats csv,json,excel
```

## Features

- Parse PDF bank statements from AIB Ireland, Revolut, and more
- Export to CSV, JSON, and Excel
- Batch processing with recursive directory scanning
- SHA-256 duplicate detection
- Transaction type classification (purchase, payment, refund, fee, transfer)
- Monthly summaries and expense analysis
- IBAN extraction and grouping
- GDPR-compliant local processing — no data leaves your machine

## Supported Banks

| Bank | Template |
|---|---|
| AIB Ireland | `aib_ireland.json` |
| Revolut | `revolut.json` |
| Generic fallback | `default.json` |

## Documentation

Full documentation and source: [github.com/longieirl/bankstatementprocessor](https://github.com/longieirl/bankstatementprocessor)
