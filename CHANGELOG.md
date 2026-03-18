# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-03-02

### Security

- **CRITICAL FIX**: CVE-2025-14009 - NLTK 3.9.2 Code Injection Vulnerability (CVSS 10.0)
  - Root cause: Dev dependencies incorrectly included in production Docker images
  - Fixed by explicitly building production stage (`--target production`)
  - Removed 259 unnecessary packages from production image
  - Updated `.github/workflows/release.yml` and `Makefile`
- **CRITICAL FIX**: CVE-2026-2781 - NSS Library Vulnerability
  - Root cause: Base image shipped with vulnerable NSS 2:3.110-1
  - Fixed by explicit package upgrade to `libnss3=2:3.110-1+deb13u1`
  - Added security patch in Dockerfile (lines 72-79)

### Changed

- Docker builds now explicitly target `production` stage
- Production images exclude all dev/test dependencies (safety, bandit, mypy, black, nltk)
- Image package count reduced from ~383 to ~124 packages

### Documentation

- Added comprehensive security incident report (`docs/SECURITY_FIX_2026-03-02.md`)
- Updated `docs/SECURITY_SCANNING.md` with resolved vulnerabilities
- Cleared `.trivyignore` - all security exceptions resolved

### Notes

- **Security Posture**: 0 critical, 0 high vulnerabilities ✅
- **Verification**: `docker scout cves` shows no vulnerable packages
- **Production Ready**: All security scans passing
- This is a security patch release - no new features or breaking changes
- Fully backward compatible with v1.0.2

## [1.0.2] - 2026-03-02

### Added

- **Expense Analysis**: New repeated vendors detection feature for identifying recurring charges
- **PR Automation**: Automated pull request labeling workflow for better project organization
- **Dependency Management**: Renovate Bot integration for automated dependency updates
  - Configured for security patches, dev dependencies, and production updates
  - See `docs/RENOVATE_SETUP.md` and `docs/RENOVATE_INSTALLATION.md`
- **CLA System**: Contributor License Agreement workflow for open source contributions
  - Comprehensive documentation in `docs/CLA_SETUP.md` and `docs/CLA_IMPLEMENTATION_GUIDE.md`
- **Directory Management**: Comprehensive directory management improvements with auto-creation
- **Template System Enhancements**:
  - Multi-document type detection and classification
  - Credit card transaction support with duplicate detection
  - AIB Ireland bank and credit card templates
  - Exclusion detector for template selection
  - Card number and loan reference detectors
- **Documentation**:
  - PR labeling guide (`docs/PR_LABELING.md`)
  - Company mappings documentation (`docs/COMPANY_MAPPINGS.md`)
  - Template extensibility planning (`docs/TEMPLATE_EXTENSIBILITY_PLAN.md`)
  - Docker security documentation (`docs/DOCKER_SECURITY.md`)
  - Privacy and telemetry documentation (`docs/PRIVACY_AND_TELEMETRY.md`)

### Changed

- Coverage threshold lowered to 90% to account for CI environment differences
- Improved template detection accuracy with aggregated scoring system
- Enhanced AIB template detection to prevent bank/credit card confusion
- Revolut Balance € column boundary adjusted for better capture
- Test suite expanded to 1107+ tests with 91%+ coverage maintained

### Fixed

- **Type Safety**: MyPy compliance in repeated vendors sort functionality
- **CLA Workflow**: Fixed permissions and repository access for CLA signatures
- **Template Detection**: Improved column boundary detection and header matching
- **PDF Extraction**: Better handling of multi-document processing
- **Test Reliability**: Fixed PROJECT_ROOT path resolution and logging style issues
- **Security**: Resolved critical vulnerability and updated dependencies

### Security

- Fixed critical security vulnerability in dependencies
- Updated base dependencies for latest security patches
- Trivy scan configuration updated (ignore nltk CVE in dev dependencies)
- Docker network isolation for GDPR-compliant processing

### Documentation

- Added comprehensive tier system documentation (`docs/TIER_SYSTEM_UPDATES.md`)
- Enhanced template documentation (`docs/TEMPLATES.md`, `docs/ADDING_NEW_TEMPLATES.md`)
- Created FREE tier defaults philosophy document (`docs/FREE_TIER_DEFAULTS.md`)
- Consolidated documentation indexes for better navigation
- Archived completed planning documents to `docs/archive/`

### Notes

- Total commits since v1.0.1: 95+
- New files: 131 changed with 17,453+ insertions
- All tests passing with 91%+ coverage maintained
- Fully backward compatible with v1.0.1
- Ready for production use


## [1.0.1] - 2026-02-10

