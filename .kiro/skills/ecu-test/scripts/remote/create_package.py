#!/usr/bin/env python3
"""
create_package.py — Create an ecu.test package from precondition, action, and postcondition steps.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.
Uses /opt/ecu-test-workspace as base directory.

Usage:
    python3 create_package.py \
      --pre-step "Set vehicle state to 'D'." \
      --action-step "Press accelerator to 50%." \
      --output "Packages/my_test.pkg"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

from api_client_setup import get_api_client

WORKSPACE = Path("/opt/ecu-test-workspace")


def _base_url(port: int = 5050) -> str:
    return f"http://127.0.0.1:{port}/api/v2"


def check_api_reachable(port: int = 5050) -> bool:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{_base_url(port)}/live", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def create_named_block(api, block_name: str):
    test_step = api.PackageApi.TestStepApi.CreateTsBlock()
    test_step.SetActionColumnText(block_name)
    return test_step


def append_named_blocks(api, parent_block, block_names: list[str]) -> None:
    for name in block_names:
        if name and name.strip():
            parent_block.AppendTestStep(create_named_block(api, name.strip()))


def resolve_output_path(output: str | None) -> Path:
    if not output:
        return WORKSPACE / "Packages" / "generated_package.pkg"
    p = Path(output)
    if p.is_absolute():
        return p
    return WORKSPACE / p


def main():
    parser = argparse.ArgumentParser(description="Create an ecu.test package.")
    parser.add_argument("--pre-step", action="append", default=[], help="Precondition step")
    parser.add_argument("--action-step", action="append", default=[], help="Action step (at least one required)")
    parser.add_argument("--post-step", action="append", default=[], help="Postcondition step")
    parser.add_argument("--output", help="Output path (relative to workspace or absolute)")
    args = parser.parse_args()

    actions = [s.strip() for s in args.action_step if s and s.strip()]
    if not actions:
        print("ERROR: At least one --action-step is required")
        sys.exit(1)

    if not check_api_reachable():
        print("ERROR: ECU-TEST REST API not reachable at port 5050")
        sys.exit(1)

    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        api = get_api_client()
        package = api.PackageApi.CreatePackage()

        pre_steps = [s.strip() for s in args.pre_step if s and s.strip()]
        post_steps = [s.strip() for s in args.post_step if s and s.strip()]

        if pre_steps:
            precondition = api.PackageApi.TestStepApi.CreateTsPreconditionBlock()
            append_named_blocks(api, precondition, pre_steps)
            package.AppendTestStep(precondition)

        action_block = api.PackageApi.TestStepApi.CreateTsBlock()
        action_block.SetActionColumnText("Action")
        append_named_blocks(api, action_block, actions)
        package.AppendTestStep(action_block)

        if post_steps:
            postcondition = api.PackageApi.TestStepApi.CreateTsPostconditionBlock()
            append_named_blocks(api, postcondition, post_steps)
            package.AppendTestStep(postcondition)

        package.Save(str(output_path))
        package.Close()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"SUCCESS: Package created at {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
