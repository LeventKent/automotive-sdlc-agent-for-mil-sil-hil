"""
api_client_setup.py — Linux-only ecu.test ApiClient path resolution.

Deployed to /opt/ecu-test-scripts/ on the remote EC2 instance.
Resolves ApiClient from /opt/ecu.test/Templates/ApiClient or ECU_TEST_API_CLIENT_PATH env var.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

_API_CLIENT_CONFIGURED = False


def _configure_api_client_path() -> None:
    global _API_CLIENT_CONFIGURED
    if _API_CLIENT_CONFIGURED:
        return

    candidates = []

    env_path = os.environ.get("ECU_TEST_API_CLIENT_PATH")
    if env_path:
        candidates.append(Path(env_path))

    candidates.append(Path("/opt/ecu.test/Templates/ApiClient"))

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            resolved_str = str(resolved)
            if resolved_str not in sys.path:
                sys.path.insert(0, resolved_str)
            _API_CLIENT_CONFIGURED = True
            return

    _API_CLIENT_CONFIGURED = True


def get_api_client():
    """Import and instantiate the ecu.test ApiClient."""
    _configure_api_client_path()

    try:
        api_client_module = importlib.import_module("ApiClient")
    except ImportError as exc:
        raise RuntimeError(
            "Could not import ApiClient. Ensure ecu.test is installed at /opt/ecu.test/ "
            "or set ECU_TEST_API_CLIENT_PATH."
        ) from exc

    try:
        api_client_class = getattr(api_client_module, "ApiClient")
    except AttributeError as exc:
        raise RuntimeError("Module ApiClient found but does not provide class ApiClient.") from exc

    return api_client_class()
