#!/usr/bin/env python3
"""
Supply Chain Risk Scoring Tool

Calculates risk scores for dependencies based on maintenance status,
age, known vulnerabilities, and other supply chain risk factors.

Usage:
    python scripts/supply_chain_risk.py --sbom sbom.spdx.json --output risk-report.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import urllib.request
import urllib.error


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


def extract_packages(sbom: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract packages from SBOM."""
    packages = []

    if "packages" in sbom:
        for pkg in sbom["packages"]:
            packages.append({
                "name": pkg.get("name", "unknown"),
                "version": pkg.get("versionInfo", "unknown"),
                "supplier": pkg.get("supplier", "unknown"),
                "download_location": pkg.get("downloadLocation", "unknown"),
            })

    return packages


def fetch_pypi_metadata(package_name: str) -> Dict[str, Any]:
    """
    Fetch package metadata from PyPI API.

    Returns empty dict if package not found or error occurs.
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return {}


def calculate_age_score(last_release_date: str) -> int:
    """
    Calculate risk score based on package age.

    Returns:
        0-30 points based on days since last release
    """
    try:
        last_release = datetime.fromisoformat(last_release_date.replace("Z", "+00:00"))
        days_old = (datetime.now(last_release.tzinfo) - last_release).days

        if days_old > 730:  # 2+ years
            return 30
        elif days_old > 365:  # 1-2 years
            return 20
        elif days_old > 180:  # 6-12 months
            return 10
        else:
            return 0
    except (ValueError, AttributeError):
        return 0


def calculate_maintenance_score(metadata: Dict[str, Any]) -> int:
    """
    Calculate risk score based on maintenance indicators.

    Returns:
        0-20 points based on project health signals
    """
    score = 0

    # Check if project has multiple maintainers (info not in PyPI JSON, estimate)
    # PyPI doesn't provide maintainer count, so we use author info as proxy
    info = metadata.get("info", {})
    if not info.get("author") and not info.get("maintainer"):
        score += 10

    # Check if project has home page / documentation
    if not info.get("home_page") and not info.get("project_urls"):
        score += 5

    # Check if project has active development (has recent releases)
    releases = metadata.get("releases", {})
    if len(releases) < 3:  # Very few releases
        score += 5

    return score


def calculate_vulnerability_score(package_name: str, version: str) -> int:
    """
    Calculate risk score based on known vulnerabilities.

    Note: This is a placeholder. In production, integrate with:
    - OSV (Open Source Vulnerabilities) API
    - GitHub Advisory Database
    - Safety DB

    Returns:
        0-50 points (25 per known CVE, max 50)
    """
    # Placeholder: Would query vulnerability databases
    # For now, return 0 (no vulnerabilities detected)
    return 0


def calculate_popularity_score(metadata: Dict[str, Any]) -> int:
    """
    Calculate risk score based on popularity (inverse - less popular = more risk).

    Returns:
        0-10 points based on download metrics
    """
    # PyPI JSON doesn't include download counts directly
    # Use project_urls and GitHub stars as proxy if available
    # For simplicity, return 0 for now (would need additional API calls)
    return 0


def calculate_risk_score(
    package: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate overall risk score for a package.

    Risk scoring:
    - 0-25: LOW
    - 26-50: MEDIUM
    - 51-75: HIGH
    - 76+: CRITICAL
    """
    scores = {
        "age": 0,
        "maintenance": 0,
        "vulnerabilities": 0,
        "popularity": 0,
    }
    reasons = []

    # Age scoring
    if metadata:
        info = metadata.get("info", {})
        releases = metadata.get("releases", {})

        # Get last release date
        if releases:
            latest_version = info.get("version", package["version"])
            release_info = releases.get(latest_version, [])
            if release_info:
                last_release_date = release_info[0].get("upload_time", "")
                age_score = calculate_age_score(last_release_date)
                scores["age"] = age_score

                if age_score >= 30:
                    reasons.append("Last release over 2 years ago")
                elif age_score >= 20:
                    reasons.append("Last release 1-2 years ago")
                elif age_score >= 10:
                    reasons.append("Last release 6-12 months ago")

        # Maintenance scoring
        maint_score = calculate_maintenance_score(metadata)
        scores["maintenance"] = maint_score

        if maint_score >= 10:
            reasons.append("Limited maintenance indicators")

    # Vulnerability scoring (placeholder)
    vuln_score = calculate_vulnerability_score(package["name"], package["version"])
    scores["vulnerabilities"] = vuln_score

    if vuln_score > 0:
        num_cves = vuln_score // 25
        reasons.append(f"{num_cves} known CVE(s)")

    # Calculate total score
    total_score = sum(scores.values())

    # Determine risk level
    if total_score >= 76:
        risk_level = "CRITICAL"
    elif total_score >= 51:
        risk_level = "HIGH"
    elif total_score >= 26:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "name": package["name"],
        "version": package["version"],
        "risk_score": total_score,
        "risk_level": risk_level,
        "score_breakdown": scores,
        "reasons": reasons,
    }


