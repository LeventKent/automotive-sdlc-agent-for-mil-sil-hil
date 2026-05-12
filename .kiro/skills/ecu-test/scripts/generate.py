#!/usr/bin/env python3
"""
generate.py — Configure a TCF in ECU-TEST, then generate a test package via AI.

Usage:
    python generate.py --tcf "Configurations/ElectricVehicle.tcf" --package "Packages/MyTest.pkg"

Or imported as a module:
    from generate import run_workflow, WorkflowResult

    result = run_workflow(tcf="...", package="...")
    if result.success:
        print("Done:", result.message)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from api_client_setup import get_api_client
from configure_tcf import configure_tcf


@dataclass
class WorkflowResult:
    success: bool
    message: str


def _open_package(package_file_path: str | Path):
    """Open an ecu.test package via the ApiClient."""
    path = Path(package_file_path)
    if not path.exists():
        print(f"ERROR: Package path {path!r} does not exist!")
        return None

    api = get_api_client()
    return api.PackageApi.OpenPackage(filename=str(path))


def generate_package(package_file_path: str | Path) -> bool:
    """Open a package and call GenerateViaAi() on all empty TsBlock steps."""
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
                print(f"ERROR: {type(e).__name__}: {e}", flush=True)
                result = False
        return result

    print(f"Generating package {package_file_path}...", flush=True)
    package = _open_package(package_file_path)

    if package is None:
        return False

    for block in package.GetTestSteps():
        match block.GetType():
            case "TsPreconditionBlock":
                overall_result &= process_test_steps(block.GetTestSteps())
            case "TsPostconditionBlock":
                overall_result &= process_test_steps(block.GetTestSteps())
            case "TsBlock":
                if block.GetActionColumnText() == "Action":
                    overall_result &= process_test_steps(block.GetTestSteps())
            case _:
                pass

    package.Save()
    return overall_result


def add_undefined_variables_for_assignments(package_file_path: str|Path) -> bool:
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

    def collect_from_step(ts: TestStep) -> None:
        getter = getattr(ts, 'GetSaveInVariableName', None)
        if callable(getter):
            try:
                name = getter()
                if name:
                    assigned.add(name)
            except TypeError:
                # signature requires an index (e.g. TsBusMonitoring) — handled below
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

def run_workflow(
    tcf: str,
    package: str,
    port: int = 5050,
    timeout: int = 120,
    verbose: bool = False,
) -> WorkflowResult:
    """
    End-to-end workflow: load TCF configuration, then generate the test package.

    Args:
        tcf: Path to the test configuration file (.tcf).
        package: Path to the ECU-TEST package file (.pkg).
        port: REST API port (default: 5050).
        timeout: Seconds to wait for TCF to become ready (default: 120).
        verbose: Print progress to stdout (default: False).

    Returns:
        WorkflowResult with success flag and a message.
    """
    if verbose:
        print("=" * 60)
        print("Step 1/2: Configure TCF")
        print("=" * 60)

    tcf_result = configure_tcf(tcf=tcf, port=port, timeout=timeout, verbose=verbose)
    if not tcf_result.success:
        return WorkflowResult(success=False, message=f"TCF configuration failed: {tcf_result.message}")

    if verbose:
        print(f"  {tcf_result.message}")
        print()
        print("=" * 60)
        print("Step 2/2: Generate test package")
        print("=" * 60)
        print(f"  Package: {package}")

    ok = generate_package(package)
    if not ok:
        return WorkflowResult(success=False, message=f"Package generation failed for '{package}'.")

    if not add_undefined_variables_for_assignments(package):
        return WorkflowResult(success=False, message=f"Adding assigned variables failed for '{package}'.")


    return WorkflowResult(success=True, message=f"TCF loaded and package '{package}' generated successfully.")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Configure TCF in ECU-TEST and generate a test package via AI.",
    )
    parser.add_argument("--tcf", required=True, help="Path to the test configuration file (.tcf)")
    parser.add_argument("--package", required=True, help="Path to the ECU-TEST package file (.pkg)")
    parser.add_argument("--port", type=int, default=5050, help="REST API port (default: 5050)")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait for TCF (default: 120)")
    return parser.parse_args()


def main():
    args = _parse_args()
    result = run_workflow(
        tcf=args.tcf,
        package=args.package,
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
