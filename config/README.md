# Configuration Files

This directory contains all configuration files for the Bank Statements Processing project.

## Files

### Code Quality & Linting
- `.coveragerc` - Test coverage configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.flake8` - Python linting configuration
- `setup.cfg` - Python setup configuration

### Development Tools
- `.editorconfig` - Editor configuration for consistent formatting
- `.gitattributes` - Git attributes configuration
- `.secrets.baseline` - Secrets detection baseline

### Docker
- `.dockerignore` - Files to ignore during Docker build

## Usage

Most tools automatically find these configuration files. Some important ones are symlinked to the project root for compatibility:

```bash
# Symlinks in project root (automatically created)
.coveragerc -> config/.coveragerc
.pre-commit-config.yaml -> config/.pre-commit-config.yaml
.flake8 -> config/.flake8
.dockerignore -> config/.dockerignore
```

## Editing Configuration

To modify any configuration:

1. Edit the file in this `config/` directory
2. The changes will automatically take effect through the symlinks
3. Test your changes with `make validate-config`

## Benefits of This Structure

- ✅ Clean project root
- ✅ All configuration in one place
- ✅ Easy to find and modify settings
- ✅ Tool compatibility maintained via symlinks
- ✅ Consistent organization