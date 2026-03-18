# Docker Documentation Index

> **Comprehensive guide to running Bank Statements Processor in Docker**

This document serves as the central navigation hub for all Docker-related documentation.

---

## Quick Links

| Topic | File | Description |
|-------|------|-------------|
| **Getting Started** | [DOCKER_USAGE.md](DOCKER_USAGE.md) | Basic setup and usage (302 lines) |
| **Commands Reference** | [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) | All Docker commands (234 lines) |
| **Troubleshooting** | [DOCKER_TROUBLESHOOTING.md](DOCKER_TROUBLESHOOTING.md) | Common issues and solutions (426 lines) |
| **Security** | [DOCKER_SECURITY.md](DOCKER_SECURITY.md) | Security best practices (564 lines) |
| **SSL Security** | [DOCKER_SSL_SECURITY.md](DOCKER_SSL_SECURITY.md) | SSL/TLS configuration (382 lines) |
| **Maintenance** | [DOCKER_MAINTENANCE.md](DOCKER_MAINTENANCE.md) | Updates and cleanup (139 lines) |
| **Modes** | [DOCKER_MODES.md](DOCKER_MODES.md) | Run modes and configurations (157 lines) |
| **README** | [DOCKER_README.md](DOCKER_README.md) | Docker overview (218 lines) |

---

## Documentation by Use Case

### I want to get started with Docker

1. **Read first**: [DOCKER_README.md](DOCKER_README.md) - Overview of Docker support
2. **Then follow**: [DOCKER_USAGE.md](DOCKER_USAGE.md) - Setup and basic usage
3. **Command reference**: [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) - All available commands

### I'm having problems

1. **Check**: [DOCKER_TROUBLESHOOTING.md](DOCKER_TROUBLESHOOTING.md) - Common issues and fixes
2. **Verify**: [DOCKER_USAGE.md](DOCKER_USAGE.md) - Ensure correct setup

### I need to secure my deployment

1. **Start here**: [DOCKER_SECURITY.md](DOCKER_SECURITY.md) - Comprehensive security guide
2. **SSL/TLS**: [DOCKER_SSL_SECURITY.md](DOCKER_SSL_SECURITY.md) - Certificate management

### I need to maintain my containers

1. **Updates**: [DOCKER_MAINTENANCE.md](DOCKER_MAINTENANCE.md) - Updating and cleaning up
2. **Modes**: [DOCKER_MODES.md](DOCKER_MODES.md) - Different operational modes

---

## Quick Start (All Tiers)

### FREE Tier (No License Required)

**Local build (default):**
```bash
make docker-local
```

**Production image:**
```bash
make docker-remote
```

**FREE tier includes:**
- ✅ CSV, JSON, Excel output
- ✅ Recursive directory scanning
- ✅ Monthly summaries and expense analysis
- ✅ IBAN required for processing

### PAID Tier (License Required)

```bash
# Generate license (on host)
python -m scripts.generate_license PAID "DOCKER-001" "Your Name" 365

# Run with license (local build)
make docker-local
```

**PAID tier adds:**
- ✅ No IBAN requirement (credit card statements)

---

## Common Commands

```bash
# Build and run from source (default)
make docker-local

# Pull and run production image
make docker-remote

# Build image only
make docker-build

# View logs
docker-compose logs -f

# Stop and cleanup
docker-compose down

# Force rebuild
docker-compose build --no-cache
```

See [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) for complete command reference.

---

## Environment Configuration

