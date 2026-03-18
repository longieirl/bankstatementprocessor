# Multi-Document Type Support - Implementation Guide

## Overview

The Bank Statements Processor has been enhanced to support multiple types of financial documents beyond just bank statements. This document outlines the architecture, implementation, and migration path.

---

## Document Types Supported

| Document Type | Identifier | Example |
|---------------|------------|---------|
| `bank_statement` | IBAN | Current account statements |
| `credit_card_statement` | Card Number | Credit/debit card statements |
| `loan_statement` | Loan Reference | Mortgage, personal loan statements |
| `investment_statement` | Portfolio Reference | Investment account statements |
| `generic` | Any/None | Fallback for unclassified documents |

---

## Architecture Changes

### 1. Enhanced Template Schema

#### Before (Bank Statements Only)
```json
{
  "id": "aib_ireland",
  "name": "AIB Ireland Bank Statement",
  "enabled": true,
  "detection": {
    "iban_patterns": ["IE[0-9]{2}AIBK"]
  }
}
```

#### After (Multi-Document Support)
```json
{
  "id": "aib_ireland",
  "name": "AIB Ireland Bank Statement",
  "document_type": "bank_statement",
  "enabled": true,
  "detection": {
    "document_identifiers": {
      "iban_patterns": ["IE[0-9]{2}AIBK"]
    }
  }
}
```

Or for credit cards:
```json
{
  "id": "aib_credit_card",
  "name": "AIB Credit Card Statement",
  "document_type": "credit_card_statement",
  "enabled": true,
  "detection": {
    "document_identifiers": {
      "card_number_patterns": ["\\*{4}\\s*\\*{4}\\s*\\*{4}\\s*[0-9]{4}"]
    },
    "header_keywords": ["AIB", "Credit Card Statement"]
  }
}
```

---

## New Template Fields

### 1. `document_type` (Required)
**Type**: String
**Values**: `bank_statement | credit_card_statement | loan_statement | investment_statement | generic`
**Purpose**: Classifies the document type for type-specific processing

```json
{
  "document_type": "credit_card_statement"
}
```

### 2. `document_identifiers` (Replaces `iban_patterns`)
**Type**: Object
**Purpose**: Supports multiple identifier types for different document types

```json
{
  "detection": {
    "document_identifiers": {
      "iban_patterns": ["[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}"],
      "card_number_patterns": ["\\*{4}\\s*\\*{4}\\s*\\*{4}\\s*[0-9]{4}"],
      "account_reference_patterns": ["Account:\\s*[A-Z0-9-]+"],
      "loan_reference_patterns": ["Loan\\s*(?:Ref|No):\\s*[A-Z0-9-]+"]
    }
  }
}
```

### 3. `transaction_types` (Optional)
**Type**: Object
**Purpose**: Categorizes transaction types for better reporting

```json
{
  "processing": {
    "transaction_types": {
      "purchase": ["PURCHASE", "POS", "CONTACTLESS"],
      "payment": ["PAYMENT", "DIRECT DEBIT"],
      "fee": ["FEE", "CHARGE", "INTEREST"],
      "refund": ["REFUND", "CREDIT"]
    }
  }
}
```

### 4. `metadata` (Optional)
**Type**: Object
**Purpose**: Additional context about the template

```json
{
  "metadata": {
    "description": "AIB-specific credit card template",
    "issuer": "Allied Irish Banks",
    "card_types": ["Visa", "Mastercard"],
    "notes": "Uses masked card numbers"
  }
}
```

---

## Backward Compatibility

### Legacy Template Support

The system maintains **full backward compatibility** with existing templates:

#### Legacy Format (Still Works)
```json
{
  "detection": {
    "iban_patterns": ["IE[0-9]{2}AIBK"]
  }
}
```

#### New Format
```json
{
  "detection": {
    "document_identifiers": {
      "iban_patterns": ["IE[0-9]{2}AIBK"]
    }
  }
}
```

**Parser Logic**: Checks both formats:
1. If `document_identifiers` exists → Use it
2. If only `iban_patterns` exists → Wrap it in `document_identifiers`
3. Set default `document_type: "bank_statement"` if missing

---

## Detection Flow

### Current Flow (Bank Statements Only)
```
PDF → IBAN Detector → Filename → Header → Column → Default
```

### Enhanced Flow (Multi-Document)
```
PDF
 ↓
[Document Type Classification]
 ├─ Check all identifier types (IBAN, card number, etc.)
 ├─ Check header keywords
 └─ Determine likely document type
 ↓
[Filter Templates by Document Type]
 ├─ If type detected: Use type-specific templates
 └─ If uncertain: Try all templates
 ↓
[Type-Specific Detection]
 ├─ Bank statements: IBAN Detector
 ├─ Credit cards: Card Number Detector
 ├─ Loans: Loan Reference Detector
 └─ Generic: Filename/Header/Column Detectors
 ↓
[Fallback to Default Template]
 └─ Use document_type-specific default
```

