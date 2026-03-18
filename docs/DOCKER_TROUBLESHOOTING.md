# Docker Troubleshooting Guide

## Problem: PDFs Not Being Processed

### Issue
After running `docker-compose up --build`, PDFs in the `input` folder are not being processed.

### Understanding the Behavior

The container processes PDFs in **two ways**:

1. **At Startup**: Processes any PDFs already in `./input/` when container starts
2. **On Demand**: You manually trigger processing after adding more PDFs

---

## Solution 1: Process PDFs Already in Input Folder

If you have PDFs in `./input/` before starting:

```bash
# 1. Make sure PDFs are in input folder FIRST
ls -la ./input/
# Should show your PDF files

# 2. Start container (will process on startup)
docker-compose down && docker-compose up --build

# 3. Check logs to see processing
docker-compose logs bank-processor

# 4. Check output
ls -la ./output/
```

**Expected log output:**
```
🚀 Starting Bank Statement Processor v1.0.0...
🔄 Running PDF processing pipeline...
INFO - No valid license found, using FREE tier
INFO - PDFs processed: 3
✅ Processing complete — results saved to /app/output
```

---

## Solution 2: Add PDFs After Container Started

If you add PDFs **after** the container is running:

```bash
# 1. Start container
docker-compose up --build -d

# 2. Add PDFs to input folder
cp ~/Downloads/statement*.pdf ./input/

# 3. Manually trigger processing
docker-compose exec bank-processor python -m src.app

# 4. Check results
ls -la ./output/
```

---

## Solution 3: Automatic Processing (Watch Mode)

To automatically process new PDFs as they're added:

### Option A: Use a File Watcher Script

Create `watch-and-process.sh`:

```bash
#!/bin/bash
while true; do
    if [ -n "$(ls -A ./input/*.pdf 2>/dev/null)" ]; then
        echo "📄 PDFs found, processing..."
        docker-compose exec -T bank-processor bankstatements
        echo "✅ Done, waiting for more PDFs..."
    fi
    sleep 10
done
```

Run it:
```bash
chmod +x watch-and-process.sh
./watch-and-process.sh
```

### Option B: Manual Trigger When Needed

Just run the processing command whenever you add PDFs:

```bash
# Add PDFs
cp statement.pdf ./input/

# Process
docker-compose exec bank-processor python -m src.app

# Results appear immediately
ls ./output/
```

---

## Checking Container Status

### Is the container running?

```bash
docker-compose ps
```

**Expected output:**
```
NAME                      STATUS
bank-statement-processor  Up 5 minutes
```

If status is `Exit 0`, the container processed and exited. Restart it:
```bash
docker-compose up -d
```

### Are PDFs in the input folder?

```bash
# Check from host
ls -la ./input/

# Check from container
docker-compose exec bank-processor ls -la /app/input/
```

Both should show the same files (volumes are mounted).

### Check logs

```bash
# View all logs
docker-compose logs bank-processor

# Follow logs in real-time
docker-compose logs -f bank-processor

# Last 50 lines
docker-compose logs --tail=50 bank-processor
```

---

## Common Issues

### Issue 1: Container Exits Immediately

**Problem:** Container starts, processes once, then exits.

**Cause:** `EXIT_AFTER_PROCESSING=true` (old default)

**Solution:** Update `docker-compose.yml`:
```yaml
environment:
  - EXIT_AFTER_PROCESSING=false  # Keep container running
```

Then restart:
```bash
docker-compose down && docker-compose up --build
```

---

### Issue 2: No PDFs in Input Folder

**Problem:** Input folder is empty.

**Check:**
```bash
ls -la ./input/
```

**Solution:** Create folder and add PDFs:
```bash
mkdir -p input
cp ~/Downloads/statement.pdf ./input/
```

---

### Issue 3: Permission Denied

**Problem:** Container can't read PDFs or write output.

**Check permissions:**
```bash
ls -la ./input/
ls -la ./output/
```

**Solution:** Fix ownership:
```bash
# Make readable by Docker
chmod -R 755 ./input ./output

# Or change ownership
sudo chown -R $USER:$USER ./input ./output
```

---

### Issue 4: PDFs Already Processed

