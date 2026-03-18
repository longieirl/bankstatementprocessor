# Custom Template Guide

This guide explains how to add your own custom bank statement templates without modifying the core codebase.

## Quick Start

> **FREE Tier Note:** In the FREE tier, only templates with IBAN patterns can be used. Templates without IBAN patterns (e.g., generic fallback templates) will be automatically disabled and logged. This ensures that all processed PDFs have valid IBANs for proper transaction tracking.

1. Create a directory for your custom templates:
   ```bash
   mkdir custom_templates
   ```

2. Create a JSON file for your bank (e.g., `custom_templates/mybank.json`):
   ```json
   {
     "id": "mybank",
     "name": "My Bank",
     "enabled": true,
     "detection": {
       "iban_patterns": ["IE[0-9]{2}MYBK[0-9A-Z]+"],
       "header_keywords": ["My Bank", "mybank.com"],
       "column_headers": ["Date", "Description", "Amount", "Balance"]
     },
     "extraction": {
       "table_top_y": 250,
       "table_bottom_y": 750,
       "columns": {
         "Date": [30, 100],
         "Details": [100, 300],
         "Debit €": [300, 380],
         "Credit €": [380, 460],
         "Balance €": [460, 540]
       }
     },
     "processing": {
       "supports_multiline": false,
       "date_format": "%d/%m/%Y",
       "currency_symbol": "€",
       "decimal_separator": "."
     }
   }
   ```

3. Set the environment variable to point to your custom templates:
   ```bash
   export CUSTOM_TEMPLATES_DIR=./custom_templates
   ```

4. Run the processor:
   ```bash
   python -m src.app
   ```

Your custom template will be loaded and used for detection alongside the built-in templates.

## Template Priority

Templates are loaded in the following priority order:

1. **Custom templates** (from `CUSTOM_TEMPLATES_DIR`) - Highest priority
2. **Built-in templates** (from `BANK_TEMPLATES_DIR` or `./templates`)
3. **Default template** - Fallback for unrecognized statements

If a custom template has the same ID as a built-in template, the custom version will override the built-in one.

## Template Structure

### Required Fields

Every template must have these fields:

```json
{
  "id": "unique_identifier",           // Lowercase, alphanumeric, hyphens, underscores
  "name": "Human Readable Name",       // Display name
  "enabled": true,                     // Whether template is active
  "detection": { ... },                // How to detect this bank's PDFs
  "extraction": { ... },               // How to extract transactions
  "processing": { ... }                // How to process the data
}
```

### Detection Configuration

Detection determines which PDFs match this template. The system tries detection methods in order:

1. **IBAN Pattern** (highest priority)
2. **Filename Pattern**
3. **Header Keywords**
4. **Column Headers** (fallback)

```json
"detection": {
  "iban_patterns": [
    "IE[0-9]{2}MYBK[0-9A-Z]+"         // Regex pattern for your bank's IBANs
  ],
  "filename_patterns": [
    "MyBank_Statement_*.pdf",          // Glob patterns for filenames
    "statement_mybank_*.pdf"
  ],
  "header_keywords": [
    "My Bank",                         // Keywords in the PDF header
    "mybank.com"
  ],
  "column_headers": [
    "Date",                            // Expected column headers
    "Description",
    "Amount",
    "Balance"
  ]
}
```

**Best Practices:**
- Use **specific IBAN patterns** (include bank code) to avoid false positives
- **FREE Tier:** MUST include at least one IBAN pattern (empty array will disable template)
- **PAID Tier:** Can use empty `[]` for generic/fallback templates without IBAN requirement
- Include multiple variations in `header_keywords` (with/without spaces, abbreviations)
- Match at least 70% of `column_headers` for detection to succeed

### Extraction Configuration

Extraction defines where to find transaction data on the PDF pages.

```json
"extraction": {
  "table_top_y": 250,                  // Y-coordinate where table starts (from top)
  "table_bottom_y": 750,               // Y-coordinate where table ends
  "enable_page_validation": true,      // Validate page structure before extraction
  "enable_header_check": true,         // Check for header row presence
  "header_check_top_y": 200,           // Y-coordinate to check for headers
  "columns": {
    "Date": [30, 100],                 // [x_start, x_end] coordinates
    "Details": [100, 300],
    "Debit €": [300, 380],
    "Credit €": [380, 460],
    "Balance €": [460, 540]
  }
}
```

**Finding Coordinates:**

Use the included coordinate finder tool:

```bash
python -m src.tools.coordinate_finder input/your_statement.pdf
```

This will display the PDF with coordinates overlaid, helping you determine:
- Table boundaries (`table_top_y`, `table_bottom_y`)
- Column boundaries (`columns` x-coordinates)

**Coordinate System:**
- Origin (0, 0) is at the **top-left** of the page
- X increases to the right
- Y increases downward
- Typical A4 page: 595 points wide × 842 points tall

