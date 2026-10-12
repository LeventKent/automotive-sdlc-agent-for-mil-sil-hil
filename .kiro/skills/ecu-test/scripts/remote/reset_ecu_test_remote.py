#!/usr/bin/env python3
"""Clear reports, remove deployed remote scripts, and stop ECU-TEST on the remote host.

The ECU-TEST Linux runner process is named ``ecu.test_runner``. This script is
intended to be called through ``ecu-test-adapter.sh`` after remote scripts have
been provisioned:

    ./ecu-test-adapter.sh reset_ecu_test_remote.py

It preserves an optional ``.keep`` placeholder in the report directory. It
removes every deployed Python script from the remote scripts directory; the
adapter provisions fresh copies on the next remote invocation.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def stop_configuration(port: int) -> None:
    """Request that ECU-TEST stop its active configuration when reachable."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/v2/configuration",
        data=json.dumps({"action": "Stop"}).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            print("Requested ECU-TEST configuration stop.")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        print("ECU-TEST configuration API is unavailable; continuing with process cleanup.")


def clear_reports(reports_dir: Path) -> int:
    """Remove generated reports while preserving an optional repository placeholder."""
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


def clear_remote_scripts(remote_scripts_dir: Path) -> int:
    """Remove deployed remote scripts so the adapter provisions fresh copies next time."""
    if not remote_scripts_dir.exists():
        return 0

    removed = 0
    for entry in remote_scripts_dir.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
        removed += 1

    return removed


def ecu_test_running(port: int) -> bool:
    """Return whether ECU-TEST's runner process or REST API is reachable."""
    process_result = subprocess.run(
        ["pgrep", "-x", "ecu.test_runner"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if process_result.returncode == 0:
        return True

    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/v2/live", timeout=2
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def stop_ecu_test(port: int, timeout_seconds: int) -> None:
    """Terminate ECU-TEST's runner and verify that its REST API closes."""
    if not ecu_test_running(port):
        print("ECU-TEST is already stopped.")
        return

    subprocess.run(["pkill", "-TERM", "-x", "ecu.test_runner"], check=False)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not ecu_test_running(port):
            print("ECU-TEST stopped successfully.")
            return
        time.sleep(1)

    raise RuntimeError("ECU-TEST did not stop within the configured timeout.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset remote ECU-TEST reports and service.")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("/opt/ecu-test-workspace/TestReports"),
    )
    parser.add_argument(
        "--remote-scripts-dir",
        type=Path,
        default=Path("/opt/ecu-test-scripts"),
        help="Remote adapter-script directory to clear after the service stops.",
    )
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--stop-timeout", type=int, default=30)
    args = parser.parse_args()

    stop_configuration(args.port)
    removed = clear_reports(args.reports_dir)
    print(f"Removed {removed} report artifact(s) from {args.reports_dir}.")
    stop_ecu_test(args.port, args.stop_timeout)
    scripts_removed = clear_remote_scripts(args.remote_scripts_dir)
    print(
        f"Removed {scripts_removed} deployed remote script artifact(s) from "
        f"{args.remote_scripts_dir}."
    )
    print("Remote ECU-TEST reset completed.")


if __name__ == "__main__":
    main()
