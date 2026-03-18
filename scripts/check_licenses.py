#!/usr/bin/env python3
"""
License Compliance Checker

Validates that all dependencies use compatible licenses according to policy.

Usage:
    python scripts/check_licenses.py --policy .github/license-policy.json --output report.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_policy(path: Path) -> Dict[str, Any]:
    """Load license policy from JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Policy file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def get_installed_licenses() -> List[Dict[str, Any]]:
    """
    Get licenses for all installed packages using pip-licenses.

    Returns:
        List of dicts with package, version, and license info
    """
    try:
        # Run pip-licenses to get JSON output
        result = subprocess.run(
            ["pip-licenses", "--format=json", "--with-urls"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running pip-licenses: {e}", file=sys.stderr)
        print("Make sure pip-licenses is installed: pip install pip-licenses", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing pip-licenses output: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: pip-licenses not found", file=sys.stderr)
        print("Install it with: pip install pip-licenses", file=sys.stderr)
        sys.exit(1)


def normalize_license_name(license_str: str) -> str:
    """Normalize license name for comparison."""
    # Common variations
    normalizations = {
        "BSD License": "BSD-3-Clause",
        "BSD": "BSD-3-Clause",
        "Apache Software License": "Apache-2.0",
        "Apache 2.0": "Apache-2.0",
        "MIT License": "MIT",
        "Python Software Foundation License": "PSF-2.0",
        "ISC License (ISCL)": "ISC",
        "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    }

    normalized = license_str.strip()
    return normalizations.get(normalized, normalized)


def check_license_compliance(
    packages: List[Dict[str, Any]],
    policy: Dict[str, Any],
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Check license compliance against policy.

    Returns:
        Tuple of (allowed, review_required, forbidden, unknown)
    """
    policy_config = policy.get("license_policy", {})
    allowed_licenses = set(policy_config.get("allowed_licenses", []))
    forbidden_licenses = set(policy_config.get("forbidden_licenses", []))
    review_licenses = set(policy_config.get("review_required", []))

    # Get package exceptions
    exceptions_config = policy.get("exceptions", {})
    exception_packages = {
        exc["package"]: exc["reason"]
        for exc in exceptions_config.get("packages", [])
    }

    allowed = []
    review_required = []
    forbidden = []
    unknown = []

    for pkg in packages:
        license_name = normalize_license_name(pkg.get("License", "Unknown"))
        pkg_name = pkg.get("Name", "Unknown")

        pkg_info = {
            "package": pkg_name,
            "version": pkg.get("Version", "Unknown"),
            "license": license_name,
            "url": pkg.get("URL", ""),
        }

        # Check if package has an exception
        if pkg_name in exception_packages:
            pkg_info["exception"] = exception_packages[pkg_name]
            allowed.append(pkg_info)
            continue

        # Check license against policy
        if license_name in forbidden_licenses:
            forbidden.append(pkg_info)
        elif license_name in review_licenses:
            review_required.append(pkg_info)
        elif license_name in allowed_licenses:
            allowed.append(pkg_info)
        elif license_name == "Unknown" or license_name == "UNKNOWN":
            pkg_info["note"] = "License not detected, manual review required"
            unknown.append(pkg_info)
        else:
            # License not in any category
            pkg_info["note"] = "License not in policy, manual review required"
            unknown.append(pkg_info)

    return allowed, review_required, forbidden, unknown


def generate_markdown_report(
    allowed: List[Dict],
    review_required: List[Dict],
    forbidden: List[Dict],
    unknown: List[Dict],
    policy: Dict[str, Any],
) -> str:
    """Generate Markdown-formatted compliance report."""
    lines = [
        "# License Compliance Report",
        "",
    ]

    # Overall status
    if forbidden:
        lines.append("## Status: ❌ FORBIDDEN LICENSES DETECTED")
    elif unknown:
        lines.append("## Status: ⚠️ UNKNOWN LICENSES DETECTED")
    elif review_required:
        lines.append("## Status: ⚠️ REVIEW REQUIRED")
    else:
        lines.append("## Status: ✅ ALL LICENSES COMPLIANT")

    lines.append("")

    # Summary
    total = len(allowed) + len(review_required) + len(forbidden) + len(unknown)
    lines.extend([
        "## Summary",
        "",
        f"- **Total packages**: {total}",
        f"- ✅ **Allowed**: {len(allowed)}",
        f"- ⚠️ **Review required**: {len(review_required)}",
        f"- ❌ **Forbidden**: {len(forbidden)}",
        f"- ❓ **Unknown**: {len(unknown)}",
        "",
    ])

    # Forbidden licenses
    if forbidden:
        lines.extend([
            "## ❌ Forbidden Licenses (Must Fix)",
            "",
            "These packages use licenses that are incompatible with the project:",
            "",
            "| Package | Version | License |",
            "|---------|---------|---------|",
        ])
        for pkg in sorted(forbidden, key=lambda x: x["package"]):
            lines.append(f"| {pkg['package']} | {pkg['version']} | {pkg['license']} |")
        lines.append("")

    # Unknown licenses
    if unknown:
        lines.extend([
            "## ❓ Unknown Licenses (Review Required)",
            "",
            "These packages have unknown or unrecognized licenses:",
            "",
            "| Package | Version | License | Note |",
            "|---------|---------|---------|------|",
        ])
        for pkg in sorted(unknown, key=lambda x: x["package"]):
            note = pkg.get("note", "")
            lines.append(
                f"| {pkg['package']} | {pkg['version']} | {pkg['license']} | {note} |"
            )
        lines.append("")

    # Review required
    if review_required:
        lines.extend([
            "## ⚠️ Licenses Requiring Review",
            "",
            "These packages use licenses that may require legal review:",
            "",
            "| Package | Version | License |",
            "|---------|---------|---------|",
        ])
        for pkg in sorted(review_required, key=lambda x: x["package"]):
            lines.append(f"| {pkg['package']} | {pkg['version']} | {pkg['license']} |")
        lines.append("")

    # Policy information
    policy_config = policy.get("license_policy", {})
    lines.extend([
        "## 📋 License Policy",
        "",
        f"**Project License**: {policy_config.get('project_license', 'Unknown')}",
        "",
        "**Allowed Licenses**:",
    ])
    for lic in sorted(policy_config.get("allowed_licenses", [])):
        lines.append(f"- {lic}")

    lines.append("")
    lines.append("**Forbidden Licenses**:")
    for lic in sorted(policy_config.get("forbidden_licenses", [])):
        lines.append(f"- {lic}")

    lines.append("")

    return "\n".join(lines)


def generate_json_report(
    allowed: List[Dict],
    review_required: List[Dict],
    forbidden: List[Dict],
    unknown: List[Dict],
) -> str:
    """Generate JSON-formatted compliance report."""
    status = "pass"
    if forbidden:
        status = "fail"
    elif unknown or review_required:
        status = "review"

    report = {
        "status": status,
        "summary": {
            "total": len(allowed) + len(review_required) + len(forbidden) + len(unknown),
            "allowed": len(allowed),
            "review_required": len(review_required),
            "forbidden": len(forbidden),
            "unknown": len(unknown),
        },
        "allowed": allowed,
        "review_required": review_required,
        "forbidden": forbidden,
        "unknown": unknown,
    }
    return json.dumps(report, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check license compliance for installed packages"
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(".github/license-policy.json"),
        help="Path to license policy file (default: .github/license-policy.json)",
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
        "--fail-on-review",
        action="store_true",
        help="Exit with error code if review-required licenses are detected",
    )

    args = parser.parse_args()

    # Load policy
    print(f"Loading policy: {args.policy}", file=sys.stderr)
    policy = load_policy(args.policy)

    # Get installed packages and their licenses
    print("Scanning installed packages...", file=sys.stderr)
    packages = get_installed_licenses()
    print(f"Found {len(packages)} packages", file=sys.stderr)

    # Check compliance
    allowed, review_required, forbidden, unknown = check_license_compliance(
        packages, policy
    )

    # Generate report
    if args.format == "markdown":
        report = generate_markdown_report(
            allowed, review_required, forbidden, unknown, policy
        )
    else:
        report = generate_json_report(
            allowed, review_required, forbidden, unknown
        )

    # Output
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)

    # Exit with appropriate code
    if forbidden:
        print("\n❌ Forbidden licenses detected", file=sys.stderr)
        sys.exit(1)
    elif unknown:
        print("\n⚠️ Unknown licenses detected, review required", file=sys.stderr)
        sys.exit(1 if args.fail_on_review else 0)
    elif review_required:
        print("\n⚠️ Licenses requiring review detected", file=sys.stderr)
        sys.exit(1 if args.fail_on_review else 0)
    else:
        print("\n✅ All licenses compliant", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
