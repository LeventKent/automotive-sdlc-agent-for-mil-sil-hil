#!/usr/bin/env python3
"""
report.py — Extract test steps from an ecu.test TRF report.

By default returns ALL test steps. Use --filter to show only specific result types.

Usage:
    python report.py --report-path "C:\\workspace\\TestReports\\my_test\\my_test.trf"
    python report.py --report-path "C:\\workspace\\TestReports\\my_test\\my_test.trf" --filter FAILED ERROR
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from api_client_setup import get_api_client


def safe_get_step_field(test_step, method_name: str) -> str:
    try:
        method = getattr(test_step, method_name)
    except AttributeError:
        return ""
    try:
        value = method()
    except Exception:
        return ""
    if value is None:
        return ""
    return str(value)


def collect_all_steps(test_step, path: str, results: list[dict], filter_results: set[str] | None = None) -> None:
    """Recursively collect test steps. If filter_results is None, collect all steps."""
    label = test_step.GetLabel()
    result = test_step.GetResult()
    current_path = f"{path} > {label}" if path else label

    if filter_results is None or result in filter_results:
        results.append({
            "path": current_path,
            "result": result,
            "comment": test_step.GetComment(),
            "value": safe_get_step_field(test_step, "GetValue"),
            "expectedValue": safe_get_step_field(test_step, "GetExpectedValue"),
        })

    for child in test_step.GetTestSteps():
        collect_all_steps(child, current_path, results, filter_results)


def build_markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "No test steps found."

    lines = [
        "| Test Step | Result | Value | Expected Value | Comment |",
        "|-----------|--------|-------|----------------|---------|",
    ]
    for row in rows:
        value = row["value"].replace("|", "\\|").replace("\n", " ")
        expected = row["expectedValue"].replace("|", "\\|").replace("\n", " ")
        comment = row["comment"].replace("|", "\\|").replace("\n", " ")
        lines.append(f'| {row["path"]} | {row["result"]} | {value} | {expected} | {comment} |')
    return "\n".join(lines)


def extract_steps_from_report(report_path: str | Path, filter_results: set[str] | None = None) -> list[dict]:
    """Open a TRF report and extract test steps.

    Args:
        report_path: Absolute path to the .trf report file.
        filter_results: If provided, only collect steps with these result types.
                        If None, collect ALL steps.
    """
    api = get_api_client()
    report = api.ReportApi.OpenReport(str(report_path))

    try:
        steps: list[dict] = []

        for package in report.GetTopLevelPackages():
            package_name = package.GetName()
            test_case = package.GetTestCase()
            for test_step in test_case.GetTestSteps():
                collect_all_steps(test_step, package_name, steps, filter_results)

        return steps
    finally:
        report.Close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract test steps from an ecu.test TRF report."
    )
    parser.add_argument(
        "--report-path",
        required=True,
        help="Absolute path to the ecu.test report file (.trf)",
    )
    parser.add_argument(
        "--filter",
        nargs="*",
        default=None,
        help="Filter by result type (e.g. FAILED ERROR INCONCLUSIVE PASSED NONE). "
             "If omitted, all test steps are returned.",
    )
    args = parser.parse_args()

    filter_results = set(args.filter) if args.filter else None
    steps = extract_steps_from_report(args.report_path, filter_results)
    print(build_markdown_table(steps))


if __name__ == "__main__":
    main()
