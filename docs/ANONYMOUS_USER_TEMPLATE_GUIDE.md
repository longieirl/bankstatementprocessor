# Quick Start: Generate Template for Your Bank Statement (Docker)

This guide shows anonymous users how to generate a custom JSON template configuration for their bank statement PDFs using the Docker image. **No installation required** - just Docker.

---

## Prerequisites

- **Docker** installed ([Get Docker](https://www.docker.com/get-started))
- A **sample PDF** of your bank statement (1-2 pages is enough)

---

## Step-by-Step Instructions

### Step 1: Pull the Docker Image

```bash
docker pull ghcr.io/longieirl/bankstatements:latest
```

---

### Step 2: Create Working Directories

```bash
# Create folders for your PDF and output
mkdir -p bank-analysis/input bank-analysis/output
cd bank-analysis
```

---

### Step 3: Add Your PDF

Copy your bank statement PDF to the `input/` folder:

```bash
# Example: Copy your statement
cp ~/Downloads/my_statement.pdf input/
```

---

### Step 4: Generate Template from Your PDF

Run the Docker container to analyze your PDF:

```bash
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="my_statement.pdf" \
  -e OUTPUT_PATH="output/my_bank_template.json" \
  -e LOG_LEVEL="INFO" \
  ghcr.io/longieirl/bankstatements:latest
```

**What this does:**
- Analyzes `input/my_statement.pdf`
- Detects table structure, columns, and IBAN
- Saves template to `output/my_bank_template.json`

---

### Step 5: Review the Generated Template

Check the output:

```bash
cat output/my_bank_template.json
```

You should see JSON like this:

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

### Step 6: Test Your Template

Verify the template works by using it to extract data:

```bash
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="my_statement.pdf" \
  -e TEMPLATE_PATH="output/my_bank_template.json" \
  -e LOG_LEVEL="INFO" \
  ghcr.io/longieirl/bankstatements:latest
```

**What this does:**
- Uses your template to extract transactions
- Shows results in the console output
- Validates column boundaries are correct

**Look for:**
```
✓ Extracted 45 transactions
✓ Column boundaries correct
✓ Template validation passed
```

---

### Step 7: Use Your Template for Processing

Once validated, use your template to process statements:

```bash
# Create templates directory
mkdir -p custom_templates

# Move your template
mv output/my_bank_template.json custom_templates/

# Process PDFs with your custom template
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/custom_templates:/app/custom_templates" \
  -e TEMPLATE_DIRS="/app/custom_templates" \
  ghcr.io/longieirl/bankstatements:latest
```

Your template will now be used automatically when processing matching PDFs!

---

## Understanding the Output

### Console Log Breakdown

When you run Step 4, you'll see detailed logs:

```
🔍 Analyzing PDF: /app/input/my_statement.pdf
⚠️  Analysis utility operates outside entitlement system (no paid features)

PDF: 2 pages, size: 595.0x842.0

Step 1-2: Detecting transaction tables...
  ✓ Table 1: x0=50, y0=300, x1=550, y1=720 (area: 162000px²)

Step 3-4: Extracting IBAN candidates (first page only)...
  ✓ Found 3 IBAN candidates

Step 5: Filtering IBANs by table overlap...
  ✓ 1 IBANs after filtering (2 rejected)

Step 6: Selecting best IBAN...
  ✓ Selected IBAN: IE29****5678 (score: 80.5)

Step 7: Analyzing column boundaries...
  ✓ Detected 5 columns:
    - Date: (26.0, 78.0)
    - Details: (78.0, 255.0)
    - Debit €: (255.0, 313.0)
    - Credit €: (313.0, 369.0)
    - Balance €: (369.0, 434.0)

✓ Template saved to: /app/output/my_bank_template.json
```

---

## Troubleshooting

### Problem: "No tables detected"

**Cause:** PDF doesn't have clear table structure

**Solutions:**
1. Verify your PDF has actual tables (not scanned images)
2. Try with a different statement from the same bank
3. Use `LOG_LEVEL=DEBUG` for more details:
   ```bash
   -e LOG_LEVEL="DEBUG"
   ```

---

### Problem: "IBAN not found"

**Cause:** IBAN only extracted from first page (by design)

**Solutions:**
1. Ensure IBAN appears on page 1 of your PDF
2. Check IBAN format is standard (e.g., IE29AIBK12345678)
3. Manually add IBAN pattern to template JSON:
   ```json
   "iban_patterns": ["^IE\\d{2}AIBK.*"]
   ```

---

### Problem: Column boundaries are wrong

**Cause:** Automatic detection isn't perfect for all layouts

**Solution:** Manually adjust the template JSON:

1. Open `output/my_bank_template.json` in a text editor
2. Adjust the X-coordinates in the `columns` section:
   ```json
   "columns": {
     "Date": [26.0, 78.0],      // Adjust these numbers
     "Details": [78.0, 255.0],  // based on your PDF layout
     "Amount": [255.0, 434.0]
   }
   ```
3. Re-test with Step 6 until extraction is correct

**Tip:** The numbers represent X-coordinates (left-to-right positions) on the PDF page. Increase the second number to make a column wider.

---

## Advanced Options

### Custom Base Template

Start from a different base template:

```bash
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/templates:/app/templates" \
  -e ANALYZE_PDF="my_statement.pdf" \
  -e OUTPUT_PATH="output/my_template.json" \
  -e BASE_TEMPLATE_PATH="templates/aib.json" \
  ghcr.io/longieirl/bankstatements:latest
```

---

### Debug Mode

See detailed analysis information:

```bash
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="my_statement.pdf" \
  -e OUTPUT_PATH="output/my_template.json" \
  -e LOG_LEVEL="DEBUG" \
  ghcr.io/longieirl/bankstatements:latest
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ANALYZE_PDF` | Yes | PDF filename in `/app/input` | `my_statement.pdf` |
| `OUTPUT_PATH` | For generation | Where to save template | `output/template.json` |
| `TEMPLATE_PATH` | For testing | Template to validate | `output/template.json` |
| `BASE_TEMPLATE_PATH` | No | Base template to use | `templates/default.json` |
| `LOG_LEVEL` | No | Logging detail level | `INFO` (default), `DEBUG` |

---

## Complete Example Workflow

Here's a full example from start to finish:

```bash
# 1. Setup
mkdir -p bank-analysis/{input,output,custom_templates}
cd bank-analysis
cp ~/Downloads/aib_statement.pdf input/

# 2. Generate template
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="aib_statement.pdf" \
  -e OUTPUT_PATH="output/aib.json" \
  ghcr.io/longieirl/bankstatements:latest

# 3. Review output
cat output/aib.json

# 4. Test template
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="aib_statement.pdf" \
  -e TEMPLATE_PATH="output/aib.json" \
  ghcr.io/longieirl/bankstatements:latest

# 5. If extraction looks good, move to production
mv output/aib.json custom_templates/

# 6. Process all PDFs with custom template
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/custom_templates:/app/custom_templates" \
  -e TEMPLATE_DIRS="/app/custom_templates" \
  ghcr.io/longieirl/bankstatements:latest

# 7. Check results
ls -lh output/
cat output/bank_statements.csv
```

---

## What Gets Generated?

The template JSON contains:

1. **Detection Rules**
   - IBAN patterns for auto-detecting your bank
   - Column header names for validation

2. **Extraction Configuration**
   - Table boundaries (top/bottom Y coordinates)
   - Column boundaries (X-coordinate ranges)
   - Header validation settings

3. **Metadata**
   - Template ID and name
   - Generation timestamp (added automatically)

---

## Best Practices

### ✅ DO:
- Use a statement with multiple transactions (10+)
- Test with 2-3 different statements from the same bank
- Keep your sample PDF alongside the template for reference
- Document any manual adjustments you make

### ❌ DON'T:
- Don't use scanned/image PDFs (text PDFs only)
- Don't expect perfection on first try - iteration is normal
- Don't share your actual IBAN in templates (obfuscated automatically)

---

## Privacy & Security

- **Template generation runs locally** in your Docker container
- **No data leaves your machine** - all processing is offline
- **IBANs are obfuscated** in logs and templates (shows last 4 digits only)
- **No telemetry or tracking** - completely anonymous

---

## Next Steps

After generating your template:

1. **Process Statements**: Use the template to extract CSV/JSON from all your statements
2. **Customize Further**: Edit the JSON to add bank-specific rules
3. **Share Template**: Consider contributing your template to help others (remove personal data first)

---

## Getting Help

### Option 1: Check Logs
Add `-e LOG_LEVEL="DEBUG"` to see detailed analysis steps

### Option 2: Review Documentation
- [PDF_ANALYSIS_GUIDE.md](./PDF_ANALYSIS_GUIDE.md) - Technical details
- [CUSTOM_TEMPLATES.md](./CUSTOM_TEMPLATES.md) - Template format reference

### Option 3: GitHub Issues
Open an issue at [github.com/longieirl/bankstatements](https://github.com/longieirl/bankstatements/issues) with:
- Docker run command used
- Full console output (remove personal data)
- Description of PDF structure

---

## FAQ

**Q: Does this work with scanned PDFs?**
A: No, only text-based PDFs with real tables work. Scanned images would require OCR.

**Q: Can I analyze multiple banks?**
A: Yes! Generate one template per bank, then use all templates together.

**Q: Is my data sent anywhere?**
A: No, all processing is local in the Docker container. Nothing leaves your machine.

**Q: Do I need a subscription?**
A: No! Template generation is completely free and works without any license.

**Q: What if column detection is wrong?**
A: You can manually edit the JSON coordinates. See "Troubleshooting" section above.

**Q: Can I use this commercially?**
A: Yes, the tool is Apache 2.0 licensed. Check LICENSE file for details.

---

## Summary

```bash
# Quick reference - The 3 essential commands:

# 1. GENERATE template from your PDF
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="your_statement.pdf" \
  -e OUTPUT_PATH="output/template.json" \
  ghcr.io/longieirl/bankstatements:latest

# 2. TEST the template
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -e ANALYZE_PDF="your_statement.pdf" \
  -e TEMPLATE_PATH="output/template.json" \
  ghcr.io/longieirl/bankstatements:latest

# 3. USE template for processing
docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/custom_templates:/app/custom_templates" \
  -e TEMPLATE_DIRS="/app/custom_templates" \
  ghcr.io/longieirl/bankstatements:latest
```

---

**🎉 You're done!** You now have a custom template for your bank statements.
