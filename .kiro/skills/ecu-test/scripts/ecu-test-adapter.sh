#!/usr/bin/env bash
# ecu-test-adapter.sh — Skill adapter for local/remote ECU-TEST execution.
#
# Usage:
#   ./ecu-test-adapter.sh <script_name> [script_args...]
#   ./ecu-test-adapter.sh --upload <local_file>
#   ./ecu-test-adapter.sh --download <remote_file> [local_dest]
#   ./ecu-test-adapter.sh --check-running
#   ./ecu-test-adapter.sh --sync [--restart-config]

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

        # --- SSH Key Path Resolution ---
        # Handles multiple path formats that arise on Windows + WSL/Git Bash:
        #   ~/ prefix          -> expand to $HOME
        #   C:\path\to\key     -> /mnt/c/path/to/key  (WSL mount)
        #   C:/path/to/key     -> /mnt/c/path/to/key  (forward-slash Windows)
        #   /c/path/to/key     -> /mnt/c/path/to/key  (Git Bash / MSYS2)
        #   Already /mnt/...   -> leave as-is

        # Expand ~ in key path
        REMOTE_KEY="${REMOTE_KEY/#\~/$HOME}"

        # Normalize all backslashes to forward slashes first
        REMOTE_KEY="${REMOTE_KEY//\\//}"

        # Translate Windows-style paths: C:/... -> /mnt/c/...
        if [[ "$REMOTE_KEY" =~ ^[A-Za-z]:/ ]]; then
            local drive="${REMOTE_KEY:0:1}"
            drive="${drive,,}"  # lowercase
            REMOTE_KEY="/mnt/${drive}/${REMOTE_KEY:3}"
        fi

        # Translate Git Bash / MSYS2 paths: /c/... -> /mnt/c/...
        if [[ "$REMOTE_KEY" =~ ^/[A-Za-z]/ && ! "$REMOTE_KEY" =~ ^/mnt/ ]]; then
            local drive="${REMOTE_KEY:1:1}"
            drive="${drive,,}"
            REMOTE_KEY="/mnt/${drive}/${REMOTE_KEY:3}"
        fi

        if [[ ! -f "$REMOTE_KEY" ]]; then
            echo "ERROR: SSH key file not found: $REMOTE_KEY"
            echo "  Resolved path: $REMOTE_KEY"
            echo "  Original config value: $(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('key_path',''))" 2>/dev/null || echo 'unknown')"
            echo ""
            echo "  Troubleshooting:"
            echo "    - Ensure the key file exists at the specified path"
            echo "    - Accepted formats: ~/.ssh/key.pem, C:\\path\\key.pem, /mnt/c/path/key.pem"
            echo "    - On WSL, Windows paths are mounted under /mnt/<drive>/"
            exit 1
        fi

        # --- SSH Key Permission Fix ---
        # Keys on Windows mounts (e.g. /mnt/c/) always show 0777 which SSH rejects
        # with "Permissions 0777 for 'key' are too open". Copy to a secure temp
        # location with correct permissions. Use a stable filename (based on uid)
        # so we don't accumulate temp files across invocations.
        local key_perms
        key_perms=$(stat -c '%a' "$REMOTE_KEY" 2>/dev/null || echo "unknown")
        if [[ "$key_perms" != "600" && "$key_perms" != "400" ]]; then
            local secure_key="/tmp/.ecu-test-ssh-key-$(id -u)"
            cp "$REMOTE_KEY" "$secure_key"
            chmod 600 "$secure_key"
            REMOTE_KEY="$secure_key"
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

# --- Workspace Sync ---

