#!/usr/bin/env python3
"""Version bump script for bankstatementsprocessor."""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into components."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version components into string."""
    return f"{major}.{minor}.{patch}"


def bump_version(version: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch = parse_version(version)

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return format_version(major, minor, patch)


def update_version_file(file_path: Path, new_version: str) -> None:
    """Update __version__.py file."""
    content = file_path.read_text()
    major, minor, patch = parse_version(new_version)

    # Update __version__
    content = re.sub(
        r'__version__ = "[^"]*"',
        f'__version__ = "{new_version}"',
        content,
    )

    # Update __version_info__
    content = re.sub(
        r"__version_info__ = \([^)]*\)",
        f"__version_info__ = ({major}, {minor}, {patch})",
        content,
    )

    file_path.write_text(content)
    print(f"✅ Updated {file_path}")


def update_pyproject_toml(file_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = file_path.read_text()
    content = re.sub(
        r'version = "[^"]*"',
        f'version = "{new_version}"',
        content,
    )
    file_path.write_text(content)
    print(f"✅ Updated {file_path}")


def update_changelog(file_path: Path, new_version: str) -> None:
    """Add new version section to CHANGELOG.md."""
    if not file_path.exists():
        print(f"⚠️  CHANGELOG.md not found, skipping")
        return

    content = file_path.read_text()
    today = datetime.now().strftime("%Y-%m-%d")

    # Find the position after the header
    lines = content.split("\n")
    insert_pos = 0

    for i, line in enumerate(lines):
        if line.startswith("## ["):
            insert_pos = i
            break

    # Insert new version section
    new_section = f"""## [{new_version}] - {today}

### Added
-

### Changed
-

### Fixed
-

"""

    lines.insert(insert_pos, new_section)
    file_path.write_text("\n".join(lines))
    print(f"✅ Updated {file_path}")


def create_git_commit_and_tag(version: str, dry_run: bool = False) -> None:
    """Create git commit and tag for version."""
    import subprocess

    tag = f"v{version}"

    if dry_run:
        print(f"\n🔍 Dry run - would create:")
        print(f"   Commit: 'chore: Bump version to {version}'")
        print(f"   Tag: {tag}")
        return

    # Stage changes
    subprocess.run(["git", "add", "src/__version__.py"], check=True)
    subprocess.run(["git", "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "add", "CHANGELOG.md"], check=False)  # May not exist

    # Create commit
    commit_msg = f"chore: Bump version to {version}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # Create tag
    tag_msg = f"Release {version}"
    subprocess.run(["git", "tag", "-a", tag, "-m", tag_msg], check=True)

    print(f"\n✅ Created commit and tag: {tag}")
    print(f"📌 Push with: git push origin main --tags")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bump version for bankstatementsprocessor")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    try:
        # Find project root
        project_root = Path(__file__).parent.parent

        # Read current version
        version_file = project_root / "src" / "__version__.py"
        if not version_file.exists():
            print(f"❌ Version file not found: {version_file}")
            return 1

        content = version_file.read_text()
        match = re.search(r'__version__ = "([^"]*)"', content)
        if not match:
            print("❌ Could not parse current version")
            return 1

        current_version = match.group(1)
        new_version = bump_version(current_version, args.bump_type)

        print(f"📦 Version bump: {current_version} → {new_version}")

        if args.dry_run:
            print("\n🔍 Dry run - no changes made")
            print(f"   Would update: src/__version__.py")
            print(f"   Would update: pyproject.toml")
            print(f"   Would update: CHANGELOG.md")
            create_git_commit_and_tag(new_version, dry_run=True)
            return 0

        # Update files
        update_version_file(version_file, new_version)
        update_pyproject_toml(project_root / "pyproject.toml", new_version)
        update_changelog(project_root / "CHANGELOG.md", new_version)

        # Create git commit and tag
        create_git_commit_and_tag(new_version, dry_run=False)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
