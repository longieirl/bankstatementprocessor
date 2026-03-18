# Docker Commands - Quick Reference

## Simple One-Command Processing

**The easiest way to process PDFs:**

```bash
docker-compose up --build
```

That's it! This will:
1. Build the Docker image
2. Process all PDFs in `./input/`
3. Save results to `./output/`
4. Exit when complete

---

## Alternative: Interactive Mode

If you want the container to stay running for repeated processing:

### Step 1: Start Container in Interactive Mode

```bash
EXIT_AFTER_PROCESSING=false docker-compose up --build -d
```

This keeps the container running in the background.

### Step 2: Add PDFs

```bash
# Add your PDFs to the input folder
cp ~/Downloads/statement.pdf ./input/
```

### Step 3: Process PDFs (Every Time You Add New Files)

```bash
docker-compose exec bank-processor python -m src.app
```

### Step 4: Check Results

```bash
ls -la ./output/
cat ./output/bank_statements_*.csv
```

---

## Complete Example

**Simple one-shot processing:**

```bash
# 1. Add PDFs
cp ~/Downloads/statements/*.pdf ./input/

# 2. Process them
docker-compose up --build

# 3. Results are ready
ls ./output/
```

**Interactive mode (for repeated processing):**

```bash
# 1. Start container (stays running)
EXIT_AFTER_PROCESSING=false docker-compose up --build -d

# 2. Add PDFs
cp statement1.pdf ./input/

# 3. Process them
docker-compose exec bank-processor python -m src.app

# 4. Add more PDFs later
cp statement2.pdf statement3.pdf ./input/

# 5. Process again
docker-compose exec bank-processor python -m src.app

# 6. Check all results
ls ./output/
```


---

## Common Commands

### Check if container is running
```bash
docker-compose ps
```

### View logs
```bash
docker-compose logs -f bank-processor
```

### Process PDFs manually
```bash
docker-compose exec bank-processor python -m src.app
```

### Check license status
```bash
docker-compose exec bank-processor python -c "
from src.app import resolve_entitlements
print(f'Tier: {resolve_entitlements().tier}')
"
```

### Restart container
```bash
docker-compose restart bank-processor
```

### Stop container
```bash
docker-compose down
```

### Full rebuild
```bash
docker-compose down -v
docker system prune -f
docker-compose up --build -d
```

---

## Why PDFs Aren't Processed Automatically

The application is designed for **on-demand processing**, not automatic watching:

1. **Security**: Automatic processing could be a security risk
2. **Control**: You decide when to process
3. **Resources**: Doesn't waste CPU watching for files
4. **Simplicity**: Explicit is better than implicit

---

## If You Want Automatic Processing

Create a simple watch script:

```bash
#!/bin/bash
# watch.sh - Process PDFs whenever they appear

while true; do
    if [ -n "$(ls -A ./input/*.pdf 2>/dev/null)" ]; then
        echo "Found PDFs, processing..."
        docker-compose exec -T bank-processor bankstatements
        sleep 5
    fi
    sleep 2
done
```

Run it:
```bash
chmod +x watch.sh
./watch.sh &
```

Now PDFs will be processed automatically when added to `./input/`.

---

## TL;DR

**The simplest command:**

```bash
# Add PDFs to ./input/, then run:
docker-compose up --build
```

**That's it!** This processes all PDFs and exits when done.

---

## Full Workflow Chart

```
┌─────────────────────────────────────┐
│ 1. docker-compose up --build -d     │  (Start once, stays running)
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│ 2. cp PDFs ./input/                 │  (Add files)
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│ 3. docker-compose exec ...          │  (Process - MANUAL TRIGGER)
│    bank-processor bankstatements    │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│ 4. ls ./output/                     │  (Check results)
└─────────────────────────────────────┘
```

**Repeat steps 2-4 as needed!**

---

## Summary

✅ **Default behavior: Process and exit**
   ```bash
   docker-compose up --build
   ```

✅ **For interactive mode: Set EXIT_AFTER_PROCESSING=false**
   ```bash
   EXIT_AFTER_PROCESSING=false docker-compose up --build -d
   ```

✅ **Simple and straightforward** - just run one command!

**The command to remember:**
```bash
docker-compose up --build
```