sync_workspace() {
    local restart_config="${1:-false}"

    if [[ "$MODE" != "remote" ]]; then
        echo "ERROR: --sync only works in remote mode"
        return 1
    fi

    # Resolve local workspace path (relative to PROJECT_ROOT if not absolute)
    local local_ws="$LOCAL_WORKSPACE"
    # Normalize Windows-style backslashes to forward slashes
    local_ws="${local_ws//\\//}"
    if [[ ! "$local_ws" = /* ]]; then
        local_ws="$PROJECT_ROOT/$local_ws"
    fi

    if [[ ! -d "$local_ws" ]]; then
        echo "ERROR: Local workspace not found: $local_ws"
        return 1
    fi

    echo "Syncing workspace: $local_ws -> ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_WORKSPACE}/"

    # Directories to sync (order matters: .workspace first for project metadata)
    local dirs=(".workspace" "Configurations" "Parameters" "fmu")
    local synced=0

    for dir in "${dirs[@]}"; do
        local local_dir="$local_ws/$dir"
        if [[ -d "$local_dir" ]]; then
            # Ensure remote directory exists
            ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
                "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p '$REMOTE_WORKSPACE/$dir'" || {
                echo "ERROR: Could not create remote directory: $REMOTE_WORKSPACE/$dir"
                return 1
            }

            # Use scp -r to upload the directory contents
            scp -r -i "$REMOTE_KEY" -o ConnectTimeout="$TRANSFER_TIMEOUT" -o StrictHostKeyChecking=no \
                "$local_dir/." "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_WORKSPACE}/$dir/" || {
                echo "ERROR: Failed to sync directory: $dir"
                return 1
            }

            echo "  Synced: $dir/"
            synced=$((synced + 1))
        fi
    done

    # Also ensure Packages directory exists on remote
    ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p '$REMOTE_WORKSPACE/Packages'" || true

    echo "Sync complete: $synced directories uploaded."

    # Optionally restart the configuration so ECU-TEST picks up changes
    if [[ "$restart_config" == "true" ]]; then
        echo "Restarting configuration..."

        # Check if ECU-TEST is running
        if ! check_ecu_test_running; then
            echo "  ECU-TEST is not running, skipping config restart."
            return 0
        fi

        # Stop current configuration
        local stop_resp
        stop_resp=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
            "${REMOTE_USER}@${REMOTE_HOST}" \
            "curl -s -X PUT -H 'Content-Type: application/json' -d '{\"action\": \"Stop\", \"tbc\": {\"tbcPath\": \"$TBC_NAME\"}, \"tcf\": {\"tcfPath\": \"$TCF_NAME\"}}' http://127.0.0.1:5050/api/v2/configuration" 2>/dev/null) || true

        sleep 3

        # Start configuration again
        local start_resp
        start_resp=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
            "${REMOTE_USER}@${REMOTE_HOST}" \
            "curl -s -X PUT -H 'Content-Type: application/json' -d '{\"action\": \"Start\", \"tbc\": {\"tbcPath\": \"$TBC_NAME\"}, \"tcf\": {\"tcfPath\": \"$TCF_NAME\"}}' http://127.0.0.1:5050/api/v2/configuration" 2>/dev/null) || true

        # Wait for configuration to be ready
        sleep 10

        # Verify configuration started
        local config_status
        config_status=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
            "${REMOTE_USER}@${REMOTE_HOST}" \
            "curl -s http://127.0.0.1:5050/api/v2/configuration" 2>/dev/null) || true

        if echo "$config_status" | grep -q '"key": "FINISHED"'; then
            echo "  Configuration restarted successfully."
        else
            echo "  WARNING: Configuration may not have started cleanly. Status: $config_status"
        fi
    fi

    return 0
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

# --- Remote Script Provisioning ---

REMOTE_SCRIPTS_HASH_FILE="/tmp/.ecu-test-scripts-hash"

ensure_remote_scripts() {
    # Ensure remote scripts are deployed and up-to-date.
    # Uses a content hash to avoid redundant uploads within the same session.

    local local_remote_dir="$SCRIPT_DIR/remote"
    if [[ ! -d "$local_remote_dir" ]]; then
        echo "ERROR: Local remote scripts directory not found: $local_remote_dir"
        return 1
    fi

    # Compute a hash of local remote scripts to detect changes
    local local_hash
    local_hash=$(find "$local_remote_dir" -type f -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)

    # Check if we already synced this hash in this session
    if [[ -f "$REMOTE_SCRIPTS_HASH_FILE" ]]; then
        local cached_hash
        cached_hash=$(cat "$REMOTE_SCRIPTS_HASH_FILE" 2>/dev/null || echo "")
        if [[ "$cached_hash" == "$local_hash" ]]; then
            return 0  # Already up-to-date
        fi
    fi

    # Check if remote scripts directory exists and has content
    local remote_count
    remote_count=$(ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
        "${REMOTE_USER}@${REMOTE_HOST}" \
        "ls '$REMOTE_SCRIPTS_DIR'/*.py 2>/dev/null | wc -l" 2>/dev/null) || remote_count="0"

    # Compare file counts as a quick staleness check
    local local_count
    local_count=$(find "$local_remote_dir" -name "*.py" -type f | wc -l)

    if [[ "$remote_count" -lt "$local_count" || "$remote_count" == "0" ]]; then
        echo "Provisioning remote scripts ($local_count files)..."

        # Create directory on remote
        ssh -i "$REMOTE_KEY" -o ConnectTimeout="$SSH_TIMEOUT" -o StrictHostKeyChecking=no \
            "${REMOTE_USER}@${REMOTE_HOST}" \
            "sudo mkdir -p '$REMOTE_SCRIPTS_DIR' && sudo chown \$(whoami):\$(whoami) '$REMOTE_SCRIPTS_DIR'" || {
            echo "ERROR: Could not create remote scripts directory"
            return 1
        }

        # Upload all scripts
        scp -r -i "$REMOTE_KEY" -o ConnectTimeout="$TRANSFER_TIMEOUT" -o StrictHostKeyChecking=no \
            "$local_remote_dir/"* "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SCRIPTS_DIR}/" || {
            echo "ERROR: Failed to upload remote scripts"
            return 1
        }

        echo "Remote scripts provisioned successfully."
    fi

    # Cache the hash so we don't re-check within this session
    echo "$local_hash" > "$REMOTE_SCRIPTS_HASH_FILE"
    return 0
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

    # Ensure remote scripts are deployed before attempting execution
    ensure_remote_scripts || {
        echo "ERROR: Cannot execute remotely — script provisioning failed."
        exit 1
    }

    # Translate path arguments
    local args=()
    for arg in "$@"; do
        args+=("$(translate_path "$arg")")
    done

    # Build the remote command with proper quoting
    local remote_cmd="cd $REMOTE_SCRIPTS_DIR && python3 $REMOTE_SCRIPTS_DIR/$script_name"
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
        --sync)
            shift
            local restart="false"
            if [[ "${1:-}" == "--restart-config" ]]; then
                restart="true"
                shift
            fi
            sync_workspace "$restart"
            exit $?
            ;;
        --ensure-scripts)
            if [[ "$MODE" != "remote" ]]; then
                echo "ERROR: --ensure-scripts only works in remote mode"
                exit 1
            fi
            ensure_remote_scripts
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
            echo "Usage: $0 <script_name> [args...] | --upload <file> | --download <file> [dest] | --sync [--restart-config] | --ensure-scripts | --check-running"
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

        # Pass configured exe_path, license, and workspace to start.py
        local start_args=("$@")
        # Add --exe-path if not already specified by the user
        local has_exe=false
        for arg in "${start_args[@]+"${start_args[@]}"}"; do
            [[ "$arg" == "--exe-path"* ]] && has_exe=true
        done
        if [[ "$has_exe" == "false" && -n "$EXE_PATH" ]]; then
            start_args+=("--exe-path" "$EXE_PATH")
        fi
        # Add --workspace-dir if not already specified
        local has_ws=false
        for arg in "${start_args[@]+"${start_args[@]}"}"; do
            [[ "$arg" == "--workspace-dir"* ]] && has_ws=true
        done
        if [[ "$has_ws" == "false" && -n "$REMOTE_WORKSPACE" ]]; then
            start_args+=("--workspace-dir" "$REMOTE_WORKSPACE")
        fi

        # Pass license via environment on the remote
        local license_env=""
        if [[ -n "$LICENSE" ]]; then
            license_env="TRACET_LICENSE=$LICENSE "
        fi

        ensure_remote_scripts || {
            echo "ERROR: Cannot execute remotely — script provisioning failed."
            exit 1
        }

        local remote_cmd="${license_env}cd $REMOTE_SCRIPTS_DIR && python3 $REMOTE_SCRIPTS_DIR/start.py"
        for arg in "${start_args[@]+"${start_args[@]}"}"; do
            remote_cmd+=" '${arg//\'/\'\\\'\'}'"
        done

        ssh -i "$REMOTE_KEY" \
            -o ConnectTimeout="$SSH_TIMEOUT" \
            -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=15 \
            "${REMOTE_USER}@${REMOTE_HOST}" \
            "$remote_cmd"
        exit $?
    fi

    if [[ "$MODE" == "local" ]]; then
        run_local "$script_name" "$@"
    else
        run_remote "$script_name" "$@"
    fi
}

main "$@"
