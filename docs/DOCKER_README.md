# Docker Quick Reference

## TL;DR - Out-of-the-Box Usage

```bash
# Build and start (FREE tier - no configuration needed)
docker-compose down && docker system prune -f && docker-compose up --build

# Your PDFs go here:
./input/

# Results appear here:
./output/
```

**That's it! The `input` folder is your default location for PDFs.**

---

## Default Directories

After running `docker-compose up --build`, these directories are automatically created:

| Directory | Purpose | Created By |
|-----------|---------|------------|
| `./input/` | **Drop your PDF files here** | docker-compose volume mount |
| `./output/` | CSV files appear here | docker-compose volume mount |
| `./logs/` | Processing activity logs | docker-compose volume mount |

---

## FREE Tier (Default)

**No configuration needed:**
- ✅ CSV output only
- ✅ Processes `./input/*.pdf`
- ✅ Outputs to `./output/*.csv`
- ✅ No license required
- ✅ No environment variables required

**Example:**
```bash
# 1. Start
docker-compose up --build

# 2. Add PDFs
cp ~/Downloads/statement.pdf ./input/

# 3. Process
docker-compose exec bank-processor bankstatements

# 4. Check results
ls ./output/
```

---

## PAID Tier (Optional)

To enable all features (JSON, Excel, monthly summaries):

### Quick Setup

1. Generate license:
   ```bash
   python -m scripts.generate_license PAID "COMPANY-001" "Company Name" 365
   ```

2. Add to `docker-compose.yml`:
   ```yaml
   volumes:
     - ./license_COMPANY-001.json:/root/.bankstatements/license.json

   environment:
     - OUTPUT_FORMATS=csv,json,excel
     - GENERATE_MONTHLY_SUMMARY=true
   ```

3. Rebuild:
   ```bash
   docker-compose up --build
   ```

---

## Directory Behavior

### Input Directory (`./input/`)
- **Purpose**: Place your bank statement PDFs here
- **Default**: `./input` (relative to project root)
- **Container path**: `/app/input`
- **Override**: Set `INPUT_DIR` environment variable

### Output Directory (`./output/`)
- **Purpose**: Processed files appear here automatically
- **Default**: `./output` (relative to project root)
- **Container path**: `/app/output`
- **FREE tier**: CSV files only
- **PAID tier**: CSV, JSON, and Excel files
- **Override**: Set `OUTPUT_DIR` environment variable

### Logs Directory (`./logs/`)
- **Purpose**: Processing activity and audit logs
- **Default**: `./logs` (relative to project root)
- **Container path**: `/app/logs`
- **Override**: Set `LOGS_DIR` environment variable

---

## Complete Example

```bash
# 1. Clean slate
docker-compose down && docker system prune -f

# 2. Build and start (FREE tier)
docker-compose up --build -d

# 3. Verify directories exist
ls -la input/ output/ logs/

# 4. Add test PDF
cp sample_statement.pdf ./input/

# 5. Process
docker-compose exec bank-processor bankstatements

# 6. View results
ls -la ./output/
cat ./output/transactions_*.csv

# 7. Check logs
cat ./logs/processing_activity.log
```

---

## Customizing Directories

If you want different directories, update `docker-compose.yml`:

```yaml
services:
  bank-processor:
    volumes:
      - /path/to/my/pdfs:/app/input        # Custom input
      - /path/to/my/results:/app/output    # Custom output
      - /path/to/my/logs:/app/logs         # Custom logs
```

Or use environment variables:
```yaml
environment:
  - INPUT_DIR=/custom/input
  - OUTPUT_DIR=/custom/output
  - LOGS_DIR=/custom/logs
```

---

## Common Commands

### Start
```bash
docker-compose up --build
```

### Process PDFs
```bash
docker-compose exec bank-processor bankstatements
```

### View Logs
```bash
docker-compose logs -f bank-processor
```

### Check License Status
```bash
docker-compose exec bank-processor python -c "
from src.app import resolve_entitlements
print(f'Tier: {resolve_entitlements().tier}')
"
```

### Clean Up
```bash
# Remove output files
rm -rf ./output/* ./logs/*

# Full rebuild
docker-compose down -v && docker-compose up --build
```

---

## Documentation

- 📖 [Complete Docker Guide](docs/DOCKER_USAGE.md)
- 🚀 [Quick Start](docs/QUICK_START_DOCKER.md)
- 🎫 [License Generation](docs/LICENSE_GENERATION.md)
- 💾 [Installation Guide](docs/INSTALLATION.md)

---

## Summary

**FREE Tier:**
- Drop PDFs in `./input/`
- Get CSV in `./output/`
- No setup required!

**PAID Tier:**
- Add license file
- Update docker-compose.yml
- Get all formats + features

**The `input` folder is always your default location for PDFs!** 🎯
