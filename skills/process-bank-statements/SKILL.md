---
name: process-bank-statements
description: Use when asked to process PDF bank statements, extract transactions from PDFs, convert bank statement PDFs to CSV or Excel, analyze banking transactions. Triggered by "process bank statements", "extract transactions from PDF", "convert bank PDFs to CSV", "read my bank statements", "analyze bank transactions", "parse bank statement folder".
---

# Bank Statement Processor

## Overview

Uses the `bankstatements-free` pip package (`bankstatements` CLI) to extract transactions from PDF bank statements and produce CSV, Excel, or JSON output. Configuration is passed via environment variables — no config file needed.

FREE tier supports: all output formats (csv, json, excel), recursive scanning, monthly summaries, expense analysis. Requires PDFs to contain IBANs (bank statements only — credit card PDFs are not supported in the free tier).

---

## Phase 0: Check Installation

```bash
pip show bankstatements-free
```

If not installed, ask:
> "bankstatements-free is not installed. How would you like to install it?
> a) `pip install bankstatements-free` — latest release from PyPI
> b) `pip install -e packages/parser-free` — local dev install from this repo"

Wait for choice, then run the selected command. Verify after:

```bash
bankstatements --version
```

---

## Phase 1: Gather Inputs

Ask for the following. Accept defaults if user says "defaults" or provides only a PDF path.

| Input | What to ask | Default |
|---|---|---|
| PDF directory | "Path to the folder containing your PDF bank statements?" | `./input` |
| Output directory | "Where should output files go?" | `./output` |
| Output format | "Format — csv, excel, json, or multiple e.g. csv,excel?" | `csv` |

**Shortcut:** If user provides a single path (e.g. "process ~/Downloads/statements"), use it as `INPUT_DIR` and default `OUTPUT_DIR` to `<INPUT_DIR>/../statements-output`.

---

## Phase 2: Run the Processor

Run via Bash with env vars inline:

```bash
INPUT_DIR=<input_path> OUTPUT_DIR=<output_path> OUTPUT_FORMATS=<formats> bankstatements
```

**Examples:**

```bash
# CSV only (most common)
INPUT_DIR=~/Downloads/statements OUTPUT_DIR=~/Downloads/output OUTPUT_FORMATS=csv bankstatements

# CSV + Excel
INPUT_DIR=/data/pdfs OUTPUT_DIR=/data/output OUTPUT_FORMATS=csv,excel bankstatements

# Excel only
INPUT_DIR=./statements OUTPUT_DIR=./output OUTPUT_FORMATS=excel bankstatements

# Verbose debug (use when 0 transactions extracted)
INPUT_DIR=./input OUTPUT_DIR=./output OUTPUT_FORMATS=csv LOG_LEVEL=DEBUG bankstatements
```

---

## Phase 3: Present Results

The CLI prints a summary block — relay it verbatim:

```
========== SUMMARY ==========
PDFs read: N
PDFs extracted: N
Pages read: N
Unique transactions: N
Duplicate transactions: N
CSV output: /path/to/output.csv
=============================
```

Then offer:
> "Would you like me to open the CSV and summarize the transactions?"

If yes, read the output file and provide:
- Total transaction count and date range
- Top 5 largest transactions (debit and credit separately)
- Any recurring patterns or notable clusters

If monthly summary or expense analysis files were also generated, offer to review those too.

---

## Quick Reference

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `INPUT_DIR` | `input` | PDF source directory (relative to CWD or `PROJECT_ROOT`) |
| `OUTPUT_DIR` | `output` | Output destination (created automatically) |
| `OUTPUT_FORMATS` | `csv` | `csv`, `excel`, `json` — comma-separated, all free tier |
| `RECURSIVE_SCAN` | `true` | Scan subdirectories for PDFs |
| `SORT_BY_DATE` | `true` | Sort transactions by date in output |
| `GENERATE_MONTHLY_SUMMARY` | `true` | Produce per-month breakdown file |
| `GENERATE_EXPENSE_ANALYSIS` | `true` | Produce expense analysis report |
| `PROJECT_ROOT` | CWD | Base dir for resolving relative paths |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` to trace template matching |

### First-time Setup

```bash
# Creates input/, output/, logs/ in current directory
bankstatements --init

# With sample .env config files
bankstatements --init --with-samples
```

### Dev Install (from this repo)

```bash
pip install -e packages/parser-free
```

---

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `command not found: bankstatements` | Not installed or wrong venv | `pip install bankstatements-free` or activate correct venv |
| 0 PDFs extracted | No bank template matched | Re-run with `LOG_LEVEL=DEBUG` to see template detection |
| 0 PDFs extracted | Credit card PDFs | Free tier requires IBANs — credit card statements not supported |
| `Invalid output format 'xlsx'` | Wrong format name | Use `excel` not `xlsx` in `OUTPUT_FORMATS` |
| `ConfigurationError: TABLE_TOP_Y must be less than TABLE_BOTTOM_Y` | Env var conflict | Unset `TABLE_TOP_Y`/`TABLE_BOTTOM_Y` to use defaults (300/720) |
| Duplicate transactions | Same PDF in multiple subdirs | Check `INPUT_DIR` for duplicate filenames |
