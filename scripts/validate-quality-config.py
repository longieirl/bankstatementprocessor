#!/usr/bin/env python3
"""
Validate that all quality tools are configured consistently
and catch the issues we want to prevent.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd.split(), capture_output=True, text=True, check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def test_flake8_line_length():
    """Test that flake8 catches long lines at 88 characters."""
    print("🔍 Testing flake8 line length detection (88 chars)...")

    # Create a test file with a line that's too long (exactly 89 characters)
    test_content = """def test_function():
    # This is a very long comment line that exceeds 88 chars and should trigger E501 here
    pass
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_content)
        f.flush()

        success, stdout, stderr = run_command(
            f"flake8 {f.name} --max-line-length=88 --extend-ignore=E203,W503,D,C420",
            check=False,
        )

        Path(f.name).unlink()  # Clean up

        if success:
            print("❌ ERROR: flake8 should have caught the long line!")
            return False
        elif "E501" in stdout or "E501" in stderr:
            print("✅ flake8 correctly detects long lines at 88 characters")
            return True
        else:
            print(f"❌ Unexpected flake8 output - stdout: {stdout}, stderr: {stderr}")
            return False


def test_black_line_length():
    """Test that Black is configured for 88 characters."""
    print("🔍 Testing Black line length configuration...")

    success, stdout, stderr = run_command("black --help", check=False)

    if success and "88" in stdout:
        print("✅ Black is available and uses 88 character default")
        return True
    else:
        print("❌ Could not verify Black configuration")
        return False


def test_coverage_threshold():
    """Test that coverage is configured for 90% threshold."""
    print("🔍 Testing coverage threshold configuration...")

    # Check .coveragerc file
    try:
        with open(".coveragerc", "r") as f:
            content = f.read()
            if "fail_under = 90" in content:
                print("✅ Coverage threshold set to 90% in .coveragerc")
                return True
            else:
                print("❌ Coverage threshold not set to 90% in .coveragerc")
                return False
    except FileNotFoundError:
        print("❌ .coveragerc file not found")
        return False


def test_pre_commit_config():
    """Test that pre-commit is configured correctly."""
    print("🔍 Testing pre-commit configuration...")

    try:
        with open(".pre-commit-config.yaml", "r") as f:
            content = f.read()

        checks = [
            ("black" in content, "Black hook configured"),
            ("isort" in content, "isort hook configured"),
            ("flake8" in content, "flake8 hook configured"),
            ("max-line-length=88" in content, "flake8 88-char limit configured"),
            ("mypy" in content, "mypy hook configured"),
            ("bandit" in content, "bandit hook configured"),
        ]

        all_good = True
        for check_passed, message in checks:
            if check_passed:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
                all_good = False

        return all_good

    except FileNotFoundError:
        print("❌ .pre-commit-config.yaml file not found")
        return False


def test_github_actions():
    """Test that GitHub Actions CI is configured correctly."""
    print("🔍 Testing GitHub Actions CI configuration...")

    try:
        with open(".github/workflows/ci.yml", "r") as f:
            content = f.read()

        checks = [
            ("black --check" in content, "Black check in CI"),
            ("isort --check" in content, "isort check in CI"),
            ("flake8" in content, "flake8 check in CI"),
            ("max-line-length=88" in content, "88-char limit in CI"),
            ("cov-fail-under=90" in content, "90% coverage threshold in CI"),
            ("mypy" in content, "mypy check in CI"),
        ]

        all_good = True
        for check_passed, message in checks:
            if check_passed:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
                all_good = False

        return all_good

    except FileNotFoundError:
        print("❌ .github/workflows/ci.yml file not found")
        return False


def main():
    """Run all validation tests."""
    print("🔧 Validating Quality Configuration")
    print("=" * 50)

    tests = [
        test_flake8_line_length,
        test_black_line_length,
        test_coverage_threshold,
        test_pre_commit_config,
        test_github_actions,
    ]

    results = []
    for test in tests:
        print()
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 ALL {total} CHECKS PASSED!")
        print("✅ Quality configuration is correctly set up to catch issues before PR.")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} checks FAILED!")
        print(
            "🚨 Quality configuration needs fixing before it can catch issues reliably."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