Key environment variables (see [DOCKER_USAGE.md](DOCKER_USAGE.md) for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_FORMATS` | `csv,json` | Output formats (csv, json, excel) |
| `SORT_BY_DATE` | `true` | Sort transactions chronologically |
| `GENERATE_MONTHLY_SUMMARY` | `false` | Generate monthly summaries |
| `GENERATE_EXPENSE_ANALYSIS` | `true` | Generate expense analysis |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Troubleshooting Quick Reference

| Issue | Solution | Details |
|-------|----------|---------|
| Permission denied | Fix volume permissions | [DOCKER_TROUBLESHOOTING.md#permissions](DOCKER_TROUBLESHOOTING.md) |
| Container exits immediately | Check logs with `docker logs` | [DOCKER_TROUBLESHOOTING.md#exit](DOCKER_TROUBLESHOOTING.md) |
| No output files generated | Verify PDF format | [DOCKER_TROUBLESHOOTING.md#no-output](DOCKER_TROUBLESHOOTING.md) |
| License not recognized | Check mount path | [DOCKER_TROUBLESHOOTING.md#license](DOCKER_TROUBLESHOOTING.md) |

See [DOCKER_TROUBLESHOOTING.md](DOCKER_TROUBLESHOOTING.md) for comprehensive troubleshooting.

---

## Security Quick Reference

| Topic | Key Points | Details |
|-------|------------|---------|
| **Network** | Use user-defined networks, avoid host mode | [DOCKER_SECURITY.md#network](DOCKER_SECURITY.md) |
| **Volumes** | Read-only where possible, specific mounts | [DOCKER_SECURITY.md#volumes](DOCKER_SECURITY.md) |
| **Images** | Use specific tags, scan regularly | [DOCKER_SECURITY.md#images](DOCKER_SECURITY.md) |
| **SSL/TLS** | Certificates for sensitive data | [DOCKER_SSL_SECURITY.md](DOCKER_SSL_SECURITY.md) |

See [DOCKER_SECURITY.md](DOCKER_SECURITY.md) for complete security guide.

---

## Maintenance Quick Reference

| Task | Command | Frequency |
|------|---------|-----------|
| **Update image** | `make docker-remote` | Weekly |
| **Clean old images** | `docker image prune -a` | Monthly |
| **Clean volumes** | `docker volume prune` | As needed |
| **Clean containers** | `docker container prune` | As needed |

See [DOCKER_MAINTENANCE.md](DOCKER_MAINTENANCE.md) for maintenance procedures.

---

## Docker Compose Configuration

Basic `docker-compose.yml` (see [DOCKER_MODES.md](DOCKER_MODES.md) for local vs production modes):

```yaml
services:
  bankstatementsprocessor:
    image: bankstatementsprocessor:latest   # local build (default)
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./license.json:/app/license.json  # PAID tier only
    environment:
      - OUTPUT_FORMATS=csv,json,excel
      - SORT_BY_DATE=true
      - GENERATE_MONTHLY_SUMMARY=true
      - LOG_LEVEL=INFO
```

See [DOCKER_MODES.md](DOCKER_MODES.md) for advanced configurations.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 Docker Host                      │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │     bankstatements Container            │    │
│  │                                         │    │
│  │  ┌──────────┐      ┌──────────────┐   │    │
│  │  │  Python  │──────│  Processing  │   │    │
│  │  │   3.11+  │      │    Engine    │   │    │
│  │  └──────────┘      └──────────────┘   │    │
│  │                                         │    │
│  └────────────────────────────────────────┘    │
│           │              │              │        │
│           ▼              ▼              ▼        │
│    ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│    │  /input  │   │  /output │   │ license  │ │
│    │  volume  │   │  volume  │   │  .json   │ │
│    └──────────┘   └──────────┘   └──────────┘ │
│           │              │              │        │
└───────────┼──────────────┼──────────────┼────────┘
            │              │              │
            ▼              ▼              ▼
      Host volumes     Host volumes   Host file
```

---

## Best Practices

1. **Always use specific image tags** in production (not `:latest`)
2. **Mount specific directories** not entire filesystem
3. **Use read-only volumes** where possible
4. **Scan images regularly** with `docker scan` or Trivy
5. **Keep images updated** to get security patches
6. **Use docker-compose** for reproducible deployments
7. **Check logs** with `docker logs` for debugging
8. **Clean up regularly** to save disk space

---

## Support and Resources

- **Main README**: [../README.md](../README.md)
- **Issue Tracker**: https://github.com/longieirl/bankstatements/issues
- **Releases**: https://github.com/longieirl/bankstatements/releases
- **Container Registry**: https://github.com/longieirl/bankstatements/packages

---

## Document Maintenance

**Last Updated**: 2026-02-19
**Maintained By**: Project maintainers
**Review Frequency**: Quarterly

This index consolidates 8 separate Docker documentation files (2,422 lines total) into a single navigation hub.
