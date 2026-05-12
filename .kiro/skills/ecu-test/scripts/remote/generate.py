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


def add_undefined_variables_for_assignments(package_file_path: str | Path) -> bool:
    """
    Walk all test steps in the package and add an <Undefined> variable for every
    variable name a step assigns to. Existing variables are left untouched.

    Sources of assigned names:
      - GetSaveInVariableName()           (most TsRead/TsCalculation/dialogs/...)
      - GetSaveInVariableNames()          (TsBusMonitoring* multi-slot steps)
      - GetReturns()[i].GetSaveInVariableName()   (TsKeyword, TsAXSCall)
    """
    if isinstance(package_file_path, str):
        package_file_path = Path(package_file_path)

    if not package_file_path.exists():
        print(f"ERROR: PackagePath {package_file_path!r} does not exist!")
        return False

    api = get_api_client()
    package = api.PackageApi.OpenPackage(filename=str(package_file_path))
    if package is None:
        return False

    assigned: set[str] = set()

    def collect_from_step(ts) -> None:
        getter = getattr(ts, 'GetSaveInVariableName', None)
        if callable(getter):
            try:
                name = getter()
                if name:
                    assigned.add(name)
            except TypeError:
                pass

        multi = getattr(ts, 'GetSaveInVariableNames', None)
        if callable(multi):
            try:
                for n in multi() or []:
                    if n:
                        assigned.add(n)
            except Exception:
                pass

        returns_getter = getattr(ts, 'GetReturns', None)
        if callable(returns_getter):
            try:
                for ret in returns_getter() or []:
                    ret_getter = getattr(ret, 'GetSaveInVariableName', None)
                    if callable(ret_getter):
                        n = ret_getter()
                        if n:
                            assigned.add(n)
            except Exception:
                pass

        children_getter = getattr(ts, 'GetTestSteps', None)
        if callable(children_getter):
            try:
                for child in children_getter() or []:
                    collect_from_step(child)
            except Exception:
                pass

    print(f"Scanning {package_file_path} for variable assignments...", flush=True)
    for ts in package.GetTestSteps():
        collect_from_step(ts)

    added = 0
    for name in sorted(assigned):
        if package.GetVariable(name) is not None:
            continue
        try:
            var = api.PackageApi.VariableApi.CreateVariable(name)
            package.AddVariable(var)
            added += 1
            print(f"  + variable {name!r}", flush=True)
        except Exception as e:
            print(f"ERROR adding variable {name!r}: {type(e).__name__}: {e}", flush=True)

    package.Save()
    print(f"Added {added} variable(s) to {package_file_path}", flush=True)
    return True


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
    if not generate_package(args.package):
        print(f"ERROR: Package generation failed for '{args.package}'")
        sys.exit(1)

    # Step 3: Add undefined variables for assignments
    if not add_undefined_variables_for_assignments(args.package):
        print(f"ERROR: Adding assigned variables failed for '{args.package}'")
        sys.exit(1)

    print(f"SUCCESS: TCF loaded and package '{args.package}' generated")
    sys.exit(0)


if __name__ == "__main__":
    main()