def analyze_supply_chain_risk(
    packages: List[Dict[str, Any]],
    fetch_metadata: bool = True,
) -> Dict[str, Any]:
    """Analyze supply chain risk for all packages."""
    risk_packages = []
    summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    print(f"Analyzing {len(packages)} packages...", file=sys.stderr)

    for i, package in enumerate(packages, 1):
        print(f"  [{i}/{len(packages)}] {package['name']}", file=sys.stderr)

        # Fetch metadata if enabled
        metadata = {}
        if fetch_metadata:
            metadata = fetch_pypi_metadata(package["name"])

        # Calculate risk score
        risk_result = calculate_risk_score(package, metadata)
        risk_packages.append(risk_result)

        # Update summary
        summary[risk_result["risk_level"]] += 1

    # Sort by risk score (highest first)
    risk_packages.sort(key=lambda x: x["risk_score"], reverse=True)

    # Calculate overall risk
    total_score = sum(pkg["risk_score"] for pkg in risk_packages)
    avg_score = total_score / len(risk_packages) if risk_packages else 0

    if avg_score >= 50:
        overall_risk = "HIGH"
    elif avg_score >= 25:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

    # Generate recommendations
    recommendations = []
    for pkg in risk_packages:
        if pkg["risk_level"] in ("HIGH", "CRITICAL"):
            recommendations.append(
                f"Consider reviewing or replacing '{pkg['name']}' (risk score: {pkg['risk_score']})"
            )

    return {
        "overall_risk": overall_risk,
        "average_score": round(avg_score, 2),
        "summary": summary,
        "packages": risk_packages,
        "recommendations": recommendations,
    }


def generate_markdown_report(risk_data: Dict[str, Any]) -> str:
    """Generate Markdown-formatted risk report."""
    lines = [
        "# Supply Chain Risk Report",
        "",
        f"**Overall Risk**: {risk_data['overall_risk']}",
        f"**Average Risk Score**: {risk_data['average_score']}/100",
        "",
        "## Summary",
        "",
        f"- 🔴 **CRITICAL**: {risk_data['summary']['CRITICAL']} packages",
        f"- 🟠 **HIGH**: {risk_data['summary']['HIGH']} packages",
        f"- 🟡 **MEDIUM**: {risk_data['summary']['MEDIUM']} packages",
        f"- 🟢 **LOW**: {risk_data['summary']['LOW']} packages",
        "",
    ]

    # High risk packages
    high_risk = [
        pkg for pkg in risk_data["packages"]
        if pkg["risk_level"] in ("HIGH", "CRITICAL")
    ]

    if high_risk:
        lines.extend([
            "## ⚠️ High Risk Packages",
            "",
        ])
        for pkg in high_risk:
            lines.append(f"### {pkg['name']} ({pkg['version']})")
            lines.append(f"- **Risk Score**: {pkg['risk_score']}/100")
            lines.append(f"- **Risk Level**: {pkg['risk_level']}")
            if pkg["reasons"]:
                lines.append("- **Issues**:")
                for reason in pkg["reasons"]:
                    lines.append(f"  - {reason}")
            lines.append("")

    # Medium risk packages
    medium_risk = [
        pkg for pkg in risk_data["packages"]
        if pkg["risk_level"] == "MEDIUM"
    ]

    if medium_risk:
        lines.extend([
            "## ℹ️ Medium Risk Packages",
            "",
            "| Package | Version | Risk Score | Issues |",
            "|---------|---------|------------|--------|",
        ])
        for pkg in medium_risk:
            issues = "; ".join(pkg["reasons"]) if pkg["reasons"] else "None"
            lines.append(
                f"| {pkg['name']} | {pkg['version']} | {pkg['risk_score']} | {issues} |"
            )
        lines.append("")

    # Recommendations
    if risk_data["recommendations"]:
        lines.extend([
            "## 📋 Recommendations",
            "",
        ])
        for rec in risk_data["recommendations"]:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate supply chain risk scores for dependencies"
    )
    parser.add_argument(
        "--sbom",
        type=Path,
        required=True,
        help="Path to SBOM file (SPDX JSON format)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output report file (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Don't fetch package metadata from PyPI (faster but less accurate)",
    )

    args = parser.parse_args()

    # Load SBOM
    print(f"Loading SBOM: {args.sbom}", file=sys.stderr)
    sbom = load_sbom(args.sbom)

    # Extract packages
    packages = extract_packages(sbom)
    print(f"Found {len(packages)} packages", file=sys.stderr)

    # Analyze risk
    risk_data = analyze_supply_chain_risk(
        packages,
        fetch_metadata=not args.no_fetch
    )

    # Generate report
    if args.format == "markdown":
        report = generate_markdown_report(risk_data)
    else:
        report = json.dumps(risk_data, indent=2)

    # Output
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\nReport written to: {args.output}", file=sys.stderr)
    else:
        print(report)

    # Exit with code based on risk level
    if risk_data["overall_risk"] == "HIGH":
        print(f"\n⚠️ High supply chain risk detected", file=sys.stderr)
        sys.exit(0)  # Don't fail build, just inform
    else:
        print(f"\n✅ Supply chain risk: {risk_data['overall_risk']}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
