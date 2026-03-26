"""Docker integration snapshot helper.

Reads the container's output directory, builds the same snapshot structure
as test_output_snapshot.py, then either updates the baseline or compares
against it.

Usage:
    # Compare against existing snapshot:
    python3 docker_snapshot.py <output_dir> <snapshot_file>

    # Update (or create) the snapshot baseline:
    python3 docker_snapshot.py <output_dir> <snapshot_file> --update
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _build_snapshot(output_dir: Path) -> dict:
    """Collect comparable metrics from the output directory.

    Mirrors the logic in test_output_snapshot._build_snapshot().
    """
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
            entry["row_count"] = len([line for line in lines if line.strip()]) - 1

        snapshot["files"][path.name] = entry

    csv_files = [
        k for k in snapshot["files"] if k.endswith(".csv") and "duplicate" not in k
    ]
    snapshot["summary"] = {
        "total_files": len(snapshot["files"]),
        "csv_outputs": len(csv_files),
        "output_filenames": sorted(snapshot["files"].keys()),
    }

    return snapshot


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: docker_snapshot.py <output_dir> <snapshot_file> [--update]",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    snapshot_file = Path(sys.argv[2])
    update = "--update" in sys.argv

    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}", file=sys.stderr)
        sys.exit(1)

    current = _build_snapshot(output_dir)

    if update:
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(
            json.dumps(current, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"✅ Snapshot updated: {snapshot_file}")
        return

    if not snapshot_file.exists():
        print(
            f"❌ No snapshot found at {snapshot_file}.\n"
            "Run with UPDATE=1 to create your baseline:\n"
            "    make docker-integration UPDATE=1",
            file=sys.stderr,
        )
        sys.exit(1)

    baseline = json.loads(snapshot_file.read_text(encoding="utf-8"))
    diffs = []

    # Compare per-file metrics
    base_files = set(baseline.get("summary", {}).get("output_filenames", []))
    curr_files = set(current.get("summary", {}).get("output_filenames", []))
    for added in sorted(curr_files - base_files):
        diffs.append(f"  new output file: {added}")
    for removed in sorted(base_files - curr_files):
        diffs.append(f"  removed output file: {removed}")

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
        print(
            f"❌ Snapshot mismatch — {len(diffs)} change(s) detected:\n"
            f"{diff_text}\n\n"
            "If intentional, re-run with UPDATE=1 to accept:\n"
            "    make docker-integration UPDATE=1",
            file=sys.stderr,
        )
        sys.exit(1)

    total = sum(
        e.get("record_count", e.get("row_count", 0))
        for e in current["files"].values()
        if "record_count" in e or "row_count" in e
    )
    print(
        f"✅ Snapshot matches baseline ({total} records across {len(curr_files)} files)"
    )


if __name__ == "__main__":
    main()
