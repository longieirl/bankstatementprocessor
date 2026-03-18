# Bank Statement Templates

This directory contains bank-specific template configurations that define how to detect and extract transaction data from PDF bank statements.

## Overview

The template system is fully runtime-configurable. To add support for a new bank, simply create a JSON file in this directory - no code changes required!

## Quick Start

### Adding Built-in Templates

1. Create a new JSON file: `templates/mybank.json`
2. Copy the structure from `examples/custom_bank_template.json`
3. Configure detection patterns and column coordinates
4. Restart the application - your template will be auto-discovered

### Adding Custom Templates (Without Modifying Core)

For developers who want to add their own templates without touching the core codebase:

1. Create a custom templates directory:
   ```bash
   mkdir custom_templates
   ```

2. Create your template file: `custom_templates/mybank.json`

3. Set the environment variable:
   ```bash
   export CUSTOM_TEMPLATES_DIR=./custom_templates
   ```

4. Run the application - your custom template will be loaded with highest priority!

**See [Custom Template Guide](../docs/CUSTOM_TEMPLATES.md) for detailed instructions.**

## Template File Format

Each template is a JSON file with the following structure:

```json
{
  "id": "unique_bank_id",
  "name": "Human Readable Bank Name",
  "enabled": true,
  "detection": { ... },
  "extraction": { ... },
  "processing": { ... }
}
```

### Required Fields

#### `id` (string)
- Unique identifier for the bank template
- Use lowercase letters, numbers, hyphens, and underscores only
- Examples: `default`, `revolut`, `bank-of-ireland`, `my_custom_bank`

#### `name` (string)
- Human-readable bank name displayed in logs and output
- Examples: `"Default Bank Statement"`, `"Revolut"`, `"Bank of Ireland"`

#### `enabled` (boolean)
- Whether this template is active
- Set to `false` to disable without deleting the file

### Detection Configuration

The `detection` object defines how to identify if a PDF belongs to this bank:

```json
"detection": {
  "iban_patterns": ["[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}"],
  "filename_patterns": ["Statement_*.pdf"],
  "header_keywords": ["Bank Name"],
  "column_headers": ["Date", "Details", "Debit", "Credit", "Balance"]
}
```

#### Detection Strategy

The system uses a chain of 4 detectors (in order):

1. **IBAN Pattern Detector** - Matches IBAN prefixes
2. **Filename Pattern Detector** - Matches PDF filename patterns
3. **Header Keyword Detector** - Searches first page for bank keywords
4. **Column Header Detector** - Matches expected table column headers

**Best Practice**: Provide multiple detection methods for robustness. If one method fails, others can still identify the bank.

#### `iban_patterns` (list of regex strings)
- Regular expressions to match IBANs on the statement
- IBANs are extracted from the PDF text automatically
- **IBAN Structure**: 2-letter country code + 2 check digits + up to 30 alphanumeric characters
- **Generic Pattern** (matches all IBANs): `"[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}"`
- Use generic pattern unless you need to match specific bank codes
- Examples:
  - Any IBAN (recommended): `"[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}"`
  - Irish IBANs only: `"IE[0-9]{2}[A-Z0-9]{1,30}"`
  - Specific bank code: `"IE[0-9]{2}AIBK[A-Z0-9]*"`

#### `filename_patterns` (list of glob patterns, optional)
- Glob patterns to match PDF filenames
- **Optional**: If omitted or empty, filename detection is skipped for this template
- Only specify this if your bank has distinctive filename patterns
- Useful when you have statements from multiple banks with specific naming conventions
- Use wildcards (`*`) for variable parts
- Examples:
  - `"Statement_*.pdf"` - Matches `Statement_2024_01.pdf`
  - `"account-statement_*_en-ie_*.pdf"` - Matches Revolut format
  - Omit entirely if your bank doesn't have a consistent filename pattern (recommended for most cases)

#### `header_keywords` (list of strings, optional)
- Keywords expected in the PDF header/first page
- Case-sensitive matching
- Should be unique to this bank (avoid generic terms like "Statement")
- Optional: Can be omitted if IBAN or column headers provide sufficient detection
- Examples: `"Revolut"`, `"revolut.com"`, `"Bank of Ireland"`

#### `column_headers` (list of strings)
- Expected column names in the transaction table
- Used to verify correct table structure
- Examples:
  - Standard format: `["Date", "Details", "Debit", "Credit", "Balance"]`
  - Revolut: `["Date", "Description", "Money out", "Money in", "Balance"]`

### Extraction Configuration

The `extraction` object defines where transaction data is located on each page:

```json
"extraction": {
  "table_top_y": 300,
  "table_bottom_y": 720,
  "enable_header_check": true,
  "header_check_top_y": 250,
  "enable_page_validation": true,
  "columns": {
    "Date": [26, 78],
    "Details": [78, 255],
    "Debit €": [255, 313],
    "Credit €": [313, 369],
    "Balance €": [369, 434]
  }
}
```

