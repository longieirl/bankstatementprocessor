# Release Process

This document describes how to create a new release of the bankstatements application.

## Overview

The application follows [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.X.0): New features, backwards compatible
- **PATCH** version (0.0.X): Bug fixes, backwards compatible

Version format: `v1.2.3` (with 'v' prefix for git tags)

## Prerequisites

Before creating a release:
1. All tests must pass (`make test`)
2. Code quality checks must pass (`make check`)
3. CHANGELOG.md should be updated with user-facing changes
4. All changes should be committed to the `main` branch

## Release Steps

### Method 1: Using Makefile (Recommended)

For a patch release (bug fixes):
```bash
make release
```

For a minor release (new features):
```bash
make version-bump-minor
git push origin main --tags
```

For a major release (breaking changes):
```bash
make version-bump-major
git push origin main --tags
```

### Method 2: Manual Process

1. **Update CHANGELOG.md**
   ```bash
   # Add a new section for the version with changes
   vim CHANGELOG.md
   ```

2. **Bump version**
   ```bash
   # For patch: 1.0.0 → 1.0.1
   python3 scripts/bump_version.py patch

   # For minor: 1.0.1 → 1.1.0
   python3 scripts/bump_version.py minor

   # For major: 1.1.0 → 2.0.0
   python3 scripts/bump_version.py major
   ```

3. **Review changes**
   ```bash
   git log -1
   git show v1.0.1  # Replace with your version
   ```

4. **Push to GitHub**
   ```bash
   git push origin main --tags
   ```

## What Happens After Pushing a Tag

Once you push a version tag (e.g., `v1.0.1`), GitHub Actions automatically:

1. **Validates version consistency** across:
   - Git tag
   - `src/__version__.py`
   - `pyproject.toml`

2. **Builds Docker images** for multiple platforms:
   - `linux/amd64` (x86_64)
   - `linux/arm64` (Apple Silicon, ARM servers)

3. **Pushes to GitHub Container Registry** with tags:
   - `ghcr.io/longieirl/bankstatements:1.0.1` (exact version)
   - `ghcr.io/longieirl/bankstatements:1.0` (minor version)
   - `ghcr.io/longieirl/bankstatements:1` (major version)
   - `ghcr.io/longieirl/bankstatements:latest` (latest stable)

4. **Creates GitHub Release** with:
   - Release notes from CHANGELOG.md
   - Auto-generated release notes from commits
   - Links to Docker images

## Checking Release Status

1. **GitHub Actions**
   - Visit: https://github.com/longieirl/bankstatements/actions
   - Look for the "Release" workflow
   - Verify all jobs passed

2. **Docker Images**
   - Visit: https://github.com/longieirl/bankstatements/packages
   - Verify new version is listed
   - Check image metadata (labels, size, platforms)

3. **GitHub Release**
   - Visit: https://github.com/longieirl/bankstatements/releases
   - Verify release notes are correct

## Using Released Versions

### Pull specific version
```bash
docker pull ghcr.io/longieirl/bankstatements:1.0.1
```

### Pull latest stable
```bash
docker pull ghcr.io/longieirl/bankstatements:latest
```

### Use in docker-compose.yml
```yaml
services:
  bank-processor:
    image: ghcr.io/longieirl/bankstatements:1.0.1
    # ... rest of config
```

### Check version in container
```bash
docker run --rm ghcr.io/longieirl/bankstatements:1.0.1 --version
```

## Dry Run Testing

Before making a real release, test with dry run:

```bash
python3 scripts/bump_version.py patch --dry-run
```

This shows what would be changed without making actual changes.

## Version Bump Script Details

The `scripts/bump_version.py` script automatically:
1. Updates `src/__version__.py` with new version
2. Updates `pyproject.toml` with new version
3. Adds new section to `CHANGELOG.md`
4. Creates git commit with message: `chore: Bump version to X.Y.Z`
5. Creates git tag: `vX.Y.Z`

## Rollback a Release

If you need to rollback a release:

1. **Delete the tag locally and remotely**
   ```bash
   git tag -d v1.0.1
   git push origin :refs/tags/v1.0.1
   ```

2. **Delete the GitHub Release**
   - Visit: https://github.com/longieirl/bankstatements/releases
   - Find the release and delete it

3. **Revert version changes**
   ```bash
   git revert HEAD  # Revert the version bump commit
   git push origin main
   ```

Note: Docker images already pushed to GHCR cannot be deleted but will become untagged.

## Troubleshooting

### Version mismatch error
If the release workflow fails with version mismatch:
1. Check `src/__version__.py` matches git tag
2. Check `pyproject.toml` matches git tag
3. Fix the mismatch and create a new tag

### Docker build fails
1. Check Dockerfile syntax
2. Test build locally: `make docker-build`
3. Review GitHub Actions logs for details

### CHANGELOG.md not updated
The script adds a template entry, but you should manually update it with meaningful changes before releasing.

## Best Practices

1. **Always use the version bump script** - Ensures consistency
2. **Update CHANGELOG.md before releasing** - Document user-facing changes
3. **Test locally before releasing** - Run `make pr-ready`
4. **Use semantic versioning correctly**:
   - PATCH: Bug fixes only
   - MINOR: New features, no breaking changes
   - MAJOR: Breaking changes, API changes
5. **Write clear git commit messages** - They appear in release notes
6. **Tag releases from main branch only** - Keep release history clean

## Version History

Track all releases at: https://github.com/longieirl/bankstatements/releases

Current version can be checked with:
```bash
make info
```
