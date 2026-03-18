# Per-Page Table Boundaries - Design Document

## Problem Statement

Some bank statements have transaction tables that start at different Y-coordinates on different pages:

**Example: Revolut Bank Statements**
- **Page 1**: Transaction table headers at Y=494 (preceded by Balance Summary at Y=359)
- **Pages 2-N**: Transaction table headers at Y=142 (no Balance Summary)

The current architecture assumes a single `table_top_y` value for the entire document, causing detection failures.

## Current Architecture Issues

### 1. Single table_top_y in Template Config

**File**: `src/templates/template_model.py:47`
```python
@dataclass
class TemplateExtractionConfig:
    table_top_y: int  # Single value for all pages
    table_bottom_y: int
    columns: dict[str, tuple[float, float]]
```

### 2. Hardcoded Extraction Logic

**File**: `src/extraction/pdf_extractor.py:195,231`
```python
# Always uses self.table_top_y regardless of page number
initial_area = page.crop((0, self.table_top_y, page.width, page.height))
table_area = page.crop((0, self.table_top_y, page.width, self.table_bottom_y))
```

### 3. Header Detection Limitations

**File**: `src/extraction/pdf_extractor.py:208`
```python
# Calculates header area based on single table_top_y
header_top = max(0, self.table_top_y - 50)
```

## Solution Design

### Approach 1: Per-Page Override (Recommended)

Add optional per-page boundary overrides to the template schema.

#### Template Schema Enhancement

```json
{
  "extraction": {
    "table_top_y": 140,
    "table_bottom_y": 735,
    "per_page_overrides": {
      "1": {
        "table_top_y": 490,
        "table_bottom_y": 735
      }
    },
    "columns": { ... }
  }
}
```

#### Implementation Changes

**1. Update Template Model** (`src/templates/template_model.py`)

```python
@dataclass
class PerPageBoundaries:
    """Per-page boundary overrides."""
    table_top_y: int | None = None
    table_bottom_y: int | None = None
    header_check_top_y: int | None = None

@dataclass
class TemplateExtractionConfig:
    table_top_y: int
    table_bottom_y: int
    columns: dict[str, tuple[float, float]]
    enable_page_validation: bool = True
    enable_header_check: bool | None = None
    header_check_top_y: int | None = None
    per_page_overrides: dict[int, PerPageBoundaries] = field(default_factory=dict)

    def get_table_top_y(self, page_num: int) -> int:
        """Get table_top_y for specific page."""
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.table_top_y is not None:
                return override.table_top_y
        return self.table_top_y

    def get_table_bottom_y(self, page_num: int) -> int:
        """Get table_bottom_y for specific page."""
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.table_bottom_y is not None:
                return override.table_bottom_y
        return self.table_bottom_y

    def get_header_check_top_y(self, page_num: int) -> int | None:
        """Get header_check_top_y for specific page."""
        if page_num in self.per_page_overrides:
            override = self.per_page_overrides[page_num]
            if override.header_check_top_y is not None:
                return override.header_check_top_y
        return self.header_check_top_y
```

**2. Update PDF Extractor** (`src/extraction/pdf_extractor.py`)

