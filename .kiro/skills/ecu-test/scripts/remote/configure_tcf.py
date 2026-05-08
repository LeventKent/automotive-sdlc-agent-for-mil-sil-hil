#!/usr/bin/env python3
"""
configure_tcf.py — Ensure a TCF (and optionally TBC) is loaded in ECU-TEST.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.

Usage:
    python3 configure_tcf.py --tcf "MyTestConfiguration.tcf"
    python3 configure_tcf.py --tcf "MyTestConfiguration.tcf" --tbc "MyTestbench.tbc"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2"


def _get_json(url: str, timeout: int = 5) -> tuple[int, dict | None]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return 0, None


def check_api_reachable(port: int) -> bool:
    """Check API reachable within 10s."""
    deadline = time.time() + 10
    while time.time() < deadline:
        status, _ = _get_json(f"{_base_url(port)}/live", timeout=3)
        if status == 200:
            return True
        time.sleep(1)
    return False


def is_tcf_already_running(port: int, tcf_path: str) -> bool:
    config = get_configuration(port)
    if config is None:
        return False
    status_key = config.get("status", {}).get("key", "")
    current_tcf = config.get("tcf", {}).get("tcfPath", "")
    if not current_tcf:
        current_tcf = config.get("order", {}).get("tcf", {}).get("tcfPath", "")
    return status_key in ("RUNNING", "FINISHED") and current_tcf == tcf_path


def get_configuration(port: int) -> dict | None:
    status, data = _get_json(f"{_base_url(port)}/configuration")
    return data if status == 200 else None


def start_configuration(port: int, tcf_path: str, tbc_path: str = "") -> tuple[bool, str]:
    body: dict = {"action": "Start", "tcf": {"tcfPath": tcf_path}}
    if tbc_path:
        body["tbc"] = {"tbcPath": tbc_path}
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{_base_url(port)}/configuration", data=data, method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                return True, "Configuration request accepted."
            return False, f"PUT /configuration returned {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"PUT /configuration returned {e.code}"
    except (urllib.error.URLError, OSError):
        return False, "Could not connect to ECU-TEST REST API."


def wait_for_running(port: int, timeout: int) -> tuple[bool, str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        config = get_configuration(port)
        if config is not None:
            status_key = config.get("status", {}).get("key", "")
            if status_key in ("RUNNING", "FINISHED"):
                return True, f"Configuration is {status_key}."
            if status_key in ("FAILED", "ERROR", "ABORTED"):
                return False, f"Configuration {status_key}."
        time.sleep(1)
    return False, f"Configuration did not reach RUNNING state within {timeout}s."


def main():
    parser = argparse.ArgumentParser(description="Configure TCF in ECU-TEST via REST API.")
    parser.add_argument("--tcf", required=True, help="Path to the test configuration file (.tcf)")
    parser.add_argument("--tbc", default="", help="Path to the test bench configuration (.tbc)")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait (default: 120)")
    args = parser.parse_args()

    if not check_api_reachable(args.port):
        print(f"ERROR: ECU-TEST REST API not reachable at port {args.port}")
        sys.exit(1)

    if is_tcf_already_running(args.port, args.tcf):
        print(f"SUCCESS: TCF '{args.tcf}' is already running")
        sys.exit(0)

    ok, msg = start_configuration(args.port, args.tcf, args.tbc)
    if not ok:
        print(f"ERROR: {msg}")
        sys.exit(1)

    ok, msg = wait_for_running(args.port, args.timeout)
    if ok:
        print(f"SUCCESS: {msg}")
        sys.exit(0)
    else:
        print(f"ERROR: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
