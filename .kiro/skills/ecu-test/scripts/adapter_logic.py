"""
Pure logic functions for the ecu-test skill adapter.

This module contains testable pure functions used by the Bash adapter
(ecu-test-adapter.sh) for path translation, configuration resolution,
mode validation, SSH command construction, and script output parsing.
"""

from typing import Dict, List, Optional, Tuple


def translate_path(local_path: str, local_workspace: str, remote_workspace: str) -> str:
    """Replace local workspace prefix with remote workspace and convert backslashes to forward slashes.

    Rules:
    1. Replace local_workspace prefix with remote_workspace
    2. Convert all backslashes to forward slashes
    3. Preserve relative path segments after the workspace root

    If the path does not start with the local workspace prefix (after normalizing
    separators), the path is returned with only backslash-to-forward-slash conversion.

    Args:
        local_path: The local file path to translate.
        local_workspace: The local workspace base path.
        remote_workspace: The remote workspace base path (e.g., /opt/ecu-test-workspace).

    Returns:
        The translated path with remote workspace prefix and forward slashes.
    """
    # Normalize separators for comparison
    normalized_path = local_path.replace("\\", "/")
    normalized_workspace = local_workspace.replace("\\", "/")

    # Ensure workspace prefix doesn't have trailing slash for consistent matching
    normalized_workspace = normalized_workspace.rstrip("/")

    if not normalized_path.startswith(normalized_workspace):
        # Path doesn't start with workspace prefix, just convert separators
        return normalized_path

    # Extract relative part after workspace prefix
    relative = normalized_path[len(normalized_workspace):]

    # Ensure remote workspace doesn't have trailing slash
    remote_ws = remote_workspace.rstrip("/")

    return remote_ws + relative


def validate_mode(mode_value: str) -> bool:
    """Validate that the execution mode is exactly "local" or "remote".

    Args:
        mode_value: The mode string to validate.

    Returns:
        True if mode_value is "local" or "remote".

    Raises:
        ValueError: If mode_value is not "local" or "remote", with a message
            listing the invalid value and the two accepted values.
    """
    accepted = ("local", "remote")
    if mode_value in accepted:
        return True
    raise ValueError(
        f"Invalid execution mode '{mode_value}'. Accepted values are: 'local', 'remote'"
    )


def resolve_config(env_vars: Dict[str, str], config_file_dict: Dict[str, str]) -> Dict[str, str]:
    """Merge configuration from environment variables and config file.

    Environment variables take precedence over config file values.
    If an env var is unset (not present in dict) or empty string, the config
    file value is used instead.

    Args:
        env_vars: Dictionary of environment variable values (may contain empty strings).
        config_file_dict: Dictionary of values from the configuration file.

    Returns:
        Merged configuration dictionary with env vars taking precedence.
    """
    merged = {}

    # Start with all keys from both sources
    all_keys = set(config_file_dict.keys()) | set(env_vars.keys())

    for key in all_keys:
        env_value = env_vars.get(key, "")
        config_value = config_file_dict.get(key, "")

        # Env var takes precedence if it is set (present) and non-empty
        if key in env_vars and env_value != "":
            merged[key] = env_value
        else:
            merged[key] = config_value

    return merged


def check_missing_params(config: Dict[str, str]) -> List[str]:
    """Check for missing required remote connection parameters.

    Required parameters are: hostname, username, key_path.
    A parameter is considered missing if it is not present in the config
    dictionary or if its value is an empty string.

    Args:
        config: The resolved configuration dictionary.

    Returns:
        List of missing parameter names. Empty list if all are present.
    """
    required = ["hostname", "username", "key_path"]
    missing = []
    for param in required:
        value = config.get(param, "")
        if value == "":
            missing.append(param)
    return missing


def build_ssh_command(
    user: str,
    host: str,
    key: str,
    script_path: str,
    args: List[str],
    timeout: int,
) -> List[str]:
    """Construct an SSH command list for remote script execution.

    Builds a command list like:
        ["ssh", "-i", key, "-o", f"ConnectTimeout={timeout}",
         f"{user}@{host}", "python3", script_path, *args]

    All arguments are preserved in their original order and content.

    Args:
        user: SSH username.
        host: Remote hostname or IP.
        key: Path to SSH private key file.
        script_path: Path to the script on the remote machine.
        args: List of command-line arguments to forward to the script.
        timeout: SSH connection timeout in seconds.

    Returns:
        List of strings representing the full SSH command.
    """
    cmd = [
        "ssh",
        "-i", key,
        "-o", f"ConnectTimeout={timeout}",
        f"{user}@{host}",
        "python3", script_path,
    ]
    cmd.extend(args)
    return cmd


def parse_script_output(stdout_text: str) -> Optional[Tuple[str, str]]:
    """Extract SUCCESS/ERROR status from script output.

    Finds the last line in stdout_text that starts with "SUCCESS:" or "ERROR:"
    and returns the status and message.

    Args:
        stdout_text: The full stdout text from a script execution.

    Returns:
        A tuple of (status, message) where status is "SUCCESS" or "ERROR"
        and message is the text after the prefix. Returns None if no
        matching line is found.
    """
    lines = stdout_text.splitlines()

    # Search from the end for the last matching line
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith("SUCCESS:"):
            return ("SUCCESS", stripped[len("SUCCESS:"):].strip())
        elif stripped.startswith("ERROR:"):
            return ("ERROR", stripped[len("ERROR:"):].strip())

    return None
