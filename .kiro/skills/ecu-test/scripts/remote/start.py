#!/usr/bin/env python3
"""
start.py — Launch ECU-TEST on Linux and wait until its REST API is ready.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.

Usage:
    python3 start.py
    python3 start.py --port 5050 --timeout 60
    python3 start.py --workspace-dir /opt/ecu-test-workspace
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

DEFAULT_EXE = "/usr/bin/ecu.test"
DEFAULT_WORKSPACE = "/opt/ecu-test-workspace"


def parse_args():
    parser = argparse.ArgumentParser(description="Start ECU-TEST and verify REST API readiness.")
    parser.add_argument("--exe-path", default=DEFAULT_EXE, help=f"Path to ECU-TEST executable (default: {DEFAULT_EXE})")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait for readiness (default: 60)")
    parser.add_argument("--workspace-dir", default=DEFAULT_WORKSPACE, help=f"ECU-TEST workspace directory (default: {DEFAULT_WORKSPACE})")
    return parser.parse_args()


def live_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2/live"


def is_already_running(port: int) -> bool:
    try:
        r = requests.get(live_url(port), timeout=2)
        return r.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


def launch_ecu_test(exe_path: str, port: int, workspace_dir: str) -> subprocess.Popen:
    cmd = [exe_path, "--start-web-api", f"--restApiPort={port}", f"--workspaceDir={workspace_dir}"]
    print(f"Launching: {' '.join(cmd)}")

    # TRACET_LICENSE must be set in the environment (passed by the adapter or set on the instance)
    env = os.environ.copy()
    license_val = env.get("TRACET_LICENSE", "")
    if license_val:
        print(f"Setting TRACET_LICENSE={license_val}")
    else:
        print("WARNING: TRACET_LICENSE not set in environment. ECU-TEST may fail to start.")

    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True, env=env)


def wait_until_ready(port: int, timeout: int) -> bool:
    url = live_url(port)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        time.sleep(2)
    return False


def main():
    args = parse_args()

    # Check if API is reachable within 10s (output contract: fail fast if unreachable and not starting)
    if is_already_running(args.port):
        print("ECU-TEST is already running.")
        print("SUCCESS: ECU-TEST started and REST API ready")
        sys.exit(0)

    try:
        launch_ecu_test(args.exe_path, args.port, args.workspace_dir)
    except FileNotFoundError:
        print(f"ERROR: Executable not found: {args.exe_path}")
        sys.exit(1)
    except PermissionError:
        print(f"ERROR: Permission denied: {args.exe_path}")
        sys.exit(1)

    if wait_until_ready(args.port, args.timeout):
        print("SUCCESS: ECU-TEST started and REST API ready")
        sys.exit(0)
    else:
        print(f"ERROR: ECU-TEST did not become ready within {args.timeout}s")
        sys.exit(1)


if __name__ == "__main__":
    main()
