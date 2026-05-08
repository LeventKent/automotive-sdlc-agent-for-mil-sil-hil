#!/usr/bin/env python3
"""
report.py — Extract test steps from an ecu.test TRF report.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.

By default returns ALL test steps. Use --filter to show only specific result types.

Usage:
    python3 report.py --report-path "/opt/ecu-test-workspace/Reports/test.trf"
    python3 report.py --report-path "/opt/ecu-test-workspace/Reports/test.trf" --filter FAILED ERROR
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from api_client_setup import get_api_client


def check_api_reachable(port: int = 5050) -> bool:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v2/live", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def collect_all_steps(test_step, path: str, results: list[dict], filter_results: set[str] | None = None) -> None:
    """Recursively collect test steps. If filter_results is None, collect all steps."""
    label = test_step.GetLabel()
    result = test_step.GetResult()
    current_path = f"{path} > {label}" if path else label

    if filter_results is None or result in filter_results:
        value = ""
        expected = ""
        try:
            value = str(test_step.GetValue() or "")
        except (AttributeError, Exception):
            pass
        try:
            expected = str(test_step.GetExpectedValue() or "")
        except (AttributeError, Exception):
            pass
        results.append({
            "path": current_path,
            "result": result,
            "comment": test_step.GetComment(),
            "value": value,
            "expectedValue": expected,
        })

    for child in test_step.GetTestSteps():
        collect_all_steps(child, current_path, results, filter_results)


def main():
    parser = argparse.ArgumentParser(description="Extract test steps from a TRF report.")
    parser.add_argument("--report-path", required=True, help="Path to the .trf report file")
    parser.add_argument(
        "--filter",
        nargs="*",
        default=None,
        help="Filter by result type (e.g. FAILED ERROR INCONCLUSIVE PASSED NONE). "
             "If omitted, all test steps are returned.",
    )
    args = parser.parse_args()

    report_path = Path(args.report_path)
    if not report_path.exists():
        print(f"ERROR: Report file not found: {report_path}")
        sys.exit(1)

    if not check_api_reachable():
        print("ERROR: ECU-TEST REST API not reachable at port 5050")
        sys.exit(1)

    filter_results = set(args.filter) if args.filter else None

    try:
        api = get_api_client()
        report = api.ReportApi.OpenReport(str(report_path))

        steps: list[dict] = []
        for package in report.GetTopLevelPackages():
            package_name = package.GetName()
            test_case = package.GetTestCase()
            for test_step in test_case.GetTestSteps():
                collect_all_steps(test_step, package_name, steps, filter_results)

        report.Close()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not steps:
        print("SUCCESS: No test steps found matching criteria.")
    else:
        lines = ["| Test Step | Result | Value | Expected | Comment |", "|---|---|---|---|---|"]
        for row in steps:
            lines.append(f"| {row['path']} | {row['result']} | {row['value']} | {row['expectedValue']} | {row['comment']} |")
        print("\n".join(lines))
        filter_desc = f" (filter: {', '.join(sorted(filter_results))})" if filter_results else ""
        print(f"SUCCESS: Report analyzed, {len(steps)} test step(s) found{filter_desc}")
    sys.exit(0)


if __name__ == "__main__":
    main()
