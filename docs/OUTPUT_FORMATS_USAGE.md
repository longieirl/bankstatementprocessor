# Output Formats Usage Guide

This guide explains how to configure and use multiple output formats with the bank statement processor.

## Overview

The application supports three output formats:
- **CSV** (`.csv`) - Comma-separated values with optional totals row
- **JSON** (`.json`) - Structured JSON with all transaction data
- **Excel** (`.xlsx`) - Microsoft Excel format with worksheet and totals

## Quick Start

### Using Docker Compose (Recommended)

**Method 1: Environment Variables**

```bash
# CSV and Excel only
OUTPUT_FORMATS=csv,excel docker-compose up

# All three formats
OUTPUT_FORMATS=csv,json,excel docker-compose up

# JSON only
OUTPUT_FORMATS=json docker-compose up
```

**Method 2: Using .env File**

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your preferred formats:
   ```bash
   OUTPUT_FORMATS=csv,excel
   ```

3. Run the processor:
   ```bash
   docker-compose up
   ```

### Using Direct Docker Run

```bash
docker run \
  -v ./input:/app/input \
  -v ./output:/app/output \
  -e OUTPUT_FORMATS=csv,excel \
  bank-statement-processor
```

### Using Python Directly (Development)

```bash
# Set environment variable
export OUTPUT_FORMATS=csv,excel

# Run the application
python -m src.app
```

## Configuration Options

### OUTPUT_FORMATS

**Format:** Comma-separated list of format names

**Valid Values:**
- `csv` - CSV format
- `json` - JSON format
- `excel` - Excel (.xlsx) format

**Default:** `csv,json`

**Examples:**
```bash
# Single format
OUTPUT_FORMATS=csv

# Two formats
OUTPUT_FORMATS=csv,excel

# All formats
OUTPUT_FORMATS=csv,json,excel
```

### TOTALS_COLUMNS

Controls which columns have totals calculated.

**Format:** Comma-separated list of column name patterns (case-insensitive)

**Default:** `debit,credit`

**Examples:**
```bash
# Default - sum Debit and Credit columns
TOTALS_COLUMNS=debit,credit

# Sum any column with "amount" in the name
TOTALS_COLUMNS=amount

# Multiple patterns
TOTALS_COLUMNS=debit,credit,balance

# Disable totals
TOTALS_COLUMNS=
```

### Auxiliary JSON Files

The following JSON files are **always generated** regardless of OUTPUT_FORMATS:
- `duplicates.json` - Duplicate transactions detected across files
- `monthly_summary.json` - Monthly aggregation of transactions (when transactions exist)

These files are not controlled by OUTPUT_FORMATS since they serve different purposes than the main transaction output.

## Output Files

### With Default Configuration

```bash
OUTPUT_FORMATS=csv,json
```

Generates:
- `output/bank_statements.csv` - Transaction data
- `output/bank_statements.json` - Transaction data
- `output/duplicates.json` - Duplicate transactions (always JSON)
- `output/monthly_summary.json` - Monthly totals (always JSON)

### With All Formats

```bash
OUTPUT_FORMATS=csv,json,excel
```

Generates:
- `output/bank_statements.csv` - Transaction data in CSV
- `output/bank_statements.json` - Transaction data in JSON
- `output/bank_statements.xlsx` - Transaction data in Excel
- `output/duplicates.json` - Duplicate transactions (always JSON)
- `output/monthly_summary.json` - Monthly totals (always JSON)

## Format-Specific Features

### CSV Format

- Standard comma-separated values
- UTF-8 encoding
- Header row with column names
- Optional totals row at the end
- Compatible with Excel, Google Sheets, Numbers

**Example Output:**
```csv
Date,Details,Debit €,Credit €,Balance €,Filename
01/01/2024,Purchase,100.00,,5000.00,statement1.pdf
02/01/2024,Deposit,,500.00,5500.00,statement1.pdf
TOTAL,,100.00,500.00,,
```

### JSON Format

- Structured JSON array
- Each transaction is an object
- All fields included
- Suitable for programmatic processing

**Example Output:**
```json
[
  {
    "Date": "01/01/2024",
    "Details": "Purchase",
    "Debit €": "100.00",
    "Credit €": "",
    "Balance €": "5000.00",
    "Filename": "statement1.pdf"
  }
]
```

### Excel Format

- Microsoft Excel (.xlsx) format
- Single worksheet named "Transactions"
- Column headers
- Optional totals row with "TOTAL" label
- Compatible with Excel, LibreOffice, Google Sheets

