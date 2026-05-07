"""
api_client_setup.py — Centralized ecu.test ApiClient path resolution and import.

All scripts that need the ecu.test ApiClient should import from here:

    from api_client_setup import get_api_client

    api = get_api_client()
    package = api.PackageApi.OpenPackage(filename="...")
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


_API_CLIENT_CONFIGURED = False


def _configure_api_client_path() -> None:
    """
    Resolve the ecu.test ApiClient path and add it to sys.path.

    Resolution order:
    1. ECU_TEST_API_CLIENT_PATH environment variable
    2. Program Files ecu.test installations (newest first)
    3. LocalAppData ecu.test installations (newest first)
    4. Linux fallback: /opt/ecu.test/Templates/ApiClient
    """
    global _API_CLIENT_CONFIGURED
    if _API_CLIENT_CONFIGURED:
        return

    candidate_paths: list[Path] = []

    # 1. Environment variable override
    configured_path = os.environ.get("ECU_TEST_API_CLIENT_PATH")
    if configured_path:
        candidate_paths.append(Path(configured_path))

    # 2. Program Files installations
    for program_files_env in ("ProgramFiles", "ProgramFiles(x86)"):
        program_files = os.environ.get(program_files_env)
        if program_files:
            candidate_paths.extend(
                sorted(Path(program_files).glob("ecu.test*/Templates/ApiClient"), reverse=True)
            )

    # 3. LocalAppData installations
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate_paths.extend(
            sorted(Path(local_app_data).glob("ecu.test*/Templates/ApiClient"), reverse=True)
        )

    # 4. Linux fallback
    candidate_paths.append(Path("/opt/ecu.test/Templates/ApiClient"))

    for candidate in candidate_paths:
        resolved = candidate.resolve()
        if not resolved.exists():
            continue
        resolved_str = str(resolved)
        if resolved_str not in sys.path:
            sys.path.insert(0, resolved_str)
        _API_CLIENT_CONFIGURED = True
        return

    # If nothing found, mark as configured anyway to avoid repeated attempts
    _API_CLIENT_CONFIGURED = True


def get_api_client():
    """
    Import and instantiate the ecu.test ApiClient.

    Raises:
        RuntimeError: If the ApiClient module cannot be found or instantiated.
    """
    _configure_api_client_path()

    try:
        api_client_module = importlib.import_module("ApiClient")
    except ImportError as exc:
        raise RuntimeError(
            "Could not import ApiClient. Make sure the ecu.test Python API client is available.\n"
            "Set ECU_TEST_API_CLIENT_PATH to the Templates/ApiClient directory, or ensure ecu.test "
            "is installed in Program Files or LocalAppData."
        ) from exc

    try:
        api_client_class = getattr(api_client_module, "ApiClient")
    except AttributeError as exc:
        raise RuntimeError(
            "Module ApiClient was found, but does not provide class ApiClient."
        ) from exc

    return api_client_class()
