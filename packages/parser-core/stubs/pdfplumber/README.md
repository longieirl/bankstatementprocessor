# pdfplumber Type Stubs

## Purpose
Minimal type stubs for pdfplumber APIs used by the bankstatementsprocessor project to support static type checking with mypy and pyright.

## Ownership & Maintenance

- **Project**: bankstatementsprocessor
- **Upstream Library**: [pdfplumber](https://github.com/jsvine/pdfplumber)
- **Stub Version**: Based on pdfplumber 0.11.x
- **Last Synchronized**: 2026-01-30
- **Maintainer**: Development team
- **Update Trigger**: When upgrading pdfplumber dependency

## Scope

### ✅ What We Stub
These stubs cover **ONLY** the pdfplumber APIs actively used in our codebase:

**Module: `pdfplumber/__init__.pyi`**
- `pdfplumber.open()` - PDF file opening
- `pdfplumber.PDF` - PDF document class with `pages` attribute

**Module: `pdfplumber/page.pyi`**
- `pdfplumber.page.Page` - PDF page class
  - `.extract_words()` - Word extraction with positioning
  - `.extract_text()` - Raw text extraction
  - `.crop()` - Page area cropping
  - `.width`, `.height` - Page dimensions

### ❌ What We Don't Stub
To keep stubs minimal and maintainable, we explicitly **DO NOT** stub:
- Image extraction APIs (`extract_images`, `to_image`)
- Drawing utilities (`draw_line`, `draw_rect`, etc.)
- Advanced table extraction parameters
- Display/debugging utilities
- PDF parsing internals
- Character-level extraction
- Any other unused pdfplumber features

**Rationale**: Stubbing unused APIs increases maintenance burden with no benefit.

## File Structure

```
stubs/pdfplumber/
├── README.md           # This file
├── __init__.pyi        # Main pdfplumber module stubs
└── page.pyi           # Page class stubs
```

## Update Process

### When to Update
Update stubs when:
1. Upgrading pdfplumber dependency version
2. Adding new pdfplumber API usage to codebase
3. pdfplumber changes signatures of used APIs
4. CI stubtest reports mismatches

### How to Update

1. **Before upgrading pdfplumber**:
   ```bash
   # Check current version
   pip show pdfplumber

   # Review pdfplumber changelog
   # URL: https://github.com/jsvine/pdfplumber/blob/stable/CHANGELOG.md
   ```

2. **After upgrading pdfplumber**:
   ```bash
   # Verify stubs match new version
   stubtest pdfplumber --allowlist stubtest-allowlist.txt

   # Run type checking
   mypy src/ --ignore-missing-imports

   # Run tests
   pytest tests/
   ```

3. **If mismatches found**:
   - Update stub signatures in `__init__.pyi` or `page.pyi`
   - Re-run stubtest and mypy
   - Update "Last Synchronized" date in this README
   - Document changes in git commit message

4. **Document the update**:
   ```bash
   git add stubs/pdfplumber/
   git commit -m "chore: Update pdfplumber stubs for version X.Y.Z

   - Updated method signatures for ...
   - Added stub for newly used API ...
   - Verified with stubtest and mypy

   Refs: pdfplumber changelog https://..."
   ```

## Validation

### Type Checking
Stubs are validated through:

1. **Mypy on source code**:
   ```bash
   mypy src/ --ignore-missing-imports
   ```

2. **Stubtest against runtime**:
   ```bash
   # Verify stubs match actual pdfplumber
   stubtest pdfplumber
   ```

3. **CI Pipeline**:
   - Automated mypy runs on every commit
   - Stubtest validation (planned)

### Usage Verification
```bash
# Find all pdfplumber API usage in codebase
grep -rn "pdfplumber\.\|\.extract_words\|\.extract_text\|\.crop" src/

# Ensure all used APIs are stubbed
# Ensure no unused APIs are stubbed
```

## Design Principles

1. **Minimal Coverage**: Only stub what we use
2. **No Logic**: Stubs use `...` (ellipsis), no implementations
3. **No Assumptions**: Don't assume dict keys, return values, etc.
4. **Match Reality**: Signatures must match actual pdfplumber API
5. **Generic Types**: Use `Dict[str, Any]` for flexible dict returns

## Common Patterns

### Good Stub Design
```python
def extract_words(
    self,
    x_tolerance: float = 3,  # ← Real default from pdfplumber
    ...
) -> List[Dict[str, Any]]:  # ← Generic return type
    """Extract words from the page."""
    ...  # ← No implementation
```

### Anti-Patterns to Avoid

❌ **Don't be too specific**:
```python
# BAD: Assumes specific dict structure
def extract_words(...) -> List[Dict[Literal['text', 'x0', 'x1'], Any]]:
```

❌ **Don't add unused APIs**:
```python
# BAD: We don't use extract_images
def extract_images(...) -> List[Image]:
```

❌ **Don't put logic in stubs**:
```python
# BAD: Contains implementation
def extract_words(...):
    return [{"text": word} for word in ...]
```

## Dependencies

These stubs only depend on:
- `typing` module (Python standard library)
- `pathlib` module (Python standard library)

No external dependencies required.

## Compatibility

- **Python**: 3.9+
- **Mypy**: 0.910+
- **Pyright**: Compatible
- **pdfplumber**: 0.11.x (update VERSION when upgrading)

## Related Documentation

- [STUB_GUIDELINES.md](../../STUB_GUIDELINES.md) - Full stub compliance documentation
- [PEP 561](https://peps.python.org/pep-0561/) - Type stub packaging standard
- [mypy stub docs](https://mypy.readthedocs.io/en/stable/stubs.html)
- [pdfplumber docs](https://github.com/jsvine/pdfplumber)

## Version History

| Date | Stub Version | pdfplumber Version | Changes |
|------|--------------|-------------------|---------|
| 2026-01-30 | 1.0 | 0.11.x | Initial stubs for used APIs |
| TBD | 1.1 | TBD | Update when pdfplumber upgraded |

---

**Last Updated**: 2026-01-30
**Next Review**: When pdfplumber dependency is upgraded
