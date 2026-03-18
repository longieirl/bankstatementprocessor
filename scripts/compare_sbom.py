#!/usr/bin/env python3
"""
SBOM Comparison Tool

Compares two SBOM files (SPDX JSON format) and generates a detailed diff report
showing added, removed, and changed packages.

Usage:
    python scripts/compare_sbom.py --base sbom-base.spdx.json --current sbom.spdx.json --output report.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_sbom(path: Path) -> Dict[str, Any]:
    """Load and parse an SBOM file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: SBOM file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_packages(sbom: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract packages from SBOM and create a lookup dictionary.

    Returns:
        Dict mapping package name to package info (version, licenses, etc.)
    """
    packages = {}

    # Handle SPDX format
    if "packages" in sbom:
        for pkg in sbom["packages"]:
            name = pkg.get("name", "unknown")
            packages[name] = {
                "version": pkg.get("versionInfo", "unknown"),
                "licenses": extract_licenses(pkg),
                "supplier": pkg.get("supplier", "unknown"),
                "download_location": pkg.get("downloadLocation", "unknown"),
            }

    return packages


def extract_licenses(package: Dict[str, Any]) -> List[str]:
    """Extract license information from a package."""
    licenses = []

    # Try licenseConcluded first
    if "licenseConcluded" in package and package["licenseConcluded"] != "NOASSERTION":
        licenses.append(package["licenseConcluded"])

    # Try licenseDeclared
    elif "licenseDeclared" in package and package["licenseDeclared"] != "NOASSERTION":
        licenses.append(package["licenseDeclared"])

    return licenses if licenses else ["Unknown"]


def compare_packages(
    base: Dict[str, Dict[str, Any]],
    current: Dict[str, Dict[str, Any]]
) -> Tuple[Dict, Dict, Dict]:
    """
    Compare two package dictionaries.

    Returns:
        Tuple of (added, removed, changed) dictionaries
    """
    base_names = set(base.keys())
    current_names = set(current.keys())

    added = {name: current[name] for name in current_names - base_names}
    removed = {name: base[name] for name in base_names - current_names}

    # Find changed packages (version or license changes)
    changed = {}
    for name in base_names & current_names:
        base_pkg = base[name]
        current_pkg = current[name]

        changes = {}
        if base_pkg["version"] != current_pkg["version"]:
            changes["version"] = {
                "old": base_pkg["version"],
                "new": current_pkg["version"],
                "change_type": classify_version_change(
                    base_pkg["version"],
                    current_pkg["version"]
                ),
            }

        if base_pkg["licenses"] != current_pkg["licenses"]:
            changes["licenses"] = {
                "old": base_pkg["licenses"],
                "new": current_pkg["licenses"],
            }

        if changes:
            changed[name] = changes

    return added, removed, changed


def classify_version_change(old_version: str, new_version: str) -> str:
    """
    Classify version change as major, minor, or patch.

    Returns:
        "major", "minor", "patch", or "unknown"
    """
    try:
        old_parts = [int(x) for x in old_version.split(".")[:3]]
        new_parts = [int(x) for x in new_version.split(".")[:3]]

        # Pad with zeros if needed
        while len(old_parts) < 3:
            old_parts.append(0)
        while len(new_parts) < 3:
            new_parts.append(0)

        if new_parts[0] > old_parts[0]:
            return "major"
        elif new_parts[1] > old_parts[1]:
            return "minor"
        elif new_parts[2] > old_parts[2]:
            return "patch"
        else:
            return "unknown"
    except (ValueError, IndexError):
        return "unknown"


def generate_markdown_report(
    added: Dict,
    removed: Dict,
    changed: Dict,
    base_path: Path,
    current_path: Path,
) -> str:
    """Generate a Markdown-formatted comparison report."""
    lines = [
        "# SBOM Comparison Report",
        "",
        f"**Base SBOM**: `{base_path.name}`",
        f"**Current SBOM**: `{current_path.name}`",
        "",
        "## Summary",
        "",
        f"- ✅ **{len(added)}** packages added",
        f"- ⚠️ **{len(removed)}** packages removed",
        f"- 🔄 **{len(changed)}** packages updated",
        "",
    ]

    # Added packages
    if added:
        lines.extend([
            "## Added Packages",
            "",
        ])
        for name in sorted(added.keys()):
            pkg = added[name]
            license_str = ", ".join(pkg["licenses"])
            lines.append(f"- `{name}` ({pkg['version']}) - {license_str}")
        lines.append("")

    # Removed packages
    if removed:
        lines.extend([
            "## Removed Packages",
            "",
        ])
        for name in sorted(removed.keys()):
            pkg = removed[name]
            lines.append(f"- `{name}` ({pkg['version']})")
        lines.append("")

    # Changed packages
    if changed:
        lines.extend([
            "## Updated Packages",
            "",
            "| Package | Old Version | New Version | Change Type |",
            "|---------|-------------|-------------|-------------|",
        ])

        for name in sorted(changed.keys()):
            changes = changed[name]
            if "version" in changes:
                old_ver = changes["version"]["old"]
                new_ver = changes["version"]["new"]
                change_type = changes["version"]["change_type"]

                # Add emoji based on change type
                emoji = {
                    "patch": "✅",
                    "minor": "⚠️",
                    "major": "❌",
                    "unknown": "❓",
                }.get(change_type, "❓")

                lines.append(
                    f"| {name} | {old_ver} | {new_ver} | {change_type.title()} {emoji} |"
                )

            # Show license changes separately
            if "licenses" in changes:
                old_lic = ", ".join(changes["licenses"]["old"])
                new_lic = ", ".join(changes["licenses"]["new"])
                lines.append(f"| {name} (license) | {old_lic} | {new_lic} | License Change ⚠️ |")

        lines.append("")

    # Statistics
    major_changes = sum(
        1 for changes in changed.values()
        if "version" in changes and changes["version"]["change_type"] == "major"
    )
    minor_changes = sum(
        1 for changes in changed.values()
        if "version" in changes and changes["version"]["change_type"] == "minor"
    )
    patch_changes = sum(
        1 for changes in changed.values()
        if "version" in changes and changes["version"]["change_type"] == "patch"
    )

    lines.extend([
        "## Change Statistics",
        "",
        f"- **Major version changes**: {major_changes}",
        f"- **Minor version changes**: {minor_changes}",
        f"- **Patch version changes**: {patch_changes}",
        f"- **Total packages**: {len(added) + len(changed) + len(set(changed.keys()))}",
        "",
    ])

    return "\n".join(lines)


def generate_json_report(
    added: Dict,
    removed: Dict,
    changed: Dict,
) -> str:
    """Generate a JSON-formatted comparison report."""
    report = {
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "added": added,
        "removed": removed,
        "changed": changed,
    }
    return json.dumps(report, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare two SBOM files and generate a diff report"
    )
    parser.add_argument(
        "--base",
        type=Path,
        required=True,
        help="Path to base SBOM file (SPDX JSON format)",
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current SBOM file (SPDX JSON format)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output report file (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    # Load SBOMs
    print(f"Loading base SBOM: {args.base}", file=sys.stderr)
    base_sbom = load_sbom(args.base)

    print(f"Loading current SBOM: {args.current}", file=sys.stderr)
    current_sbom = load_sbom(args.current)

    # Extract packages
    base_packages = extract_packages(base_sbom)
    current_packages = extract_packages(current_sbom)

    print(f"Base packages: {len(base_packages)}", file=sys.stderr)
    print(f"Current packages: {len(current_packages)}", file=sys.stderr)

    # Compare
    added, removed, changed = compare_packages(base_packages, current_packages)

    # Generate report
    if args.format == "markdown":
        report = generate_markdown_report(
            added, removed, changed, args.base, args.current
        )
    else:
        report = generate_json_report(added, removed, changed)

    # Output
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)

    # Exit with appropriate code
    if added or removed or any(
        "version" in changes and changes["version"]["change_type"] == "major"
        for changes in changed.values()
    ):
        print("\n⚠️ Significant changes detected", file=sys.stderr)
        sys.exit(0)  # Don't fail, just inform
    else:
        print("\n✅ No significant changes", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