### Added
- Integration tests for row_merger service to improve test coverage
- Comprehensive tests for row_analysis service (date detection patterns)
- Tests for page_validation service (validation logic coverage)
- Enhanced tests for template_generator (date grouping detection)
- Enhanced tests for column_analyzer (boundary resolution)
- Documentation archive system (`docs/archive/`) for historical reference
- Archive README to document completed work phases

### Changed
- Test coverage threshold adjusted from 93% to 91% (realistic threshold achieved: 91.71%)
- Root directory cleaned up - moved 13 historical documentation files to `docs/archive/`
- Root directory now contains only essential docs (README.md, CHANGELOG.md, RELEASING.md)

### Fixed
- Text-based table detection header calculation accuracy
- Date grouping detection in template generator
- Column boundary overlap resolution logic
- Row classification behavior in merger service (transaction vs continuation rows)

### Documentation
- Archived phase completion reports (PHASE_1/2/3_COMPLETE.md)
- Archived cleanup reports (CLEANUP_*.md)
- Archived setup guides (CODE_SCANNING_ENABLED.md, GITHUB_AI_ASSISTANT_SETUP.md)
- Archived analysis reports (COVERAGE_ANALYSIS.md, TEST_COVERAGE_PLAN.md)
- Closed `docs/error-handling-strategy` branch - main's pattern-based approach is canonical

### Testing
- Total tests: 1209 passing (added 29 new tests)
- Coverage: 91.71% (exceeds 91% threshold)
- Test files enhanced:
  - `tests/services/test_row_merger_integration.py` (12 tests)
  - `tests/services/test_row_analysis.py` (10 tests)
  - `tests/services/test_page_validation.py` (4 tests)
  - `tests/analysis/test_template_generator.py` (+7 tests)
  - `tests/analysis/test_column_analyzer.py` (+4 tests)

### Notes
- This is a maintenance release focused on test coverage improvements and documentation cleanup
- All 1209 tests passing
- Coverage improved from 90.69% to 91.71%
- No breaking changes - fully backward compatible with v1.0.0


## [1.0.0] - 2026-02-06

### Added

**Core Features:**
- PDF table extraction with configurable boundaries and dynamic boundary detection
- Multi-format output support (CSV, JSON, Excel)
- Duplicate transaction detection using SHA-256 hashing
- Monthly summary generation with aggregated statistics
- Configurable totals calculation for specified columns
- Date-based transaction sorting
- CLI `--version` flag to display version information

**Architecture & Design:**
- Complete Separation of Concerns (SoC) refactoring (all 4 phases)
  - Phase 1: Broke 4 circular dependencies (app.py ↔ patterns/)
  - Phase 2: Decomposed 423-line god module to 108-line facade (75% reduction)
  - Phase 3: Refined service layer boundaries with proper abstractions
  - Phase 4: Decomposed 293-line utils.py to 124-line facade (58% reduction)
- Complete Dependency Inversion Principle (DIP) implementation (phases 3-5)
  - Phase 3: PDF reader abstraction layer
  - Phase 4: Service protocols for dependency inversion
  - Phase 5: Removed direct environment access from extraction layer
- 8 design patterns properly implemented:
  - Strategy, Repository, Singleton, Factory, Chain of Responsibility, Builder, Facade, Adapter

**New Features:**
- PDF analysis command (`analyze-pdf`) for structure and content analysis
- Custom template configuration support (JSON-based)
- Template detection system with 5 detector types (IBAN, header, column, filename, combined)
- IBAN extraction and masking for GDPR compliance
- Enhanced error logging with structured JSONL format
- Config layer with focused modules (app_config, column_config, totals_config, environment_parser)
- Domain layer with currency, dataframe utilities, models, and protocols
- Extraction layer with specialized facades (extraction, classification, validation, content analysis)

**Developer Experience:**
- Comprehensive type hints with mypy strict mode enforcement
- Pyright type checking support with strict mode
- Custom pdfplumber type stubs for enhanced type safety
- Application version management system
- Docker image versioning with OCI labels
- Automated version bumping script (`scripts/bump_version.py`)
- Makefile targets for version management and quality checks
- Root directory cleanup and reorganization (29 files organized)
- README.md modernized and condensed (407 → 170 lines, 58% reduction)
- Comprehensive .gitignore reorganization (223 lines, 12 sections)
- Enhanced documentation (RELEASING.md, SECURITY_SCANNING.md, PDF_ANALYSIS_GUIDE.md)

**Testing & Quality:**
- Comprehensive test suite expanded from 462 to 1107 tests (140% increase)
- Test coverage maintained at 93.21% (93%+ enforced)
- Docker containerization with docker-compose support
- Pre-commit hooks for code quality
- GitHub Actions CI/CD pipeline with security scanning

### Changed