```python
def _determine_boundaries_and_extract(
    self, page: Any, page_num: int
) -> list[dict] | None:
    """Determine table boundaries and extract words (per-page aware)."""

    # Get page-specific boundaries (NEW)
    from src.templates.template_model import TemplateExtractionConfig

    if isinstance(self.extraction_config, TemplateExtractionConfig):
        table_top_y = self.extraction_config.get_table_top_y(page_num)
        table_bottom_y = self.extraction_config.get_table_bottom_y(page_num)
        header_check_top_y = self.extraction_config.get_header_check_top_y(page_num)
    else:
        # Fallback for direct initialization
        table_top_y = self.table_top_y
        table_bottom_y = self.table_bottom_y
        header_check_top_y = self.header_check_top_y

    # Use page-specific values instead of self.table_top_y
    if self.enable_dynamic_boundary:
        initial_area = page.crop((0, table_top_y, page.width, page.height))
        all_words = initial_area.extract_words(use_text_flow=True)

        if self.header_check_enabled:
            header_top = header_check_top_y if header_check_top_y else max(0, table_top_y - 50)
            header_area = page.crop((0, header_top, page.width, page.height))
            header_words = header_area.extract_words(use_text_flow=True)

            if not detect_table_headers(header_words, self.columns):
                logger.info(f"Page {page_num}: No table headers detected, skipping")
                return None

        dynamic_bottom_y = detect_table_end_boundary_smart(
            all_words, table_top_y, self.columns, table_bottom_y
        )

        table_area = page.crop((0, table_top_y, page.width, dynamic_bottom_y))
        words = table_area.extract_words(use_text_flow=True)
    else:
        # Static mode with per-page boundaries
        table_area = page.crop((0, table_top_y, page.width, table_bottom_y))
        words = table_area.extract_words(use_text_flow=True)

        if self.header_check_enabled:
            header_top = header_check_top_y if header_check_top_y else max(0, table_top_y - 50)
            header_area = page.crop((0, header_top, page.width, table_bottom_y))
            header_words = header_area.extract_words(use_text_flow=True)

            if not detect_table_headers(header_words, self.columns):
                logger.info(f"Page {page_num}: No table headers detected, skipping")
                return None

    return words
```

**3. Update Template Registry Parser** (`src/templates/template_registry.py`)

```python
def _parse_template(template_id: str, data: dict) -> BankTemplate:
    # ... existing code ...

    extraction_data = data.get("extraction", {})

    # Parse per-page overrides (NEW)
    per_page_overrides = {}
    if "per_page_overrides" in extraction_data:
        for page_str, override_data in extraction_data["per_page_overrides"].items():
            page_num = int(page_str)
            per_page_overrides[page_num] = PerPageBoundaries(
                table_top_y=override_data.get("table_top_y"),
                table_bottom_y=override_data.get("table_bottom_y"),
                header_check_top_y=override_data.get("header_check_top_y")
            )

    extraction = TemplateExtractionConfig(
        table_top_y=extraction_data.get("table_top_y", 300),
        table_bottom_y=extraction_data.get("table_bottom_y", 720),
        columns=extraction_data.get("columns", {}),
        enable_page_validation=extraction_data.get("enable_page_validation", True),
        enable_header_check=extraction_data.get("enable_header_check"),
        header_check_top_y=extraction_data.get("header_check_top_y"),
        per_page_overrides=per_page_overrides  # NEW
    )

    # ... rest of parsing ...
```

**4. Update PDFTableExtractor Constructor** (`src/extraction/pdf_extractor.py`)

```python
def __init__(
    self,
    columns: dict[str, tuple[int | float, int | float]],
    table_top_y: int = 300,
    table_bottom_y: int = 720,
    enable_dynamic_boundary: bool = False,
    enable_page_validation: bool = True,
    enable_header_check: bool = True,
    header_check_top_y: int | None = None,
    pdf_reader: "IPDFReader | None" = None,
    extraction_config: "TemplateExtractionConfig | None" = None,  # NEW
):
    """Initialize with optional extraction config for per-page support."""
    self.columns = columns
    self.table_top_y = table_top_y
    self.table_bottom_y = table_bottom_y
    self.extraction_config = extraction_config  # NEW
    # ... rest of init ...
```

## Example Usage

### Revolut Template with Per-Page Overrides

