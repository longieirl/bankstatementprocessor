# Quick Guide: Adding New Bank Statement Templates

## 5-Minute Quick Start

### Step 1: Create Template File

```bash
# Option A: Built-in template (committed to repo)
touch templates/yourbank.json

# Option B: Custom template (user-specific)
mkdir -p custom_templates
touch custom_templates/yourbank.json
```

### Step 2: Copy Template Skeleton

```json
{
  "id": "yourbank",
  "name": "Your Bank Statement",
  "enabled": true,
  "document_type": "bank_statement",
  "detection": {
    "iban_patterns": ["XX[0-9]{2}YOUR.*"],
    "header_keywords": ["Your Bank Name"],
    "column_headers": ["Date", "Description", "Amount"]
  },
  "extraction": {
    "table_top_y": 300,
    "table_bottom_y": 720,
    "columns": {
      "Date": [26, 78],
      "Details": [78, 255],
      "Debit €": [255, 313],
      "Credit €": [313, 369],
      "Balance €": [369, 450]
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

### Step 3: Calibrate Column Boundaries

```bash
# Extract coordinates from sample PDF
python
>>> import pdfplumber
>>> pdf = pdfplumber.open("sample.pdf")
>>> page = pdf.pages[0]
>>> words = page.extract_words()
>>> for w in words[:10]:  # Check first 10 words
...     print(f"{w['text']:20} X: {w['x0']:.1f}-{w['x1']:.1f}")
```

Update column boundaries in template:
```json
"columns": {
  "Date": [x0, x1],      // From coordinate analysis
  "Details": [x0, x1],
  ...
}
```

### Step 4: Test Template

```bash
# Test detection and extraction
python -m src.commands.test_template \
    --template yourbank \
    --pdf samples/yourbank_sample.pdf \
    --verbose

# Process actual PDF
python -m src.app --input-dir input --output-dir output
```

---

## Detection Methods (Choose What Works Best)

### Option 1: IBAN Pattern (BEST - Most Specific)

**Use when**: Bank has unique IBAN prefix

```json
"detection": {
  "iban_patterns": [
    "IE[0-9]{2}AIBK",              // AIB Ireland
    "GB[0-9]{2}BARC[0-9A-Z]{4}",   // Barclays UK
    "[A-Z]{2}[0-9]{2}REVO[0-9A-Z]+" // Revolut (any country)
  ]
}
```

**IBAN Structure**: `CCNN BBBB AAAA AAAA AAAA AA`
- CC = Country code (2 letters)
- NN = Check digits (2 numbers)
- BBBB = Bank code (4 chars, **use this for matching**)
- Rest = Account-specific

**Examples**:
- AIB Ireland: `IE48 AIBK 9340 8921 4590 15` → Pattern: `IE[0-9]{2}AIBK`
- Revolut: `GB48 REVO 0099 6984 1704 26` → Pattern: `[A-Z]{2}[0-9]{2}REVO`

### Option 2: Filename Pattern (GOOD - Easy to Implement)

**Use when**: Bank uses consistent filename format

```json
"detection": {
  "filename_patterns": [
    "Statement JL CA *.pdf",        // AIB specific format
    "*yourbank*statement*.pdf",     // Generic with bank name
    "eStatement_[0-9]{8}.pdf"       // Date-based format
  ]
}
```

**Glob Syntax**:
- `*` = Match any characters
- `?` = Match single character
- `[0-9]` = Match any digit
- `[a-z]` = Match any lowercase letter

### Option 3: Header Keywords (OK - Less Specific)

**Use when**: Bank name appears in header

```json
"detection": {
  "header_keywords": [
    "Allied Irish Banks",           // Full bank name
    "Personal Bank Account",        // Account type
    "Statement of Account with"     // Document title phrase
  ]
}
```

**Tips**:
- Use full names, not abbreviations
- Include distinctive phrases unique to bank
- Detector searches top 30% of first page

### Option 4: Column Headers (FALLBACK)

**Use when**: No other method available

```json
"detection": {
  "column_headers": [
    "Date",
    "Transaction Details",
    "Debit",
    "Credit",
    "Balance"
  ]
}
```

**Note**: Requires 70% match (e.g., 4 out of 5 columns)

---

## Column Boundary Calibration

### Method 1: pdfplumber Interactive

```python
import pdfplumber

pdf = pdfplumber.open("sample.pdf")
page = pdf.pages[0]

# Show all words with coordinates
words = page.extract_words()
for w in words:
    print(f"{w['text']:30} X: {w['x0']:6.1f} - {w['x1']:6.1f}  Y: {w['top']:6.1f}")

# Focus on transaction area
transaction_words = [w for w in words if 300 < w['top'] < 720]
for w in transaction_words[:20]:  # First 20 words
    print(f"{w['text']:30} X: {w['x0']:6.1f} - {w['x1']:6.1f}")
```

### Method 2: Visual Mapping

```
Example PDF layout:

