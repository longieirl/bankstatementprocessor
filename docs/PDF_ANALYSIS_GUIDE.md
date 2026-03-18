# PDF Analysis Utility - User Guide

## Overview

The PDF Analysis Utility helps you generate template configurations for new bank statement formats by automatically detecting table structures, IBANs, and column boundaries.

## Quick Start

### Step 1: Analyze a PDF
```bash
python -m src.commands.analyze_pdf input/statement.pdf \
    --output custom_templates/mybank.json
```

This will:
- Detect transaction tables
- Extract IBAN from the header (first page only)
- Analyze column boundaries
- Generate a template JSON file at `custom_templates/mybank.json`

### Step 2: Test the Template
```bash
python -m src.commands.analyze_pdf input/statement.pdf \
    --template custom_templates/mybank.json
```

This will:
- Use the generated template to extract transactions
- Validate that the column boundaries are correct
- Show extraction results in the log output

### Step 3: Iterate (if needed)
If extraction isn't perfect:
1. Manually edit `custom_templates/mybank.json` to adjust column boundaries
2. Re-run Step 2 to test your changes
3. Repeat until extraction is correct

---

## Command-Line Options

```
python -m src.commands.analyze_pdf <pdf_path> [OPTIONS]

Required:
  pdf_path              Path to PDF file to analyze

Optional:
  --output PATH         Save generated template to PATH (creates/overwrites)
  --template PATH       Test extraction using existing template at PATH
  --base-template PATH  Base template to use (default: templates/default.json)
  --log-level LEVEL     Logging verbosity: DEBUG|INFO|WARNING|ERROR (default: INFO)
```

---

## Docker Usage

### Mode 1: Generate Template

```bash
docker run --rm \
  -v ./input:/app/input \
  -v ./custom_templates:/app/custom_templates \
  -e ANALYZE_PDF="statement.pdf" \
  -e OUTPUT_PATH="custom_templates/mybank.json" \
  bankstatements:latest
```

**Result**: Creates `./custom_templates/mybank.json` on your host

### Mode 2: Test Template

```bash
docker run --rm \
  -v ./input:/app/input \
  -v ./custom_templates:/app/custom_templates \
  -e ANALYZE_PDF="statement.pdf" \
  -e TEMPLATE_PATH="custom_templates/mybank.json" \
  bankstatements:latest
```

**Result**: Logs showing extraction results with your template

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANALYZE_PDF` | Yes | PDF filename (relative to `/app/input`) |
| `OUTPUT_PATH` | No | Template output path (generation mode) |
| `TEMPLATE_PATH` | No | Template to validate (test mode) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

---

## Understanding the Output

### Console Logs

The utility provides detailed logging output:

```
Step 1-2: Detecting transaction tables...
  Table 1: BBox(x0=50.0, y0=300.0, x1=550.0, y1=720.0), area=162000px²

Step 3-4: Extracting IBAN candidates (first page only)...
  Found 3 IBAN candidates
    - IE29****5678 at BBox(x0=100.0, y0=50.0, x1=200.0, y1=60.0)

Step 5: Filtering IBANs by table overlap...
  1 IBANs after filtering (2 rejected)

Step 6: Selecting best IBAN...
  ✓ Selected IBAN: IE29****5678 (score: 80.5)

Step 7: Analyzing column boundaries...
  Detected 5 columns:
    Date: (26.0, 78.0)
    Details: (78.0, 255.0)
    Debit €: (255.0, 313.0)
    Credit €: (313.0, 369.0)
    Balance €: (369.0, 434.0)