### Processing Configuration

Processing controls how extracted data is interpreted.

```json
"processing": {
  "supports_multiline": false,         // Whether transactions can span multiple rows
  "date_format": "%d/%m/%Y",           // Python strftime format
  "currency_symbol": "€",              // Currency symbol to expect
  "decimal_separator": "."             // Decimal separator (. or ,)
}
```

**Date Format Examples:**
- `"%d/%m/%Y"` → 31/12/2025
- `"%d %b %Y"` → 31 Dec 2025
- `"%Y-%m-%d"` → 2025-12-31
- `"%d-%m-%Y"` → 31-12-2025

**Multiline Support:**
- Set `supports_multiline: true` for banks that split long transaction descriptions across multiple rows
- Set `supports_multiline: false` for standard single-row transactions

## Environment Variables

### CUSTOM_TEMPLATES_DIR

Path to directory containing your custom templates.

```bash
# Relative path
export CUSTOM_TEMPLATES_DIR=./custom_templates

# Absolute path
export CUSTOM_TEMPLATES_DIR=/path/to/my/templates

# Multiple users can have their own custom directories
export CUSTOM_TEMPLATES_DIR=$HOME/.bankstatements/templates
```

### BANK_TEMPLATES_DIR

Override the built-in templates directory (advanced use).

```bash
export BANK_TEMPLATES_DIR=./templates
```

### DEFAULT_TEMPLATE

Force a specific template as the default fallback.

```bash
export DEFAULT_TEMPLATE=mybank
```

## Examples

### Example 1: Simple Bank Statement

For a bank with standard format:

```json
{
  "id": "simplebank",
  "name": "Simple Bank",
  "enabled": true,
  "detection": {
    "iban_patterns": ["IE[0-9]{2}SMPL[0-9]+"],
    "header_keywords": ["Simple Bank"],
    "column_headers": ["Date", "Description", "Debit", "Credit", "Balance"]
  },
  "extraction": {
    "table_top_y": 300,
    "table_bottom_y": 720,
    "columns": {
      "Date": [26, 78],
      "Details": [78, 255],
      "Debit €": [255, 313],
      "Credit €": [313, 369],
      "Balance €": [369, 434]
    }
  },
  "processing": {
    "supports_multiline": false,
    "date_format": "%d/%m/%Y",
    "currency_symbol": "€",
    "decimal_separator": "."
  }
}
```

### Example 2: Multiline Transaction Support

For a bank like Revolut with multiline transactions:

```json
{
  "id": "multibank",
  "name": "Multi Bank",
  "enabled": true,
  "detection": {
    "iban_patterns": ["[A-Z]{2}[0-9]{2}MULT[0-9A-Z]+"],
    "header_keywords": ["Multi Bank", "multibank.io"],
    "column_headers": ["Date", "Description", "Out", "In", "Balance"]
  },
  "extraction": {
    "table_top_y": 140,
    "table_bottom_y": 735,
    "enable_page_validation": false,
    "columns": {
      "Date": [42, 120],
      "Details": [124, 330],
      "Debit €": [335, 416],
      "Credit €": [417, 525],
      "Balance €": [526, 556]
    }
  },
  "processing": {
    "supports_multiline": true,
    "date_format": "%d %b %Y",
    "currency_symbol": "€",
    "decimal_separator": "."
  }
}
```

### Example 3: Generic Fallback Template

For catching any unrecognized statement format:

```json
{
  "id": "generic",
  "name": "Generic Bank Statement",
  "enabled": true,
  "detection": {
    "iban_patterns": [],                    // No IBAN pattern (fallback only)
    "column_headers": ["Date", "Details", "Amount", "Balance"]
  },
  "extraction": {
    "table_top_y": 250,
    "table_bottom_y": 750,
    "columns": {
      "Date": [30, 100],
      "Details": [100, 350],
      "Debit €": [350, 420],
      "Credit €": [420, 490],
      "Balance €": [490, 560]
    }
  },
  "processing": {
    "supports_multiline": false,
    "date_format": "%d/%m/%Y",
    "currency_symbol": "€",
    "decimal_separator": "."
  }
}
```

## Testing Your Template

### Step 1: Validate JSON Syntax

```bash
# Use jq to validate JSON
jq . custom_templates/mybank.json
```

### Step 2: Test Template Loading

```bash
export CUSTOM_TEMPLATES_DIR=./custom_templates
python -c "from src.templates import TemplateRegistry; r = TemplateRegistry.from_default_config(); print(r.list_all())"
```

### Step 3: Test Detection

```bash
export CUSTOM_TEMPLATES_DIR=./custom_templates
python -m src.app
```

Check the logs for:
```
Loaded template: mybank from mybank.json
Template detected by IBAN: My Bank for statement.pdf
```

