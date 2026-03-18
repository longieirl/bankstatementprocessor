#!/usr/bin/env python3
"""
Dependency Drift Detection Tool

Detects unexpected dependency changes based on configurable policy rules.
Alerts on major version changes, new dependencies, and other supply chain risks.

Usage:
    python scripts/detect_drift.py --sbom sbom.spdx.json --baseline sbom-baseline.json --policy .github/drift-policy.yml
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml


class DriftPolicy:
    """Drift detection policy configuration."""

    def __init__(self, policy_data: Dict[str, Any]):
        """Initialize policy from configuration data."""
        drift_config = policy_data.get("drift_detection", {})
        rules = drift_config.get("rules", {})

        self.baseline = drift_config.get("baseline", "main")
        self.patch_bumps = rules.get("patch_bumps", "allow")
        self.minor_bumps = rules.get("minor_bumps", "warn")
        self.major_bumps = rules.get("major_bumps", "fail")
        self.new_dependencies = rules.get("new_dependencies", "fail")
        self.transitive_changes = rules.get("transitive_changes", "warn")
        self.exceptions = {
            exc["package"]: exc["reason"]
            for exc in drift_config.get("exceptions", [])
        }


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


def load_policy(path: Path) -> DriftPolicy:
    """Load drift policy from YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)
            return DriftPolicy(policy_data)
    except FileNotFoundError:
        print(f"Warning: Policy file not found: {path}, using defaults", file=sys.stderr)
        # Return default policy
        return DriftPolicy({
            "drift_detection": {
                "rules": {
                    "patch_bumps": "allow",
                    "minor_bumps": "warn",
                    "major_bumps": "fail",
                    "new_dependencies": "fail",
                    "transitive_changes": "warn",
                }
            }
        })
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_packages(sbom: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract packages from SBOM."""
    packages = {}

    if "packages" in sbom:
        for pkg in sbom["packages"]:
            name = pkg.get("name", "unknown")
            packages[name] = {
                "version": pkg.get("versionInfo", "unknown"),
                "supplier": pkg.get("supplier", "unknown"),
            }

    return packages


def classify_version_change(old_version: str, new_version: str) -> str:
    """Classify version change as major, minor, or patch."""
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


def detect_drift(
    baseline: Dict[str, Dict[str, Any]],
    current: Dict[str, Dict[str, Any]],
    policy: DriftPolicy,
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Detect dependency drift based on policy.

    Returns:
        Tuple of (failures, warnings, info, new_dependencies)
    """
    failures = []
    warnings = []
    info = []
    new_dependencies = []

    baseline_names = set(baseline.keys())
    current_names = set(current.keys())

    # Check for new dependencies
    added = current_names - baseline_names
    if added:
        for name in added:
            pkg = current[name]
            drift = {
                "package": name,
                "version": pkg["version"],
                "change": "NEW_DEPENDENCY",
                "message": f"New dependency added: {name} ({pkg['version']})",
            }

            # Check if exception applies
            if name in policy.exceptions:
                drift["exception_reason"] = policy.exceptions[name]
                info.append(drift)
            elif policy.new_dependencies == "fail":
                failures.append(drift)
            elif policy.new_dependencies == "warn":
                warnings.append(drift)
            else:
                info.append(drift)

            new_dependencies.append(drift)

    # Check for removed dependencies
    removed = baseline_names - current_names
    if removed:
        for name in removed:
            warnings.append({
                "package": name,
                "version": baseline[name]["version"],
                "change": "REMOVED",
                "message": f"Dependency removed: {name}",
            })

    # Check for version changes
    for name in baseline_names & current_names:
        baseline_pkg = baseline[name]
        current_pkg = current[name]

        if baseline_pkg["version"] != current_pkg["version"]:
            change_type = classify_version_change(
                baseline_pkg["version"],
                current_pkg["version"]
            )

            drift = {
                "package": name,
                "old_version": baseline_pkg["version"],
                "new_version": current_pkg["version"],
                "change": change_type.upper(),
                "message": f"{name}: {baseline_pkg['version']} → {current_pkg['version']} ({change_type})",
            }

            # Check if exception applies
            if name in policy.exceptions:
                drift["exception_reason"] = policy.exceptions[name]
                info.append(drift)
                continue

            # Apply policy rules
            if change_type == "major":
                if policy.major_bumps == "fail":
                    failures.append(drift)
                elif policy.major_bumps == "warn":
                    warnings.append(drift)
                else:
                    info.append(drift)
            elif change_type == "minor":
                if policy.minor_bumps == "fail":
                    failures.append(drift)
                elif policy.minor_bumps == "warn":
                    warnings.append(drift)
                else:
                    info.append(drift)
            elif change_type == "patch":
                if policy.patch_bumps == "fail":
                    failures.append(drift)
                elif policy.patch_bumps == "warn":
                    warnings.append(drift)
                else:
                    info.append(drift)

    return failures, warnings, info, new_dependencies


def generate_markdown_report(
    failures: List[Dict],
    warnings: List[Dict],
    info: List[Dict],
    new_dependencies: List[Dict],
) -> str:
    """Generate Markdown-formatted drift report."""
    lines = [
        "# Dependency Drift Report",
        "",
    ]

    # Overall status
    if failures:
        lines.append("## Status: ❌ FAILURES DETECTED")
    elif warnings:
        lines.append("## Status: ⚠️ WARNINGS DETECTED")
    else:
        lines.append("## Status: ✅ NO DRIFT DETECTED")

    lines.append("")

    # Failures
    if failures:
        lines.extend([
            "## ❌ Failures (Build Should Fail)",
            "",
        ])
        for drift in failures:
            lines.append(f"- **{drift['package']}**: {drift['message']}")
        lines.append("")

    # Warnings
    if warnings:
        lines.extend([
            "## ⚠️ Warnings (Review Required)",
            "",
        ])
        for drift in warnings:
            lines.append(f"- **{drift['package']}**: {drift['message']}")
        lines.append("")

    # New dependencies
    if new_dependencies:
        lines.extend([
            "## 📦 New Dependencies",
            "",
        ])
        for drift in new_dependencies:
            msg = drift['message']
            if 'exception_reason' in drift:
                msg += f" *(Allowed: {drift['exception_reason']})*"
            lines.append(f"- {msg}")
        lines.append("")

    # Info
    if info:
        lines.extend([
            "## ℹ️ Informational Changes",
            "",
        ])
        for drift in info:
            msg = drift['message']
            if 'exception_reason' in drift:
                msg += f" *(Allowed: {drift['exception_reason']})*"
            lines.append(f"- {msg}")
        lines.append("")

    # Summary
    lines.extend([
        "## Summary",
        "",
        f"- **Failures**: {len(failures)}",
        f"- **Warnings**: {len(warnings)}",
        f"- **New Dependencies**: {len(new_dependencies)}",
        f"- **Total Changes**: {len(failures) + len(warnings) + len(info)}",
        "",
    ])

    return "\n".join(lines)


def generate_json_report(
    failures: List[Dict],
    warnings: List[Dict],
    info: List[Dict],
    new_dependencies: List[Dict],
) -> str:
    """Generate JSON-formatted drift report."""
    report = {
        "status": "fail" if failures else ("warn" if warnings else "pass"),
        "summary": {
            "failures": len(failures),
            "warnings": len(warnings),
            "new_dependencies": len(new_dependencies),
            "total_changes": len(failures) + len(warnings) + len(info),
        },
        "failures": failures,
        "warnings": warnings,
        "new_dependencies": new_dependencies,
        "info": info,
    }
    return json.dumps(report, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect dependency drift based on policy rules"
    )
    parser.add_argument(
        "--sbom",
        type=Path,
        required=True,
        help="Path to current SBOM file (SPDX JSON format)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline SBOM file (SPDX JSON format)",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(".github/drift-policy.yml"),
        help="Path to drift policy file (default: .github/drift-policy.yml)",
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
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with error code if warnings are detected",
    )

    args = parser.parse_args()

    # Load policy
    print(f"Loading policy: {args.policy}", file=sys.stderr)
    policy = load_policy(args.policy)

    # Load SBOMs
    print(f"Loading baseline SBOM: {args.baseline}", file=sys.stderr)
    baseline_sbom = load_sbom(args.baseline)

    print(f"Loading current SBOM: {args.sbom}", file=sys.stderr)
    current_sbom = load_sbom(args.sbom)

    # Extract packages
    baseline_packages = extract_packages(baseline_sbom)
    current_packages = extract_packages(current_sbom)

    print(f"Baseline packages: {len(baseline_packages)}", file=sys.stderr)
    print(f"Current packages: {len(current_packages)}", file=sys.stderr)

    # Detect drift
    failures, warnings, info, new_dependencies = detect_drift(
        baseline_packages, current_packages, policy
    )

    # Generate report
    if args.format == "markdown":
        report = generate_markdown_report(failures, warnings, info, new_dependencies)
    else:
        report = generate_json_report(failures, warnings, info, new_dependencies)

    # Output
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)

    # Exit with appropriate code
    if failures:
        print("\n❌ Drift detection failed", file=sys.stderr)
        sys.exit(1)
    elif warnings and args.fail_on_warnings:
        print("\n⚠️ Drift warnings detected (--fail-on-warnings)", file=sys.stderr)
        sys.exit(1)
    elif warnings:
        print("\n⚠️ Drift warnings detected", file=sys.stderr)
        sys.exit(0)
    else:
        print("\n✅ No significant drift detected", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
