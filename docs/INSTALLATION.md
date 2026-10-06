# Installation Guide

## Table of Contents

- [pip Installation](#pip-installation)
- [Development Installation](#development-installation)
- [Docker](#docker)
- [Verifying Installation](#verifying-installation)
- [Configuration](#configuration)

---

## pip Installation

```bash
pip install bankstatements-cli
```

This installs the `bankstatements` CLI command with all dependencies.

### Features

- ✓ CSV, JSON, and Excel (.xlsx) output
- ✓ PDF parsing and extraction
- ✓ Duplicate detection
- ✓ Recursive directory scanning
- ✓ Monthly summary reports
- ✓ Expense analysis
- ✓ Credit card statement support
- ✓ IBAN extraction and grouping

---

## Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/longieirl/bankstatementprocessor.git
cd bankstatementprocessor

# Install both packages in editable mode with dev/test extras
pip install -e packages/parser-core[dev,test]
pip install -e packages/parser-cli[test]
```

---

## Docker

A `Dockerfile` and `docker-compose.yml` are provided for local development:

```bash
git clone https://github.com/longieirl/bankstatementprocessor.git
cd bankstatementprocessor

docker-compose up --build
```

Place PDFs in `./input/` before running. Results are written to `./output/`.

---

## Verifying Installation

### Check Installed Version

```bash
bankstatements --version
```

### Test Basic Functionality

```bash
# Create test directory structure
mkdir -p input output

# Run the application (will show no PDFs found, but verifies it works)
bankstatements
```

---

## Configuration

Configure the application using environment variables or a `.env` file:

```bash
# Input and output directories
INPUT_DIR=input
OUTPUT_DIR=output

# Output formats
OUTPUT_FORMATS=csv,json,excel

# Enable monthly summaries
GENERATE_MONTHLY_SUMMARY=true

# Logging
LOG_LEVEL=INFO
```

See [docs/REFERENCE.md](REFERENCE.md) for the full environment variable reference.
