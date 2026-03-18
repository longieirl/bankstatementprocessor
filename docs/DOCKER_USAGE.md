# Docker Usage Guide - FREE and PAID Tiers

## Quick Start - FREE Tier (Out-of-the-Box)

The FREE tier works **without any configuration** - just build and run!

### Basic Commands

```bash
# Rebuild and start
docker-compose down && docker system prune -f && docker-compose up --build

# Run FREE tier (no parameters needed!)
docker-compose exec app bankstatements

# That's it! FREE tier just works.
```

**What happens:**
- ✅ No license file needed
- ✅ No environment variables needed
- ✅ All output formats (CSV, JSON, Excel)
- ✅ Recursive scanning, monthly summaries, expense analysis
- ✅ IBAN required for processing
- ✅ Works out-of-the-box!

---

## PAID Tier Setup

For PAID tier features (no IBAN requirement for credit card statements), you need a license file.

### Step 1: Generate License

```bash
# Generate PAID license on your host machine
python -m scripts.generate_license PAID "DOCKER-001" "Docker User" 365 \
  -o docker_license.json
```

### Step 2: Add to Dockerfile

Add this line to your Dockerfile:

```dockerfile
# Copy license into container
COPY docker_license.json /root/.bankstatements/license.json
```

### Step 3: Rebuild and Run

```bash
# Rebuild with license
docker-compose down && docker-compose up --build

# Run PAID tier (with all features)
docker-compose exec app bankstatements
```

**What happens:**
- ✅ License automatically loaded
- ✅ PAID tier activated
- ✅ All formats: CSV, JSON, Excel
- ✅ Monthly summaries enabled

---

## Alternative: Mount License at Runtime

If you don't want to rebuild for each license:

### Update docker-compose.yml

```yaml
services:
  app:
    volumes:
      - ./docker_license.json:/root/.bankstatements/license.json
```

### Run Commands

```bash
# Build once
docker-compose up --build

# Run with PAID license (mounted)
docker-compose up
```

---

## Testing Both Tiers

### Test FREE Tier

```bash
# Remove any license
docker-compose exec app rm -f /root/.bankstatements/license.json

# Run - should use FREE tier
docker-compose exec app bankstatements
```

**Expected output:**
```
INFO - No valid license found, using FREE tier
INFO - FREE tier limitations:
INFO -   - CSV output only
INFO -   - No recursive directory scanning
INFO -   - No monthly summaries
```

### Test PAID Tier

```bash
# Copy license into container
docker-compose cp docker_license.json app:/root/.bankstatements/license.json

# Run - should use PAID tier
docker-compose exec app bankstatements
```

**Expected output:**
```
INFO - Loading license from: /root/.bankstatements/license.json
INFO - License validated: PAID tier
INFO - Licensed to: Docker User
INFO - License expires: 2027-01-30
```

---

## Environment Variables (Optional)

You can override settings via environment in `docker-compose.yml`:

### FREE Tier Example

```yaml
services:
  app:
    environment:
      - OUTPUT_FORMATS=csv                    # FREE tier default
      - GENERATE_MONTHLY_SUMMARY=false        # FREE tier default
      - INPUT_DIR=/app/input
      - OUTPUT_DIR=/app/output
```

### PAID Tier Example

```yaml
services:
  app:
    environment:
      - OUTPUT_FORMATS=csv,json,excel         # PAID tier
      - GENERATE_MONTHLY_SUMMARY=true         # PAID tier
      - INPUT_DIR=/app/input
      - OUTPUT_DIR=/app/output
      - LICENSE_PATH=/root/.bankstatements/license.json
    volumes:
      - ./docker_license.json:/root/.bankstatements/license.json
```

---

## Verification Commands

### Check License Status

```bash
docker-compose exec app python -c "
from src.app import resolve_entitlements
ent = resolve_entitlements()
print(f'Tier: {ent.tier}')
print(f'Output formats: {ent.allowed_output_formats}')
print(f'Recursive scan: {ent.allow_recursive_scan}')
print(f'Monthly summary: {ent.allow_monthly_summary}')
"
```

### Check Application Version

```bash
docker-compose exec app bankstatements --version
```

---

## Troubleshooting

### Issue: "Output format 'json' is not available in FREE tier"

**Cause:** Trying to use JSON output without PAID license.

**Solutions:**
1. Remove `OUTPUT_FORMATS` override (defaults to CSV)
2. Install PAID license

```bash
# Option 1: Use default (CSV only)
docker-compose exec app sh -c 'unset OUTPUT_FORMATS && bankstatements'

# Option 2: Install PAID license
docker-compose cp docker_license.json app:/root/.bankstatements/license.json
```

### Issue: "License file not found"

**Cause:** License not copied into container.

**Solution:**
```bash
# Check if license exists
docker-compose exec app ls -la /root/.bankstatements/

# Copy license
docker-compose cp docker_license.json app:/root/.bankstatements/license.json
```

### Issue: "License validation failed"

**Cause:** Invalid or expired license.

**Solution:** Generate new license:
```bash
python -m scripts.generate_license PAID "NEW-KEY-001" "User" 365
docker-compose cp license_NEW-KEY-001.json app:/root/.bankstatements/license.json
```

---

## Complete Example

Here's a complete workflow from scratch:

```bash
# 1. Clean slate
docker-compose down && docker system prune -f

# 2. Test FREE tier (no configuration)
docker-compose up --build -d
docker-compose exec app bankstatements
# Output: "using FREE tier"

# 3. Generate PAID license
python -m scripts.generate_license PAID "PROD-001" "Production" 365

# 4. Install license
docker-compose exec app mkdir -p /root/.bankstatements
docker-compose cp license_PROD-001.json app:/root/.bankstatements/license.json

# 5. Test PAID tier
docker-compose exec app bankstatements
# Output: "License validated: PAID tier"

# 6. Verify all features work
docker-compose exec app python -c "
from src.app import resolve_entitlements
ent = resolve_entitlements()
assert ent.tier == 'PAID'
assert 'json' in ent.allowed_output_formats
assert 'xlsx' in ent.allowed_output_formats
assert ent.allow_monthly_summary == True
print('✓ All PAID features verified!')
"
```

---

## Best Practices

1. **FREE Tier Users**: No setup needed, just run!
2. **PAID Tier Users**: Mount license via volume for easy updates
3. **Development**: Use separate licenses for dev/staging/prod
4. **CI/CD**: Generate licenses programmatically with custom secret keys
5. **Security**: Never commit license files to version control

---

## Summary

### FREE Tier (Out-of-the-Box)
```bash
docker-compose up --build
docker-compose exec app bankstatements
# Done! No configuration needed.
```

### PAID Tier (With License)
```bash
# Generate license once
python -m scripts.generate_license PAID "KEY" "Name" 365

# Copy into container
docker-compose cp license_KEY.json app:/root/.bankstatements/license.json

# Run with all features
docker-compose exec app bankstatements
```

That's it! The application automatically detects the license and activates the appropriate tier.