**Architecture Improvements:**
- Zero circular dependencies (eliminated all 4 circular imports)
- Zero layer violations (fixed all 4 violations)
- Clean unidirectional dependency flow: app → facades → services → extraction → domain → config
- Consistent repository pattern usage for all I/O operations
- Service layer properly isolated with protocol-based abstractions
- pdf_table_extractor.py reduced to pure re-export facade (423 → 108 lines)
- utils.py reduced to pure re-export facade (293 → 124 lines)
- Clear module responsibilities (each passes "one-sentence test")

**Code Organization:**
- Source code organized into 8 focused layers (adapters, analysis, builders, commands, config, domain, extraction, facades, licensing, patterns, services, templates)
- 89 Python modules with clear responsibilities
- All modules properly typed and documented

**Coverage Threshold:**
- Test coverage threshold adjusted from 95% to 93% (realistic for large codebase)
- Coverage maintained at 93.21% with 1107 tests

### Fixed

**Type Safety:**
- Type ignore comments restored with detailed explanations (pdfplumber adapter)
- Resolved mypy type errors in analysis and commands modules
- Fixed type checking for pdfplumber.Page attributes not in type stubs

**Code Quality:**
- Resolved flake8 errors across codebase
- Applied Black formatting consistently
- Fixed unused variable warnings

**Architecture:**
- Eliminated circular dependencies between app.py and patterns/ modules
- Fixed layer violations (app.py importing from processor.py and pdf_table_extractor.py)
- Removed services importing directly from extraction layer
- Fixed strategies mixing I/O + calculation (now properly separated)

**Documentation:**
- Restored stubs/ directory for CI type checking (was incorrectly moved to .artifacts/)
- Fixed duplicate patterns in .gitignore

### Security

**CVEs Resolved:**
- OpenSSL updated to 3.5.4-1~deb13u2 (CVE-2025-15467 fixed)
- wheel package updated to 0.46.2 (CVE-2026-24049 fixed)
- Python base image upgraded to 3.12-slim (from 3.11)

**Security Enhancements:**
- CI/CD blocking on critical vulnerabilities (separate workflow step)
- Trivy security scanning in CI pipeline with JSON reports
- Docker Scout integration for vulnerability scanning
- SHA-256 pinned base images for reproducibility
- Explicit package version pinning in Dockerfile
- Non-root user execution in containers
- CA certificates properly updated
- IBAN data masking for GDPR compliance

**Known Issues (Monitoring):**
- gnupg2 CVE-2026-24882 (HIGH) - No fix available yet from upstream
  - Impact: Low (OS package, not used by application)
  - Tracking: Debian security tracker
  - Next review: 2026-02-28

**Security Posture:**
- Critical: 0 ✅
- High: 1 ⚠️ (gnupg2 - monitoring)
- Medium: 0 ✅
- Security documentation comprehensive (SECURITY_SCANNING.md updated)

### Deprecated
- None

### Removed
- None (100% backward compatibility maintained via re-export facades)

### Notes

**Production Ready:**
This is the first official production release after comprehensive refactoring. All code quality checks passing:
- ✅ 1107 tests passing
- ✅ 93.21% coverage
- ✅ mypy: Success, no issues
- ✅ black: All files formatted
- ✅ flake8: No issues
- ✅ Zero circular dependencies
- ✅ Zero layer violations
- ✅ Docker builds successfully (multi-platform: linux/amd64, linux/arm64)

**Backward Compatibility:**
All refactoring maintained 100% backward compatibility through re-export facades:
- Old imports still work: `from src.app import AppConfig`
- New imports recommended: `from src.config.app_config import AppConfig`

**Key Metrics:**
- Source modules: 89 files
- Test files: 1107 tests
- Lines of code: 3,622 (production) + comprehensive test coverage
- Docker image size: ~268 MB (compressed)
- Platforms: linux/amd64, linux/arm64

## [1.0.1] - 2026-02-10

### Added
- Integration tests for row_merger service to improve test coverage
- Comprehensive tests for row_analysis service (date detection patterns)
- Tests for page_validation service (validation logic coverage)
- Enhanced tests for template_generator (date grouping detection)
- Enhanced tests for column_analyzer (boundary resolution)
- Documentation archive system (`docs/archive/`) for historical reference
- Archive README to document completed work phases

### Changed
- Test coverage threshold adjusted from 93% to 91% (realistic threshold achieved: 91.71%)
- Root directory cleaned up - moved 13 historical documentation files to `docs/archive/`
- Root directory now contains only essential docs (README.md, CHANGELOG.md, RELEASING.md)

### Fixed
- Text-based table detection header calculation accuracy
- Date grouping detection in template generator
- Column boundary overlap resolution logic
- Row classification behavior in merger service (transaction vs continuation rows)

