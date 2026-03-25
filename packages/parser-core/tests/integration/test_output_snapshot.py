"""Integration snapshot test for end-to-end output validation.

Runs the full processing pipeline against the real input/ directory and
compares key output metrics against a committed snapshot baseline.

Usage:
    # Run the integration test (skipped by default):
    pytest -m integration

    # Update the snapshot baseline (first run or after intentional change):
    pytest -m integration --snapshot-update

The snapshot file is committed to source control so changes are visible in
code review. Input/output folders are gitignored and never committed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Root of the repo (two levels up from this file: tests/integration/ -> tests/ -> parser-core/)
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
INPUT_DIR = REPO_ROOT / "input"
OUTPUT_DIR = REPO_ROOT / "output"
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SNAPSHOT_FILE = SNAPSHOT_DIR / "output_snapshot.json"


def _build_snapshot(output_dir: Path) -> dict:
    """Collect comparable metrics from the output directory."""
    snapshot: dict = {"files": {}}

    for path in sorted(output_dir.iterdir()):
        if path.name.startswith(".") or path.is_dir():
            continue

        entry: dict = {"size_bytes": path.stat().st_size}

        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    entry["record_count"] = len(data)
                elif isinstance(data, dict):
                    entry["keys"] = sorted(data.keys())
            except json.JSONDecodeError:
                pass

        if path.suffix == ".csv":
            lines = path.read_text(encoding="utf-8").splitlines()
            # header + data rows (exclude empty trailing lines)
            entry["row_count"] = len([l for l in lines if l.strip()]) - 1

        snapshot["files"][path.name] = entry

    # Top-level summary metrics
    csv_files = [k for k in snapshot["files"] if k.endswith(".csv") and "duplicate" not in k]
    snapshot["summary"] = {
        "total_files": len(snapshot["files"]),
        "csv_outputs": len(csv_files),
        "output_filenames": sorted(snapshot["files"].keys()),
    }

    return snapshot


@pytest.mark.integration
def test_output_snapshot(request: pytest.FixtureRequest) -> None:
    """Run full processing pipeline and compare output against snapshot baseline.

    Pass --snapshot-update to regenerate the baseline instead of comparing.
    """
    if not INPUT_DIR.exists() or not any(INPUT_DIR.rglob("*.pdf")):
        pytest.skip(f"No PDF files found in {INPUT_DIR} — skipping snapshot test")

    # Import here so the test is skippable without importing the full app
    from bankstatements_core.config.app_config import AppConfig
    from bankstatements_core.entitlements import Entitlements
    from bankstatements_core.facades.processing_facade import BankStatementProcessingFacade

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        recursive_scan=True,
        generate_monthly_summary=True,
        generate_expense_analysis=True,
    )

    facade = BankStatementProcessingFacade(config, Entitlements.free_tier())
    summary = facade.process_all()

    current = _build_snapshot(OUTPUT_DIR)
    current["processing_summary"] = {
        "pdf_count": summary.get("pdf_count"),
        "pages_read": summary.get("pages_read"),
        "transactions": summary.get("transactions"),
        "duplicates": summary.get("duplicates"),
    }

    update = request.config.getoption("--snapshot-update", default=False)

    if update:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(
            json.dumps(current, indent=2, sort_keys=True), encoding="utf-8"
        )
        pytest.skip(f"Snapshot updated: {SNAPSHOT_FILE}")
        return

    if not SNAPSHOT_FILE.exists():
        pytest.fail(
            f"No snapshot found at {SNAPSHOT_FILE}.\n"
            "Run with --snapshot-update to create the baseline."
        )

    baseline = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))

    diffs = []

    # Compare processing summary counts
    for key in ("pdf_count", "pages_read", "transactions", "duplicates"):
        base_val = baseline.get("processing_summary", {}).get(key)
        curr_val = current.get("processing_summary", {}).get(key)
        if base_val != curr_val:
            diffs.append(f"  processing_summary.{key}: {base_val} → {curr_val}")

    # Compare output file names
    base_files = set(baseline.get("summary", {}).get("output_filenames", []))
    curr_files = set(current.get("summary", {}).get("output_filenames", []))
    for added in sorted(curr_files - base_files):
        diffs.append(f"  new output file: {added}")
    for removed in sorted(base_files - curr_files):
        diffs.append(f"  removed output file: {removed}")

    # Compare per-file metrics
    for fname in sorted(base_files & curr_files):
        base_entry = baseline["files"].get(fname, {})
        curr_entry = current["files"].get(fname, {})
        for metric in ("row_count", "record_count"):
            bv = base_entry.get(metric)
            cv = curr_entry.get(metric)
            if bv is not None and bv != cv:
                diffs.append(f"  {fname}.{metric}: {bv} → {cv}")

    if diffs:
        diff_text = "\n".join(diffs)
        pytest.fail(
            f"Output snapshot mismatch — {len(diffs)} change(s) detected:\n"
            f"{diff_text}\n\n"
            "If this change is intentional, re-run with --snapshot-update to accept it."
        )
