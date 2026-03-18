# Template Detection Architecture Issue

## Problem Statement

Template detection is incorrectly selecting "AIB Credit Card Statement" for an AIB bank account statement PDF. This causes column extraction to fail because:

1. Wrong column boundaries are applied
2. Date formats may differ
3. Transaction structures are different

## Root Cause

### Current Detection Logic
The template detection system uses multiple strategies:
1. **Header Detector** - Scans for keywords in header area
2. **IBAN Detector** - Looks for IBAN patterns
3. **Column Header Detector** - Matches column headers
4. **Filename Detector** - Matches filename patterns

However, there are **priority and specificity issues**:

### Issue 1: Overly Broad Header Keywords

Both templates share the same header keyword:
- **AIB Credit Card Template**: `"Allied Irish Banks", "AIB", "Credit Card Statement"`
- **AIB Ireland Bank Template**: Missing explicit header keywords beyond column headers

When "Allied Irish Banks" is found, the credit card template matches even though:
- The document says "Personal Bank Account Statement"
- The document has an IBAN (bank accounts have IBANs, credit cards don't)
- The document does NOT contain "Credit Card Statement"

### Issue 2: Detection Priority

The current system doesn't properly prioritize detection methods:
- Header detection matches first (too generic)
- IBAN detection should take priority for bank statements
- More specific keywords should override generic ones

## Impact

When the wrong template is selected:
1. **Column boundaries mismatch** - Text extraction captures wrong data
2. **Date parsing fails** - Different formats between templates
3. **Transaction classification fails** - Credit card vs bank transactions
4. **Output is corrupted** - Missing details, wrong amounts, invalid dates

### Example: AIB Bank Statement Extracted with Credit Card Template

**Expected (correct template)**:
```csv
Date,Details,Debit €,Credit €,Balance €
24 Apr 2025,VDP-IRISH RAIL 763,21.48,,1899.96
25 Apr 2025,VDP-GAA CUL CAMPS,82.50,,1817.46
```

**Actual (wrong template)**:
```csv
Date,Details,Debit €,Credit €,Balance €
Apr 2025,,21.48,,
Apr 2025,,,,
```

## Solution Architecture

### 1. Template Detection Priority (Highest to Lowest)

```
1. IBAN Pattern Match (most specific for bank statements)
2. Specific Document Identifiers (e.g., card numbers for credit cards)
3. Exact Phrase Match in Header (e.g., "Credit Card Statement")
4. Column Header Signature (unique column combinations)
5. Generic Keywords (e.g., "Allied Irish Banks")
6. Filename Patterns (least reliable)
```

### 2. Template Specificity Scoring

Each template should have a specificity score based on:
- **High specificity** (score: 100): IBAN pattern, card number pattern
- **Medium specificity** (score: 50): Exact phrases, unique column headers
- **Low specificity** (score: 10): Generic keywords, filename patterns

When multiple templates match, select the one with the **highest specificity score**.

### 3. Improved Template Configuration

#### AIB Ireland Bank Statement
```json
{
  "detection": {
    "iban_patterns": ["IE[0-9]{2}AIBK"],  // HIGH SPECIFICITY
    "header_keywords": [
      "Personal Bank Account",            // MEDIUM (specific phrase)
      "Statement of Account with Allied Irish Banks"  // MEDIUM
    ],
    "column_headers": ["Date", "Details", "Debit", "Credit", "Balance"]
  },
  "priority": 80  // Higher priority (has IBAN)
}
```

#### AIB Credit Card Statement
```json
{
  "detection": {
    "document_identifiers": {
      "card_number_patterns": ["\\*{4}\\s*\\*{4}\\s*\\*{4}\\s*[0-9]{4}"]  // HIGH SPECIFICITY
    },
    "header_keywords": [
      "Credit Card Statement",            // MEDIUM (specific phrase)
      "AIB Credit Card"                   // MEDIUM
    ],
    "exclude_keywords": [
      "IBAN"  // If IBAN is present, this is NOT a credit card
    ],
    "column_headers": ["Date", "Transaction Details", "Debit", "Credit"]
  },
  "priority": 70  // Lower priority (no IBAN)
}
```

### 4. Detection Algorithm

```python
def detect_template(pdf_path: str, registry: TemplateRegistry) -> Template:
    """Detect the best matching template with specificity scoring."""

    candidates = []

    for template in registry.get_enabled_templates():
        score = 0
        reasons = []

        # 1. Check IBAN patterns (highest priority)
        if has_iban_match(pdf_path, template.iban_patterns):
            score += 100
            reasons.append(f"IBAN match: {template.id}")

        # 2. Check document identifiers (e.g., card numbers)
        if has_document_identifier_match(pdf_path, template.document_identifiers):
            score += 100
            reasons.append(f"Doc ID match: {template.id}")

        # 3. Check exact phrase matches in header
        exact_matches = find_exact_phrase_matches(pdf_path, template.header_keywords)
        score += len(exact_matches) * 50

        # 4. Check column header signature
        if has_column_header_match(pdf_path, template.column_headers):
            score += 30
            reasons.append(f"Column headers match: {template.id}")

        # 5. Check generic keywords (low weight)
        generic_matches = find_generic_keyword_matches(pdf_path, template.header_keywords)
        score += len(generic_matches) * 10

        # 6. Check exclude keywords (disqualify if found)
        if template.exclude_keywords:
            if has_any_keyword(pdf_path, template.exclude_keywords):
                score = 0  # Disqualify
                reasons.append(f"EXCLUDED: {template.id}")

        if score > 0:
            candidates.append((template, score, reasons))

    # Sort by score (descending) and select best match
    candidates.sort(key=lambda x: x[1], reverse=True)

    if candidates:
        best_template, best_score, reasons = candidates[0]
        logger.info(f"Selected template: {best_template.id} (score: {best_score})")
        logger.debug(f"Reasons: {reasons}")
        return best_template

    # Fallback to default
    return registry.get_default_template()
```

## Implementation Plan

### Phase 1: Quick Fix (Immediate)
1. Add `exclude_keywords: ["IBAN"]` to AIB Credit Card template
2. Add explicit header keywords to AIB Ireland template
3. Adjust detection order: IBAN first, then header keywords

### Phase 2: Scoring System (Short-term)
1. Implement template specificity scoring
2. Add score thresholds for template selection
3. Log detection scores for debugging

### Phase 3: Template Isolation (Long-term)
1. Each template should be completely self-contained
2. No shared extraction logic between templates
3. Template-specific extractors for complex cases
4. Template validation on load (column boundaries, required fields)

## Testing Strategy

### Unit Tests
- Test each detector in isolation
- Test scoring algorithm with mock templates
- Test priority resolution with ambiguous documents

### Integration Tests
- Test with real PDFs from each bank
- Test with edge cases (e.g., AIB bank + credit card in same batch)
- Test fallback to default template

### Regression Tests
- Ensure Revolut statements still work after changes
- Ensure AIB statements work after changes
- Ensure new templates don't break old ones

## Success Criteria

1. ✅ AIB bank statements correctly detected as "AIB Ireland Bank Statement"
2. ✅ AIB credit card statements correctly detected as "AIB Credit Card Statement"
3. ✅ Revolut statements still correctly detected
4. ✅ All columns extracted correctly for each template
5. ✅ No cross-contamination between templates

## Related Files

- `src/templates/template_detector.py` - Main detection logic
- `src/templates/detectors/` - Individual detector implementations
- `templates/aib_ireland.json` - AIB bank statement template
- `templates/aib_credit_card.json` - AIB credit card template
- `templates/revolut.json` - Revolut template
