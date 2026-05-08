"""
Property-based and unit tests for adapter_logic.py.

Uses Hypothesis for property-based testing of pure logic functions.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Add the scripts directory to sys.path so we can import adapter_logic
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".kiro" / "skills" / "ecu-test" / "scripts"))

from adapter_logic import (
    translate_path,
    validate_mode,
    resolve_config,
    check_missing_params,
    build_ssh_command,
    parse_script_output,
)

# --- Strategies ---

# Path segment: printable chars without path separators for clean relative segments
path_segment = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z"), blacklist_characters="/\\:\0"),
    min_size=1,
    max_size=20,
)

relative_path = st.lists(path_segment, min_size=1, max_size=5).map(lambda parts: "/".join(parts))

# Shell-dangerous strings for argument forwarding tests
shell_strings = st.text(
    alphabet=st.characters(blacklist_characters="\0"),
    min_size=0,
    max_size=50,
)


# ============================================================
# Feature: remote-ecu-test-execution, Property 1: Path translation round-trip preserves relative structure
# ============================================================

class TestPathTranslationProperty:
    @given(rel=relative_path)
    @settings(max_examples=100)
    def test_relative_structure_preserved(self, rel):
        """Relative path segments after workspace root are preserved unchanged."""
        local_ws = "/Users/dev/workspace"
        remote_ws = "/opt/ecu-test-workspace"
        local_path = f"{local_ws}/{rel}"

        result = translate_path(local_path, local_ws, remote_ws)

        assert result == f"{remote_ws}/{rel}"

    @given(rel=relative_path)
    @settings(max_examples=100)
    def test_backslashes_converted(self, rel):
        """All backslashes are converted to forward slashes."""
        local_ws = "C:\\Users\\dev\\workspace"
        remote_ws = "/opt/ecu-test-workspace"
        local_path = f"{local_ws}\\{rel}".replace("/", "\\")

        result = translate_path(local_path, local_ws, remote_ws)

        assert "\\" not in result

    @given(rel=relative_path)
    @settings(max_examples=100)
    def test_remote_prefix_replaces_local(self, rel):
        """Remote workspace prefix replaces local workspace prefix."""
        local_ws = "/home/user/work"
        remote_ws = "/opt/ecu-test-workspace"
        local_path = f"{local_ws}/{rel}"

        result = translate_path(local_path, local_ws, remote_ws)

        assert result.startswith(remote_ws)


# ============================================================
# Feature: remote-ecu-test-execution, Property 2: Mode validation accepts only valid modes
# ============================================================

class TestModeValidationProperty:
    @given(mode=st.text(min_size=0, max_size=30))
    @settings(max_examples=100)
    def test_only_local_and_remote_accepted(self, mode):
        """Only 'local' and 'remote' are accepted; all others raise ValueError."""
        if mode in ("local", "remote"):
            assert validate_mode(mode) is True
        else:
            with pytest.raises(ValueError) as exc_info:
                validate_mode(mode)
            msg = str(exc_info.value)
            assert mode in msg or repr(mode) in msg
            assert "local" in msg
            assert "remote" in msg


# ============================================================
# Feature: remote-ecu-test-execution, Property 3: Configuration resolution precedence
# ============================================================

CONFIG_KEYS = ["mode", "hostname", "username", "key_path", "local_workspace", "remote_workspace"]

config_values = st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N")))


class TestConfigPrecedenceProperty:
    @given(
        env=st.fixed_dictionaries({}, optional={k: config_values for k in CONFIG_KEYS}),
        cfg=st.fixed_dictionaries({}, optional={k: config_values for k in CONFIG_KEYS}),
    )
    @settings(max_examples=100)
    def test_env_takes_precedence(self, env, cfg):
        """Env var value used when both present and env is non-empty."""
        result = resolve_config(env, cfg)

        for key in CONFIG_KEYS:
            env_val = env.get(key, "")
            cfg_val = cfg.get(key, "")
            if key in env and env_val != "":
                assert result.get(key) == env_val
            else:
                assert result.get(key, "") == cfg_val


# ============================================================
# Feature: remote-ecu-test-execution, Property 4: Missing parameter detection is complete
# ============================================================

REQUIRED_PARAMS = ["hostname", "username", "key_path"]


class TestMissingParamsProperty:
    @given(present=st.sets(st.sampled_from(REQUIRED_PARAMS)))
    @settings(max_examples=100)
    def test_reports_exactly_missing_params(self, present):
        """Error lists exactly the missing parameter names — no more, no fewer."""
        config = {p: "value" for p in present}
        missing = check_missing_params(config)
        expected_missing = set(REQUIRED_PARAMS) - present

        assert set(missing) == expected_missing


# ============================================================
# Feature: remote-ecu-test-execution, Property 5: Argument forwarding preserves order and content
# ============================================================

class TestArgumentForwardingProperty:
    @given(args=st.lists(shell_strings, min_size=0, max_size=10))
    @settings(max_examples=100)
    def test_arguments_preserved_in_order(self, args):
        """SSH command preserves all arguments in original order with original content."""
        cmd = build_ssh_command(
            user="ubuntu",
            host="10.0.0.1",
            key="/path/key.pem",
            script_path="/opt/ecu-test-scripts/test.py",
            args=args,
            timeout=30,
        )

        # The args should appear at the end of the command in order
        script_idx = cmd.index("/opt/ecu-test-scripts/test.py")
        forwarded = cmd[script_idx + 1:]
        assert forwarded == args


# ============================================================
# Unit Tests: Edge cases
# ============================================================

class TestPathTranslationEdgeCases:
    def test_path_without_workspace_prefix(self):
        """Path not starting with workspace prefix gets only separator conversion."""
        result = translate_path("/other/path/file.fmu", "/workspace", "/opt/ecu-test-workspace")
        assert result == "/other/path/file.fmu"

    def test_path_is_workspace_prefix_exactly(self):
        """Path that IS the workspace prefix maps to remote workspace."""
        result = translate_path("/workspace", "/workspace", "/opt/ecu-test-workspace")
        assert result == "/opt/ecu-test-workspace"

    def test_windows_path_full_conversion(self):
        """Windows path with backslashes fully converted."""
        result = translate_path(
            "C:\\workspace\\Reports\\test.trf",
            "C:\\workspace",
            "/opt/ecu-test-workspace",
        )
        assert result == "/opt/ecu-test-workspace/Reports/test.trf"

    def test_trailing_slash_on_workspace(self):
        """Trailing slash on workspace doesn't break translation."""
        result = translate_path("/workspace/file.fmu", "/workspace/", "/opt/ecu-test-workspace")
        assert result == "/opt/ecu-test-workspace/file.fmu"

    def test_empty_path(self):
        """Empty path returns empty string."""
        result = translate_path("", "/workspace", "/opt/ecu-test-workspace")
        assert result == ""


