# FREE Tier Default Configuration

> **All FREE tier features are enabled by default - users can disable if not needed**

## Philosophy

FREE tier features should work **out-of-the-box** with zero configuration:
- ✅ **Opt-out model**: Features enabled by default, users can disable
- ❌ **Not opt-in**: Users shouldn't have to enable FREE features

---

## Current Defaults (FREE Tier)

### Output Formats
```bash
# Default: All formats enabled
OUTPUT_FORMATS=csv,json,excel

# Users can disable formats they don't want:
OUTPUT_FORMATS=csv              # CSV only
OUTPUT_FORMATS=csv,json         # CSV and JSON only
```

**Code Default**:
```python
# src/config/app_config.py
output_formats: list[str] = field(
    default_factory=lambda: ["csv", "json", "excel"]
)  # All formats available in FREE tier
```

### Monthly Summaries
```bash
# Default: Enabled
GENERATE_MONTHLY_SUMMARY=true

# Users can disable:
GENERATE_MONTHLY_SUMMARY=false
```

**Code Default**:
```python
# src/config/app_config.py
generate_monthly_summary: bool = True
```

### Expense Analysis
```bash
# Default: Enabled
GENERATE_EXPENSE_ANALYSIS=true

# Users can disable:
GENERATE_EXPENSE_ANALYSIS=false
```

**Code Default**:
```python
# src/config/app_config.py
generate_expense_analysis: bool = True
```

### Transaction Sorting
```bash
# Default: Enabled (chronological order)
SORT_BY_DATE=true

# Users can disable (preserve PDF order):
SORT_BY_DATE=false
```

**Code Default**:
```python
# src/config/app_config.py
sort_by_date: bool = True
```

### Recursive Directory Scanning
```bash
# Default: Disabled (for safety - prevents unexpected deep scans)
RECURSIVE_SCAN=false

# Users can enable:
RECURSIVE_SCAN=true
```

**Code Default**:
```python
# src/config/app_config.py
recursive_scan: bool = False
```

**Note**: Recursive scanning is FREE tier, but defaults to `false` for safety reasons:
- Prevents accidental scanning of entire filesystems
- Users explicitly opt-in to recursive behavior
- Top-level directory scanning is sufficient for most use cases

---

## Zero-Config Experience

### What Users Get Out-of-the-Box

Running with **zero configuration**:
```bash
python -m src.app
```

Automatically provides:
- ✅ **CSV output** (bank_statements.csv)
- ✅ **JSON output** (bank_statements.json)
- ✅ **Excel output** (bank_statements.xlsx)
- ✅ **Monthly summaries** (monthly_summary.json)
- ✅ **Expense analysis** (expense_analysis.json)
- ✅ **Chronological sorting** (oldest to newest)
- ✅ **Column totals** (debit/credit sums)
- ✅ **Duplicate detection** (SHA-256 based)
- ✅ **Top-level directory scan** (./input/*.pdf)

### What Users Can Disable

If users want minimal output:
```bash
# Minimal configuration
OUTPUT_FORMATS=csv
GENERATE_MONTHLY_SUMMARY=false
GENERATE_EXPENSE_ANALYSIS=false
SORT_BY_DATE=false
TOTALS_COLUMNS=
```

Results in:
- ✅ **CSV output only** (no JSON, no Excel)
- ❌ No monthly summaries
- ❌ No expense analysis
- ❌ No sorting (PDF order preserved)
- ❌ No column totals

---

## PAID Tier: No Additional Toggles

PAID tier **does not add new features** - it only removes the IBAN requirement:

```python
# FREE tier
require_iban: bool = True   # Bank statements with IBAN patterns only

# PAID tier
require_iban: bool = False  # Credit cards, statements without IBAN
```

**No environment variables for PAID tier** - license file automatically enables:
- Processing documents without IBAN patterns
- Credit card statements
- Other financial documents

---

## Configuration Principles

### 1. FREE Features = Enabled by Default
```python
# ✅ CORRECT: FREE tier feature enabled by default
generate_monthly_summary: bool = True

# ❌ WRONG: FREE tier feature disabled by default
generate_monthly_summary: bool = False
```

### 2. Users Can Disable Anything
```bash
# ✅ Users can disable any feature they don't need
GENERATE_MONTHLY_SUMMARY=false
OUTPUT_FORMATS=csv
```

### 3. Safety Defaults for Potentially Dangerous Operations
```python
# ✅ CORRECT: Recursive scan defaults to false (safety)
recursive_scan: bool = False

# ✅ CORRECT: Auto-cleanup defaults to false (safety)
auto_cleanup_on_exit: bool = False
```

### 4. No Feature Toggles for PAID-Only Features
```python
# ✅ CORRECT: License-based, not toggle-based
if entitlements.require_iban and not has_iban_pattern(template):
    skip_template()

# ❌ WRONG: Don't add toggles like ENABLE_CREDIT_CARDS=true
```

---

## Migration from Previous Model

### Before (Opt-in Model)
```bash
# Users had to enable features manually
OUTPUT_FORMATS=csv                    # Default
GENERATE_MONTHLY_SUMMARY=false        # Default

# To get full FREE tier, users needed:
OUTPUT_FORMATS=csv,json,excel
GENERATE_MONTHLY_SUMMARY=true
```

**Problem**: Users didn't know FREE tier capabilities

### After (Opt-out Model)
```bash
# Users get everything by default
OUTPUT_FORMATS=csv,json,excel         # Default
GENERATE_MONTHLY_SUMMARY=true         # Default

# Users can disable if not needed:
OUTPUT_FORMATS=csv
GENERATE_MONTHLY_SUMMARY=false
```

**Benefit**: Users experience full FREE tier immediately

---

## Testing Defaults

### Unit Tests Verify Defaults
```python
def test_app_config_defaults():
    """Test that FREE tier features are enabled by default."""
    config = AppConfig()

    assert config.generate_monthly_summary is True
    assert config.generate_expense_analysis is True
    assert config.output_formats == ["csv", "json", "excel"]
    assert config.sort_by_date is True
```

### Integration Tests Verify Zero-Config Experience
```python
def test_zero_config_processing():
    """Test that running with no config provides full FREE tier."""
    # No .env file, no environment variables
    result = run_processor()

    # Should generate all outputs
    assert exists("bank_statements.csv")
    assert exists("bank_statements.json")
    assert exists("bank_statements.xlsx")
    assert exists("monthly_summary.json")
    assert exists("expense_analysis.json")
```

---

## Documentation Standards

### ✅ Correct Documentation
```markdown
**Default**: Enabled (FREE tier)

Set to `false` to disable:
```

### ❌ Incorrect Documentation
```markdown
**Default**: Disabled

Set to `true` to enable (FREE tier only):
```

---

## Summary

| Feature | FREE Tier | Default | Can Disable |
|---------|-----------|---------|-------------|
| CSV output | ✅ | ✅ | ✅ |
| JSON output | ✅ | ✅ | ✅ |
| Excel output | ✅ | ✅ | ✅ |
| Monthly summaries | ✅ | ✅ | ✅ |
| Expense analysis | ✅ | ✅ | ✅ |
| Transaction sorting | ✅ | ✅ | ✅ |
| Column totals | ✅ | ✅ | ✅ |
| Duplicate detection | ✅ | ✅ | ❌ (always on) |
| Recursive scanning | ✅ | ❌ (safety) | ✅ |
| IBAN bypass | ❌ PAID | N/A | N/A |

**Philosophy**: FREE tier provides full value out-of-the-box. Users customize by disabling, not enabling.

---

**Last Updated**: 2026-02-19
**Effective Version**: 1.0.1+
