#!/usr/bin/env python3
"""
configure_tcf.py — Ensure a TCF (and optionally TBC) is loaded in ECU-TEST.

Can be used as a CLI tool:
    python configure_tcf.py --tcf "MyTestConfiguration.tcf"
    python configure_tcf.py --tcf "MyTestConfiguration.tcf" --tbc "MyTestbench.tbc"

Or imported as a module:
    from configure_tcf import configure_tcf

    result = configure_tcf("MyTestConfiguration.tcf", tbc="MyTestbench.tbc")
    if result.success:
        print("Configuration is running")
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass


@dataclass
class ConfigureResult:
    success: bool
    message: str


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/v2"


def _get_json(url: str, timeout: int = 5) -> tuple[int, dict | None]:
    """GET a URL and return (status_code, parsed_json). Returns (0, None) on connection error."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return 0, None


def get_configuration(port: int) -> dict | None:
    """GET the current configuration status. Returns the JSON body or None on error."""
    status, data = _get_json(f"{_base_url(port)}/configuration")
    if status == 200:
        return data
    return None


def is_tcf_already_running(port: int, tcf_path: str) -> bool:
    """Check if the desired TCF is already loaded and active (RUNNING or FINISHED)."""
    config = get_configuration(port)
    if config is None:
        return False
    status_key = config.get("status", {}).get("key", "")
    # The TCF path can be at top-level or nested under "order"
    current_tcf = config.get("tcf", {}).get("tcfPath", "")
    if not current_tcf:
        current_tcf = config.get("order", {}).get("tcf", {}).get("tcfPath", "")
    return status_key in ("RUNNING", "FINISHED") and current_tcf == tcf_path


def start_configuration(port: int, tcf_path: str, tbc_path: str = "") -> tuple[bool, str]:
    """PUT a Start action to load the TBC/TCF. Returns (success, message)."""
    body: dict = {
        "action": "Start",
        "tcf": {"tcfPath": tcf_path},
    }
    if tbc_path:
        body["tbc"] = {"tbcPath": tbc_path}

    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{_base_url(port)}/configuration",
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                return True, "Configuration request accepted."
            return False, f"PUT /configuration returned {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"PUT /configuration returned {e.code}: {e.read().decode('utf-8', errors='replace')}"
    except (urllib.error.URLError, OSError):
        return False, "Could not connect to ECU-TEST REST API."


_CONFIG_OK_STATES = frozenset({"RUNNING", "FINISHED"})
_CONFIG_FAILED_STATES = frozenset({"FAILED", "ERROR", "ABORTED"})
_CONFIG_IN_PROGRESS_STATES = frozenset({"WAITING", ""})


def wait_for_running(port: int, timeout: int, verbose: bool = False) -> tuple[bool, str]:
    """Poll /configuration until a terminal state is reached or timeout expires."""
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        config = get_configuration(port)
        status_key = ""
        if config is not None:
            status_key = config.get("status", {}).get("key", "")
            status_msg = config.get("status", {}).get("message", "")

            if status_key in _CONFIG_OK_STATES:
                return True, f"Configuration is {status_key} (after ~{attempt}s)."

            if status_key in _CONFIG_FAILED_STATES:
                msg = f"Configuration {status_key} (after ~{attempt}s)."
                if status_msg:
                    msg += f" {status_msg}"
                return False, msg

            if status_key not in _CONFIG_IN_PROGRESS_STATES:
                msg = f"Configuration entered unexpected state: {status_key}"
                if status_msg:
                    msg += f" — {status_msg}"
                return False, msg

        if verbose:
            print(
                f"  Waiting for configuration... status={status_key or 'N/A'} ({attempt}s / {timeout}s)",
                end="\r",
            )
        time.sleep(1)

    if verbose:
        print()
    return False, f"Configuration did not reach RUNNING state within {timeout}s."


def check_ecu_test_reachable(port: int) -> tuple[bool, str]:
    """Check if ECU-TEST is reachable at the given port."""
    status, _ = _get_json(f"{_base_url(port)}/live", timeout=3)
    if status == 200:
        return True, "ECU-TEST is reachable."
    if status == 0:
        return False, f"Cannot reach ECU-TEST at port {port}. Is it running?"
    return False, f"ECU-TEST /live returned {status}. Is it running?"


def configure_tcf(
    tcf: str,
    tbc: str = "",
    port: int = 5050,
    timeout: int = 120,
    verbose: bool = False,
) -> ConfigureResult:
    """
    Ensure the given TCF (and optionally TBC) is loaded in ECU-TEST.

    Args:
        tcf: Path to the test configuration file (.tcf).
        tbc: Path to the test bench configuration file (.tbc). Optional.
        port: REST API port (default: 5050).
        timeout: Seconds to wait for configuration to become ready (default: 120).
        verbose: Print progress to stdout (default: False).

    Returns:
        ConfigureResult with success flag and a message.
    """
    if verbose:
        print(f"TCF  : {tcf}")
        print(f"TBC  : {tbc or '(not specified)'}")
        print(f"Port : {port}")
        print()

    reachable, msg = check_ecu_test_reachable(port)
    if not reachable:
        return ConfigureResult(success=False, message=msg)

    if verbose:
        print("ECU-TEST is reachable.")

    if is_tcf_already_running(port, tcf):
        return ConfigureResult(success=True, message=f"TCF '{tcf}' is already running. Nothing to do.")

    if verbose:
        print(f"Starting configuration with TCF '{tcf}'...")

    ok, msg = start_configuration(port, tcf, tbc)
    if not ok:
        return ConfigureResult(success=False, message=msg)

    if verbose:
        print(f"Configuration request accepted. Waiting up to {timeout}s for RUNNING state...")

    ok, msg = wait_for_running(port, timeout, verbose=verbose)
    if ok:
        return ConfigureResult(success=True, message=f"Configuration is active at {_base_url(port)}")
    return ConfigureResult(success=False, message=msg)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Ensure a TCF configuration is loaded in ECU-TEST via REST API.",
    )
    parser.add_argument("--tcf", required=True, help="Path to the test configuration file (.tcf)")
    parser.add_argument("--tbc", default="", help="Path to the test bench configuration file (.tbc). Optional.")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait (default: 120)")
    return parser.parse_args()


def main():
    args = _parse_args()
    result = configure_tcf(
        tcf=args.tcf,
        tbc=args.tbc,
        port=args.port,
        timeout=args.timeout,
        verbose=True,
    )
    if result.success:
        print(f"\nSUCCESS: {result.message}")
        sys.exit(0)
    else:
        print(f"\nERROR: {result.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
