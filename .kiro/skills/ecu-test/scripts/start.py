#!/usr/bin/env python3
"""
start.py — Launch ECU-TEST and wait until its REST API is ready.

Usage:
    python start.py --exe-path "C:\\Program Files\\ecu.test 2026.2\\ecu.test.exe"
    python start.py --exe-path "..." --port 5050 --timeout 60
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Install it with: pip install requests")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Start ECU-TEST and verify it is ready via REST API.")
    parser.add_argument(
        "--exe-path",
        required=True,
        help='Path to the ECU-TEST executable, e.g. "C:\\Program Files\\ecu.test 2026.2\\ecu.test.exe"',
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="REST API port ECU-TEST should listen on (default: 5050)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Seconds to wait for ECU-TEST to become ready (default: 60)",
    )
    return parser.parse_args()


def live_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2/live"


def is_already_running(port: int) -> bool:
    """Return True if ECU-TEST is already up and responding."""
    try:
        r = requests.get(live_url(port), timeout=2)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def launch_ecu_test(exe_path: str, port: int) -> subprocess.Popen:
    """Start ECU-TEST as a detached subprocess."""
    cmd = [exe_path, "--start-web-api", f"--restApiPort={port}"]
    print(f"Launching: {' '.join(cmd)}")
    kwargs: dict = dict(
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        print("WARNING: ECU-TEST is a Windows application. Launch step may fail on this platform.")

    return subprocess.Popen(cmd, **kwargs)


def wait_until_ready(port: int, timeout: int) -> bool:
    """Poll the /live endpoint until 200 OK or timeout. Returns True on success."""
    url = live_url(port)
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"ECU-TEST is ready (responded after ~{attempt}s).")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"  Waiting for ECU-TEST... ({attempt}s / {timeout}s)", end="\r")
        time.sleep(1)
    print()
    return False


def main():
    args = parse_args()
    exe_path = args.exe_path
    port = args.port
    timeout = args.timeout

    print(f"ECU-TEST executable : {exe_path}")
    print(f"REST API port       : {port}")
    print(f"Startup timeout     : {timeout}s")
    print()

    if is_already_running(port):
        print("ECU-TEST is already running and responding on the REST API. Nothing to do.")
        sys.exit(0)

    exe = Path(exe_path)
    if sys.platform == "win32" and not exe.exists():
        print(f"ERROR: Executable not found: {exe_path}")
        sys.exit(1)

    try:
        launch_ecu_test(exe_path, port)
    except FileNotFoundError:
        print(f"ERROR: Could not launch ECU-TEST — file not found: {exe_path}")
        sys.exit(1)
    except PermissionError:
        print(f"ERROR: Permission denied when launching: {exe_path}")
        sys.exit(1)

    print(f"Process launched. Waiting up to {timeout}s for REST API to become ready...")
    print()

    if wait_until_ready(port, timeout):
        print(f"\nSUCCESS: ECU-TEST started and REST API is ready at http://127.0.0.1:{port}/api/v2")
        sys.exit(0)
    else:
        print(f"\nERROR: ECU-TEST did not become ready within {timeout}s.")
        sys.exit(1)


if __name__ == "__main__":
    main()