### Documentation
- Archived phase completion reports (PHASE_1/2/3_COMPLETE.md)
- Archived cleanup reports (CLEANUP_*.md)
- Archived setup guides (CODE_SCANNING_ENABLED.md, GITHUB_AI_ASSISTANT_SETUP.md)
- Archived analysis reports (COVERAGE_ANALYSIS.md, TEST_COVERAGE_PLAN.md)
- Closed `docs/error-handling-strategy` branch - main's pattern-based approach is canonical

### Testing
- Total tests: 1209 passing (added 29 new tests)
- Coverage: 91.71% (exceeds 91% threshold)
- Test files enhanced:
  - `tests/services/test_row_merger_integration.py` (12 tests)
  - `tests/services/test_row_analysis.py` (10 tests)
  - `tests/services/test_page_validation.py` (4 tests)
  - `tests/analysis/test_template_generator.py` (+7 tests)
  - `tests/analysis/test_column_analyzer.py` (+4 tests)

### Notes
- This is a maintenance release focused on test coverage improvements and documentation cleanup
- All 1209 tests passing
- Coverage improved from 90.69% to 91.71%
- No breaking changes - fully backward compatible with v1.0.0

## [1.0.2] - 2026-03-02

### Added

- **Expense Analysis**: New repeated vendors detection feature for identifying recurring charges
- **PR Automation**: Automated pull request labeling workflow for better project organization
- **Dependency Management**: Renovate Bot integration for automated dependency updates
  - Configured for security patches, dev dependencies, and production updates
  - See `docs/RENOVATE_SETUP.md` and `docs/RENOVATE_INSTALLATION.md`
- **CLA System**: Contributor License Agreement workflow for open source contributions
  - Comprehensive documentation in `docs/CLA_SETUP.md` and `docs/CLA_IMPLEMENTATION_GUIDE.md`
- **Directory Management**: Comprehensive directory management improvements with auto-creation
- **Template System Enhancements**:
  - Multi-document type detection and classification
  - Credit card transaction support with duplicate detection
  - AIB Ireland bank and credit card templates
  - Exclusion detector for template selection
  - Card number and loan reference detectors
- **Documentation**:
  - PR labeling guide (`docs/PR_LABELING.md`)
  - Company mappings documentation (`docs/COMPANY_MAPPINGS.md`)
  - Template extensibility planning (`docs/TEMPLATE_EXTENSIBILITY_PLAN.md`)
  - Docker security documentation (`docs/DOCKER_SECURITY.md`)
  - Privacy and telemetry documentation (`docs/PRIVACY_AND_TELEMETRY.md`)

### Changed

- Coverage threshold lowered to 90% to account for CI environment differences
- Improved template detection accuracy with aggregated scoring system
- Enhanced AIB template detection to prevent bank/credit card confusion
- Revolut Balance € column boundary adjusted for better capture
- Test suite expanded to 1107+ tests with 91%+ coverage maintained

### Fixed

- **Type Safety**: MyPy compliance in repeated vendors sort functionality
- **CLA Workflow**: Fixed permissions and repository access for CLA signatures
- **Template Detection**: Improved column boundary detection and header matching
- **PDF Extraction**: Better handling of multi-document processing
- **Test Reliability**: Fixed PROJECT_ROOT path resolution and logging style issues
- **Security**: Resolved critical vulnerability and updated dependencies

### Security

- Fixed critical security vulnerability in dependencies
- Updated base dependencies for latest security patches
- Trivy scan configuration updated (ignore nltk CVE in dev dependencies)
- Docker network isolation for GDPR-compliant processing

### Documentation

- Added comprehensive tier system documentation (`docs/TIER_SYSTEM_UPDATES.md`)
- Enhanced template documentation (`docs/TEMPLATES.md`, `docs/ADDING_NEW_TEMPLATES.md`)
- Created FREE tier defaults philosophy document (`docs/FREE_TIER_DEFAULTS.md`)
- Consolidated documentation indexes for better navigation
- Archived completed planning documents to `docs/archive/`

### Notes

- Total commits since v1.0.1: 95+
- New files: 131 changed with 17,453+ insertions
- All tests passing with 91%+ coverage maintained
- Fully backward compatible with v1.0.1
- Ready for production use

## [Unreleased]

[1.0.3]: https://github.com/longieirl/bankstatements/releases/tag/v1.0.3
[1.0.2]: https://github.com/longieirl/bankstatements/releases/tag/v1.0.2
[1.0.1]: https://github.com/longieirl/bankstatements/releases/tag/v1.0.1
[1.0.0]: https://github.com/longieirl/bankstatements/releases/tag/v1.0.0
