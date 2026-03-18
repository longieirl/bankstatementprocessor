# Python Version Support

## Supported Versions

The bankstatements project officially supports the following Python versions:

- **Python 3.11** ✅ (Minimum required)
- **Python 3.12** ✅ (Recommended for production)
- **Python 3.13** ✅ (Fully tested and supported)

## Version Policy

We follow a rolling support policy:
- Support the current stable Python release
- Support the previous two stable releases
- Docker images use Python 3.12 by default (best balance of stability and modern features)

## Compatibility Testing

All supported versions are tested in CI/CD:
- Linting and type checking: Python 3.12
- Unit tests: Python 3.11, 3.12, 3.13 (matrix testing)
- Docker images: Python 3.12

## Version-Specific Features

### Python 3.11+
- **Required minimum version**
- PEP 646 (Variadic Generics)
- Improved error messages
- Faster startup and runtime

### Python 3.12 (Recommended)
- PEP 701 (f-strings in annotations)
- Improved type parameter syntax
- Better performance (~15% faster than 3.11)
- Enhanced error messages

### Python 3.13
- PEP 594 (Dead batteries removal)
- Experimental JIT compiler support
- Improved REPL
- Enhanced debugging features

## Migration Guide

### From Python 3.10 to 3.11+

Python 3.10 is **not supported**. To migrate:

1. Install Python 3.11 or later:
   ```bash
   # macOS
   brew install python@3.12

   # Ubuntu/Debian
   sudo apt install python3.12
   ```

2. Update your virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run tests to verify compatibility:
   ```bash
   pytest tests/
   ```

### Using Python 3.13

Python 3.13 is fully supported but may show deprecation warnings from third-party dependencies:

```bash
# Run with Python 3.13
python3.13 -m pytest tests/
```

**Known deprecation warnings**:
- pytest internal AST usage (will be fixed in pytest 8.0+)
- No action required from users

## Docker Images

### Current Base Image
```dockerfile
FROM python:3.12-slim@sha256:5e2dbd4bbdd9c0e67412aea9463906f74a22c60f89eb7b5bbb7d45b66a2b68a6
```

### Why Python 3.12?
- **Stability**: Production-ready since October 2023
- **Performance**: ~15% faster than 3.11
- **Security**: Regular security updates from Python team
- **Compatibility**: Best balance between modern features and ecosystem support

### Building with Different Versions

To use Python 3.11:
```dockerfile
FROM python:3.11-slim@sha256:5be45dbade29bebd6886af6b438fd7e0b4eb7b611f39ba62b430263f82de36d2 AS base
```

To use Python 3.13:
```dockerfile
FROM python:3.13-slim AS base
```

## Local Development

### Recommended Setup
```bash
# Install Python 3.12
brew install python@3.12  # macOS
# or
sudo apt install python3.12  # Ubuntu/Debian

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements/dev.txt
pip install -r requirements/test.txt

# Verify installation
python --version  # Should show Python 3.12.x
pytest tests/
```

### Using pyenv (Multi-version Management)
```bash
# Install multiple Python versions
pyenv install 3.11.10
pyenv install 3.12.7
pyenv install 3.13.1

# Set local version for project
pyenv local 3.12.7

# Test with all versions
for version in 3.11.10 3.12.7 3.13.1; do
  pyenv shell $version
  pytest tests/
done
```

## Type Checking Configuration

Type checking is configured for Python 3.12:

```toml
[tool.mypy]
python_version = "3.12"

[tool.pyright]
pythonVersion = "3.12"
```

This ensures type hints are validated against Python 3.12 semantics.

## CI/CD Configuration

### GitHub Actions Matrix

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12', '3.13']
```

All versions must pass tests before merging PRs.

## Deprecation Policy

When Python releases a new version:
1. We test compatibility within 2 weeks
2. CI is updated to include the new version
3. Docker images are updated after 3 months (to ensure ecosystem stability)

When Python deprecates a version:
1. We continue support for 6 months after EOL
2. Security backports are applied as needed
3. Users are notified via release notes

## Version History

- **2024-12**: Python 3.11 minimum requirement established
- **2026-01**: Added Python 3.12 and 3.13 support
- **2026-01**: Docker upgraded to Python 3.12
- **2026-01**: CI/CD updated to test all supported versions

## FAQ

### Why not Python 3.10?
Python 3.10 lacks key features we use:
- PEP 646 (Variadic Generics)
- Improved type hints
- Performance improvements

### Will you support Python 3.14?
Yes, we'll add support when Python 3.14 is released (expected October 2025).

### Can I use Python 3.9?
No. The minimum version is Python 3.11. Please upgrade.

### Which version should I use in production?
**Python 3.12** is recommended for production due to:
- Stability and maturity
- Performance improvements
- Active security support
- Best ecosystem compatibility

## Resources

- [Python Release Schedule](https://peps.python.org/pep-0693/)
- [Python 3.12 Release Notes](https://docs.python.org/3.12/whatsnew/3.12.html)
- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)