✓ Template saved to: custom_templates/mybank.json
```

### Generated Template

The template JSON follows this structure:

```json
{
  "id": "custom_generated",
  "name": "Custom Template - Generated",
  "detection": {
    "iban_patterns": ["^IE\\d{2}.*"],
    "column_headers": ["Date", "Details", "Debit €", "Credit €", "Balance €"]
  },
  "extraction": {
    "table_top_y": 300.0,
    "table_bottom_y": 720.0,
    "header_check_top_y": 250.0,
    "enable_header_check": true,
    "columns": {
      "Date": [26.0, 78.0],
      "Details": [78.0, 255.0],
      "Debit €": [255.0, 313.0],
      "Credit €": [313.0, 369.0],
      "Balance €": [369.0, 434.0]
    }
  }
}
```

---

## Troubleshooting

### No Tables Detected

If the utility reports "No transaction tables detected":

1. **Check PDF structure**: Open the PDF in a viewer and ensure it has actual tables (not just text)
2. **Try DEBUG logging**: `--log-level DEBUG` to see more details
3. **Manual inspection**: Use a PDF analysis tool to check table structure

### IBAN Not Found

If IBAN extraction fails:

1. **Check first page**: IBANs are only extracted from page 1 (by design)
2. **Check IBAN format**: Must be valid format (2 letters + 2 digits + alphanumerics)
3. **Manual addition**: You can manually add IBAN patterns to the template

### Incorrect Column Boundaries

If column detection is wrong:

1. **Manually edit** the template JSON `columns` section
2. **Adjust X coordinates**: Use the logged table bbox to understand coordinate space
3. **Re-test**: Run with `--template` to validate your changes

Example manual adjustment:
```json
"columns": {
  "Date": [26.0, 78.0],        # Adjust these X-coordinates
  "Details": [78.0, 255.0],    # based on your PDF layout
  "Amount": [255.0, 434.0]
}
```

---

## Best Practices

### 1. Use a Representative Sample
- Choose a PDF with typical transaction data
- Ensure it has all the columns you expect
- Multiple transactions help column detection

### 2. Verify Before Production Use
- Always run validation mode (`--template`) before using in production
- Test with multiple PDF samples from the same bank
- Check edge cases (few transactions, multi-line descriptions)

### 3. Iterative Refinement
- Don't expect perfection on first run
- Use the iterative workflow (generate → test → adjust → re-test)
- Small coordinate adjustments can make a big difference

### 4. Document Your Templates
- Add comments to your template JSON files
- Note any bank-specific quirks or requirements
- Keep a test PDF alongside each template

---

## Limitations

### By Design
- **First page only for IBAN**: IBANs are only extracted from page 1 (prevents false positives from transaction descriptions)
- **Single table per page**: Uses the largest table found
- **No paid features**: Utility does not trigger any subscription-tier features

### Technical
- Requires clear table structure in PDF (not scanned images)
- Column detection works best with aligned text
- IBAN must be in standard format (ISO 13616)

---

## Examples

### Example 1: AIB Bank Statement
```bash
# Generate template
python -m src.commands.analyze_pdf input/aib_statement.pdf \
    --output custom_templates/aib.json

# Output shows:
# - IBAN: IE29****5678
# - 5 columns detected
# - Template saved

# Test template
python -m src.commands.analyze_pdf input/aib_statement.pdf \
    --template custom_templates/aib.json

# Extraction shows 45 transactions correctly parsed
```

### Example 2: Deutsche Bank Statement
```bash
# Generate template
python -m src.commands.analyze_pdf input/deutsche_statement.pdf \
    --output custom_templates/deutsche.json

# Column boundaries slightly off - manually adjust deutsche.json
# Change "Details" column from [80, 200] to [80, 220]

# Re-test
python -m src.commands.analyze_pdf input/deutsche_statement.pdf \
    --template custom_templates/deutsche.json

# Now extraction is correct!
```

---

## Support

For issues or questions:
1. Check the logs with `--log-level DEBUG`
2. Review the [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) for technical details
3. Open an issue on GitHub with:
   - Command used
   - Full log output
   - Sample PDF (if possible, or describe structure)

---

## Technical Notes

### Why First Page Only for IBAN?
- IBANs appear in statement headers (page 1)
- Transaction descriptions often contain IBAN-like patterns (false positives)
- This design choice improves accuracy significantly

### Why Direct Instantiation?
- The utility bypasses the normal factory pattern to avoid entitlement checks
- This ensures it works as a free utility without triggering subscription features
- Production processing uses the normal entitlement system

### Column Detection Algorithm
1. Extract all words from table region
2. Cluster X-coordinates (left edges) with tolerance
3. Detect gaps between clusters as column boundaries
4. Match header text to assign column names
5. Fall back to generic names if no headers found
