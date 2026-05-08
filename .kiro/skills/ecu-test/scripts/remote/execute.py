#!/usr/bin/env python3
"""
execute.py — Configure TBC+TCF in ECU-TEST, then execute a test case.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.

Usage:
    python3 execute.py --test-case "Packages/MyTest.pkg" --tbc "Configs/Bench.tbc" --tcf "Configs/Config.tcf"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

from configure_tcf import check_api_reachable, start_configuration, wait_for_running, is_tcf_already_running


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2"


def _put_execution(port: int, test_case_path: str) -> tuple[bool, int, str]:
    body = {"testCasePath": test_case_path}
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{_base_url(port)}/execution", data=data, method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                return True, resp.status, "Execution request accepted."
            return False, resp.status, f"PUT /execution returned {resp.status}"
    except urllib.error.HTTPError as e:
        return False, e.code, f"PUT /execution returned {e.code}"
    except (urllib.error.URLError, OSError):
        return False, 0, "Could not connect to ECU-TEST REST API."


def start_execution(port: int, test_case_path: str, retry_timeout: int = 120) -> tuple[bool, str]:
    ok, status, msg = _put_execution(port, test_case_path)
    if ok:
        return True, msg
    if status != 409:
        return False, msg

    deadline = time.time() + retry_timeout
    while time.time() < deadline:
        time.sleep(5)
        ok, status, msg = _put_execution(port, test_case_path)
        if ok:
            return True, msg
        if status != 409:
            return False, msg

    return False, f"ECU-TEST remained busy for {retry_timeout}s"


def wait_for_execution(port: int, exec_timeout: int) -> tuple[bool, str, str]:
    """Returns (success, message, test_report_id)."""
    deadline = time.time() + exec_timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{_base_url(port)}/execution", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                execution = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            time.sleep(1)
            continue

        status_key = execution.get("status", {}).get("key", "")
        result_obj = execution.get("result", {})
        report_id = result_obj.get("testReportId", "")

        if status_key == "FINISHED":
            return True, "Test execution finished.", report_id
        if status_key in ("FAILED", "ERROR", "ABORTED"):
            return False, f"Test execution {status_key}.", report_id

        time.sleep(1)

    return False, f"Execution did not finish within {exec_timeout}s.", ""


def main():
    parser = argparse.ArgumentParser(description="Configure TBC+TCF and execute a test case.")
    parser.add_argument("--test-case", required=True, help="Path to the test case package (.pkg)")
    parser.add_argument("--tbc", required=True, help="Path to the test bench configuration (.tbc)")
    parser.add_argument("--tcf", required=True, help="Path to the test configuration (.tcf)")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Config timeout (default: 120)")
    parser.add_argument("--exec-timeout", type=int, default=600, help="Execution timeout (default: 600)")
    args = parser.parse_args()

    if not check_api_reachable(args.port):
        print(f"ERROR: ECU-TEST REST API not reachable at port {args.port}")
        sys.exit(1)

    # Step 1: Configure TBC + TCF
    if not is_tcf_already_running(args.port, args.tcf):
        ok, msg = start_configuration(args.port, args.tcf, args.tbc)
        if not ok:
            print(f"ERROR: Configuration failed: {msg}")
            sys.exit(1)
        ok, msg = wait_for_running(args.port, args.timeout)
        if not ok:
            print(f"ERROR: {msg}")
            sys.exit(1)

    # Step 2: Execute test case
    ok, msg = start_execution(args.port, args.test_case, retry_timeout=120)
    if not ok:
        print(f"ERROR: {msg}")
        sys.exit(1)

    # Step 3: Wait for completion
    ok, msg, report_id = wait_for_execution(args.port, args.exec_timeout)
    if ok:
        summary = msg
        if report_id:
            summary += f" Report ID: {report_id}"
        print(f"SUCCESS: {summary}")
        sys.exit(0)
    else:
        print(f"ERROR: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
