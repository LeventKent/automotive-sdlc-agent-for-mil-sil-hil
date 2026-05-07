#!/usr/bin/env python3
"""
report.py — Extract failed/error/inconclusive test steps from an ecu.test TRF report.

Usage:
    python report.py --report-path "C:\\workspace\\TestReports\\my_test\\my_test.trf"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from api_client_setup import get_api_client


FAILED_RESULTS = {"FAILED", "ERROR", "INCONCLUSIVE"}


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


def collect_failed_steps(test_step, path: str, results: list[dict]) -> None:
    label = test_step.GetLabel()
    result = test_step.GetResult()
    current_path = f"{path} > {label}" if path else label

    if result in FAILED_RESULTS:
        results.append({
            "path": current_path,
            "result": result,
            "comment": test_step.GetComment(),
            "value": safe_get_step_field(test_step, "GetValue"),
            "expectedValue": safe_get_step_field(test_step, "GetExpectedValue"),
        })

    for child in test_step.GetTestSteps():
        collect_failed_steps(child, current_path, results)


def build_markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "All test steps passed successfully."

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


def extract_failed_steps_from_report(report_path: str | Path) -> list[dict]:
    """Open a TRF report and extract all failed/error/inconclusive steps."""
    api = get_api_client()
    report = api.ReportApi.OpenReport(str(report_path))

    try:
        failed_steps: list[dict] = []

        for package in report.GetTopLevelPackages():
            package_name = package.GetName()
            test_case = package.GetTestCase()
            for test_step in test_case.GetTestSteps():
                collect_failed_steps(test_step, package_name, failed_steps)

        return failed_steps
    finally:
        report.Close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract failed/error/inconclusive test steps from an ecu.test TRF report."
    )
    parser.add_argument(
        "--report-path",
        required=True,
        help="Absolute path to the ecu.test report file (.trf)",
    )
    args = parser.parse_args()

    failed_steps = extract_failed_steps_from_report(args.report_path)
    print(build_markdown_table(failed_steps))


if __name__ == "__main__":
    main()
