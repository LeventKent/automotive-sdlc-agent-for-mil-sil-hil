#!/usr/bin/env bash
# -----------------------------------------------------------------------
# Standalone convenience script for compiling FMU on remote.
# For the full workflow, use ecu-test-adapter.sh --sync then compile.
# -----------------------------------------------------------------------
set -euo pipefail

CONFIG_FILE=".ecu-test-remote.json"
HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['hostname'])")
USER=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['username'])")
KEY_RAW=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['key_path'])")
LOCAL_WORKSPACE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['local_workspace'])")
TCF_NAME=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('tcf_name') or 'fmu.tcf')")
FMU_NAME=$(python3 -c "import sys, xml.etree.ElementTree as ET; root=ET.parse(sys.argv[1]).getroot(); print(next((element.text or '').strip() for element in root.iter() if element.tag.endswith('MODEL-FILE') and (element.text or '').strip()))" "$LOCAL_WORKSPACE/Configurations/$TCF_NAME")

# Normalize key path for macOS/Linux/WSL and expand a leading home shortcut.
KEY_PATH="${KEY_RAW//\\//}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"
if [[ "$KEY_PATH" =~ ^[A-Za-z]:/ ]]; then
    drive="${KEY_PATH:0:1}"
    drive="${drive,,}"
    KEY_PATH="/mnt/${drive}/${KEY_PATH:3}"
fi

# Fix permissions
SECURE_KEY="/tmp/.ecu-test-ssh-key-$(id -u)"
cp "$KEY_PATH" "$SECURE_KEY"
chmod 600 "$SECURE_KEY"

echo "Compiling $FMU_NAME on remote: $USER@$HOST"
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" "cd /opt/ecu-test-workspace/fmu && python3 compile_fmu.py '$FMU_NAME'"

# A configuration restart requires the ECU-TEST REST API. Compilation is still
# complete when ECU-TEST is intentionally stopped or failed to start.
if ! ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" \
    'curl -fsS http://127.0.0.1:5050/api/v2/live >/dev/null'; then
    echo ""
    echo "ECU-TEST API is not running; FMU compilation completed, so configuration restart is deferred."
    exit 0
fi

echo ""
echo "Restarting ECU-TEST configuration..."

# Stop configuration
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" 'curl -s -X PUT -H "Content-Type: application/json" -d "{\"action\":\"Stop\",\"tbc\":{\"tbcPath\":\"fmu.tbc\"},\"tcf\":{\"tcfPath\":\"fmu.tcf\"}}" http://127.0.0.1:5050/api/v2/configuration'

echo ""
echo "Waiting 5 seconds..."
sleep 5

# Start configuration
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" 'curl -s -X PUT -H "Content-Type: application/json" -d "{\"action\":\"Start\",\"tbc\":{\"tbcPath\":\"fmu.tbc\"},\"tcf\":{\"tcfPath\":\"fmu.tcf\"}}" http://127.0.0.1:5050/api/v2/configuration'

echo ""
echo "Waiting 15 seconds for FMU to load..."
sleep 15

# Verify configuration status
echo "Checking configuration status..."
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" 'curl -s http://127.0.0.1:5050/api/v2/configuration'

echo ""
echo "Done."
