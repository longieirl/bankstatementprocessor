# Excluded Files Logging

## Overview

The bank statement processor automatically logs all files that could not be processed to a JSON file. This provides transparency and audit trail for files that were skipped during processing.

## How It Works

### Exclusion Logic

A PDF is only excluded and logged if:

1. **No IBAN found** - The PDF does not contain a valid IBAN (likely a credit card statement)
2. **No data extracted** - No transaction rows could be extracted
3. **Has pages** - The PDF is not empty (has at least 1 page)

**Key Rule**: If a PDF has an IBAN, it is assumed to be a bank statement and will be processed (even if no transactions are extracted). Only PDFs without IBANs are excluded.

### Automatic Logging

When a PDF cannot be processed, the processor:

1. **Logs the exclusion** with detailed metadata
2. **Continues processing** other PDFs in the batch
3. **Writes a JSON file** with all excluded files at the end

### Excluded Files JSON

The `excluded_files.json` file is created in the output directory and contains:

```json
{
  "summary": {
    "total_excluded": 2,
    "generated_at": "2026-01-29T10:30:45.123456",
    "note": "Files excluded from processing due to missing IBAN or no extractable data"
  },
  "excluded_files": [
    {
      "filename": "credit_card_jan.pdf",
      "path": "/path/to/input/credit_card_jan.pdf",
      "reason": "Could not be processed - no IBAN found (likely credit card statement)",
      "timestamp": "2026-01-29T10:30:12.456789",
      "pages": 3
    },
    {
      "filename": "credit_card_feb.pdf",
      "path": "/path/to/input/credit_card_feb.pdf",
      "reason": "Could not be processed - no IBAN found (likely credit card statement)",
      "timestamp": "2026-01-29T10:30:18.987654",
      "pages": 2
    }
  ]
}
```

## Exclusion Reasons

### No IBAN Found (Credit Card Statements)

The most common reason for exclusion is missing IBAN:

- **Trigger**: PDF has no IBAN and no extractable transaction data
- **Likely cause**: Credit card statements (have card numbers, not IBANs)
- **Reason text**: "Could not be processed - no IBAN found (likely credit card statement)"
- **See also**: [Credit Card Detection](CREDIT_CARD_DETECTION.md)

### Bank Statements with IBAN

**Important**: PDFs that contain an IBAN are NEVER excluded, even if:
- No transaction rows were extracted
- Extraction encountered errors
- The PDF has formatting issues

If an IBAN is present, the processor assumes it's a bank statement and attempts to process it.

### Future Exclusion Reasons

Potential future reasons for exclusion (not currently implemented):
- Invalid PDF format
- Password-protected PDFs
- Corrupted files
- Files with no extractable text

## File Structure

### Summary Section

```json
{
  "summary": {
    "total_excluded": 2,          // Total number of excluded files
    "generated_at": "2026-01-29T10:30:45.123456",  // ISO 8601 timestamp
    "note": "Files excluded from processing due to missing IBAN or no extractable data"
  }
}
```

### Excluded Files List

Each excluded file entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Name of the excluded PDF file |
| `path` | string | Full path to the PDF file |
| `reason` | string | Human-readable reason for exclusion |
| `timestamp` | string | ISO 8601 timestamp when exclusion occurred |
| `pages` | integer | Number of pages in the PDF |

## Usage Examples

### Checking Excluded Files

```bash
# View excluded files log
cat output/excluded_files.json

# Count excluded files
jq '.summary.total_excluded' output/excluded_files.json

# List all excluded filenames
jq '.excluded_files[].filename' output/excluded_files.json

# Filter by reason
jq '.excluded_files[] | select(.reason == "Credit card statement detected")' output/excluded_files.json
```

### Processing Multiple PDFs

```bash
input/
├── bank_statement_jan.pdf     # ✅ Processed
├── credit_card_jan.pdf         # ⏭️ Excluded
├── bank_statement_feb.pdf      # ✅ Processed
└── credit_card_feb.pdf         # ⏭️ Skipped

output/
├── 5678_transactions.csv       # Processed transactions
├── 5678_duplicates.csv         # Duplicates (if any)
├── monthly_summary.json        # Monthly summary
├── ibans.json                  # Extracted IBANs
└── excluded_files.json         # ⭐ Excluded files log
```

## Log Output

### Console Logs

When files are excluded, you'll see console logs:

```
INFO - Processing PDF 1 of 4
INFO - IBAN found on page 1: IE29****5678
INFO - Processing 150 transactions for IBAN suffix: 5678

INFO - Processing PDF 2 of 4
WARNING - Credit card statement detected in credit_card_jan.pdf. Credit card statements are not currently supported. Skipping file.
WARNING - PDF 2 (credit_card_jan.pdf) could not be processed: No IBAN found, no data extracted

INFO - Processing PDF 3 of 4
INFO - IBAN found on page 1: IE29****5678
INFO - Processing 100 transactions for IBAN suffix: 5678

INFO - Processing PDF 4 of 4
WARNING - Credit card statement detected in credit_card_feb.pdf. Credit card statements are not currently supported. Skipping file.
WARNING - PDF 4 (credit_card_feb.pdf) could not be processed: No IBAN found, no data extracted

INFO - Excluded files log saved to: output/excluded_files.json (2 files could not be processed)
```

