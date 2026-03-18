# Contributing to Bank Statements Processor

Thank you for your interest in contributing to the Bank Statements Processor project! 🎉

This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Contributor License Agreement (CLA)](#contributor-license-agreement-cla)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

---

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

---

## Getting Started

### Prerequisites

- Python 3.11, 3.12, or 3.13
- Git
- Docker (optional, for containerized development)

### Local Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/bankstatements.git
   cd bankstatements
   ```

2. **Set up Development Environment**
   ```bash
   make setup
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Install pre-commit hooks
   - Set up git hooks

3. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

4. **Verify Setup**
   ```bash
   make test
   make check
   ```

---

## Contributor License Agreement (CLA)

**All external contributors must sign a CLA before their contributions can be merged.**

### Why We Require a CLA

The CLA protects both you (the contributor) and the project by:
- Clarifying intellectual property rights
- Ensuring the project can legally distribute your contributions
- Protecting contributors from patent claims
- Maintaining project licensing integrity

### How to Sign the CLA

1. **Submit your Pull Request** as usual
2. **CLA Bot will comment** on your PR with instructions
3. **Read the CLA**: Review [.github/CLA.md](.github/CLA.md)
4. **Sign by commenting**:
   ```
   I have read the CLA Document and I hereby sign the CLA
   ```
5. **One-time process**: You only need to sign once for all future contributions

### Already Signed?

If you've previously signed but the check is failing, comment `recheck` on your PR.

**Note**: Automated bot accounts (dependabot, renovate, etc.) are automatically exempt.

For more details, see [docs/CLA_SETUP.md](docs/CLA_SETUP.md).

---

## Development Workflow

### Branch Naming

- `feature/descriptive-name` - New features
- `fix/descriptive-name` - Bug fixes
- `docs/descriptive-name` - Documentation updates
- `refactor/descriptive-name` - Code refactoring

**Quick Commands**:
```bash
make new-feature NAME=my-feature  # Creates feature/my-feature
make new-fix NAME=my-fix         # Creates fix/my-fix
```

### Making Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our [code standards](#code-standards)

3. **Write tests** for your changes (required)

4. **Run quality checks**
   ```bash
   make pr-ready
   ```
   This runs:
   - Code formatting (Black, isort)
   - Linting (Flake8)
   - Type checking (MyPy)
   - Security scanning (Bandit)
   - Tests with coverage (91% minimum)

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "descriptive commit message"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## Code Standards

### Formatting

- **Line Length**: 88 characters (Black default)
- **Quotes**: Double quotes for strings
- **Imports**: Organized by isort (stdlib → third-party → local)

**Auto-format**:
```bash
make format
```

### Linting

- **Flake8**: Code quality and style
- **MyPy**: Static type checking (strict mode)
- **Bandit**: Security linting

**Run checks**:
```bash
make lint          # Flake8
make type-check    # MyPy
make security      # Bandit + Safety
```

### Type Hints

All functions must have type hints:

```python
def process_transaction(amount: Decimal, date: datetime) -> Transaction:
    """Process a bank transaction."""
    ...
```

### Naming Conventions

- **Classes**: PascalCase (`BankStatementProcessor`)
- **Functions/Variables**: snake_case (`parse_date`)
- **Constants**: UPPER_SNAKE_CASE (`TABLE_TOP_Y`)
- **Private**: `_leading_underscore`

### Documentation

- **Docstrings**: Use Google-style docstrings for all public APIs
- **Comments**: Explain "why", not "what"
- **Type hints**: Prefer type hints over docstring type annotations

### Design Patterns

This project uses several design patterns:
- **Facade**: Simplified interfaces
- **Strategy**: Interchangeable algorithms
- **Repository**: Data access abstraction
- **Factory**: Object creation
- **Chain of Responsibility**: Sequential handlers

Follow existing patterns when adding new features.

---

## Testing

### Test Requirements

- **Coverage**: Minimum 91% code coverage (enforced by CI)
- **Types**: Unit tests + integration tests
- **Fast**: Tests should run in < 30 seconds locally
- **Isolated**: No external dependencies (use mocks)

### Running Tests

```bash
# All tests with coverage
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Fast parallel execution
make test-fast

# Specific test file
pytest tests/test_processor.py -v
```

### Writing Tests

```python
# tests/services/test_my_service.py
import pytest
from src.services.my_service import MyService

def test_my_service_success():
    """Test MyService successful operation."""
    service = MyService()
    result = service.process("input")
    assert result == "expected"

def test_my_service_error():
    """Test MyService error handling."""
    service = MyService()
    with pytest.raises(ValueError):
        service.process(None)
```

### Test Organization

```
tests/
├── test_app.py           # Entry point tests
├── test_processor.py     # Core processor
├── services/             # Service layer tests
├── extraction/           # PDF extraction tests
└── patterns/             # Design pattern tests
```

---

## Pull Request Process

### Before Submitting

1. ✅ Run `make pr-ready` successfully
2. ✅ Add tests for new functionality
3. ✅ Update documentation if needed
4. ✅ Check your code follows our standards
5. ✅ Rebase on latest `main` branch

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass locally
- [ ] Coverage maintained at 91%+

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] CLA signed (for first-time contributors)
```

### CI Checks

Your PR must pass:
- ✅ **CLA Signature** (first-time contributors)
- ✅ **Linting**: Black, isort, Flake8, MyPy
- ✅ **Tests**: Python 3.11, 3.12, 3.13 with 91%+ coverage
- ✅ **Security**: Bandit, Safety, CodeQL
- ✅ **Docker**: Build and Trivy scan

### Review Process

1. **Automated checks** run on your PR
2. **Maintainer review** (usually within 48 hours)
3. **Address feedback** if requested
4. **Approval and merge** by maintainers

### Merge Requirements

- ✅ All CI checks passing
- ✅ At least one maintainer approval
- ✅ CLA signed
- ✅ No merge conflicts
- ✅ Branch up-to-date with main

---

## Reporting Bugs

### Before Reporting

1. Check [existing issues](https://github.com/longieirl/bankstatements/issues)
2. Verify you're using the latest version
3. Reproduce with minimal test case

### Bug Report Template

```markdown
**Describe the bug**
Clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. ...
2. ...

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.12.0]
- Project version: [e.g., 1.0.1]

**Additional context**
Screenshots, logs, or other relevant info.
```

---

## Feature Requests

We welcome feature requests! Please:

1. Check [existing issues](https://github.com/longieirl/bankstatements/issues) first
2. Create a new issue with `enhancement` label
3. Describe the use case and benefits
4. Propose implementation approach (optional)

---

## Development Commands Reference

### Setup & Installation
```bash
make setup              # Full dev environment
make install-dev        # Dev dependencies only
make pre-commit-install # Git hooks
```

### Code Quality
```bash
make format            # Format with Black + isort
make lint              # Run Flake8
make type-check        # Run MyPy
make security          # Security scans
make check             # All quality checks
make pr-ready          # Full PR validation
```

### Testing
```bash
make test              # All tests + coverage
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-fast         # Parallel execution
```

### Docker
```bash
make docker-build      # Build image
make docker-up         # Start with compose
make docker-scan       # Trivy scan
```

### Release Management
```bash
make version-bump-patch # Bump patch version
make version-bump-minor # Bump minor version
make version-bump-major # Bump major version
```

---

## Questions or Help?

- **Documentation**: Check [docs/](docs/) directory
- **Issues**: Open a [GitHub issue](https://github.com/longieirl/bankstatements/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/longieirl/bankstatements/discussions)

---

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for contributing to Bank Statements Processor! 🚀