#### `table_top_y` (number)
- Y-coordinate where the transaction table starts (in PDF points)
- Measured from bottom of page
- Exclude the header row with column names

#### `table_bottom_y` (number)
- Y-coordinate where the transaction table ends
- Measured from bottom of page
- Exclude footer information

#### `enable_header_check` (boolean, optional)
- Whether to verify column headers exist above table
- Default: `false`
- Useful for ensuring correct table detection

#### `header_check_top_y` (number, optional)
- Y-coordinate to search for column headers
- Only used if `enable_header_check` is `true`

#### `enable_page_validation` (boolean, optional)
- Whether to validate page structure before extraction
- Default: `true`
- Set to `false` for simpler statements

#### `columns` (object)
- Maps column names to X-coordinate ranges `[left, right]`
- Coordinates are in PDF points from left edge of page
- **Critical**: These must be accurate for correct extraction!

### Processing Configuration

The `processing` object defines how to parse extracted data:

```json
"processing": {
  "supports_multiline": false,
  "date_format": "%d/%m/%Y",
  "currency_symbol": "€",
  "decimal_separator": "."
}
```

#### `supports_multiline` (boolean)
- Whether transaction descriptions can span multiple lines
- `true` - Descriptions can wrap (e.g., Revolut)
- `false` - One transaction per line (standard format)

#### `date_format` (string)
- Python strftime format for parsing dates
- Examples:
  - `"%d/%m/%Y"` - `31/12/2024`
  - `"%d %b %Y"` - `31 Dec 2024`
  - `"%Y-%m-%d"` - `2024-12-31`

#### `currency_symbol` (string)
- Currency symbol used in amounts
- Examples: `"€"`, `"$"`, `"£"`

#### `decimal_separator` (string)
- Character separating whole and fractional amounts
- Usually `"."` or `","`

## Finding Column Coordinates

The most challenging part of creating a template is finding accurate column coordinates. Here's how:

### Method 1: Using PDF Debug Tools

1. Open the statement PDF in a PDF viewer with coordinate display
2. Hover over the left edge of each column to get X-coordinates
3. Record `[left_x, right_x]` for each column

### Method 2: Trial and Error

1. Start with approximate coordinates from visual inspection
2. Run extraction and examine output
3. Adjust coordinates if text is cut off or bleeding between columns
4. Iterate until extraction is clean

### Method 3: Using pdfplumber (Recommended)

```python
import pdfplumber

with pdfplumber.open("statement.pdf") as pdf:
    page = pdf.pages[0]

    # Extract all text with positions
    words = page.extract_words()

    # Find column headers
    headers = [w for w in words if w['top'] < 300]  # Adjust Y threshold

    # Print header positions
    for h in headers:
        print(f"{h['text']}: x0={h['x0']:.0f}, x1={h['x1']:.0f}")
```

### Coordinate Tips

- PDF coordinates start from **bottom-left** corner
- Y-coordinates increase upward
- X-coordinates increase rightward
- Add small margins (5-10 points) to avoid cutting text
- Test with multiple statement pages to verify consistency

## Step-by-Step Guide: Adding a New Bank

### Step 1: Gather Sample Statements

Collect 2-3 PDF statements from the bank to understand variations in format.

### Step 2: Analyze Structure

Open a statement and note:
- Bank name and unique identifiers
- Filename pattern
- IBAN prefix
- Column headers
- Date format
- Whether descriptions wrap across lines

### Step 3: Create Template File

```bash
# Create new template file
touch templates/mybank.json
```

### Step 4: Configure Detection

Start with the easiest detection method:

```json
{
  "id": "mybank",
  "name": "My Bank",
  "enabled": true,
  "detection": {
    "header_keywords": ["My Bank Name"],
    "iban_patterns": ["IE[0-9]{2}MYBK.*"],
    "filename_patterns": ["mybank-statement-*.pdf"],
    "column_headers": ["Date", "Description", "Amount", "Balance"]
  }
}
```

### Step 5: Find Column Coordinates

Use pdfplumber or trial-and-error to find coordinates:

```json
"extraction": {
  "table_top_y": 200,
  "table_bottom_y": 700,
  "columns": {
    "Date": [50, 120],
    "Description": [125, 350],
    "Amount": [355, 450],
    "Balance": [455, 550]
  }
}
```

### Step 6: Configure Processing

```json
"processing": {
  "supports_multiline": false,
  "date_format": "%d/%m/%Y",
  "currency_symbol": "€",
  "decimal_separator": "."
}
```

### Step 7: Test Your Template

```bash
# Place your template in templates/
cp mybank.json templates/

# Run extraction
python -m src.app

# Check logs for template loading
# Should see: "Loaded template: mybank from mybank.json"
```