```json
{
  "id": "revolut",
  "name": "Revolut Bank Statement",
  "document_type": "bank_statement",
  "enabled": true,
  "detection": {
    "iban_patterns": ["[A-Z]{2}[0-9]{2}REVO[0-9A-Z]+"],
    "header_keywords": ["Revolut", "Revolut Bank UAB"],
    "column_headers": ["Date", "Description", "Money out", "Money in", "Balance"]
  },
  "extraction": {
    "table_top_y": 140,
    "table_bottom_y": 735,
    "enable_page_validation": false,
    "enable_header_check": false,
    "per_page_overrides": {
      "1": {
        "table_top_y": 490,
        "header_check_top_y": 440
      }
    },
    "columns": {
      "Date": [40, 120],
      "Description": [120, 330],
      "Money out": [330, 415],
      "Money in": [415, 525],
      "Balance": [525, 595]
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

## Backward Compatibility

✅ **Fully backward compatible**:
- Existing templates without `per_page_overrides` continue working unchanged
- Default behavior: use `table_top_y` for all pages
- Override behavior: only applied to specified pages

## Testing Strategy

### Unit Tests

```python
def test_per_page_boundaries_override():
    """Test that page 1 uses override, page 2 uses default."""
    config = TemplateExtractionConfig(
        table_top_y=140,
        table_bottom_y=735,
        columns={"Date": (40, 120)},
        per_page_overrides={
            1: PerPageBoundaries(table_top_y=490)
        }
    )

    assert config.get_table_top_y(1) == 490  # Override
    assert config.get_table_top_y(2) == 140  # Default
    assert config.get_table_bottom_y(1) == 735  # No override

def test_per_page_no_overrides():
    """Test that without overrides, all pages use default."""
    config = TemplateExtractionConfig(
        table_top_y=300,
        table_bottom_y=720,
        columns={"Date": (40, 120)}
    )

    assert config.get_table_top_y(1) == 300
    assert config.get_table_top_y(99) == 300
```

### Integration Tests

- Test Revolut PDF with per-page overrides
- Test AIB PDF without overrides (backward compatibility)
- Test mixed scenarios (some pages with overrides, some without)

## Alternative Approaches Considered

### Approach 2: Auto-Detection (More Complex)

Automatically detect table boundaries per page using heuristics:
- Pros: No manual configuration needed
- Cons: Less reliable, harder to debug, slower processing

### Approach 3: Multiple Templates (Rejected)

Create separate templates for first page vs subsequent pages:
- Pros: Simple implementation
- Cons: Template duplication, harder to maintain, confusing for users

## Implementation Checklist

- [ ] Update `TemplateExtractionConfig` with `per_page_overrides` and getter methods
- [ ] Create `PerPageBoundaries` dataclass
- [ ] Update `_parse_template()` to parse per-page overrides from JSON
- [ ] Update `PDFTableExtractor.__init__()` to accept extraction_config
- [ ] Update `_determine_boundaries_and_extract()` to use page-specific boundaries
- [ ] Update template instantiation in processor to pass extraction_config
- [ ] Add unit tests for per-page boundary logic
- [ ] Update Revolut template with per-page overrides
- [ ] Add integration test with Revolut PDF
- [ ] Update documentation

## Rollout Plan

### Phase 1: Core Implementation
1. Add schema support (template_model.py changes)
2. Add extraction support (pdf_extractor.py changes)
3. Add parsing support (template_registry.py changes)
4. Write unit tests

### Phase 2: Template Updates
1. Update Revolut template with per-page overrides
2. Test with actual Revolut PDFs
3. Validate all existing templates still work

### Phase 3: Documentation
1. Update template creation guide
2. Add examples to README
3. Document troubleshooting for multi-page issues

## Benefits

✅ **Solves the Revolut problem**: Page 1 can use Y=490, pages 2+ use Y=140
✅ **Backward compatible**: Existing templates work unchanged
✅ **Extensible**: Supports any per-page variation
✅ **Explicit**: Template author controls exact boundaries
✅ **Testable**: Easy to write tests for specific page scenarios
✅ **Maintainable**: Clear, simple logic without complex auto-detection

---

**Status**: Design Complete - Ready for Implementation
**Priority**: High (blocks Revolut statement processing)
**Estimated Effort**: 4-6 hours (implementation + testing)