---

## Implementation Roadmap

### Phase 1: Schema Enhancement (COMPLETED ✓)
- [x] Add `document_type` field to template schema
- [x] Add `document_identifiers` structure
- [x] Update existing templates with `document_type: "bank_statement"`
- [x] Create example credit card templates
- [x] Maintain backward compatibility

### Phase 2: Detection System Updates (TODO)
- [ ] Create `CardNumberDetector` class
- [ ] Create `LoanReferenceDetector` class
- [ ] Update `TemplateDetector` to support document types
- [ ] Add document type classification logic
- [ ] Update `TemplateRegistry` to filter by document type

### Phase 3: Processing Updates (TODO)
- [ ] Add transaction type categorization
- [ ] Support credit card specific fields (posting date, merchant code)
- [ ] Add document type to output files
- [ ] Update reports to handle multiple document types

### Phase 4: Testing & Validation (TODO)
- [ ] Add credit card statement test fixtures
- [ ] Add mixed document type test suite
- [ ] Validate detection accuracy
- [ ] Performance testing with mixed documents

---

## Code Changes Required

### 1. New Detector Classes

#### `src/templates/detectors/card_number_detector.py` (NEW)
```python
class CardNumberDetector(BaseDetector):
    """Detects templates by matching card number patterns."""

    def detect(self, pdf_path, first_page, templates):
        # Extract card numbers from header area
        # Pattern: **** **** **** 1234 or similar
        # Match against template.document_identifiers.card_number_patterns
```

#### `src/templates/detectors/loan_reference_detector.py` (NEW)
```python
class LoanReferenceDetector(BaseDetector):
    """Detects templates by matching loan reference patterns."""

    def detect(self, pdf_path, first_page, templates):
        # Extract loan references
        # Pattern: "Loan Ref: 12345" or similar
        # Match against template.document_identifiers.loan_reference_patterns
```

### 2. Update Template Model

#### `src/templates/template_model.py` (MODIFY)
```python
@dataclass
class TemplateDetectionConfig:
    # Legacy support
    iban_patterns: list[str] = field(default_factory=list)

    # New multi-identifier support
    document_identifiers: dict[str, list[str]] = field(default_factory=dict)

    # Existing fields...
    filename_patterns: list[str] = field(default_factory=list)
    header_keywords: list[str] = field(default_factory=list)
    column_headers: list[str] = field(default_factory=list)

@dataclass
class BankTemplate:
    id: str
    name: str
    document_type: str = "bank_statement"  # NEW: Default to bank statement
    enabled: bool = True
    detection: TemplateDetectionConfig
    extraction: TemplateExtractionConfig
    processing: TemplateProcessingConfig
```

### 3. Update Registry Parser

#### `src/templates/template_registry.py` (MODIFY)
```python
def _parse_template(template_id: str, data: dict) -> BankTemplate:
    # ... existing code ...

    detection_data = data.get("detection", {})

    # Support both legacy and new formats
    document_identifiers = {}

    if "document_identifiers" in detection_data:
        # New format
        document_identifiers = detection_data["document_identifiers"]
    elif "iban_patterns" in detection_data:
        # Legacy format - wrap in document_identifiers
        document_identifiers = {
            "iban_patterns": detection_data["iban_patterns"]
        }

    detection = TemplateDetectionConfig(
        iban_patterns=document_identifiers.get("iban_patterns", []),
        document_identifiers=document_identifiers,
        filename_patterns=detection_data.get("filename_patterns", []),
        header_keywords=detection_data.get("header_keywords", []),
        column_headers=detection_data.get("column_headers", []),
    )

    # Get document_type (default to bank_statement for backward compatibility)
    document_type = data.get("document_type", "bank_statement")

    return BankTemplate(
        id=template_id,
        name=data.get("name", template_id),
        document_type=document_type,  # NEW
        enabled=data.get("enabled", True),
        detection=detection,
        extraction=extraction,
        processing=processing,
    )
```

### 4. Update Template Detector

#### `src/templates/template_detector.py` (MODIFY)
```python
class TemplateDetector:
    def __init__(self, registry: TemplateRegistry):
        self.registry = registry
        self.detectors: list[BaseDetector] = [
            IBANDetector(),
            CardNumberDetector(),        # NEW
            LoanReferenceDetector(),     # NEW
            FilenameDetector(),
            HeaderDetector(),
            ColumnHeaderDetector(),
        ]

    def detect_template(self, pdf_path: Path, first_page: Page) -> BankTemplate:
        # Try to classify document type first
        document_type = self._classify_document_type(first_page)

        # Get templates, optionally filtered by type
        if document_type:
            templates = self.registry.get_templates_by_type(document_type)
        else:
            templates = self.registry.get_all_templates()

        # Try each detector
        for detector in self.detectors:
            result = detector.detect(pdf_path, first_page, templates)
            if result:
                return result

        # Use document-type specific default
        return self.registry.get_default_for_type(document_type or "bank_statement")

    def _classify_document_type(self, first_page: Page) -> str | None:
        """Classify document type based on content signals."""
        text = first_page.extract_text()

        # Check for credit card indicators
        if any(keyword in text for keyword in ["Credit Card", "Card Statement"]):
            return "credit_card_statement"

        # Check for loan indicators
        if any(keyword in text for keyword in ["Loan Statement", "Mortgage"]):
            return "loan_statement"

        # Check for IBAN (bank statement indicator)
        if re.search(r"IBAN:\s*[A-Z]{2}[0-9]{2}", text):
            return "bank_statement"

        return None  # Uncertain
```