X=26      X=78          X=255       X=313       X=369       X=450
|         |             |           |           |           |
Date      Details       Debit €     Credit €    Balance €
01 Jan    ATM Withdrawal 50.00                  1,450.23
02 Jan    Salary                    2,500.00    3,950.23
```

Template columns:
```json
"columns": {
  "Date": [26, 78],         // Start=26, End=78
  "Details": [78, 255],     // Start=78, End=255
  "Debit €": [255, 313],
  "Credit €": [313, 369],
  "Balance €": [369, 450]
}
```

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Overlapping columns** | Data in wrong column | Add gap between columns: `[26,78]` then `[80,255]` (not `[78,255]`) |
| **Truncated text** | Missing last characters | Extend end boundary: `[78,255]` → `[78,260]` |
| **Missing column data** | Empty column values | Check if boundary includes data: add buffer ±2 points |

---

## Table Boundaries

### Finding Top/Bottom Y Coordinates

```python
import pdfplumber

pdf = pdfplumber.open("sample.pdf")
page = pdf.pages[0]

# Show all words with Y coordinates
words = page.extract_words()
for w in words:
    if 'date' in w['text'].lower() or 'transaction' in w['text'].lower():
        print(f"{w['text']:30} Y: {w['top']:6.1f}")  # Table header area

# Find first transaction
for w in words:
    if w['text'].isdigit() and len(w['text']) == 2:  # Likely a day number
        print(f"First transaction likely starts around Y={w['top']:.1f}")
        break
```

### Template Configuration

```json
"extraction": {
  "table_top_y": 300,      // Start extraction here (after headers)
  "table_bottom_y": 720    // Stop extraction here (before footer)
}
```

**Tips**:
- Set `table_top_y` just below column headers
- Set `table_bottom_y` just above page footer
- Standard A4 page height: ~842 points
- Leave buffer: Don't use exact values (e.g., use 720 not 730 if footer at 725)

---

## Date Formats

### Common Formats

| Format | Example | Python Format String |
|--------|---------|---------------------|
| DD/MM/YYYY | 01/01/2024 | `"%d/%m/%Y"` |
| DD MMM YYYY | 01 Jan 2024 | `"%d %b %Y"` |
| DD MMMM YYYY | 01 January 2024 | `"%d %B %Y"` |
| MM/DD/YYYY | 01/01/2024 (US) | `"%m/%d/%Y"` |
| YYYY-MM-DD | 2024-01-01 (ISO) | `"%Y-%m-%d"` |
| DD.MM.YYYY | 01.01.2024 (EU) | `"%d.%m.%Y"` |

### Testing Date Format

```python
from datetime import datetime

# Test your format
date_str = "01 Jan 2024"
format_str = "%d %b %Y"

try:
    dt = datetime.strptime(date_str, format_str)
    print(f"✅ Success: {dt}")
except ValueError as e:
    print(f"❌ Failed: {e}")
```

---

## Special Cases

### Multi-Page Layouts (Different Boundaries per Page)

**Example**: Revolut has summary on page 1, transactions on page 2+

```json
{
  "extraction": {
    "table_top_y": 140,              // Default for all pages
    "table_bottom_y": 735,
    "per_page_overrides": {
      "1": {
        "table_top_y": 490           // Page 1 starts lower
      }
    }
  }
}
```

### Multi-Line Transactions

**Example**: Transaction spans 2-3 lines

```
01 Jan  Company Name Ltd
        Invoice INV-12345
        Payment Reference
```

**Solution**:
```json
"processing": {
  "supports_multiline": true
}
```

### Credit Card Statements (No IBAN)

```json
{
  "id": "yourbank_credit_card",
  "document_type": "credit_card_statement",
  "detection": {
    "document_identifiers": {
      "card_number_patterns": ["\\*{4}\\s*\\*{4}\\s*\\*{4}\\s*[0-9]{4}"]
    },
    "header_keywords": ["Credit Card Statement"],
    "exclude_keywords": ["IBAN", "Bank Account"],  // Reject bank statements
    "filename_patterns": ["*credit*card*.pdf"]
  }
}
```

---

## Testing & Validation

### Step 1: Template Structure Validation

```bash
# Template loads without errors
python -c "
from src.templates.template_registry import TemplateRegistry
registry = TemplateRegistry.from_default_config()
template = registry.get_template('yourbank')
print(f'✅ Template loaded: {template.name}')
"
```

### Step 2: Detection Test

```bash
# Verify correct template detected
python -m src.commands.test_template \
    --template yourbank \
    --pdf sample.pdf
# Expected: ✅ PASS: Template correctly detected
```

### Step 3: Extraction Test

```bash
# Check extracted transactions
python -m src.commands.test_template \
    --template yourbank \
    --pdf sample.pdf \
    --verbose
# Expected: ✅ PASS: Extracted N transactions
```

### Step 4: Full Processing Test

```bash
# Process actual PDF
mkdir -p input output
cp sample.pdf input/
python -m src.app --input-dir input --output-dir output
# Check output/transactions.csv
```

---

## Troubleshooting

### "Wrong template detected"

**Cause**: Another template matched first
**Solution**: Make your detection more specific
- Use IBAN pattern (highest priority)
- Add more header keywords
- Make filename pattern more specific

### "No transactions extracted"

**Cause**: Table boundaries incorrect
**Solution**:
```bash
# Check where transactions are
python -c "
import pdfplumber
pdf = pdfplumber.open('sample.pdf')
words = pdf.pages[0].extract_words()
for w in words:
    print(f'{w[\"text\"]:20} Y: {w[\"top\"]:.1f}')
