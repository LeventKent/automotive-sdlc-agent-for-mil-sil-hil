#!/usr/bin/env bash
# Build FMU on remote EC2 instance
set -euo pipefail

CONFIG_FILE=".ecu-test-remote.json"
HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['hostname'])")
USER=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['username'])")
KEY_RAW=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['key_path'])")

# Normalize key path for WSL
KEY_PATH="${KEY_RAW//\\//}"
if [[ "$KEY_PATH" =~ ^[A-Za-z]:/ ]]; then
    drive="${KEY_PATH:0:1}"
    drive="${drive,,}"
    KEY_PATH="/mnt/${drive}/${KEY_PATH:3}"
fi

# Fix permissions
SECURE_KEY="/tmp/.ecu-test-ssh-key-$(id -u)"
cp "$KEY_PATH" "$SECURE_KEY"
chmod 600 "$SECURE_KEY"

echo "Building FMU on remote: $USER@$HOST"
ssh -i "$SECURE_KEY" -o ConnectTimeout=30 -o StrictHostKeyChecking=no \
    "${USER}@${HOST}" "cd /opt/ecu-test-workspace/fmu && python3 build_fmu.py"

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
