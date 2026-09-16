#!/usr/bin/env bash
# Compile the FMU referenced by the configured ECU-TEST TCF and reload it remotely.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/.ecu-test-remote.json"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: Remote ECU-TEST configuration not found: $CONFIG_FILE" >&2
    exit 1
fi

config_value() {
    local key="$1"
    python3 - "$CONFIG_FILE" "$key" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as config_file:
    config = json.load(config_file)
print(config.get(sys.argv[2], ""))
PY
}

select_configuration_file() {
    local extension="$1"
    local configured_name="$2"
    local configuration_dir="$LOCAL_WORKSPACE/Configurations"

    if [[ -n "$configured_name" ]]; then
        local configured_path="$configuration_dir/$configured_name"
        if [[ ! -f "$configured_path" ]]; then
            echo "ERROR: Configured .$extension file not found: $configured_path" >&2
            exit 1
        fi
        basename "$configured_path"
        return
    fi

    local candidates=("$configuration_dir"/*."$extension")
    if [[ ${#candidates[@]} -ne 1 || ! -f "${candidates[0]}" ]]; then
        echo "ERROR: Expected exactly one .$extension file in $configuration_dir; configure ${extension}_name to disambiguate." >&2
        exit 1
    fi
    basename "${candidates[0]}"
}

HOST="$(config_value hostname)"
USER="$(config_value username)"
KEY_RAW="$(config_value key_path)"
LOCAL_WORKSPACE="$(config_value local_workspace)"
REMOTE_WORKSPACE="$(config_value remote_workspace)"
REMOTE_WORKSPACE="${REMOTE_WORKSPACE:-/opt/ecu-test-workspace}"

if [[ -z "$HOST" || -z "$USER" || -z "$KEY_RAW" || -z "$LOCAL_WORKSPACE" ]]; then
    echo "ERROR: hostname, username, key_path, and local_workspace are required in $CONFIG_FILE" >&2
    exit 1
fi

if [[ "$LOCAL_WORKSPACE" != /* ]]; then
    LOCAL_WORKSPACE="$PROJECT_ROOT/$LOCAL_WORKSPACE"
fi

TCF_NAME="$(select_configuration_file "tcf" "$(config_value tcf_name)")"
TBC_NAME="$(select_configuration_file "tbc" "$(config_value tbc_name)")"
TCF_PATH="$LOCAL_WORKSPACE/Configurations/$TCF_NAME"

FMU_FILE="$(python3 - "$TCF_PATH" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
for element in root.iter():
    if element.tag.rsplit('}', 1)[-1] == 'MODEL-FILE' and element.text:
        print(element.text.strip())
        break
else:
    raise SystemExit(f"ERROR: MODEL-FILE not found in {sys.argv[1]}")
PY
)"

if [[ -z "$FMU_FILE" ]]; then
    echo "ERROR: The configured TCF does not reference an FMU." >&2
    exit 1
fi

# Normalize key paths for macOS, Linux, and WSL.
KEY_PATH="${KEY_RAW/#\~/$HOME}"
KEY_PATH="${KEY_PATH//\\//}"
if [[ "$KEY_PATH" =~ ^[A-Za-z]:/ ]]; then
    drive="${KEY_PATH:0:1}"
    drive="${drive,,}"
    KEY_PATH="/mnt/${drive}/${KEY_PATH:3}"
fi

if [[ ! -f "$KEY_PATH" ]]; then
    echo "ERROR: SSH key not found: $KEY_PATH" >&2
    exit 1
fi

SECURE_KEY="$(mktemp "${TMPDIR:-/tmp}/ecu-test-ssh-key.XXXXXX")"
trap 'rm -f "$SECURE_KEY"' EXIT
cp "$KEY_PATH" "$SECURE_KEY"
chmod 600 "$SECURE_KEY"

printf 'Compiling FMU referenced by %s: %s\n' "$TCF_NAME" "$FMU_FILE"
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" \
    "cd '$REMOTE_WORKSPACE/fmu' && python3 compile_fmu.py '$FMU_FILE'"

printf '\nRestarting ECU-TEST configuration: %s / %s\n' "$TBC_NAME" "$TCF_NAME"
CONFIGURATION_URL="http://127.0.0.1:5050/api/v2/configuration"
STOP_PAYLOAD="$(python3 - "$TBC_NAME" "$TCF_NAME" <<'PY'
import json
import sys
print(json.dumps({"action": "Stop", "tbc": {"tbcPath": sys.argv[1]}, "tcf": {"tcfPath": sys.argv[2]}}))
PY
)"
START_PAYLOAD="$(python3 - "$TBC_NAME" "$TCF_NAME" <<'PY'
import json
import sys
print(json.dumps({"action": "Start", "tbc": {"tbcPath": sys.argv[1]}, "tcf": {"tcfPath": sys.argv[2]}}))
PY
)"

ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" \
    "curl -s -X PUT -H 'Content-Type: application/json' -d '$STOP_PAYLOAD' '$CONFIGURATION_URL'"

printf '\nWaiting 5 seconds...\n'
sleep 5

ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" \
    "curl -s -X PUT -H 'Content-Type: application/json' -d '$START_PAYLOAD' '$CONFIGURATION_URL'"

printf '\nWaiting 15 seconds for the FMU to load...\n'
sleep 15

printf 'Checking configuration status...\n'
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" \
    "curl -s '$CONFIGURATION_URL'"
printf '\nDone.\n'
