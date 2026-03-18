# Bank Statements Processor

[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/longieirl/bankstatements/packages)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> Automated PDF bank statement extraction to CSV/Excel/JSON with local processing and GDPR compliance.

**Lead Maintainer:** [J Long](https://github.com/longieirl)

## Quick Start

**Local (build from source):**
```bash
make docker-local          # Build image and run via docker-compose
```

**Production (prebuilt image):**
```bash
make docker-remote         # Pull prebuilt image and run via docker-compose
```

## Features

**FREE Tier:**
- PDF extraction with configurable boundaries
- CSV/JSON/Excel export with formatting
- Batch processing with recursive directory scanning
- SHA-256 duplicate detection
- Credit card duplicate detection (ignores transaction type mismatches)
- Transaction type classification (purchase, payment, refund, fee, transfer)
- Monthly transaction summaries
- Expense analysis (recurring charges, outliers)
- IBAN extraction and grouping
- Multi-document type support (bank statements, credit cards, loans)
- GDPR-compliant local processing
- Template-based statement detection (AIB, Revolut, credit cards)

**PAID Tier:**
- All FREE tier features
- Credit card statement support (no IBAN required)
- Loan statement support (no IBAN required)
- Process templates without IBAN patterns

## Configuration

**Initialize Directory Structure:**
```bash
make docker-build          # Build image first if not already built
mkdir -p input output logs
```

**Project Root (all directories under one location):**
```bash
PROJECT_ROOT=/data/bank-app make docker-local
# Uses: /data/bank-app/input, /data/bank-app/output, /data/bank-app/logs
```

**Output Formats:**
```bash
OUTPUT_FORMATS=csv,json,excel make docker-local
```

**Custom Columns:**
```bash
TABLE_COLUMNS='{"Date": [20,80], "Details": [80,250], "Amount": [250,400]}' make docker-local
```

See [`.env.example`](.env.example) for all options.

## Architecture

Clean architecture following SOLID principles with 8 design patterns:

```
src/
├── app.py                  # Entry point (Facade)
├── config/                 # Configuration (DIP)
├── domain/                 # Domain models
├── extraction/             # PDF extraction (Chain of Responsibility, Template Method)
├── services/               # Business logic (SRP)
├── patterns/               # Design patterns (Factory, Repository, Strategy, Singleton)
└── facades/                # Simplified interfaces
```

**Quality:**
- **Coverage:** 92% (1377 tests, 91%+ enforced)
- **Patterns:** Strategy, Repository, Singleton, Factory, Chain of Responsibility, Builder, Facade, Template Method
- **Standards:** Black, Flake8, MyPy, Bandit

## Development

**Common Commands:**
```bash
make help          # Show all commands
make test          # Run tests with coverage
make lint          # Run all linters
make format        # Auto-format code
make pr-ready      # Pre-PR validation
make docker-scan   # Security scan
```

**Git Hooks:**
```bash
./setup-git-hooks.sh  # Install pre-commit hooks
```

**Branch Management:**
```bash
make new-feature NAME=my-feature
make new-fix NAME=my-fix
```

## Documentation

**User Guides:**
- [Output Formats](docs/OUTPUT_FORMATS_USAGE.md)
- [Privacy Notice](docs/PRIVACY_NOTICE.md)
- [GDPR Compliance](docs/GDPR_COMPLIANCE.md)

**Developer Guides:**
- [Architecture](docs/architecture.md)
- [Design Patterns](docs/design_patterns_guide.md)
- [Development Workflow](.github/DEVELOPMENT_WORKFLOW.md)
- [Security Scanning](docs/SECURITY_SCANNING.md)
- [Phase 3: Advanced SBOM & Dependency Analysis](docs/PHASE3_IMPLEMENTATION.md)

**Operations:**
- [Releasing](RELEASING.md)
- [Changelog](CHANGELOG.md)
- [Docker Maintenance](docs/DOCKER_MAINTENANCE.md)

## Contributing

We welcome contributions! 🎉

**Before you start:**
1. ⚠️ **All external contributors must sign the [Contributor License Agreement (CLA)](.github/CLA.md)** before PRs can be merged
2. Read the [Contributing Guide](CONTRIBUTING.md) for detailed instructions
3. Check [Development Workflow](.github/DEVELOPMENT_WORKFLOW.md) for workflow details

**Quick workflow:**
1. Fork the repository
2. Setup: `make setup`
3. Create branch: `make new-feature NAME=your-feature`
4. Make changes + add tests (91%+ coverage required)
5. Validate: `make pr-ready`
6. Submit PR (CLA bot will guide you through signing)

**Requirements:**
- ✅ CLA signed (first-time contributors)
- ✅ All CI checks passing
- ✅ Tests with 91%+ coverage
- ✅ Code follows standards (Black, Flake8, MyPy)
- ✅ Security scans pass (Bandit, Safety, Trivy, pip-audit)
- ✅ License compliance validated
- ✅ [Conventional commits](https://www.conventionalcommits.org/)

**Note:** PRs blocked if CRITICAL vulnerabilities found. See [Security Quick Reference](docs/SECURITY_QUICK_REFERENCE.md).

## Versioning

Follows [Semantic Versioning](https://semver.org/):
- `ghcr.io/longieirl/bankstatements:1.0.0` - Specific version (recommended)
- `ghcr.io/longieirl/bankstatements:latest` - Latest stable
- `ghcr.io/longieirl/bankstatements:main` - Development

```bash
docker run --rm ghcr.io/longieirl/bankstatements:latest --version
```

## License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**Apache License 2.0** - Free for commercial use with modifications allowed.

**Third-Party:**
- [NOTICE](NOTICE) - Attribution notices
- [docs/LICENSES/](docs/LICENSES/) - Full license texts
- [License Compliance](docs/LICENSE_COMPLIANCE.md) - Analysis

**Premium Features:**
Contact maintainer for licensing via GitHub issue with tag `license-inquiry`.

## Acknowledgments

[Thank You](./THANKYOU.md) to all contributors.
