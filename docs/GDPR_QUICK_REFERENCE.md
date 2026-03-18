# GDPR Quick Reference Guide

Quick reference for GDPR compliance features in the Bank Statements Processor.

---

## Common Operations

### Delete All Data (Right to Erasure)
```bash
make delete-data
```
Prompts for confirmation, then securely deletes all output files.

### Clean Up Old Files (Data Retention)
```bash
# Set retention period (e.g., 90 days)
export DATA_RETENTION_DAYS=90

# Clean up expired files
make cleanup-old-data
```

### Enable Encryption
```bash
export ENCRYPT_OUTPUT=true
docker-compose up
```
Encrypts all output files with AES-256-GCM.

### Enable Activity Logging
```bash
export LOGS_DIR=logs
docker-compose up
```
Creates audit trail in `logs/processing_activity.jsonl`.

### Auto-Cleanup After Processing
```bash
export AUTO_CLEANUP_ON_EXIT=true
docker-compose up
```
Automatically deletes all output files after processing completes.

---

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATA_RETENTION_DAYS` | Days to retain files (0 = no limit) | `0` | `90` |
| `AUTO_CLEANUP_ON_EXIT` | Delete files after processing | `false` | `true` |
| `LOGS_DIR` | Activity log directory | `logs` | `logs` |
| `ENCRYPT_OUTPUT` | Enable file encryption | `false` | `true` |
| `ENCRYPTION_KEY_PATH` | Custom encryption key path | `.encryption_key` | `/secure/key.bin` |

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make delete-data` | Delete all output files (with confirmation) |
| `make cleanup-old-data` | Delete files older than retention period |
| `make show-retention-status` | Show expired file count |

---

## Data Subject Rights

| Right | How to Exercise |
|-------|-----------------|
| **Access** | Output files in `output/` directory |
| **Rectification** | Edit output files or reprocess PDFs |
| **Erasure** | `make delete-data` |
| **Restriction** | Don't run processing |
| **Portability** | Files already in CSV/JSON/Excel formats |
| **Object** | Stop using application, delete data |

---

## Compliance Checklist

- [ ] Set `DATA_RETENTION_DAYS` appropriate for your use case
- [ ] Enable encryption if processing sensitive data (`ENCRYPT_OUTPUT=true`)
- [ ] Enable activity logging for audit trail (`LOGS_DIR=logs`)
- [ ] Test deletion procedures (`make delete-data`)
- [ ] Document your legal basis for processing
- [ ] Secure encryption key if using encryption
- [ ] Review [PRIVACY_NOTICE.md](PRIVACY_NOTICE.md)

---

## Example Configurations

### Minimal GDPR Compliance (Personal Use)
```bash
# .env
DATA_RETENTION_DAYS=90
LOGS_DIR=logs
```

### Enhanced Security (Business Use)
```bash
# .env
DATA_RETENTION_DAYS=365
AUTO_CLEANUP_ON_EXIT=false
ENCRYPT_OUTPUT=true
ENCRYPTION_KEY_PATH=/secure/encryption.key
LOGS_DIR=logs
```

### High Security (Sensitive Data)
```bash
# .env
DATA_RETENTION_DAYS=30
AUTO_CLEANUP_ON_EXIT=true
ENCRYPT_OUTPUT=true
LOGS_DIR=logs
```

---

## File Locations

| Type | Location | Purpose |
|------|----------|---------|
| Input PDFs | `input/` | Source bank statements |
| Output files | `output/` | Processed transactions |
| Activity logs | `logs/processing_activity.jsonl` | Audit trail |
| Encryption key | `.encryption_key` | AES-256 key (keep secure!) |

---

## Security Best Practices

1. ✅ **Set retention period**: Don't keep data indefinitely
2. ✅ **Enable encryption**: For sensitive financial data
3. ✅ **Secure backups**: Encrypt backup copies
4. ✅ **Restrict access**: Use file system permissions
5. ✅ **Monitor logs**: Review activity log regularly
6. ✅ **Update software**: Keep dependencies up to date
7. ✅ **Test deletion**: Verify files are securely deleted

---

## Troubleshooting

### Files Not Being Deleted
```bash
# Check retention status
make show-retention-status

# Verify DATA_RETENTION_DAYS is set
echo $DATA_RETENTION_DAYS

# Manual cleanup
python3 scripts/delete_data.py --all --force
```

### Encryption Key Issues
```bash
# Check key exists
ls -la .encryption_key

# Generate new key
python3 -c "import secrets; open('.encryption_key', 'wb').write(secrets.token_bytes(32))"
chmod 600 .encryption_key
```

### Activity Log Not Created
```bash
# Create logs directory
mkdir -p logs
chmod 755 logs

# Verify LOGS_DIR setting
echo $LOGS_DIR
```

---

## Need More Help?

- **Full Documentation**: [GDPR_COMPLIANCE.md](GDPR_COMPLIANCE.md)
- **Privacy Notice**: [PRIVACY_NOTICE.md](PRIVACY_NOTICE.md)
- **Encryption Guide**: [ENCRYPTION.md](ENCRYPTION.md)
- **Issues**: [GitHub Issues](https://github.com/longieirl/bankstatements/issues)
