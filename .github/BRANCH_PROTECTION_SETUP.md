# Branch Protection Setup for Private Repository

This document explains how to set up branch protection for a private GitHub repository on the free plan, which has limited features compared to public repositories or paid plans.

## Available Features on Free Private Repositories

✅ **Available** (Can be configured in GitHub Settings > Branches):
- Require a pull request before merging
- Require approvals (1+ reviewers)
- Dismiss stale PR approvals when new commits are pushed
- Require review from code owners
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require conversation resolution before merging

❌ **NOT Available** (Requires GitHub Team+ plan):
- Restrict pushes that create files larger than specified limit
- Require signed commits
- Require linear history
- Advanced rulesets
- Push restrictions for specific users/teams

## Step-by-Step Setup

### 1. Configure Branch Protection Rule

1. Go to **Settings > Branches** in your GitHub repository
2. Click **Add rule**
3. Set **Branch name pattern**: `main`
4. Enable these settings:

```
✅ Require a pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale PR approvals when new commits are pushed
  ✅ Require review from code owners

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging

  Required status checks (add these exact names):
  - lint
  - test (3.11)
  - test (3.12)
  - docker-build

✅ Require conversation resolution before merging

⚠️ Include administrators: UNCHECKED (allows repo admins to bypass rules in emergencies)
```

### 2. Verify Required Status Checks

After your first CI run, the status check names will appear in the dropdown. Add all of these:

- `lint` - Code Quality & Security checks
- `test (3.11)` - Python 3.11 tests
- `test (3.12)` - Python 3.12 tests
- `docker-build` - Docker build and container security scan

### 3. Create CODEOWNERS File

This file was already created at `.github/CODEOWNERS`. Update it with your team members:

```
# Global code owners - require review for all changes
* @longieirl @teammate1 @teammate2

# Critical files require additional scrutiny
/.github/ @longieirl
/requirements/ @longieirl
/Dockerfile @longieirl
/docker-compose.yml @longieirl
```

## Additional Protection Layers

Since some features aren't available, we implement additional protection through:

### 1. **Strict Pre-commit Hooks** (Local Enforcement)
- Code formatting (Black)
- Linting (Flake8)
- Type checking (MyPy)
- Security scanning (Bandit)
- File size limits
- Commit message validation

### 2. **Comprehensive CI/CD Pipeline**
- Multiple security scanners
- Docker vulnerability scanning
- Dependency vulnerability checks
- Code quality gates
- Test coverage requirements

### 3. **Local Git Hooks**
- Prevent direct pushes to main
- Enforce commit message format
- Run local security checks

### 4. **Team Workflow Guidelines**
- Always create feature branches
- Never push directly to main
- Require meaningful commit messages
- Document all changes in PRs

## Testing Your Setup

1. **Create a test branch:**
   ```bash
   git checkout -b test-branch-protection
   echo "test" > test.txt
   git add test.txt
   git commit -m "test: verify branch protection"
   git push origin test-branch-protection
   ```

2. **Try to push to main (should fail):**
   ```bash
   git checkout main
   git push origin main  # Should be blocked by pre-commit hooks
   ```

3. **Open a PR and verify:**
   - PR cannot be merged without approval
   - All CI checks must pass
   - Conversations must be resolved

## Troubleshooting

### Status Checks Not Appearing
- Run CI at least once to generate status check names
- Check that job names in `.github/workflows/ci.yml` match exactly

### Pre-commit Hooks Not Working
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
pre-commit install --hook-type pre-push
```

### Direct Push Still Possible
- This is a limitation of free private repos
- Rely on team discipline and pre-commit hooks
- Consider upgrading to GitHub Team if this is critical

## Enforcement Strategy

**Multi-layered protection approach:**

1. **Pre-commit Hooks** → Catch issues before commit
2. **CI/CD Pipeline** → Block PRs with failing checks
3. **Required Reviews** → Human oversight and knowledge sharing
4. **Team Discipline** → Clear workflow guidelines

This setup provides robust protection while working within the constraints of GitHub's free private repository limitations.