"
# Adjust table_top_y and table_bottom_y
```

### "Data in wrong columns"

**Cause**: Column boundaries overlapping or incorrect
**Solution**:
```bash
# Check X coordinates
python -c "
import pdfplumber
pdf = pdfplumber.open('sample.pdf')
words = pdf.pages[0].extract_words()
for w in words:
    print(f'{w[\"text\"]:30} X: {w[\"x0\"]:6.1f} - {w[\"x1\"]:6.1f}')
"
# Adjust column boundaries
```

### "Date parsing fails"

**Cause**: Wrong date_format string
**Solution**:
```python
from datetime import datetime
# Extract actual date from PDF
date_str = "01 Jan 2024"  # From PDF
# Test formats
for fmt in ["%d/%m/%Y", "%d %b %Y", "%d %B %Y"]:
    try:
        dt = datetime.strptime(date_str, fmt)
        print(f"✅ {fmt} works")
        break
    except:
        print(f"❌ {fmt} failed")
```

---

## Checklist

Before submitting template:

- [ ] Template file created in `templates/` or `custom_templates/`
- [ ] Unique `id` (no spaces, lowercase, alphanumeric + underscore)
- [ ] Descriptive `name`
- [ ] At least one detection method (IBAN preferred)
- [ ] Column boundaries calibrated with sample PDF
- [ ] Table boundaries set (top/bottom Y)
- [ ] Date format matches PDF data
- [ ] Currency symbol correct
- [ ] Tested with `test_template` command
- [ ] Extracted transactions verified
- [ ] No warnings about column overlaps
- [ ] Full processing test passed

---

## Examples

### Simple Bank Template
```json
{
  "id": "simple_bank",
  "name": "Simple Bank Statement",
  "enabled": true,
  "detection": {
    "iban_patterns": ["XX[0-9]{2}SIMP.*"],
    "header_keywords": ["Simple Bank"]
  },
  "extraction": {
    "table_top_y": 300,
    "table_bottom_y": 720,
    "columns": {
      "Date": [26, 78],
      "Details": [78, 350],
      "Amount": [350, 450]
    }
  },
  "processing": {
    "date_format": "%d/%m/%Y",
    "currency_symbol": "€"
  }
}
```

### Complex Template (Multiple Detection Methods)
```json
{
  "id": "complex_bank",
  "name": "Complex Bank Statement",
  "enabled": true,
  "detection": {
    "iban_patterns": ["XX[0-9]{2}CPLX.*", "XX[0-9]{2}CMPX.*"],
    "filename_patterns": ["*complex*statement*.pdf", "Statement_Complex_*.pdf"],
    "header_keywords": ["Complex Bank", "Complex Banking Group"],
    "column_headers": ["Date", "Transaction", "Debit", "Credit", "Balance"]
  },
  "extraction": {
    "table_top_y": 300,
    "table_bottom_y": 720,
    "enable_page_validation": true,
    "enable_header_check": true,
    "columns": {
      "Date": [26, 78],
      "Details": [78, 255],
      "Debit €": [255, 313],
      "Credit €": [313, 369],
      "Balance €": [369, 450]
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

---

## Need Help?

1. **Read full documentation**: `docs/TEMPLATE_EXTENSIBILITY_PLAN.md`
2. **Check existing templates**: Browse `templates/*.json` for examples
3. **Test with samples**: Use `test_template` command
4. **Report issues**: Create GitHub issue with sample PDF (redacted)

---

## Quick Reference: Template Fields

| Field | Required | Default | Purpose |
|-------|----------|---------|---------|
| `id` | ✅ Yes | - | Unique identifier |
| `name` | ✅ Yes | - | Display name |
| `enabled` | No | true | Enable/disable template |
| `document_type` | No | bank_statement | Document classification |
| `detection.iban_patterns` | No | [] | IBAN regex patterns |
| `detection.filename_patterns` | No | [] | Filename glob patterns |
| `detection.header_keywords` | No | [] | Header keywords |
| `detection.column_headers` | No | [] | Expected column names |
| `detection.exclude_keywords` | No | [] | Keywords to reject |
| `extraction.table_top_y` | ✅ Yes | - | Top Y boundary |
| `extraction.table_bottom_y` | ✅ Yes | - | Bottom Y boundary |
| `extraction.columns` | ✅ Yes | - | Column definitions |
| `extraction.per_page_overrides` | No | {} | Page-specific overrides |
| `processing.supports_multiline` | No | false | Merge multi-line rows |
| `processing.date_format` | No | %d/%m/%Y | Date parsing format |
| `processing.currency_symbol` | No | € | Currency symbol |
| `processing.decimal_separator` | No | . | Decimal separator |

---

**Last Updated**: 2026-02-19
**Version**: 1.0.1
