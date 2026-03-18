# Quick Start - Docker (FREE Tier)

## Out-of-the-Box Setup

After running:
```bash
docker-compose down && docker system prune -f && docker-compose up --build -d
```

**Note:** Container processes PDFs on startup, then waits. To process PDFs added later, run:
```bash
docker-compose exec bank-processor python -m src.app
```

## Default Directories

The following directories are automatically created and mounted:

| Host Directory | Container Path | Purpose |
|----------------|----------------|---------|
| `./input` | `/app/input` | **Place your PDF files here** |
| `./output` | `/app/output` | Processed CSV files appear here |
| `./logs` | `/app/logs` | Processing activity logs |

### Default Behavior (FREE Tier)

✅ **Input Directory**: `./input` (automatically created)
- Place your bank statement PDFs here
- Container monitors this directory

✅ **Output Directory**: `./output` (automatically created)
- CSV files generated here
- One CSV per IBAN/account

✅ **Output Format**: CSV only (FREE tier)

✅ **Monthly Summary**: Disabled (FREE tier)

---

## Usage Example

### 1. Start the Application

```bash
# Start container in detached mode (runs in background)
docker-compose down && docker system prune -f && docker-compose up --build -d
```

**What happens:**
- Container builds with FREE tier defaults
- Creates `input`, `output`, and `logs` directories
- Processes any PDFs already in `./input` (if any)
- Detects no license → activates FREE tier
- Stays running, ready for processing commands

### 2. Add PDF Files

```bash
# Copy your bank statements to the input folder
cp ~/Downloads/statement*.pdf ./input/
```

### 3. Process Files

**Trigger processing manually** (doesn't happen automatically):

```bash
docker-compose exec bank-processor python -m src.app
```

**Watch logs in real-time:**
```bash
docker-compose logs -f bank-processor
```

### 4. Get Results

```bash
# Check output
ls -la ./output/

# View generated CSV
cat ./output/transactions_IE12BOFI90000112345678.csv
```

---

## Directory Structure After First Run

```
bankstatements/
├── input/                    # ← Place PDFs here
│   └── statement_jan.pdf
├── output/                   # ← CSV files appear here
│   ├── transactions_IE12BOFI90000112345678.csv
│   └── duplicates_IE12BOFI90000112345678.csv
├── logs/                     # ← Processing logs
│   └── processing_activity.log
├── docker-compose.yml
├── Dockerfile
└── ...
```

---

## No Configuration Required!

The defaults work out-of-the-box:

- ✅ **No environment variables** needed
- ✅ **No license file** needed
- ✅ **No .env file** needed
- ✅ **Just place PDFs in `./input`** and run

---

## Upgrading to PAID Tier

To enable all features (JSON, Excel, monthly summaries):

### 1. Generate License

```bash
python -m scripts.generate_license PAID "DOCKER-001" "Company Name" 365
```

### 2. Add to docker-compose.yml

```yaml
services:
  bank-processor:
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./logs:/app/logs
      - ./license_DOCKER-001.json:/root/.bankstatements/license.json  # Add this
    environment:
      # Update these for PAID tier
      - OUTPUT_FORMATS=csv,json,excel
      - GENERATE_MONTHLY_SUMMARY=true
```

### 3. Rebuild

```bash
docker-compose down && docker-compose up --build
```

**PAID tier features now active!**

---

## Common Operations

### View Logs
```bash
docker-compose logs -f bank-processor
```

### Exec into Container
```bash
docker-compose exec bank-processor bash
```

### Check License Status
```bash
docker-compose exec bank-processor python -c "
from src.app import resolve_entitlements
ent = resolve_entitlements()
print(f'Tier: {ent.tier}')
print(f'Formats: {ent.allowed_output_formats}')
"
```

### Cleanup
```bash
# Remove processed files
rm -rf ./output/* ./logs/*

# Full cleanup and rebuild
docker-compose down -v
docker system prune -f
docker-compose up --build
```

---

## Troubleshooting

### Issue: No `input` folder

**Solution:** Create it manually:
```bash
mkdir -p input output logs
docker-compose up --build
```

### Issue: Permission denied

**Solution:** Fix permissions:
```bash
sudo chown -R $USER:$USER input output logs
```

### Issue: PDFs not processing

**Check:**
1. Are PDFs in `./input`?
   ```bash
   ls -la ./input/
   ```

2. Is container running?
   ```bash
   docker-compose ps
   ```

3. Check logs:
   ```bash
   docker-compose logs bank-processor
   ```

---

## Summary

### FREE Tier (Default)
```bash
# Build
docker-compose up --build

# Add PDFs
cp statement.pdf ./input/

# Process
docker-compose exec bank-processor bankstatements

# Check results
ls ./output/
```

**That's it! The `input` folder is your default drop location for PDFs.**

### PAID Tier (With License)
```bash
# Generate license
python -m scripts.generate_license PAID "KEY" "Name" 365

# Update docker-compose.yml to mount license

# Rebuild
docker-compose up --build

# Process with all features
docker-compose exec bank-processor bankstatements
```

**All features unlocked: JSON, Excel, monthly summaries, recursive scanning.**
