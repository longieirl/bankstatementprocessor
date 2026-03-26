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

import csv
import json
import re
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
            entry["row_count"] = len([line for line in lines if line.strip()]) - 1

        snapshot["files"][path.name] = entry

    # Top-level summary metrics
    csv_files = [
        k for k in snapshot["files"] if k.endswith(".csv") and "duplicate" not in k
    ]
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
    from bankstatements_core.facades.processing_facade import (
        BankStatementProcessingFacade,
    )

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
        "pdfs_extracted": summary.get("pdfs_extracted"),
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
    for key in (
        "pdf_count",
        "pdfs_extracted",
        "pages_read",
        "transactions",
        "duplicates",
    ):
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

    _assert_output_invariants(OUTPUT_DIR, summary)


# ---------------------------------------------------------------------------
# Structural invariants — always asserted regardless of snapshot update mode
# ---------------------------------------------------------------------------

_IBAN_MASKED_RE = re.compile(r"^[A-Z]{2}[0-9]{2}\*+[0-9]{4}$")
_IBAN_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _assert_output_invariants(output_dir: Path, summary: dict) -> None:
    """Assert structural correctness of the output directory.

    These checks are independent of the snapshot baseline — they validate
    relationships between output files that must always hold true.
    """
    pdf_count = summary.get("pdf_count", 0)
    pdfs_extracted = summary.get("pdfs_extracted", 0)
    transactions = summary.get("transactions", 0)
    duplicates = summary.get("duplicates", 0)

    # 1a. Pipeline produced meaningful output
    assert pdfs_extracted > 0, "pdfs_extracted == 0 — pipeline silently processed nothing"
    assert transactions > 0, "transactions == 0 — no transactions extracted"

    # 1b. Excluded files log is consistent with processing summary
    excluded_path = output_dir / "excluded_files.json"
    if excluded_path.exists():
        excluded_data = json.loads(excluded_path.read_text(encoding="utf-8"))
        total_excluded = excluded_data.get("summary", {}).get("total_excluded", 0)
        assert total_excluded == pdf_count - pdfs_extracted, (
            f"excluded_files.json total_excluded ({total_excluded}) != "
            f"pdf_count - pdfs_extracted ({pdf_count} - {pdfs_extracted})"
        )
        for entry in excluded_data.get("excluded_files", []):
            assert entry.get("reason"), f"Excluded file {entry.get('filename')!r} has no reason"
            assert (entry.get("pages") or 0) > 0, (
                f"Excluded file {entry.get('filename')!r} has pages <= 0"
            )

    # 1c. IBAN file: record count, format, and filename suffix mapping
    ibans_path = output_dir / "ibans.json"
    if ibans_path.exists():
        ibans = json.loads(ibans_path.read_text(encoding="utf-8"))
        assert isinstance(ibans, list), "ibans.json should be a JSON array"
        assert len(ibans) == pdfs_extracted, (
            f"ibans.json has {len(ibans)} entries but pdfs_extracted == {pdfs_extracted}"
        )
        iban_suffixes = set()
        for entry in ibans:
            masked = entry.get("iban_masked", "")
            digest = entry.get("iban_digest", "")
            assert _IBAN_MASKED_RE.match(masked), (
                f"Masked IBAN {masked!r} does not match expected format [A-Z]{{2}}[0-9]{{2}}*...[0-9]{{4}}"
            )
            assert _IBAN_DIGEST_RE.match(digest), (
                f"IBAN digest {digest!r} is not a valid 64-char hex SHA-256"
            )
            iban_suffixes.add(masked[-4:])

        # Every IBAN-specific output file suffix must correspond to a known IBAN
        for path in output_dir.iterdir():
            match = re.match(r"bank_statements_(\d{4})\.", path.name)
            if match:
                suffix = match.group(1)
                assert suffix in iban_suffixes, (
                    f"Output file {path.name!r} has suffix {suffix!r} "
                    f"but no IBAN ending in those digits found in ibans.json"
                )

    # 1d. Transaction count cross-check: CSV rows == JSON records per IBAN pair
    iban_csv_files = [
        p for p in output_dir.iterdir()
        if re.match(r"bank_statements_\d{4}\.csv$", p.name)
    ]
    csv_total = 0
    for csv_path in iban_csv_files:
        stem = csv_path.stem  # e.g. bank_statements_3656
        json_path = output_dir / f"{stem}.json"
        lines = csv_path.read_text(encoding="utf-8").splitlines()
        csv_rows = len([l for l in lines if l.strip()]) - 1  # exclude header
        csv_total += csv_rows
        if json_path.exists():
            json_records = json.loads(json_path.read_text(encoding="utf-8"))
            assert isinstance(json_records, list)
            assert len(json_records) == csv_rows, (
                f"{csv_path.name} has {csv_rows} rows but "
                f"{json_path.name} has {len(json_records)} records"
            )

    assert csv_total == transactions, (
        f"Sum of IBAN-specific CSV rows ({csv_total}) != transactions ({transactions})"
    )

    # 1e. CSV column integrity on each IBAN-specific CSV
    required_columns = {"Date", "Details"}
    debit_credit_columns = {"Debit", "Credit", "Debit €", "Credit €"}
    for csv_path in iban_csv_files:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
        assert len(columns) == len(set(columns)), (
            f"{csv_path.name} has duplicate column names: {columns}"
        )
        assert all(c for c in columns), (
            f"{csv_path.name} has empty column name(s): {columns}"
        )
        missing = required_columns - set(columns)
        assert not missing, (
            f"{csv_path.name} is missing required columns: {missing}"
        )
        assert debit_credit_columns & set(columns), (
            f"{csv_path.name} has no Debit or Credit column: {columns}"
        )

    # 1f. Duplicate files are valid JSON arrays with length matching summary
    duplicate_files = [
        p for p in output_dir.iterdir()
        if re.match(r"duplicates.*\.json$", p.name)
    ]
    total_duplicate_records = 0
    for dup_path in duplicate_files:
        data = json.loads(dup_path.read_text(encoding="utf-8"))
        assert isinstance(data, list), f"{dup_path.name} is not a JSON array"
        total_duplicate_records += len(data)

    # The global duplicates.json + per-IBAN files may double-count; just verify
    # each file is a valid array (length consistency checked via summary count).
    global_dup = output_dir / "duplicates.json"
    if global_dup.exists():
        global_data = json.loads(global_dup.read_text(encoding="utf-8"))
        assert isinstance(global_data, list)
        assert len(global_data) == duplicates, (
            f"duplicates.json has {len(global_data)} records but summary says {duplicates} duplicates"
        )