## Behavior

### When Excluded Files JSON is Created

The `excluded_files.json` file is ONLY created when at least one file is excluded:

- ✅ **Created**: If any PDFs are excluded during processing
- ❌ **Not Created**: If all PDFs are successfully processed

### No Impact on Processing

File exclusion does NOT affect:
- Processing of other PDFs in the batch
- IBAN extraction from valid bank statements
- Transaction deduplication
- Output file generation
- Monthly summaries

### Error Handling

If an exception occurs during PDF processing:
- The file is NOT logged as excluded
- The error is logged to console
- Processing continues with next file
- The `excluded_files.json` reflects only intentional exclusions

## Testing

Run the excluded files logging tests:

```bash
pytest tests/test_excluded_files_logging.py -v
```

Test coverage:
- ✅ JSON file creation when files are excluded
- ✅ JSON file NOT created when all files processed
- ✅ Multiple exclusions logged correctly
- ✅ Mixed scenarios (some excluded, some processed)
- ✅ JSON structure validation
- ✅ Exception handling
- ✅ End-to-end integration with credit card detection
- ✅ PDFs with IBAN are NOT excluded (even with no rows)
- ✅ Only PDFs without IBAN are excluded

**Total**: 9 comprehensive tests covering all scenarios

## API Reference

### BankStatementProcessor

**Modified Method**:
```python
def _process_all_pdfs(self) -> Tuple[List[dict], int, Dict[str, str]]:
    """
    Process all PDF files in the input directory.

    Now tracks excluded files and writes excluded_files.json
    when files are skipped.
    """
```

**New Method**:
```python
def _save_excluded_files(self, excluded_files: List[Dict[str, Any]]) -> None:
    """
    Save excluded files log to JSON file.

    Args:
        excluded_files: List of dictionaries containing:
            - filename: Name of excluded PDF
            - path: Full path to PDF
            - reason: Reason for exclusion
            - timestamp: ISO 8601 timestamp
            - pages: Number of pages
    """
```

## Integration with Other Features

### Credit Card Detection

The excluded files logging is tightly integrated with credit card detection:

1. Credit card detection runs on first page of each PDF
2. If detected, PDF is skipped and logged to `excluded_files.json`
3. Reason is set to "Credit card statement detected"

See [Credit Card Detection](CREDIT_CARD_DETECTION.md) for more details.

### IBAN Extraction

Excluded files are processed independently from IBAN extraction:

- Excluded files are NOT included in `ibans.json`
- IBAN extraction still happens for valid bank statements
- Both `ibans.json` and `excluded_files.json` can coexist

See [IBAN Extraction](IBAN_EXTRACTION.md) for more details.

## Troubleshooting

### Q: excluded_files.json was not created

**A**: This is normal if no files were excluded. The file is only created when at least one PDF is skipped.

### Q: A file is excluded but I think it should be processed

**A**: Check the `reason` field in `excluded_files.json`. Files are only excluded if they have no IBAN. If it's a bank statement, verify that the PDF contains a valid IBAN (format: country code + numbers, e.g., "IE29 AIBK 9311 5212 3456 78").

### Q: A PDF has an IBAN but no transactions were extracted. Is it excluded?

**A**: No. PDFs with IBANs are NEVER excluded, even if no transactions are extracted. The presence of an IBAN indicates it's a bank statement and should be processed. Check the logs for extraction errors.

### Q: Can I disable exclusion logging?

**A**: Currently there's no flag to disable it, but the file is only created when exclusions occur, so it won't be present if all PDFs are processed successfully.

### Q: How do I view excluded files in a readable format?

**A**: Use `jq` for pretty printing:
```bash
jq '.' output/excluded_files.json
```

## Example Workflow

### 1. Process Bank Statements

```bash
python -m src.app
```

### 2. Check for Excluded Files

```bash
if [ -f output/excluded_files.json ]; then
    echo "Some files were excluded:"
    jq '.excluded_files[].filename' output/excluded_files.json
else
    echo "All files processed successfully"
fi
```

### 3. Generate Report

```bash
# Create a simple report
jq -r '.excluded_files[] | "\(.filename) - \(.reason) (\(.pages) pages)"' output/excluded_files.json > excluded_report.txt
```

## Related Documentation

- [Credit Card Detection](CREDIT_CARD_DETECTION.md)
- [IBAN Extraction](IBAN_EXTRACTION.md)
- [IBAN-Based File Grouping](IBAN_FILENAME_GROUPING.md)
- [Output Formats Guide](OUTPUT_FORMATS_USAGE.md)

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Feature Status**: ✅ Production Ready
