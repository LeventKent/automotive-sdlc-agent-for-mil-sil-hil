#!/usr/bin/env python3
"""Resolve adapter config and print shell variable assignments."""
import json
import os
import sys

def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else ""
    cfg = {}
    if config_file and os.path.isfile(config_file):
        with open(config_file) as f:
            cfg = json.load(f)

    # Env vars override config file
    def get(key, env_var, default=""):
        val = os.environ.get(env_var, "")
        if val:
            return val
        return str(cfg.get(key, default))

    mode = get("mode", "ECU_TEST_MODE", "local")
    host = get("hostname", "ECU_TEST_REMOTE_HOST", "")
    user = get("username", "ECU_TEST_REMOTE_USER", "ubuntu")
    key = get("key_path", "ECU_TEST_REMOTE_KEY", "")
    local_ws = get("local_workspace", "ECU_TEST_LOCAL_WORKSPACE", "")
    remote_ws = get("remote_workspace", "ECU_TEST_REMOTE_WORKSPACE", "/opt/ecu-test-workspace")
    remote_scripts = get("remote_scripts_dir", "ECU_TEST_REMOTE_SCRIPTS_DIR", "/opt/ecu-test-scripts")
    exe_path = get("exe_path", "ECU_TEST_EXE_PATH", "/usr/bin/ecu.test")
    license_val = get("license", "ECU_TEST_LICENSE", "")
    tbc_name = get("tbc_name", "ECU_TEST_TBC_NAME", "")
    tcf_name = get("tcf_name", "ECU_TEST_TCF_NAME", "")
    ssh_timeout = get("ssh_timeout", "ECU_TEST_SSH_TIMEOUT", "30")
    exec_timeout = get("exec_timeout", "ECU_TEST_EXEC_TIMEOUT", "600")
    transfer_timeout = get("transfer_timeout", "ECU_TEST_TRANSFER_TIMEOUT", "300")

    # Output shell assignments
    print(f'MODE="{mode}"')
    print(f'REMOTE_HOST="{host}"')
    print(f'REMOTE_USER="{user}"')
    print(f'REMOTE_KEY="{key}"')
    print(f'LOCAL_WORKSPACE="{local_ws}"')
    print(f'REMOTE_WORKSPACE="{remote_ws}"')
    print(f'REMOTE_SCRIPTS_DIR="{remote_scripts}"')
    print(f'EXE_PATH="{exe_path}"')
    print(f'LICENSE="{license_val}"')
    print(f'TBC_NAME="{tbc_name}"')
    print(f'TCF_NAME="{tcf_name}"')
    print(f'SSH_TIMEOUT="{ssh_timeout}"')
    print(f'EXEC_TIMEOUT="{exec_timeout}"')
    print(f'TRANSFER_TIMEOUT="{transfer_timeout}"')

if __name__ == "__main__":
    main()