**Problem:** PDFs were processed on first startup, output already exists.

**Check:**
```bash
ls -la ./output/
```

If files exist, they were already processed.

**Solution:**
- To reprocess: Delete output files first
  ```bash
  rm ./output/*.csv
  docker-compose exec bank-processor python -m src.app
  ```

- To process new PDFs: Just add them and run command
  ```bash
  cp new_statement.pdf ./input/
  docker-compose exec bank-processor python -m src.app
  ```

---

### Issue 5: Container Not Found

**Problem:** `Error: No such service: bank-processor`

**Solution:** Check service name in docker-compose.yml:
```bash
docker-compose ps
```

Use the correct service name:
```bash
docker-compose exec bank-processor python -m src.app
```

---

## Step-by-Step Debug Process

Run these commands to diagnose:

```bash
# 1. Is Docker running?
docker --version
docker-compose --version

# 2. Is container running?
docker-compose ps

# 3. What's in input folder (host)?
ls -la ./input/

# 4. What's in input folder (container)?
docker-compose exec bank-processor ls -la /app/input/

# 5. Can we exec into container?
docker-compose exec bank-processor bash
# Then inside container:
ls /app/input/
python -m src.app
exit

# 6. Check logs for errors
docker-compose logs bank-processor | grep -i error
docker-compose logs bank-processor | grep -i fail

# 7. Rebuild from scratch
docker-compose down -v
docker system prune -f
docker-compose up --build
```

---

## Understanding the Workflow

### Initial Startup
```
1. docker-compose up --build
   ↓
2. Container starts
   ↓
3. Runs: python -m src.app (processes PDFs in /app/input)
   ↓
4. If EXIT_AFTER_PROCESSING=true → exits
   If EXIT_AFTER_PROCESSING=false → stays running
```

### After Startup (Container Running)
```
1. Add PDFs to ./input/ folder
   ↓
2. Run: docker-compose exec bank-processor python -m src.app
   ↓
3. PDFs processed immediately
   ↓
4. Results appear in ./output/
```

---

## Recommended Workflow

### For Interactive Use (Default)
```bash
# 1. Start once (container stays running)
docker-compose up --build -d

# 2. Add PDFs whenever you want
cp statements/*.pdf ./input/

# 3. Process them
docker-compose exec bank-processor python -m src.app

# 4. Repeat steps 2-3 as needed
```

### For Batch Processing (CI/CD)
```bash
# 1. Add all PDFs first
cp statements/*.pdf ./input/

# 2. Process once and exit
EXIT_AFTER_PROCESSING=true docker-compose up --build

# 3. Results in ./output/
```

---

## Quick Test

Verify everything works:

```bash
# 1. Clean state
docker-compose down -v
rm -rf ./input ./output ./logs
mkdir -p ./input ./output ./logs

# 2. Add test PDF
echo "Test" > ./input/test.txt  # Not a real PDF, just for testing

# 3. Start container
docker-compose up --build -d

# 4. Verify container is running
docker-compose ps
# Should show: Up

# 5. Verify files are visible
docker-compose exec bank-processor ls -la /app/input/
# Should show: test.txt

# 6. Try processing
docker-compose exec bank-processor python -m src.app
# Will show logs

# 7. Check if command worked (even without real PDFs)
echo $?
# Should be: 0 (success)
```

---

## Getting Help

If still not working:

1. **Collect information:**
   ```bash
   docker-compose ps > debug.txt
   docker-compose logs bank-processor >> debug.txt
   ls -la ./input/ >> debug.txt
   ls -la ./output/ >> debug.txt
   ```

2. **Share the debug.txt** with your team/support

3. **Common solution:** Full rebuild
   ```bash
   docker-compose down -v
   docker system prune -af
   docker-compose up --build
   ```

---

## Summary

**Problem:** PDFs not processing after `docker-compose up --build`

**Root Cause:** Container processes on startup, then waits for manual trigger

**Solution:**
```bash
# Add PDFs
cp statement.pdf ./input/

# Process them
docker-compose exec bank-processor python -m src.app

# Check results
ls ./output/
```

**That's the expected workflow!** The container doesn't watch for new files automatically - you trigger processing when ready.
