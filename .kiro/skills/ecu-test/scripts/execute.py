#!/usr/bin/env python3
"""
execute.py — Configure TBC+TCF in ECU-TEST, then execute a test case.

Usage:
    python execute.py --test-case "Packages/MyTest.pkg" --tbc "Configs/Bench.tbc" --tcf "Configs/Config.tcf"

Or imported as a module:
    from execute import run_workflow, WorkflowResult

    result = run_workflow(test_case="...", tbc="...", tcf="...")
    if result.success:
        print(f"Report ID: {result.test_report_id}")
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from configure_tcf import configure_tcf


@dataclass
class ExecutionResult:
    success: bool
    message: str
    test_report_id: str = ""
    test_report_path: str = ""
    result_raw: dict | None = None


@dataclass
class WorkflowResult:
    success: bool
    message: str
    test_report_id: str = ""
    test_report_path: str = ""
    result_raw: dict | None = None


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2"


def _get_json(url: str, timeout: int = 5) -> tuple[int, dict | None]:
    """GET a URL and return (status_code, parsed_json)."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return 0, None


def _put_execution(port: int, test_case_path: str) -> tuple[bool, int, str]:
    """Single PUT /execution attempt. Returns (success, status_code, message)."""
    body = {"testCasePath": test_case_path}
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{_base_url(port)}/execution",
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                return True, resp.status, "Execution request accepted."
            return False, resp.status, f"PUT /execution returned {resp.status}"
    except urllib.error.HTTPError as e:
        return False, e.code, f"PUT /execution returned {e.code}: {e.read().decode('utf-8', errors='replace')}"
    except (urllib.error.URLError, OSError):
        return False, 0, "Could not connect to ECU-TEST REST API."


def start_execution(port: int, test_case_path: str, retry_timeout: int = 120, verbose: bool = False) -> tuple[bool, str]:
    """PUT /execution to start a test case. Retries on 409 (busy) up to retry_timeout seconds."""
    ok, status, msg = _put_execution(port, test_case_path)
    if ok:
        return True, msg
    if status != 409:
        return False, msg

    # ECU-TEST is busy — retry until it becomes available
    if verbose:
        print("ECU-TEST is busy, waiting for it to become available...")
    deadline = time.time() + retry_timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        time.sleep(5)
        if verbose:
            print(f"  Retrying execution... ({attempt * 5}s / {retry_timeout}s)", end="\r")
        ok, status, msg = _put_execution(port, test_case_path)
        if ok:
            if verbose:
                print()
            return True, msg
        if status != 409:
            if verbose:
                print()
            return False, msg

    if verbose:
        print()
    return False, f"ECU-TEST remained busy for {retry_timeout}s. Last error: {msg}"


def get_execution_status(port: int) -> dict | None:
    """GET the current execution status."""
    status, data = _get_json(f"{_base_url(port)}/execution")
    if status == 200:
        return data
    return None


def _report_directory_for_test_case(test_case: str) -> Path:
    """Infer the workspace TestReports directory from a workspace Packages path."""
    package_path = Path(test_case)
    return package_path.parent.parent / "TestReports"


def wait_for_report_path(
    test_case: str,
    execution_started_at: float,
    timeout: int = 30,
) -> str:
    """Return the newly generated TRF path for a completed package, if available."""
    reports_dir = _report_directory_for_test_case(test_case)
    package_name = Path(test_case).stem
    deadline = time.time() + timeout

    while time.time() < deadline:
        candidates = [
            report
            for report in reports_dir.glob(f"{package_name}_*/*.trf")
            if report.is_file() and report.stat().st_mtime >= execution_started_at - 5
        ]
        if candidates:
            return str(max(candidates, key=lambda report: report.stat().st_mtime))
        time.sleep(1)

    return ""


def _extract_result(execution: dict) -> tuple[str, dict]:
    """Extract test report ID and raw result from an execution response."""
    result_obj = execution.get("result", {})
    test_report_id = result_obj.get("testReportId", "")
    return test_report_id, result_obj


_TERMINAL_STATES = frozenset({"FINISHED", "FAILED", "ERROR", "ABORTED"})
_IN_PROGRESS_STATES = frozenset({"WAITING", "RUNNING", ""})