---

## Template Examples

### Bank Statement Template
```json
{
  "id": "aib_ireland",
  "name": "AIB Ireland Bank Statement",
  "document_type": "bank_statement",
  "enabled": true,
  "detection": {
    "document_identifiers": {
      "iban_patterns": ["IE[0-9]{2}AIBK"]
    },
    "header_keywords": ["Allied Irish Banks"],
    "column_headers": ["Date", "Details", "Debit", "Credit", "Balance"]
  },
  "extraction": {
    "table_top_y": 300,
    "table_bottom_y": 720,
    "columns": {
      "Date": [29, 78],
      "Details": [78, 255],
      "Debit €": [255, 313],
      "Credit €": [313, 369],
      "Balance €": [369, 450]
    }
  },
  "processing": {
    "supports_multiline": true,
    "date_format": "%d %b %Y",
    "currency_symbol": "€"
  }
}
```

### Credit Card Template
```json
{
  "id": "aib_credit_card",
  "name": "AIB Credit Card Statement",
  "document_type": "credit_card_statement",
  "enabled": true,
  "detection": {
    "document_identifiers": {
      "card_number_patterns": ["\\*{4}\\s*\\*{4}\\s*\\*{4}\\s*[0-9]{4}"]
    },
    "header_keywords": ["AIB", "Credit Card Statement"],
    "column_headers": ["Date", "Transaction Details", "Debit", "Credit"]
  },
  "extraction": {
    "table_top_y": 320,
    "table_bottom_y": 720,
    "columns": {
      "Date": [29, 78],
      "Transaction Details": [78, 320],
      "Debit €": [320, 400],
      "Credit €": [400, 480]
    }
  },
  "processing": {
    "supports_multiline": true,
    "date_format": "%d %b %Y",
    "currency_symbol": "€",
    "transaction_types": {
      "purchase": ["POS", "CONTACTLESS", "ONLINE"],
      "payment": ["PAYMENT RECEIVED"],
      "fee": ["ANNUAL FEE", "LATE FEE"],
      "refund": ["REFUND", "CREDIT"]
    }
  }
}
```

---

## Migration Path

### For Existing Users

1. **No Changes Required** - Existing templates continue to work
2. **Optional**: Add `document_type: "bank_statement"` to existing templates
3. **Optional**: Migrate `iban_patterns` → `document_identifiers.iban_patterns`

### For New Document Types

1. Create new template with appropriate `document_type`
2. Define `document_identifiers` for the document type
3. Set up columns specific to that document type
4. Add to `templates/` directory

---

## Testing Strategy

### Unit Tests
- Test backward compatibility with legacy templates
- Test new identifier types (card numbers, loan refs)
- Test document type classification

### Integration Tests
- Mixed document processing (bank + credit card in same batch)
- Template priority with multiple types
- Fallback behavior for unknown document types

### Test Fixtures
- Create sample PDFs for each document type
- Include edge cases (malformed identifiers, mixed content)

---

## Future Enhancements

### Planned Features
1. **Investment Statements**: Portfolio summaries, trade confirmations
2. **Utility Bills**: Electricity, gas, internet bills
3. **Receipt Processing**: Individual transaction receipts
4. **Tax Documents**: P60, P45, tax returns
5. **Insurance Statements**: Policy summaries, premium statements

### API Enhancements
1. Document type in API response
2. Type-specific validation rules
3. Custom transaction categorization
4. Multi-document batch processing with mixed types

---

## Summary

✅ **Completed:**
- Enhanced template schema with `document_type` field
- Added `document_identifiers` structure
- Created credit card template examples
- Updated existing templates with document types
- Maintained full backward compatibility

🔄 **Next Steps:**
- Implement new detector classes (CardNumber, LoanReference)
- Update TemplateDetector to support document types
- Add document type classification logic
- Extend processing for type-specific features

📝 **Key Benefits:**
- **Extensible**: Easy to add new document types
- **Backward Compatible**: Existing templates still work
- **Type-Safe**: Clear separation of document types
- **Future-Proof**: Architecture supports any financial document type

The foundation is now in place for supporting multiple document types! 🎉
