#!/usr/bin/env python3
"""
generate_xam.py — Generate an ecu.test XAM (Master Mapping) file from an FMU.

Reads the TCF to find the referenced XAM file and FMU, extracts the FMU's
modelDescription.xml, and generates MAPPING-ITEM entries for each ScalarVariable.

The script checks whether the XAM file needs updating by comparing the existing
content with what would be generated from the FMU. If the TCF does not reference
an XAM or FMU, the script exits cleanly (no update needed).

Usage:
    python generate_xam.py --tcf "C:\\path\\to\\config.tcf"
    python generate_xam.py --fmu "C:\\path\\to\\model.fmu" --output "C:\\path\\to\\mapping.xam"
    python generate_xam.py --tcf "C:\\path\\to\\config.tcf" --model-key "Plant model"

When --tcf is provided, the script:
  1. Parses the TCF to check if an XAM file and FMU are referenced
  2. If not referenced, exits with success (no XAM needed for this config)
  3. Compares the existing XAM content with what the FMU would produce
  4. Only writes the XAM if it differs or does not exist

When --fmu and --output are provided directly, those are used instead.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom


def extract_model_description(fmu_path: str) -> ET.Element:
    """Extract and parse modelDescription.xml from an FMU file."""
    if not os.path.isfile(fmu_path):
        raise FileNotFoundError(f"FMU file not found: {fmu_path}")

    with zipfile.ZipFile(fmu_path, "r") as z:
        if "modelDescription.xml" not in z.namelist():
            raise ValueError(f"No modelDescription.xml found in {fmu_path}")
        with z.open("modelDescription.xml") as f:
            tree = ET.parse(f)
            return tree.getroot()


def get_variables(model_desc: ET.Element) -> list:
    """
    Extract ScalarVariable entries from modelDescription.xml.

    Returns a list of dicts with keys: name, description, causality, variability.
    """
    variables = []
    model_variables = model_desc.find("ModelVariables")
    if model_variables is None:
        return variables

    for sv in model_variables.findall("ScalarVariable"):
        var = {
            "name": sv.get("name", ""),
            "description": sv.get("description", sv.get("name", "")),
            "causality": sv.get("causality", ""),
            "variability": sv.get("variability", ""),
        }
        variables.append(var)

    return variables


def extract_non_signal_items(xam_path: str) -> list[str]:
    """
    Read an existing XAM file and extract MAPPING-ITEM elements that do NOT
    contain an xaModelSignal XACCESS (e.g. xaJob items for StartSimulation,
    StopSimulation, etc.).

    Returns a list of XML strings (one per preserved item) that can be
    inserted verbatim into the generated XAM.
    """
    if not os.path.isfile(xam_path):
        return []

    try:
        tree = ET.parse(xam_path)
    except ET.ParseError:
        return []

    root = tree.getroot()
    preserved = []

    for item in root.findall("MAPPING-ITEM"):
        # Check if this item has an xaModelSignal XACCESS
        xaccess = item.find("XACCESS")
        if xaccess is not None:
            xsi_type = xaccess.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            if xsi_type == "xaModelSignal":
                continue  # Skip signal items — they will be regenerated

        # Preserve this item (non-signal mapping like xaJob)
        preserved.append(ET.tostring(item, encoding="unicode"))

    return preserved


def generate_xam_xml(variables: list, model_key: str, preserved_items: list[str] | None = None) -> str:
    """
    Generate the XAM XML content from the list of FMU variables.

    Each variable becomes a MAPPING-ITEM with an xaModelSignal XACCESS element.
    Non-signal mapping items (e.g. xaJob for StartSimulation/StopSimulation)
    from the existing XAM are preserved and placed before the signal items.
    """
    doc = minidom.getDOMImplementation().createDocument(None, "MASTER-MAPPING", None)
    root = doc.documentElement
    root.setAttribute("format-rev", "1")
    root.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Insert preserved non-signal items first (e.g. xaJob mappings)
    if preserved_items:
        for item_xml in preserved_items:
            try:
                item_elem = minidom.parseString(item_xml).documentElement
                imported = doc.importNode(item_elem, deep=True)
                root.appendChild(imported)
            except Exception:
                pass  # Skip malformed preserved items

    for var in variables:
        # Create MAPPING-ITEM
        mapping_item = doc.createElement("MAPPING-ITEM")
        mapping_item.setAttribute("format-rev", "2")
        mapping_item.setAttribute("xsi:type", "mappingItem")

        # ID element: "<model_key>.<variable_name>"
        id_elem = doc.createElement("ID")
        id_elem.setAttribute("xsi:type", "string")
        id_text = doc.createTextNode(f"{model_key}.{var['name']}")
        id_elem.appendChild(id_text)
        mapping_item.appendChild(id_elem)

        # DESCRIPTION element
        desc_elem = doc.createElement("DESCRIPTION")
        desc_elem.setAttribute("xsi:type", "string")
        desc_text = doc.createTextNode(var["description"])
        desc_elem.appendChild(desc_text)
        mapping_item.appendChild(desc_elem)

        # XACCESS element (xaModelSignal)
        xaccess = doc.createElement("XACCESS")
        xaccess.setAttribute("format-rev", "2")
        xaccess.setAttribute("xsi:type", "xaModelSignal")

        # MAPPING-ENUM (empty vtab)
        mapping_enum = doc.createElement("MAPPING-ENUM")
        mapping_enum.setAttribute("xsi:type", "vtabInfoEmpty")
        xaccess.appendChild(mapping_enum)

        # MODEL-KEY
        model_key_elem = doc.createElement("MODEL-KEY")
        model_key_elem.setAttribute("xsi:type", "string")
        model_key_text = doc.createTextNode(model_key)
        model_key_elem.appendChild(model_key_text)
        xaccess.appendChild(model_key_elem)

        # VARIABLE-PATH
        var_path_elem = doc.createElement("VARIABLE-PATH")
        var_path_elem.setAttribute("xsi:type", "string")
        var_path_text = doc.createTextNode(var["name"])
        var_path_elem.appendChild(var_path_text)
        xaccess.appendChild(var_path_elem)

        mapping_item.appendChild(xaccess)
        root.appendChild(mapping_item)

    # Pretty print
    xml_str = doc.toprettyxml(indent="        ", encoding="utf-8").decode("utf-8")

    # Clean up the declaration and empty lines
    lines = xml_str.split("\n")
    lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
    cleaned = "\n".join(line for line in lines if line.strip() != "")
    return cleaned


# ---------------------------------------------------------------------------
# TCF parsing helpers
# ---------------------------------------------------------------------------

_TCF_NS = {"et": "http://www.tracetronic.de/xml/ecu-test"}


def parse_tcf(tcf_path: str) -> dict:
    """
    Parse a TCF file and extract the XAM mapping file path, FMU file path,
    and model key.

    Returns a dict with keys:
        xam_relative_path: str or None
        fmu_filename: str or None
        model_key: str or None
        workspace_dir: str  (parent of the TCF file, used as base for relative paths)
    """
    tcf = Path(tcf_path)
    if not tcf.exists():
        raise FileNotFoundError(f"TCF file not found: {tcf_path}")

    tree = ET.parse(tcf)
    root = tree.getroot()

    # The workspace root is typically the parent of the "Configurations" folder
    # i.e., the grandparent of the TCF file
    workspace_dir = tcf.parent.parent

    result = {
        "xam_relative_path": None,
        "fmu_filename": None,
        "model_key": None,
        "workspace_dir": str(workspace_dir),
    }

    # Find MAPPING-FILES -> ELEMENT -> EXPRESSION -> PATH-EXPRESSION -> VALUE
    common = root.find("et:COMMON", _TCF_NS)
    if common is not None:
        mapping_files = common.find("et:MAPPING-FILES", _TCF_NS)
        if mapping_files is not None:
            for element in mapping_files.findall("et:ELEMENT", _TCF_NS):
                expression = element.find("et:EXPRESSION", _TCF_NS)
                if expression is not None:
                    path_expr = expression.find("et:PATH-EXPRESSION", _TCF_NS)
                    if path_expr is not None:
                        value = path_expr.find("et:VALUE", _TCF_NS)
                        if value is not None and value.text:
                            result["xam_relative_path"] = value.text
                            break

    # Find MODEL-ACCESS -> DATA -> DVALUE -> MODEL-FILE and the dkey attribute
    model_access = root.find("et:MODEL-ACCESS", _TCF_NS)
    if model_access is not None:
        for data in model_access.findall("et:DATA", _TCF_NS):
            model_key = data.get("dkey")
            if model_key:
                result["model_key"] = model_key
            dvalue = data.find("et:DVALUE", _TCF_NS)
            if dvalue is not None:
                model_file = dvalue.find("et:MODEL-FILE", _TCF_NS)
                if model_file is not None and model_file.text:
                    result["fmu_filename"] = model_file.text
                    break

    return result


def resolve_fmu_path(workspace_dir: str, fmu_filename: str) -> str:
    """
    Resolve the FMU file path. Searches common locations relative to workspace:
      - workspace/fmu/<filename>
      - workspace/<filename>
      - workspace/Models/<filename>

    Returns the absolute path if found, raises FileNotFoundError otherwise.
    """
    workspace = Path(workspace_dir)
    candidates = [
        workspace / "fmu" / fmu_filename,
        workspace / fmu_filename,
        workspace / "Models" / fmu_filename,
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"FMU file '{fmu_filename}' not found in workspace '{workspace_dir}'. "
        f"Searched: {[str(c) for c in candidates]}"
    )


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def is_xam_up_to_date(xam_path: str, xam_content: str) -> bool:
    """
    Check if the existing XAM file matches the content that would be generated.

    Returns True if the file exists and its content is identical (no update needed).
    """
    if not os.path.isfile(xam_path):
        return False
    try:
        with open(xam_path, "r", encoding="utf-8") as f:
            existing = f.read()
        return existing == xam_content
    except (OSError, UnicodeDecodeError):
        return False


def generate_xam_from_tcf(
    tcf_path: str,
    model_key_override: str | None = None,
    verbose: bool = False,
) -> tuple[bool, str]:
    """
    Parse the TCF, find the FMU and XAM paths, check if update is needed,
    and generate the XAM file only if necessary.

    Args:
        tcf_path: Absolute path to the TCF file.
        model_key_override: Override the model key (default: read from TCF).
        verbose: Print progress.

    Returns:
        (success, message) tuple.
    """
    if verbose:
        print(f"Parsing TCF: {tcf_path}")

    tcf_info = parse_tcf(tcf_path)

    if not tcf_info["xam_relative_path"]:
        msg = "No XAM mapping file referenced in the TCF. No update needed."
        if verbose:
            print(f"  {msg}")
        return True, msg

    if not tcf_info["fmu_filename"]:
        msg = "No FMU model file referenced in the TCF. No update needed."
        if verbose:
            print(f"  {msg}")
        return True, msg

    model_key = model_key_override or tcf_info["model_key"] or "Plant model"
    workspace_dir = tcf_info["workspace_dir"]
    xam_path = str(Path(workspace_dir) / tcf_info["xam_relative_path"])

    try:
        fmu_path = resolve_fmu_path(workspace_dir, tcf_info["fmu_filename"])
    except FileNotFoundError as e:
        return False, str(e)

    if verbose:
        print(f"  Workspace : {workspace_dir}")
        print(f"  FMU       : {fmu_path}")
        print(f"  XAM output: {xam_path}")
        print(f"  Model key : {model_key}")
        print()

    return generate_xam(fmu_path=fmu_path, output_path=xam_path, model_key=model_key, verbose=verbose)


def generate_xam(
    fmu_path: str,
    output_path: str,
    model_key: str = "Plant model",
    verbose: bool = False,
) -> tuple[bool, str]:
    """
    Generate an XAM file from an FMU. Only writes if the content has changed.

    Args:
        fmu_path: Absolute path to the FMU file.
        output_path: Absolute path for the output XAM file.
        model_key: Model key for the mapping items.
        verbose: Print progress.

    Returns:
        (success, message) tuple.
    """
    try:
        model_desc = extract_model_description(fmu_path)
    except (FileNotFoundError, ValueError) as e:
        return False, str(e)

    model_name = model_desc.get("modelName", "Unknown")
    fmi_version = model_desc.get("fmiVersion", "Unknown")

    if verbose:
        print(f"  FMU model : {model_name} (FMI {fmi_version})")

    variables = get_variables(model_desc)
    if not variables:
        return False, f"No ScalarVariables found in {fmu_path}"

    if verbose:
        print(f"  Variables : {len(variables)}")
        for var in variables:
            print(f"    - {var['name']} ({var['causality']}, {var['variability']})")
        print()

    # Preserve existing non-signal mapping items (e.g. xaJob for Start/StopSimulation)
    preserved_items = extract_non_signal_items(output_path)
    if verbose and preserved_items:
        print(f"  Preserving {len(preserved_items)} non-signal mapping item(s)")

    xam_content = generate_xam_xml(variables, model_key, preserved_items=preserved_items)

    # Check if the XAM is already up-to-date
    if is_xam_up_to_date(output_path, xam_content):
        msg = f"XAM is already up-to-date: {output_path}"
        if verbose:
            print(f"  {msg}")
        return True, msg

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xam_content)

    msg = f"Generated XAM with {len(variables)} mapping items: {output_path}"
    if verbose:
        print(f"  {msg}")

    return True, msg


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an ecu.test XAM mapping file from an FMU.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tcf",
        help="Path to the TCF file. XAM path and FMU are read from the TCF.",
    )
    group.add_argument(
        "--fmu",
        help="Direct path to the FMU file (use with --output).",
    )
    parser.add_argument(
        "--output",
        help="Output path for the XAM file (required when using --fmu).",
    )
    parser.add_argument(
        "--model-key",
        default=None,
        help='Model key for the mapping (default: read from TCF; falls back to "Plant model" if not found).',
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.fmu:
        if not args.output:
            print("ERROR: --output is required when using --fmu directly.")
            sys.exit(1)
        model_key = args.model_key or "Plant model"
        success, msg = generate_xam(
            fmu_path=args.fmu,
            output_path=args.output,
            model_key=model_key,
            verbose=True,
        )
    else:
        success, msg = generate_xam_from_tcf(
            tcf_path=args.tcf,
            model_key_override=args.model_key,
            verbose=True,
        )

    if success:
        print(f"\nSUCCESS: {msg}")
        sys.exit(0)
    else:
        print(f"\nERROR: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