def wait_for_execution(port: int, exec_timeout: int, verbose: bool = False) -> ExecutionResult:
    """Poll /execution until a terminal state is reached or timeout expires."""
    deadline = time.time() + exec_timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        execution = get_execution_status(port)
        status_key = ""
        if execution is not None:
            status_key = execution.get("status", {}).get("key", "")
            status_msg = execution.get("status", {}).get("message", "")

            if status_key in _TERMINAL_STATES:
                test_report_id, result_obj = _extract_result(execution)

                if status_key == "FINISHED":
                    msg = f"Test execution finished (after ~{attempt}s)."
                    return ExecutionResult(
                        success=True,
                        message=msg,
                        test_report_id=test_report_id,
                        result_raw=result_obj,
                    )

                msg = f"Test execution {status_key} (after ~{attempt}s)."
                if status_msg:
                    msg += f" {status_msg}"
                return ExecutionResult(
                    success=False,
                    message=msg,
                    test_report_id=test_report_id,
                    result_raw=result_obj,
                )

            if status_key not in _IN_PROGRESS_STATES:
                test_report_id, result_obj = _extract_result(execution)
                msg = f"Execution entered unexpected state: {status_key}"
                if status_msg:
                    msg += f" — {status_msg}"
                return ExecutionResult(
                    success=False,
                    message=msg,
                    test_report_id=test_report_id,
                    result_raw=result_obj,
                )

        if verbose:
            print(
                f"  Waiting for execution... status={status_key or 'N/A'} ({attempt}s / {exec_timeout}s)",
                end="\r",
            )
        time.sleep(1)

    if verbose:
        print()
    return ExecutionResult(success=False, message=f"Execution did not finish within {exec_timeout}s.")


def execute_test_case(
    test_case: str,
    port: int = 5050,
    exec_timeout: int = 600,
    verbose: bool = False,
) -> ExecutionResult:
    """Execute a test case in ECU-TEST and wait for completion."""
    if verbose:
        print(f"Test case: {test_case}")
        print(f"Port     : {port}")
        print()

    execution_started_at = time.time()
    ok, msg = start_execution(port, test_case, retry_timeout=120, verbose=verbose)
    if not ok:
        return ExecutionResult(success=False, message=msg)

    if verbose:
        print(f"Execution request accepted. Waiting up to {exec_timeout}s for completion...")

    result = wait_for_execution(port, exec_timeout, verbose=verbose)
    if result.success:
        result.test_report_path = wait_for_report_path(
            test_case,
            execution_started_at,
        )
    return result


def run_workflow(
    test_case: str,
    tbc: str,
    tcf: str,
    port: int = 5050,
    timeout: int = 120,
    exec_timeout: int = 600,
    verbose: bool = False,
) -> WorkflowResult:
    """
    End-to-end workflow: load TBC+TCF configuration, then execute a test case.

    Args:
        test_case: Path to the test case package (.pkg).
        tbc: Path to the test bench configuration file (.tbc).
        tcf: Path to the test configuration file (.tcf).
        port: REST API port (default: 5050).
        timeout: Seconds to wait for configuration (default: 120).
        exec_timeout: Seconds to wait for test execution (default: 600).
        verbose: Print progress to stdout (default: False).

    Returns:
        WorkflowResult with success flag, message, and test_report_id.
    """
    if verbose:
        print("=" * 60)
        print("Step 1/2: Configure TBC + TCF")
        print("=" * 60)

    config_result = configure_tcf(tcf=tcf, tbc=tbc, port=port, timeout=timeout, verbose=verbose)
    if not config_result.success:
        return WorkflowResult(success=False, message=f"Configuration failed: {config_result.message}")

    if verbose:
        print(f"  {config_result.message}")
        print()
        print("=" * 60)
        print("Step 2/2: Execute test case")
        print("=" * 60)

    exec_result = execute_test_case(
        test_case=test_case,
        port=port,
        exec_timeout=exec_timeout,
        verbose=verbose,
    )

    report_suffix = ""
    if exec_result.test_report_id:
        report_suffix += f" Test Report ID: {exec_result.test_report_id}"
    if exec_result.test_report_path:
        report_suffix += f" Report path: {exec_result.test_report_path}"

    if not exec_result.success:
        return WorkflowResult(
            success=False,
            message=f"Execution failed: {exec_result.message}{report_suffix}",
            test_report_id=exec_result.test_report_id,
            test_report_path=exec_result.test_report_path,
            result_raw=exec_result.result_raw,
        )

    return WorkflowResult(
        success=True,
        message=f"Test case '{test_case}' execution finished.{report_suffix}",
        test_report_id=exec_result.test_report_id,
        result_raw=exec_result.result_raw,
    )


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Configure TBC+TCF in ECU-TEST and execute a test case.",
    )
    parser.add_argument("--test-case", required=True, help="Path to the test case package (.pkg)")
    parser.add_argument("--tbc", required=True, help="Path to the test bench configuration (.tbc)")
    parser.add_argument("--tcf", required=True, help="Path to the test configuration (.tcf)")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Config timeout in seconds (default: 120)")
    parser.add_argument("--exec-timeout", type=int, default=600, help="Execution timeout in seconds (default: 600)")
    return parser.parse_args()


def main():
    args = _parse_args()
    result = run_workflow(
        test_case=args.test_case,
        tbc=args.tbc,
        tcf=args.tcf,
        port=args.port,
        timeout=args.timeout,
        exec_timeout=args.exec_timeout,
        verbose=True,
    )
    if result.success:
        print(f"\nSUCCESS: {result.message}")
    else:
        print(f"\nERROR: {result.message}")

    if result.test_report_id:
        print(f"Test Report ID: {result.test_report_id}")
    if result.test_report_path:
        print(f"Report path: {result.test_report_path}")
    if result.result_raw:
        print(f"Raw result: {json.dumps(result.result_raw, indent=2)}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
