# bankstatements-core

[![CI](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml/badge.svg)](https://github.com/longieirl/bankstatementprocessor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bankstatements-core)](https://pypi.org/project/bankstatements-core/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Core PDF bank statement parsing library — PDF extraction, services, and templates.

Used as the foundation for [`bankstatements-free`](https://pypi.org/project/bankstatements-free/) and the premium distribution.

---

## Installation

```bash
pip install bankstatements-core
```

## Features

- PDF extraction with configurable table boundaries
- Template-based statement detection (AIB Ireland, Revolut, and more)
- CSV, JSON, and Excel export
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

## Quick Start

```python
from bankstatements_core.services.processor import StatementProcessor

processor = StatementProcessor(input_dir="./input", output_dir="./output")
results = processor.process()
```

## Documentation

Full documentation and source: [github.com/longieirl/bankstatementprocessor](https://github.com/longieirl/bankstatementprocessor)
