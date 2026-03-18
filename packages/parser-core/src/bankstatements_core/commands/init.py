"""Initialize directory structure for bank statement processing."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def init_directories(
    base_dir: Path | None = None,
    create_samples: bool = False,
    verbose: bool = True,
) -> int:
    """
    Initialize default directory structure for bank statement processing.

    Creates the following directories:
    - input/          : For PDF bank statements
    - output/         : For processed CSV/JSON/Excel files
    - logs/           : For processing activity logs (GDPR audit trail)
    - custom_templates/: For user-defined bank statement templates (optional)

    Args:
        base_dir: Base directory for initialization (default: current working directory)
        create_samples: If True, also create sample files (.env.example, README)
        verbose: If True, print progress messages

    Returns:
        Exit code: 0 for success, 1 for failure

    Example:
        >>> from bankstatements_core.commands.init import init_directories
        >>> init_directories()  # Initialize in current directory
        >>> init_directories(Path("/data/bank-app"))  # Initialize in specific directory
    """
    try:
        # Determine base directory
        base = base_dir if base_dir else Path.cwd()

        if verbose:
            print(f"Initializing directory structure in: {base.resolve()}")
            print()

        # Define directories to create
        directories = {
            "input": "Place PDF bank statements here for processing",
            "output": "Processed files (CSV, JSON, Excel) will be saved here",
            "logs": "Processing activity logs for GDPR audit trail",
            "custom_templates": "Optional: Add custom bank statement templates (JSON)",
        }

        # Create directories
        created_count = 0
        for dir_name, description in directories.items():
            dir_path = base / dir_name

            if dir_path.exists():
                if verbose:
                    print(f"✓ Already exists: {dir_path.relative_to(base)}")
            else:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_count += 1
                    if verbose:
                        print(f"✓ Created: {dir_path.relative_to(base)}")
                except OSError as e:
                    # Expected errors: permission issues, disk full
                    logger.error(f"Failed to create directory {dir_path}: {e}")
                    if verbose:
                        print(f"✗ Failed to create {dir_path.relative_to(base)}: {e}")
                    return 1
                # Let unexpected errors bubble up

            if verbose and description:
                print(f"  {description}")

        # Create sample files if requested
        if create_samples:
            if verbose:
                print()
                print("Creating sample files...")

            # Create .env file if it doesn't exist
            env_file = base / ".env"
            if not env_file.exists():
                try:
                    env_content = """# Bank Statement Processor Configuration
# Copy from .env.example and customize as needed

LOG_LEVEL=INFO
OUTPUT_FORMATS=csv,json
"""
                    env_file.write_text(env_content)
                    if verbose:
                        print("✓ Created: .env")
                except OSError as e:
                    logger.warning(f"Failed to create .env file: {e}")
                    if verbose:
                        print(f"✗ Failed to create .env: {e}")
            else:
                if verbose:
                    print("✓ Already exists: .env")

            # Create README in input directory
            input_readme = base / "input" / "README.md"
            if not input_readme.exists():
                try:
                    readme_content = """# Input Directory

Place your PDF bank statements in this directory for processing.

## Supported Banks

- AIB Ireland
- Revolut
- Generic bank statements with standard formats

## File Organization

```
input/
├── statement1.pdf
├── statement2.pdf
└── statements/
    ├── 2024-01.pdf
    └── 2024-02.pdf
```

For recursive scanning (PAID tier), organize statements in subdirectories.
"""
                    input_readme.write_text(readme_content)
                    if verbose:
                        print("✓ Created: input/README.md")
                except OSError as e:
                    logger.warning(f"Failed to create input README: {e}")

        # Success message
        if verbose:
            print()
            if created_count > 0:
                print(
                    f"✅ Successfully created {created_count} director{'y' if created_count == 1 else 'ies'}"
                )
            else:
                print("✅ All directories already exist")
            print()
            print("Next steps:")
            print("  1. Place PDF bank statements in input/")
            print("  2. Run: bankstatements")
            print("  3. Find processed files in output/")
            print()

        return 0

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error during initialization")
        if verbose:
            print(f"\n❌ Initialization failed: {e}")
        return 1


def main() -> int:
    """
    Main entry point for init command.

    Returns:
        Exit code
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize directory structure for bank statement processing"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for initialization (default: current directory)",
    )
    parser.add_argument(
        "--with-samples",
        action="store_true",
        help="Also create sample configuration files",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages",
    )

    args = parser.parse_args()

    return init_directories(
        base_dir=args.base_dir,
        create_samples=args.with_samples,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    sys.exit(main())
