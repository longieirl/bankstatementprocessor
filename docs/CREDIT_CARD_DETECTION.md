# Credit Card Statement Detection

## Overview

The bank statement processor now automatically detects and skips credit card statements, as they have a different structure from bank account statements and are not currently supported.

## How It Works

### Detection Logic

The system checks the **first page** of each PDF for the presence of any credit card indicators (case-insensitive). Detection patterns include:

- **Card Number** - Standard credit card identifier
- **Credit Limit** - Indicates credit card account
- **Credit Card** - Explicit credit card text
- **Visa** - Visa card indicator
- **Mastercard** - Mastercard indicator

If **any** of these patterns are found:

1. **Logs a warning** that the file is a credit card statement
2. **Skips the entire PDF** - no processing attempted
3. **Continues to the next PDF** - processing continues normally

### Example Detection

**Credit Card Statement** (will be skipped):
```
Credit Card Statement
Account Holder: John Doe
Card Number: **** **** **** 1234
Statement Period: January 2024
```

**Bank Statement** (will be processed):
```
Bank Statement
Account Holder: John Doe
IBAN: IE29 AIBK 9311 5212 3456 78
Statement Period: January 2024
```

## Log Output

When a credit card statement is detected, you'll see:

```
WARNING - Credit card statement detected in credit_card_statement.pdf. Credit card statements are not currently supported. Skipping file.
INFO - PDF 2 (credit_card_statement.pdf) excluded: Credit card statement detected
```

### Excluded Files JSON

All excluded files are automatically logged to `excluded_files.json` in the output directory. This provides an audit trail of all skipped files with timestamps and reasons.

See [Excluded Files Logging](EXCLUDED_FILES_LOGGING.md) for more details.

## Behavior

### What Gets Skipped
- The entire PDF file is skipped
- No transactions are extracted
- No output files are generated for that PDF
- Processing continues with the next PDF in the directory

### What Doesn't Get Affected
- Other PDFs in the same batch continue to process normally
- IBAN extraction still happens for bank statements
- File grouping still works as expected

## Technical Details

### Detection Patterns
```python
# Case-insensitive search for multiple patterns
credit_card_patterns = [
    r"card\s+number",   # Card Number
    r"credit\s+limit",  # Credit Limit
    r"credit\s+card",   # Credit Card
    r"\bvisa\b",        # Visa (word boundary)
    r"\bmastercard\b",  # Mastercard (word boundary)
]
```

### Variations Detected
All case variations and patterns are detected:
- `Card Number`, `CARD NUMBER`, `card number`
- `Credit Limit`, `CREDIT LIMIT`, `credit limit`
- `Credit Card`, `CREDIT CARD`, `credit card`
- `Visa`, `VISA`, `visa`
- `Mastercard`, `MASTERCARD`, `mastercard`

### Detection Scope
- Only the **first page** is checked
- If "Card Number" appears on page 2 or later, it's ignored
- This prevents false positives in appendices or footnotes

## Testing

Run the credit card detection tests:
```bash
pytest tests/test_credit_card_detection.py -v
```

Test coverage:
- ✅ Detection with "Card Number" present
- ✅ Detection with "Credit Limit" present
- ✅ Detection with "Credit Card" text
- ✅ Detection with "Visa" keyword
- ✅ Detection with "Mastercard" keyword
- ✅ All patterns tested individually
- ✅ Case-insensitive matching
- ✅ False positive prevention (normal bank statements)
- ✅ Error handling during detection
- ✅ Only checks first page
- ✅ Direct method testing

**Total**: 12 comprehensive tests covering all detection patterns

## Example Usage

### Processing Multiple PDFs

```bash
input/
├── bank_statement_jan.pdf     # ✅ Processed
├── credit_card_jan.pdf         # ⏭️ Skipped (has "Card Number")
├── bank_statement_feb.pdf      # ✅ Processed
└── credit_card_feb.pdf         # ⏭️ Skipped (has "Card Number")
```

**Result**: Only the 2 bank statements are processed. Credit card statements are logged and skipped.

### Log Output Example

```
INFO - Processing PDF 1 of 4
INFO - IBAN found on page 1: IE29****5678
INFO - Processing 150 transactions for IBAN suffix: 5678

INFO - Processing PDF 2 of 4
WARNING - Credit card statement detected in credit_card_jan.pdf. Credit card statements are not currently supported. Skipping file.

INFO - Processing PDF 3 of 4
INFO - IBAN found on page 1: IE29****5678
INFO - Processing 100 transactions for IBAN suffix: 5678

INFO - Processing PDF 4 of 4
WARNING - Credit card statement detected in credit_card_feb.pdf. Credit card statements are not currently supported. Skipping file.
```

## Future Enhancements

Potential improvements (not currently implemented):
- [ ] Support for credit card statement processing
- [ ] Additional detection patterns (e.g., "Credit Card", "Cardholder")
- [ ] Separate output directory for skipped files
- [ ] Summary report of skipped files

## API Changes

### PDFTableExtractor

**New Method**:
```python
def _is_credit_card_statement(self, page: Any) -> bool:
    """
    Check if a PDF page contains credit card statement indicators.

    Returns:
        True if credit card statement detected, False otherwise
    """
```

**Modified Method**:
```python
def extract(self, pdf_path: Path) -> Tuple[List[dict], int, Optional[str]]:
    """
    Extract table data from PDF file.

    Now includes credit card detection on first page.
    Returns empty results if credit card statement detected.
    """
```

## Troubleshooting

### Q: My credit card statement wasn't detected
**A**: Check if the first page contains "Card Number" text. If the text is in an image or uses different terminology, it won't be detected.

### Q: My bank statement was incorrectly flagged as a credit card
**A**: Check the first page for "Card Number" text. If it appears (e.g., in a footnote), it will trigger detection. This is rare but possible.

### Q: Can I disable this feature?
**A**: Currently there's no flag to disable it, but you can modify the code or remove credit card PDFs from the input directory before processing.

## Related Documentation

- [Excluded Files Logging](EXCLUDED_FILES_LOGGING.md)
- [IBAN Extraction](IBAN_EXTRACTION.md)
- [IBAN-Based File Grouping](IBAN_FILENAME_GROUPING.md)
- [Output Formats Guide](OUTPUT_FORMATS_USAGE.md)

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Feature Status**: ✅ Production Ready
