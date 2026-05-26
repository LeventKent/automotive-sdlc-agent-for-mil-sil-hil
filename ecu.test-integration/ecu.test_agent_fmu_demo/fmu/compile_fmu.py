#!/usr/bin/env python3
"""
compile_fmu.py — Compile a source-only FMU for linux64.

This script takes a source-only .fmu (produced by MATLAB's exportToFMU with
BuildConfiguration='source-code') and compiles the C sources for linux64,
producing a ready-to-run FMU with a shared library.

Run on the remote EC2 instance after syncing the workspace:
    python3 compile_fmu.py TemperatureMonitoringSystem.fmu

The script:
  1. Extracts the .fmu (a zip archive)
  2. Finds C source files in sources/
  3. Compiles them into a shared library for linux64
  4. Repackages the .fmu with binaries/linux64/<modelIdentifier>.so
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

DEFAULT_FMU_DIR = Path("/opt/ecu-test-workspace/fmu")


def get_model_identifier(fmu_extract_dir: Path) -> str:
    """Parse modelDescription.xml to get the modelIdentifier."""
    md_path = fmu_extract_dir / "modelDescription.xml"
    if not md_path.exists():
        raise FileNotFoundError(f"modelDescription.xml not found in {fmu_extract_dir}")

    tree = ET.parse(md_path)
    root = tree.getroot()

    # Check CoSimulation element first, then ModelExchange
    for elem_name in ("CoSimulation", "ModelExchange"):
        elem = root.find(elem_name)
        if elem is not None:
            model_id = elem.get("modelIdentifier")
            if model_id:
                return model_id

    raise ValueError("Could not find modelIdentifier in modelDescription.xml")


def find_source_files(fmu_extract_dir: Path) -> list[Path]:
    """Find all C source files in the extracted FMU."""
    sources_dir = fmu_extract_dir / "sources"
    if not sources_dir.exists():
        raise FileNotFoundError(f"No sources/ directory found in FMU")

    c_files = list(sources_dir.rglob("*.c"))
    if not c_files:
        raise FileNotFoundError(f"No .c files found in {sources_dir}")

    return c_files


def find_include_dirs(fmu_extract_dir: Path) -> list[Path]:
    """Find include directories for compilation."""
    include_dirs = []

    sources_dir = fmu_extract_dir / "sources"
    if sources_dir.exists():
        include_dirs.append(sources_dir)
        # Add any subdirectories that contain .h files
        for h_file in sources_dir.rglob("*.h"):
            parent = h_file.parent
            if parent not in include_dirs:
                include_dirs.append(parent)

    return include_dirs


def compile_fmu(fmu_path: Path) -> Path:
    """Compile a source-only FMU for linux64. Returns path to the compiled FMU."""
    if not fmu_path.exists():
        print(f"ERROR: FMU file not found: {fmu_path}", file=sys.stderr)
        sys.exit(1)

    # Verify it's a valid zip/FMU
    if not zipfile.is_zipfile(fmu_path):
        print(f"ERROR: Not a valid FMU (zip) file: {fmu_path}", file=sys.stderr)
        sys.exit(1)

    # Extract to temp directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="fmu_compile_"))
    extract_dir = tmp_dir / "fmu_contents"

    try:
        with zipfile.ZipFile(fmu_path, "r") as z:
            z.extractall(extract_dir)

        # Get model identifier
        model_id = get_model_identifier(extract_dir)
        print(f"Model identifier: {model_id}")

        # Find source files
        c_files = find_source_files(extract_dir)
        print(f"Found {len(c_files)} source file(s)")

        # Find include directories
        include_dirs = find_include_dirs(extract_dir)

        # Create output directory for linux64 binary
        bin_dir = extract_dir / "binaries" / "linux64"
        bin_dir.mkdir(parents=True, exist_ok=True)

        so_path = bin_dir / f"{model_id}.so"

        # Build gcc command
        compile_cmd = ["gcc", "-shared", "-fPIC", "-O2"]

        # Add include paths
        for inc_dir in include_dirs:
            compile_cmd.extend(["-I", str(inc_dir)])

        # Add output
        compile_cmd.extend(["-o", str(so_path)])

        # Add source files
        compile_cmd.extend([str(f) for f in c_files])

        # Link math library
        compile_cmd.append("-lm")

        print(f"Compiling: {' '.join(compile_cmd)}")
        result = subprocess.run(compile_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"ERROR: Compilation failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

        print(f"Compiled: {so_path}")

        # Repackage the FMU with the compiled binary
        compiled_fmu_path = fmu_path  # Overwrite the source-only FMU
        with zipfile.ZipFile(compiled_fmu_path, "w", zipfile.ZIP_DEFLATED) as z:
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(extract_dir)
                    z.write(file_path, arcname)

        size_kb = compiled_fmu_path.stat().st_size / 1024
        print(f"FMU compiled and repackaged: {compiled_fmu_path} ({size_kb:.1f} KB)")
        return compiled_fmu_path

    finally:
        shutil.rmtree(tmp_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Compile a source-only FMU for linux64"
    )
    parser.add_argument(
        "fmu_file",
        nargs="?",
        help="Path to the source-only .fmu file. If just a filename, looks in the default FMU directory.",
    )
    parser.add_argument(
        "--fmu-dir",
        type=Path,
        default=DEFAULT_FMU_DIR,
        help=f"Directory containing FMU files (default: {DEFAULT_FMU_DIR})",
    )
    args = parser.parse_args()

    if args.fmu_file:
        fmu_path = Path(args.fmu_file)
        if not fmu_path.is_absolute():
            fmu_path = args.fmu_dir / fmu_path
    else:
        # Find the first .fmu file in the directory
        fmu_files = list(args.fmu_dir.glob("*.fmu"))
        if not fmu_files:
            print(f"ERROR: No .fmu files found in {args.fmu_dir}", file=sys.stderr)
            sys.exit(1)
        if len(fmu_files) > 1:
            print(f"Multiple .fmu files found. Specify which one:", file=sys.stderr)
            for f in fmu_files:
                print(f"  {f.name}", file=sys.stderr)
            sys.exit(1)
        fmu_path = fmu_files[0]

    compile_fmu(fmu_path)


if __name__ == "__main__":
    main()