### Step 4: Verify Extraction

Check the output CSV files to ensure:
- All transactions are extracted
- Dates are parsed correctly
- Amounts are in correct columns
- No missing data

### Step 5: Compare Coordinates

If extraction is incorrect:

1. Use the coordinate finder:
   ```bash
   python -m src.tools.coordinate_finder input/statement.pdf
   ```

2. Adjust coordinates in your template

3. Test again

## Troubleshooting

### Template Disabled in FREE Tier

**Problem**: Template is ignored with message "no IBAN patterns configured".

**Cause**: FREE tier requires all templates to have IBAN patterns for proper transaction tracking.

**Solutions**:
1. Add IBAN pattern to your template's `detection.iban_patterns` array
2. Use bank-specific pattern (e.g., `"IE[0-9]{2}MYBK[0-9A-Z]+"`)
3. If you need generic templates without IBAN, upgrade to PAID tier
4. Check logs for specific template names that were disabled

**Example Log Message:**
```
WARNING - FREE tier requires IBAN patterns for PDF processing.
Ignoring 1 template(s) without IBAN patterns: Default Bank Statement
INFO - Template 'Default Bank Statement' (id: default) disabled: no IBAN patterns configured
```

### Template Not Detected

**Problem**: Your template isn't being used for your PDFs.

**Solutions**:
1. Check IBAN pattern matches your PDF's IBAN
2. Ensure header keywords appear in top 250 points of page
3. Verify at least 70% of column headers match
4. Check template is `"enabled": true`
5. Review logs for detection attempts
6. **FREE Tier**: Verify template has IBAN patterns configured

### Missing Transactions

**Problem**: Some transactions are not extracted.

**Solutions**:
1. Verify `table_top_y` is above first transaction
2. Ensure `table_bottom_y` is below last transaction
3. Check if bank uses multiline format (`supports_multiline: true`)
4. Use coordinate finder to verify boundaries

### Wrong Column Data

**Problem**: Transaction details appear in wrong columns.

**Solutions**:
1. Use coordinate finder to get exact column boundaries
2. Ensure column x-coordinates don't overlap
3. Check for extra spaces or padding in PDF

### Date Parsing Errors

**Problem**: Dates are not recognized or parsed incorrectly.

**Solutions**:
1. Verify `date_format` matches your bank's format
2. Check for locale-specific date formats
3. Look at raw extracted text in debug logs
4. Try different format strings

### Override Not Working

**Problem**: Custom template doesn't override built-in template.

**Solutions**:
1. Ensure custom template has same `"id"` as built-in template
2. Verify `CUSTOM_TEMPLATES_DIR` is set correctly
3. Check custom template loads first (check logs)
4. Confirm template is valid JSON

## Docker Usage

To use custom templates with Docker:

1. Create custom templates directory on host:
   ```bash
   mkdir custom_templates
   ```

2. Mount custom templates and set environment variable in docker-compose.yml:
   ```yaml
   services:
     bank-statement-processor:
       volumes:
         - ./input:/app/input
         - ./output:/app/output
         - ./custom_templates:/app/custom_templates  # Mount custom templates
       environment:
         - CUSTOM_TEMPLATES_DIR=/app/custom_templates  # Point to mounted dir
   ```

3. Run Docker:
   ```bash
   docker-compose up
   ```

## Contributing Your Template

If you create a template for a popular bank, consider contributing it to the main repository:

1. Test your template thoroughly with multiple statement PDFs
2. Remove any personal information (IBANs, account numbers, etc.)
3. Add example detection patterns (sanitized)
4. Submit a pull request to add your template to `templates/`
5. Include sample PDF structure description in PR

## Security Considerations

### Sensitive Data

- **Never commit** custom templates containing real IBANs or account numbers
- Use generic patterns in templates (e.g., `"IE[0-9]{2}MYBK.*"` not your actual IBAN)
- Add `custom_templates/` to `.gitignore` if it contains sensitive patterns

### Private Templates

If your custom templates contain proprietary information:
- Keep them in a private directory outside the repository
- Use absolute paths for `CUSTOM_TEMPLATES_DIR`
- Don't share templates publicly

## Best Practices

1. **Start with built-in templates** as reference
2. **Test incrementally** - start with detection, then extraction, then processing
3. **Use specific patterns** - avoid overly generic IBAN/filename patterns
4. **Document your coordinates** - add comments to your JSON (they'll be ignored)
5. **Version control** - keep custom templates in a separate git repository
6. **Backup regularly** - custom templates are valuable for your workflow

## Support

For help with custom templates:
- Review built-in templates in `templates/` directory
- Check logs for detection/extraction errors
- Use coordinate finder tool for troubleshooting
- Open an issue with sanitized template and error description

## Related Documentation

- [Template Detection System](templates/README.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Configuration Guide](CONFIGURATION.md)
