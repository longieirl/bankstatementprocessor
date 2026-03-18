# Installation Guide

This guide covers installation options for both FREE and PAID tiers of the bankstatements application.

## Table of Contents

- [FREE Tier Installation](#free-tier-installation)
- [PAID Tier Installation](#paid-tier-installation)
- [Development Installation](#development-installation)
- [License Setup](#license-setup)
- [Verifying Installation](#verifying-installation)

---

## FREE Tier Installation

The FREE tier includes core functionality with CSV output only.

### Using pip with pyproject.toml

```bash
# Clone the repository
git clone https://github.com/yourusername/bankstatements.git
cd bankstatements

# Install FREE tier (core dependencies only)
pip install .
```

### Using requirements files

```bash
# Install FREE tier dependencies
pip install -r requirements/base.txt
```

### FREE Tier Features

- ✓ CSV output format
- ✓ JSON output format
- ✓ Excel (.xlsx) output format
- ✓ PDF parsing and extraction
- ✓ Duplicate detection
- ✓ Recursive directory scanning
- ✓ Monthly summary reports
- ✓ Expense analysis
- ✗ No IBAN requirement (PAID only - for credit card statements)

---

## PAID Tier Installation

The PAID tier includes all features plus premium functionality.

### Using pip with optional dependencies

```bash
# Clone the repository
git clone https://github.com/yourusername/bankstatements.git
cd bankstatements

# Install PAID tier (includes Excel support)
pip install .[paid]
```

### Using requirements files

```bash
# Install PAID tier dependencies (includes base + paid features)
pip install -r requirements/paid.txt
```

### PAID Tier Features

- ✓ All FREE tier features
- ✓ JSON output format
- ✓ Excel (.xlsx) output format
- ✓ Recursive directory scanning
- ✓ Monthly summary reports

---

## Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/yourusername/bankstatements.git
cd bankstatements

# Install with dev dependencies
pip install .[dev,paid,test]

# Or using requirements files
pip install -r requirements/dev.txt -r requirements/paid.txt -r requirements/test.txt
```

This includes:
- All PAID tier features
- Code formatting tools (black, isort)
- Type checking (mypy, pyright)
- Testing tools (pytest, coverage)
- Security tools (bandit, safety)
- Pre-commit hooks

---

## License Setup

After installing PAID tier, you need a valid license file to unlock premium features.

### License File Locations

The application checks for licenses in this order:

1. Path specified in `LICENSE_PATH` environment variable
2. `~/.bankstatements/license.json` (user home directory)
3. `./license.json` (current directory)

### Installing Your License

#### Option 1: User Home Directory (Recommended)

```bash
# Create the directory
mkdir -p ~/.bankstatements

# Copy your license file
cp license.json ~/.bankstatements/
```

#### Option 2: Current Directory

```bash
# Place license in project directory
cp license.json ./
```

#### Option 3: Environment Variable

```bash
# Set LICENSE_PATH in your environment
export LICENSE_PATH=/path/to/your/license.json

# Or add to .env file
echo "LICENSE_PATH=/path/to/your/license.json" >> .env
```

### License Format

A valid license file looks like this:

```json
{
  "tier": "PAID",
  "license_key": "ABC-123-XYZ",
  "issued_to": "Your Company Name",
  "issued_at": "2024-01-30T10:00:00",
  "expires_at": "2025-01-30T10:00:00",
  "signature": "base64-encoded-signature"
}
```

**Note:** Do not modify license files manually. Licenses are cryptographically signed and any modifications will invalidate them.

---

## Verifying Installation

### Check Installed Version

```bash
bankstatements --version
```

### Verify License Status

```bash
python -c "from src.app import resolve_entitlements; ent = resolve_entitlements(); print(f'Tier: {ent.tier}')"
```

Expected output:
- **FREE tier (no license):** `Tier: FREE`
- **PAID tier (with license):** `Tier: PAID`

### Test Basic Functionality

```bash
# Create test directory structure
mkdir -p input output

# Run the application (will show no PDFs found, but verifies it works)
bankstatements
```

### Verify PAID Features

If you have a PAID license, verify premium features are enabled:

```python
from src.app import resolve_entitlements

ent = resolve_entitlements()

print(f"Tier: {ent.tier}")
print(f"Output formats: {', '.join(sorted(ent.allowed_output_formats))}")
print(f"Recursive scanning: {ent.allow_recursive_scan}")
print(f"Monthly summaries: {ent.allow_monthly_summary}")
```

Expected PAID tier output:
```
Tier: PAID
Output formats: csv, json, xlsx
Recursive scanning: True
Monthly summaries: True
```

---

## Configuration

After installation, configure the application using environment variables or a `.env` file:

```bash
# Input and output directories
INPUT_DIR=input
OUTPUT_DIR=output

# Output formats (FREE tier: csv only, PAID tier: csv,json,excel)
OUTPUT_FORMATS=csv,json,excel

# Enable monthly summaries (PAID tier only)
GENERATE_MONTHLY_SUMMARY=true

# Logging
LOG_LEVEL=INFO

# License location (optional)
LICENSE_PATH=~/.bankstatements/license.json
```

---

## Troubleshooting

### Issue: "Output format 'json' is not available in FREE tier"

**Solution:** Either install PAID tier or use CSV output only:
```bash
# Option 1: Upgrade to PAID tier
pip install .[paid]

# Option 2: Use CSV only (FREE tier)
export OUTPUT_FORMATS=csv
```

### Issue: "License validation failed"

**Solution:** Ensure your license file is valid and in the correct location:
1. Check license file exists: `ls ~/.bankstatements/license.json`
2. Verify license content is valid JSON
3. Contact your license provider for a new license

### Issue: "ModuleNotFoundError: No module named 'openpyxl'"

**Solution:** Install PAID tier dependencies:
```bash
pip install .[paid]
# or
pip install -r requirements/paid.txt
```

---

## Upgrading

### From FREE to PAID Tier

```bash
# Install PAID tier dependencies
pip install --upgrade .[paid]

# Install your license
cp license.json ~/.bankstatements/

# Verify upgrade
python -c "from src.app import resolve_entitlements; print(resolve_entitlements().tier)"
```

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Reinstall with your tier
pip install --upgrade .[paid]  # or just . for FREE tier
```

---

## Uninstallation

```bash
# Remove the package
pip uninstall bankstatements

# Remove license (optional)
rm ~/.bankstatements/license.json
```

---

## Support

For installation issues or questions:
- Check the [FAQ](FAQ.md)
- Open an issue on [GitHub](https://github.com/yourusername/bankstatements/issues)
- Contact support with your license key
