#!/usr/bin/env python3
"""Delete generated ECU-TEST report artifacts without stopping ECU-TEST.

Invoke through the adapter only when the user explicitly requests report cleanup:

    ./ecu-test-adapter.sh cleanup_ecu_test_reports.py
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def clear_reports(reports_dir: Path) -> int:
    """Remove report artifacts while preserving an optional .keep placeholder."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    removed = 0

    for entry in reports_dir.iterdir():
        if entry.name == ".keep":
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
        removed += 1

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete generated report artifacts from the remote ECU-TEST workspace."
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("/opt/ecu-test-workspace/TestReports"),
        help="Remote report directory to clean.",
    )
    args = parser.parse_args()

    removed = clear_reports(args.reports_dir)
    print(f"Removed {removed} report artifact(s) from {args.reports_dir}.")


if __name__ == "__main__":
    main()