**Features:**
- **Numeric columns written as numbers** - Debit, Credit, Balance, and Amount columns are stored as actual numeric types, not text
- **Number formatting applied** - Cells formatted with comma separators (#,##0.00)
- **Excel formulas work** - Can use SUM, AVERAGE, and other functions on numeric columns
- **Proper sorting** - Numeric columns sort correctly by value, not alphabetically
- Totals row is visually separated (empty row before totals)
- Works with all modern spreadsheet applications

**Numeric Column Detection:**
The Excel strategy automatically identifies numeric columns by name patterns:
- "debit", "credit", "balance", "amount"
- "total", "price", "cost", "fee", "charge"
- Currency symbols: €, $, £, ¥

## Complete Docker Compose Example

**docker-compose.yml**

```yaml
services:
  bank-processor:
    build: .
    volumes:
      - ./input:/app/input
      - ./output:/app/output
    environment:
      # Output configuration
      - OUTPUT_FORMATS=csv,excel
      - TOTALS_COLUMNS=debit,credit
      - GENERATE_MONTHLY_SUMMARY=true

      # Processing configuration
      - SORT_BY_DATE=true
      - ENABLE_DYNAMIC_BOUNDARY=false

      # Logging
      - LOG_LEVEL=INFO
```

## Programmatic Usage

### Using Factory Pattern

```python
from pathlib import Path
from src.app import AppConfig
from src.patterns.factories import ProcessorFactory

# Configure output formats
config = AppConfig(
    input_dir=Path("input"),
    output_dir=Path("output"),
    output_formats=["csv", "excel"]
)

# Create processor with factory
processor = ProcessorFactory.create_from_config(config)

# Run processing
summary = processor.run()

print(f"Generated files:")
print(f"  CSV: {summary['csv_path']}")
print(f"  Excel: {summary['excel_path']}")
```

### Using Custom Strategies

```python
from pathlib import Path
from src.patterns.strategies import CSVOutputStrategy, ExcelOutputStrategy
from src.patterns.factories import ProcessorFactory
from src.app import AppConfig

# Create custom strategy instances
strategies = {
    "csv": CSVOutputStrategy(),
    "excel": ExcelOutputStrategy(),
}

config = AppConfig.from_env()

# Inject custom strategies
processor = ProcessorFactory.create_from_config(
    config,
    output_strategies=strategies
)

summary = processor.run()
```

## Troubleshooting

### Excel Files Not Generated

**Problem:** `OUTPUT_FORMATS=excel` but no .xlsx file created

**Solution:** Ensure `openpyxl` is installed:
```bash
pip install openpyxl>=3.1.0
```

For Docker, this is already included in requirements.

### Invalid Format Error

**Problem:** `ConfigurationError: Invalid output format 'xls'`

**Solution:** Use valid format names: `csv`, `json`, or `excel` (not `xls`)

### Empty Format List Error

**Problem:** `ConfigurationError: At least one output format must be specified`

**Solution:** Ensure OUTPUT_FORMATS is not empty:
```bash
# Wrong
OUTPUT_FORMATS=

# Correct
OUTPUT_FORMATS=csv
```

### Totals Not Appearing

**Problem:** No totals row in CSV or Excel output

**Solution:** Check TOTALS_COLUMNS configuration:
```bash
# Enable totals
TOTALS_COLUMNS=debit,credit

# Verify column names match (case-insensitive)
# If columns are "Debit €" and "Credit €", use:
TOTALS_COLUMNS=debit,credit
```

## Advanced: Adding New Formats

The application uses the Strategy pattern, making it easy to add new output formats.

### 1. Create a New Strategy

```python
# src/patterns/strategies.py

from pathlib import Path
from typing import List

class PDFOutputStrategy(OutputFormatStrategy):
    """Strategy for writing transactions as PDF files."""

    def write(self, transactions: List[dict], file_path: Path,
              column_names: List[str], **kwargs) -> None:
        # Implementation here
        pass
```

### 2. Register in Factory

```python
# src/patterns/factories.py

strategy_map = {
    "csv": CSVOutputStrategy(),
    "json": JSONOutputStrategy(),
    "excel": ExcelOutputStrategy(),
    "pdf": PDFOutputStrategy(),  # Add new format
}
```

### 3. Update Configuration Validation

```python
# src/app.py

def _validate_output_formats(self) -> None:
    valid_formats = {"csv", "json", "excel", "pdf"}  # Add new format
    # ... rest of validation
```

### 4. Use the New Format

```bash
OUTPUT_FORMATS=csv,pdf docker-compose up
```

See `docs/DESIGN_PATTERNS.md` for more details on the Strategy pattern implementation.

## Best Practices

1. **Use CSV for maximum compatibility** - Works everywhere
2. **Use JSON for programmatic processing** - Easy to parse
3. **Use Excel for business users** - Familiar spreadsheet interface
4. **Enable multiple formats** when unsure - Small overhead, maximum flexibility
5. **Keep TOTALS_COLUMNS simple** - Match your actual column names
6. **Use .env.example as a starting point** - Copy and customize

## See Also

- [README.md](../README.md) - Main documentation
- [DESIGN_PATTERNS.md](./DESIGN_PATTERNS.md) - Design pattern details
- [PATTERN_INTEGRATION_STATUS.md](./PATTERN_INTEGRATION_STATUS.md) - Integration status
- [.env.example](../.env.example) - Configuration template