class TestConfigParsing:
    def test_empty_env_falls_back_to_config(self):
        env = {"mode": ""}
        cfg = {"mode": "remote"}
        result = resolve_config(env, cfg)
        assert result["mode"] == "remote"

    def test_all_from_config_when_no_env(self):
        cfg = {"hostname": "ec2.example.com", "username": "ubuntu"}
        result = resolve_config({}, cfg)
        assert result["hostname"] == "ec2.example.com"
        assert result["username"] == "ubuntu"


class TestOutputParsing:
    def test_success_line(self):
        output = "Starting...\nDone\nSUCCESS: Test passed"
        status, msg = parse_script_output(output)
        assert status == "SUCCESS"
        assert msg == "Test passed"

    def test_error_line(self):
        output = "Starting...\nERROR: API not reachable"
        status, msg = parse_script_output(output)
        assert status == "ERROR"
        assert msg == "API not reachable"

    def test_no_matching_prefix(self):
        output = "Just some output\nNo status here"
        assert parse_script_output(output) is None

    def test_last_matching_line_wins(self):
        output = "ERROR: first error\nSUCCESS: recovered"
        status, msg = parse_script_output(output)
        assert status == "SUCCESS"
        assert msg == "recovered"

    def test_empty_output(self):
        assert parse_script_output("") is None


class TestModeValidationEdgeCases:
    def test_local_accepted(self):
        assert validate_mode("local") is True

    def test_remote_accepted(self):
        assert validate_mode("remote") is True

    def test_capitalized_rejected(self):
        with pytest.raises(ValueError):
            validate_mode("Local")

    def test_uppercase_rejected(self):
        with pytest.raises(ValueError):
            validate_mode("REMOTE")

    def test_whitespace_rejected(self):
        with pytest.raises(ValueError):
            validate_mode(" remote")


class TestMissingParamsEdgeCases:
    def test_all_present(self):
        config = {"hostname": "h", "username": "u", "key_path": "k"}
        assert check_missing_params(config) == []

    def test_all_missing(self):
        assert set(check_missing_params({})) == {"hostname", "username", "key_path"}

    def test_empty_string_counts_as_missing(self):
        config = {"hostname": "", "username": "u", "key_path": "k"}
        assert check_missing_params(config) == ["hostname"]


class TestBuildSshCommand:
    def test_basic_command_structure(self):
        cmd = build_ssh_command("ubuntu", "10.0.0.1", "/key.pem", "/opt/script.py", ["--arg", "val"], 30)
        assert cmd == [
            "ssh", "-i", "/key.pem", "-o", "ConnectTimeout=30",
            "ubuntu@10.0.0.1", "python3", "/opt/script.py", "--arg", "val",
        ]

    def test_no_args(self):
        cmd = build_ssh_command("u", "h", "k", "/s.py", [], 10)
        assert cmd[-1] == "/s.py"
