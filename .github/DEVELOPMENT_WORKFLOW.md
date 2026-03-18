# Development Workflow Guide

This guide outlines the development workflow for the Bank Statements Processor project, designed to work with GitHub's free plan limitations for private repositories.

## Quick Start for New Developers

```bash
# 1. Run setup script (installs git hooks and pre-commit)
chmod +x setup-git-hooks.sh
./setup-git-hooks.sh

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements/dev.txt

# 3. Verify everything works
make test
```

## Branch Protection Strategy

Since this is a private repository on GitHub's free plan, we use a **multi-layered protection approach**:

### 🛡️ Protection Layers

1. **Local Git Hooks** - Block problematic commits/pushes before they leave your machine
2. **Pre-commit Hooks** - Comprehensive quality checks during commit
3. **GitHub Branch Protection** - Basic PR requirements (available on free plan)
4. **CI/CD Pipeline** - Comprehensive testing and security scanning
5. **Team Discipline** - Clear workflow guidelines and code review culture

## 📋 Development Workflow

### 1. **Starting New Work**

```bash
# Always start from main
git checkout main
git pull origin main

# Create feature branch with descriptive name
git checkout -b feature/pdf-encryption-support
# OR
git checkout -b fix/transaction-parser-regex
# OR
git checkout -b chore/update-dependencies
```

**Branch Naming Convention:**
- `feature/` - New features
- `fix/` - Bug fixes
- `chore/` - Maintenance tasks
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding/updating tests

### 2. **Making Changes**

```bash
# Make your changes
vim src/processor.py

# Check what changed
git status
git diff

# Stage changes
git add src/processor.py

# Commit with conventional format (enforced by commit-msg hook)
git commit -m "feat(processor): add support for encrypted PDF parsing"
```

**Commit Message Format (Required):**
```
<type>(<scope>): <description>

Valid types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
Example: feat(pdf): add support for password-protected files
```

### 3. **Quality Checks (Automated)**

The following checks run automatically on commit/push:

- ✅ **Code formatting** (Black)
- ✅ **Import sorting** (isort)
- ✅ **Linting** (Flake8)
- ✅ **Type checking** (MyPy)
- ✅ **Security scanning** (Bandit)
- ✅ **Secrets detection** (detect-secrets)
- ✅ **Docker linting** (Hadolint)
- ✅ **Dependency vulnerabilities** (Safety)

### 4. **Testing Locally**

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration

# Check coverage
make coverage

# Run security checks
make security

# Format and lint code
make format
make lint
```

### 5. **Pushing Changes**

```bash
# Push feature branch (pre-push hook prevents pushing to main)
git push origin feature/pdf-encryption-support

# If branch doesn't exist remotely yet
git push -u origin feature/pdf-encryption-support
```

### 6. **Creating Pull Request**

1. **Open PR on GitHub**
   - Use the provided PR template
   - Fill in description, testing notes, and checklist

2. **Required for PR Merge:**
   - ✅ At least 1 approval from code owner
   - ✅ All CI checks pass (`lint`, `test`, `docker-build`, `codeql`)
   - ✅ Branch is up-to-date with main
   - ✅ All conversations resolved

3. **PR Review Process:**
   - Address reviewer feedback
   - Push additional commits (will trigger re-review if configured)
   - Ensure CI passes after changes

### 7. **Merging**

- **Only merge through GitHub UI**
- Use "Squash and merge" for cleaner history (recommended)
- Delete feature branch after merge (automated if configured)

## 🚫 What's Blocked

The following are **automatically prevented**:

- ❌ Direct pushes to `main` branch (pre-push hook)
- ❌ Commits with invalid message format (commit-msg hook)
- ❌ Code that doesn't pass linting (pre-commit hooks)
- ❌ Large files (>1MB) being committed
- ❌ Secrets being committed (detect-secrets)
- ❌ PRs with failing CI checks
- ❌ PRs without required approvals

## 🆘 Emergency Procedures

### Force Push (Use Sparingly)
```bash
# If pre-push hook blocks legitimate push
git push --no-verify origin feature-branch

# If you need to force push to main (EMERGENCY ONLY)
git push --no-verify origin main
```

### Bypass Pre-commit Checks
```bash
# Skip all pre-commit checks (NOT RECOMMENDED)
git commit --no-verify -m "emergency: critical hotfix"

# Skip specific check
SKIP=flake8 git commit -m "fix: temporary bypass for urgent fix"
```

## 🔧 Common Issues & Solutions

### Pre-commit Hook Failures

**Black formatting issues:**
```bash
# Auto-fix formatting
black src tests
git add -u
git commit -m "style: fix code formatting"
```

**Flake8 linting errors:**
```bash
# Check what's wrong
flake8 src tests

# Common fixes
# - Remove unused imports
# - Fix line length (max 88 chars)
# - Add missing docstrings
```

**MyPy type errors:**
```bash
# Check type issues
mypy src

# Common fixes
# - Add type annotations
# - Use # type: ignore for complex cases
# - Install missing type stubs
```

### Git Hook Issues

**Hooks not running:**
```bash
# Reinstall hooks
./setup-git-hooks.sh

# OR manually
git config core.hooksPath .githooks
pre-commit install --install-hooks
```

**Can't push to main:**
```
✅ This is working as intended!
Follow the proper workflow:
1. Create feature branch
2. Push feature branch
3. Create PR
4. Merge through GitHub
```

## 📊 Quality Metrics

We maintain high quality through:

- **Code Coverage:** 92%+ (far exceeds industry standards)
- **Security:** No high/critical vulnerabilities
- **Performance:** All tests pass within reasonable time
- **Documentation:** All public APIs documented
- **Conventional Commits:** 100% compliance

## 🎯 Best Practices

### Code Style
- Use Black formatting (88 char line length)
- Follow PEP 8 guidelines
- Add type hints to public APIs
- Write descriptive docstrings

### Testing
- Write tests for new features
- Maintain/update tests when refactoring
- Use meaningful test names
- Mock external dependencies

### Security
- Never commit secrets/credentials
- Review security scan results
- Use parameterized queries for databases
- Validate all external inputs

### Performance
- Profile code for bottlenecks
- Use appropriate data structures
- Cache expensive operations when possible
- Monitor memory usage in Docker containers

## 📚 Additional Resources

- [Branch Protection Setup](.github/BRANCH_PROTECTION_SETUP.md)
- [PR Template](.github/PULL_REQUEST_TEMPLATE.md)
- [CI/CD Workflow](.github/workflows/ci.yml)
- [Pre-commit Configuration](.pre-commit-config.yaml)

## 🤝 Getting Help

- **Repository Issues:** Create GitHub issue
- **Urgent Problems:** Contact @longieirl
- **Documentation:** Check README.md and docs/
- **CI/CD Issues:** Check GitHub Actions logs

---

**Remember:** This workflow ensures code quality and security while working within GitHub's free plan limitations. The multi-layered approach provides robust protection through local tools, CI/CD, and team discipline.