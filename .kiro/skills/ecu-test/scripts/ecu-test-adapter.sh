#!/usr/bin/env bash
# ecu-test-adapter.sh — Skill adapter for local/remote ECU-TEST execution.
#
# Usage:
#   ./ecu-test-adapter.sh <script_name> [script_args...]
#   ./ecu-test-adapter.sh --upload <local_file>
#   ./ecu-test-adapter.sh --download <remote_file> [local_dest]
#   ./ecu-test-adapter.sh --check-running

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/.ecu-test-remote.json"

# --- Configuration Loading ---

load_config() {
    # Use a Python script to resolve config and output shell-safe assignments
    local config_output
    config_output=$(python3 "$SCRIPT_DIR/resolve_config.py" "$CONFIG_FILE" 2>&1) || {
        echo "ERROR: Configuration resolution failed: $config_output"
        exit 1
    }
    eval "$config_output"
}

validate_config() {
    if [[ "$MODE" != "local" && "$MODE" != "remote" ]]; then
        echo "ERROR: Invalid execution mode '$MODE'. Accepted values are: 'local', 'remote'"
        exit 1
    fi

    if [[ "$MODE" == "remote" ]]; then
        local missing=()
        [[ -z "$REMOTE_HOST" ]] && missing+=("hostname")
        [[ -z "$REMOTE_USER" ]] && missing+=("username")
        [[ -z "$REMOTE_KEY" ]] && missing+=("key_path")
        if [[ ${#missing[@]} -gt 0 ]]; then
            echo "ERROR: Missing required remote parameters: ${missing[*]}"
            exit 1
        fi
        # Expand ~ in key path
        REMOTE_KEY="${REMOTE_KEY/#\~/$HOME}"
        if [[ ! -f "$REMOTE_KEY" ]]; then
            echo "ERROR: SSH key file not found: $REMOTE_KEY"
            exit 1
        fi
    fi
}

# --- Path Translation ---

translate_path() {
    python3 -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from adapter_logic import translate_path
print(translate_path(sys.argv[1], sys.argv[2], sys.argv[3]))
" "$1" "$LOCAL_WORKSPACE" "$REMOTE_WORKSPACE"
}

# --- File Transfer ---

upload_file() {
    local local_file="$1"
    local remote_dest="${2:-$REMOTE_WORKSPACE/$(basename "$local_file")}"

    if [[ ! -f "$local_file" ]]; then
        echo "ERROR: Local file not found: $local_file"
        return 1
    fi

    local local_size
    local_size=$(stat -f '%z' "$local_file" 2>/dev/null || stat --printf='%s' "$local_file" 2>/dev/null)

    scp -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "$local_file" "${REMOTE_USER}@${REMOTE_HOST}:${remote_dest}" || {
        echo "ERROR: SCP upload failed for $local_file -> $remote_dest"
        return 1
    }

    local remote_size
    remote_size=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "${REMOTE_USER}@${REMOTE_HOST}" "stat --printf='%s' '$remote_dest'" 2>/dev/null) || {
        echo "ERROR: Could not verify remote file: $remote_dest"
        return 1
    }

    if [[ "$local_size" != "$remote_size" ]]; then
        ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
            "${REMOTE_USER}@${REMOTE_HOST}" "rm -f '$remote_dest'" 2>/dev/null
        echo "ERROR: File size mismatch: local=$local_size remote=$remote_size for $local_file"
        return 1
    fi
    echo "Uploaded: $local_file -> $remote_dest ($local_size bytes)"
}

download_file() {
    local remote_file="$1"
    local local_dest="${2:-.}"

    scp -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "${REMOTE_USER}@${REMOTE_HOST}:${remote_file}" "$local_dest" || {
        echo "ERROR: SCP download failed for $remote_file -> $local_dest"
        return 1
    }
    echo "Downloaded: $remote_file -> $local_dest"
}

# --- ECU-TEST Lifecycle ---

check_ecu_test_running() {
    local result
    result=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "${REMOTE_USER}@${REMOTE_HOST}" \
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5050/api/v2/live 2>/dev/null || echo 000") || {
        echo "ERROR: SSH connection failed to $REMOTE_HOST"
        return 2
    }
    [[ "$result" == "200" ]]
}

# --- Execution ---

run_local() {
    local script_name="$1"
    shift
    python3 "$SCRIPT_DIR/$script_name" "$@"
}

run_remote() {
    local script_name="$1"
    shift

    # Translate path arguments
    local args=()
    for arg in "$@"; do
        args+=("$(translate_path "$arg")")
    done

    # Build the remote command with proper quoting
    local remote_cmd="cd /opt/ecu-test-scripts && python3 /opt/ecu-test-scripts/$script_name"
    for arg in "${args[@]+"${args[@]}"}"; do
        remote_cmd+=" '${arg//\'/\'\\\'\'}'"
    done

    ssh -i "$REMOTE_KEY" \
        -o ConnectTimeout="$SSH_TIMEOUT" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=15 \
        "${REMOTE_USER}@${REMOTE_HOST}" \
        "$remote_cmd"
}

# --- Main ---

main() {
    load_config
    validate_config

    case "${1:-}" in
        --upload)
            shift
            upload_file "$@"
            exit $?
            ;;
        --download)
            shift
            download_file "$@"
            exit $?
            ;;
        --check-running)
            if [[ "$MODE" != "remote" ]]; then
                echo "ERROR: --check-running only works in remote mode"
                exit 1
            fi
            if check_ecu_test_running; then
                echo "ECU-TEST is running on $REMOTE_HOST"
            else
                echo "ECU-TEST is NOT running on $REMOTE_HOST"
                exit 1
            fi
            exit 0
            ;;
        "")
            echo "Usage: $0 <script_name> [args...] | --upload <file> | --download <file> [dest] | --check-running"
            exit 1
            ;;
    esac

    local script_name="$1"
    shift

    # Special handling for start.py in remote mode
    if [[ "$MODE" == "remote" && "$script_name" == "start.py" ]]; then
        if check_ecu_test_running; then
            echo "ECU-TEST is already running on $REMOTE_HOST. Skipping start."
            echo "SUCCESS: ECU-TEST started and REST API ready"
            exit 0
        fi
    fi

    if [[ "$MODE" == "local" ]]; then
        run_local "$script_name" "$@"
    else
        run_remote "$script_name" "$@"
    fi
}

main "$@"
