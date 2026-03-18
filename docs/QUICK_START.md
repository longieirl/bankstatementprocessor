# Quick Start - Bank Statement Processor

## Local Build Setup

Build and run from source using Docker:

```bash
# 1. Build the image
make docker-build

# 2. Add your PDFs
mkdir -p input output
cp ~/Downloads/statement.pdf input/

# 3. Process
make docker-local

# 4. Check results
ls -la output/
```

**That's it!** All directories are created automatically. No manual setup required.

---

## Docker Setup (Local Build)

### One Command Processing

Process all PDFs in one simple command:

```bash
make docker-local
```

That's it! The container will:
1. Build the Docker image from source
2. Process all PDFs in `./input/`
3. Save CSV output to `./output/`
4. Exit when complete

## Setup

1. **Add your PDF bank statements to the input folder:**
   ```bash
   cp ~/Downloads/*.pdf ./input/
   ```

2. **Run the processor:**
   ```bash
   make docker-local
   ```

3. **Get your results:**
   ```bash
   ls ./output/
   # Files created:
   # - bank_statements_<IBAN-last-4-digits>.csv
   # - duplicates_<IBAN-last-4-digits>.json
   # - ibans.json
   ```

## Example Output

```
PDFs processed: 11
Pages read: 62
Unique transactions: 1357
Duplicate transactions: 0
```

Output CSV file: `./output/bank_statements_9015.csv`

## Features (FREE Tier)

✅ Extract transactions from PDF bank statements
✅ Automatic IBAN detection
✅ CSV output format
✅ Duplicate detection
✅ Chronological sorting
✅ Column totals calculation
✅ No configuration required

## Interactive Mode

If you need to process multiple batches, use interactive mode:

```bash
# Start container (stays running)
EXIT_AFTER_PROCESSING=false make docker-local

# Add more PDFs
cp new_statements.pdf ./input/

# Stop when done
docker-compose down
```

## Troubleshooting

**Issue: No PDFs found**
```bash
# Check input folder
ls -la ./input/

# Make sure PDFs are there
cp your_statements.pdf ./input/
```

**Issue: Permission errors**
```bash
# Fix permissions
chmod -R 755 ./input ./output
```

**Issue: Want to reprocess**
```bash
# Clean output
rm -rf ./output/*

# Run again
make docker-local
```

## Next Steps

- See [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) for detailed Docker usage
- See [DOCKER_TROUBLESHOOTING.md](DOCKER_TROUBLESHOOTING.md) for troubleshooting

## PAID Tier Features

PAID tier removes the IBAN requirement, allowing you to process:
- Credit card statements (without IBAN patterns)
- Other financial documents without IBAN

All other features (CSV, JSON, Excel, monthly summaries, recursive scanning) are available in FREE tier.

See documentation for license generation instructions.

---

## Environment Variables

```bash
# Set project root (all directories under one location)
PROJECT_ROOT=/data/bank-app make docker-local

# Output formats
OUTPUT_FORMATS=csv,json,excel make docker-local
```

---

## Directory Management

### Automatic Creation
All directories are created automatically:
- ✅ `input/` - Created when processing starts
- ✅ `output/` - Created before writing results
- ✅ `logs/` - Created for GDPR audit trail

### PROJECT_ROOT Configuration
Set a single base directory for all paths:

```bash
# In .env file
PROJECT_ROOT=/data/bank-statements
```

This resolves all relative paths to:
- `/data/bank-statements/input/`
- `/data/bank-statements/output/`
- `/data/bank-statements/logs/`

**Note:** Absolute paths in `INPUT_DIR`, `OUTPUT_DIR`, `LOGS_DIR` ignore `PROJECT_ROOT`.
