#!/usr/bin/env python3
"""
generate.py — Configure TCF in ECU-TEST, then generate a test package via AI.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.

Usage:
    python3 generate.py --tcf "Configurations/ElectricVehicle.tcf" --package "Packages/MyTest.pkg"
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
from configure_tcf import check_api_reachable, start_configuration, wait_for_running, is_tcf_already_running


def generate_package(package_file_path: str) -> bool:
    """Open a package and call GenerateViaAi() on all empty TsBlock steps."""
    path = Path(package_file_path)
    if not path.exists():
        print(f"Package path does not exist: {path}")
        return False

    api = get_api_client()
    package = api.PackageApi.OpenPackage(filename=str(path))
    if package is None:
        return False

    overall_result = True

    def process_test_steps(test_steps) -> bool:
        result = True
        for ts_step in test_steps:
            if ts_step.GetType() != "TsBlock":
                continue
            if len(ts_step.GetTestSteps()):
                continue
            try:
                ts_step.GenerateViaAi()
            except Exception as e:
                print(f"GenerateViaAi failed: {e}")
                result = False
        return result

    for block in package.GetTestSteps():
        match block.GetType():
            case "TsPreconditionBlock" | "TsPostconditionBlock":
                overall_result &= process_test_steps(block.GetTestSteps())
            case "TsBlock":
                if block.GetActionColumnText() == "Action":
                    overall_result &= process_test_steps(block.GetTestSteps())

    package.Save()
    return overall_result


def main():
    parser = argparse.ArgumentParser(description="Configure TCF and generate test package via AI.")
    parser.add_argument("--tcf", required=True, help="Path to the test configuration file (.tcf)")
    parser.add_argument("--package", required=True, help="Path to the ECU-TEST package file (.pkg)")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait for TCF (default: 120)")
    args = parser.parse_args()

    if not check_api_reachable(args.port):
        print(f"ERROR: ECU-TEST REST API not reachable at port {args.port}")
        sys.exit(1)

    # Step 1: Configure TCF
    if not is_tcf_already_running(args.port, args.tcf):
        ok, msg = start_configuration(args.port, args.tcf)
        if not ok:
            print(f"ERROR: TCF configuration failed: {msg}")
            sys.exit(1)
        ok, msg = wait_for_running(args.port, args.timeout)
        if not ok:
            print(f"ERROR: {msg}")
            sys.exit(1)

    # Step 2: Generate package
    if generate_package(args.package):
        print(f"SUCCESS: TCF loaded and package '{args.package}' generated")
        sys.exit(0)
    else:
        print(f"ERROR: Package generation failed for '{args.package}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
