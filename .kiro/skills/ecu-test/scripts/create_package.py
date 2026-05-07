#!/usr/bin/env python3
"""
create_package.py — Create an ecu.test package from precondition, action, and postcondition steps.

Usage:
    python create_package.py \
      --pre-step "Set vehicle state to 'D'." \
      --action-step "Press accelerator to 50%%." \
      --action-step "Verify velocity > 50 km/h within 9s." \
      --output "C:\\workspace\\Packages\\my_test.pkg"
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from api_client_setup import get_api_client


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SCRATCH_DIR = WORKSPACE_ROOT / ".scratch"


def normalize_block_names(block_names: list[str] | None) -> list[str]:
    if not block_names:
        return []
    return [name.strip() for name in block_names if name and name.strip()]


def create_named_block(api, block_name: str):
    test_step = api.PackageApi.TestStepApi.CreateTsBlock()
    test_step.SetActionColumnText(block_name)
    return test_step


def append_named_blocks(api, parent_block, block_names: list[str]) -> None:
    for name in block_names:
        if not name or not name.strip():
            continue
        parent_block.AppendTestStep(create_named_block(api, name.strip()))


def create_package_with_conditions(
    precondition_blocks: list[str] | None,
    action_blocks: list[str] | None,
    postcondition_blocks: list[str] | None,
) -> str:
    """Create a package in a temp file and return its path."""
    normalized_pre = normalize_block_names(precondition_blocks)
    normalized_actions = normalize_block_names(action_blocks)
    normalized_post = normalize_block_names(postcondition_blocks)

    if not normalized_actions:
        raise ValueError("At least one action step is required to create an ecu.test package.")

    api = get_api_client()
    package = api.PackageApi.CreatePackage()

    if normalized_pre:
        precondition = api.PackageApi.TestStepApi.CreateTsPreconditionBlock()
        append_named_blocks(api, precondition, normalized_pre)
        package.AppendTestStep(precondition)

    action = api.PackageApi.TestStepApi.CreateTsBlock()
    action.SetActionColumnText("Action")
    append_named_blocks(api, action, normalized_actions)
    package.AppendTestStep(action)

    if normalized_post:
        postcondition = api.PackageApi.TestStepApi.CreateTsPostconditionBlock()
        append_named_blocks(api, postcondition, normalized_post)
        package.AppendTestStep(postcondition)

    fd, output_path = tempfile.mkstemp(prefix="GeneratedPackage_", suffix=".pkg")
    os.close(fd)

    package.Save(output_path)
    package.Close()
    return output_path


def save_package_with_conditions(
    precondition_blocks: list[str] | None,
    action_blocks: list[str] | None,
    postcondition_blocks: list[str] | None,
    output_path: str | os.PathLike[str],
) -> str:
    """Create a package and move it to the desired output path."""
    package_path = create_package_with_conditions(precondition_blocks, action_blocks, postcondition_blocks)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(package_path, target)
    return str(target)


def resolve_output_path(output: str | None) -> Path:
    if not output:
        return SCRATCH_DIR / "generated_package.pkg"
    p = Path(output)
    if p.is_absolute():
        return p
    return SCRATCH_DIR / p


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an ecu.test package from explicit precondition, action, and postcondition steps.",
    )
    parser.add_argument(
        "--pre-step",
        action="append",
        default=[],
        help="Repeat for each required precondition step.",
    )
    parser.add_argument(
        "--action-step",
        action="append",
        default=[],
        help="Repeat for each required action or expected-result step.",
    )
    parser.add_argument(
        "--post-step",
        action="append",
        default=[],
        help="Repeat for each required postcondition or cleanup step.",
    )
    parser.add_argument(
        "--output",
        help="Target file name or path for the generated .pkg file. Relative paths go to .scratch/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = resolve_output_path(args.output)

    try:
        created_path = save_package_with_conditions(
            precondition_blocks=args.pre_step,
            action_blocks=args.action_step,
            postcondition_blocks=args.post_step,
            output_path=output_path,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(created_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