### Step 8: Verify Extraction

Process a test PDF and verify:
- All transactions are extracted
- Dates parse correctly
- Amounts are accurate
- No text bleeding between columns
- Multi-line descriptions work (if applicable)

### Step 9: Refine Coordinates

If extraction is incorrect:
- Adjust `table_top_y` and `table_bottom_y` if rows are missed
- Adjust column ranges if text is cut off or bleeding
- Enable/disable `enable_header_check` if needed

## Environment Variables

### `BANK_TEMPLATES_DIR`

Override the default templates directory:

```bash
export BANK_TEMPLATES_DIR=/custom/templates
python -m src.app
```

Use cases:
- Maintain private templates separately from codebase
- Test new templates without affecting main config
- Deploy with custom template locations

### `DEFAULT_TEMPLATE`

Set the default template when detection fails:

```bash
export DEFAULT_TEMPLATE=revolut
python -m src.app
```

Without this variable, the first enabled template is used as default.

## Testing Your Template

### Unit Test (Optional)

```python
# tests/templates/test_mybank.py
from pathlib import Path
from src.templates.template_registry import TemplateRegistry

def test_mybank_template_loads():
    """Test MyBank template loads correctly."""
    registry = TemplateRegistry.from_directory("templates")
    mybank = registry.get_template("mybank")

    assert mybank is not None
    assert mybank.name == "My Bank"
    assert mybank.enabled is True
```

### Integration Test

```python
from src.detection.template_detector import TemplateDetector

def test_mybank_detection():
    """Test MyBank PDF is detected correctly."""
    registry = TemplateRegistry.from_directory("templates")
    detector = TemplateDetector(registry)

    # Use real PDF or mock
    template = detector.detect_template("test_data/mybank.pdf", first_page_text)
    assert template.id == "mybank"
```

### Manual Testing

```bash
# Test with sample PDF
python -m src.app
# Process a MyBank PDF
# Verify output CSV has correct transactions
```

## Troubleshooting

### Template Not Loading

**Symptom**: Template file exists but isn't detected

**Solutions**:
- Check JSON syntax (use `python -m json.tool templates/mybank.json`)
- Verify `id` field matches filename (without `.json`)
- Check file permissions (must be readable)
- Look for error messages in logs

### Detection Not Working

**Symptom**: PDFs not matched to your template

**Solutions**:
- Add more detection methods (IBAN, filename, keywords)
- Check detection patterns are unique to your bank
- Verify keywords are spelled exactly as in PDF
- Test IBAN regex with actual IBANs from statements

### Extraction Incomplete

**Symptom**: Missing transactions or corrupted data

**Solutions**:
- Verify `table_top_y` and `table_bottom_y` boundaries
- Check column coordinates don't overlap
- Enable debug logging to see extraction process
- Test with multiple statement pages

### Date Parsing Errors

**Symptom**: Invalid date format errors

**Solutions**:
- Verify `date_format` matches actual dates in PDF
- Check for locale-specific month names
- Try parsing a sample date manually to test format

### Amount Extraction Wrong

**Symptom**: Incorrect amounts or missing decimals

**Solutions**:
- Verify `decimal_separator` matches PDF format
- Check `currency_symbol` is correct
- Ensure column coordinates don't cut off digits
- Verify no thousands separators are interfering

## Best Practices

1. **Use Multiple Detection Methods** - Don't rely on just one pattern
2. **Test with Multiple Statements** - Formats can vary over time
3. **Be Specific with Patterns** - Avoid overly broad matches
4. **Add Margins to Coordinates** - 5-10 points buffer prevents text clipping
5. **Document Your Template** - Add comments (not in JSON, but separately)
6. **Version Control** - Keep template files in git
7. **Share with Community** - Consider contributing templates via PR

## Example Templates

See the `examples/` directory for annotated example templates:
- `custom_bank_template.json` - Fully commented example

## Contributing Templates

To share your template with the community:

1. Create a new template file in `templates/`
2. Test thoroughly with multiple statements
3. Remove any sensitive information
4. Submit a pull request with:
   - Template JSON file
   - Sample anonymized output (if possible)
   - Brief description of the bank

## Schema Validation (Optional)

For IDE autocomplete and validation, use `template_schema.json`:

```json
{
  "$schema": "./template_schema.json"
}
```

Add this line at the top of your template file to enable schema validation in VS Code and other editors.

## Support

If you encounter issues:
1. Check this README for troubleshooting tips
2. Review existing templates (default.json, revolut.json) as examples
3. Enable debug logging to see extraction details
4. Open an issue with template file and error logs

## Version History

- **v1.0** - Initial runtime-configurable template system
  - Support for individual template files
  - Environment variable configuration
  - Auto-discovery from templates directory
