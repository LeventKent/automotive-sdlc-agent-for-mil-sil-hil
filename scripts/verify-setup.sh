#!/usr/bin/env bash
# verify-setup.sh — Checks all prerequisites for the Automotive SDLC Agent project.
# Run from the project root: ./scripts/verify-setup.sh
#
# Exit codes:
#   0 — all required prerequisites pass (warnings are OK)
#   1 — one or more required prerequisites failed

set -uo pipefail

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0
WARN=0

pass() {
  echo "  [PASS] $1"
  PASS=$((PASS + 1))
}

fail() {
  echo "  [FAIL] $1"
  FAIL=$((FAIL + 1))
}

warn() {
  echo "  [WARN] $1"
  WARN=$((WARN + 1))
}

echo "=== Automotive SDLC Agent — Setup Verification ==="
echo ""

# ---------- 1. MATLAB ----------
echo "Checking MATLAB..."
if command -v matlab &>/dev/null; then
  MATLAB_VER=$(matlab -batch "disp(version)" 2>/dev/null | tail -1 || true)
  pass "MATLAB found in PATH${MATLAB_VER:+ (${MATLAB_VER})}"
elif [ -d "/Applications/MATLAB_R2025b.app" ]; then
  pass "MATLAB found at /Applications/MATLAB_R2025b.app"
elif [ -d "/Applications/MATLAB_R2025a.app" ]; then
  pass "MATLAB found at /Applications/MATLAB_R2025a.app"
elif ls /Applications/MATLAB_R20*.app &>/dev/null 2>&1; then
  pass "MATLAB found in /Applications/"
else
  fail "MATLAB not found — install MATLAB R2025a+ and ensure it is in PATH or /Applications/"
fi

# ---------- 2. Simulink Agentic Toolkit ----------
echo "Checking simulink-agentic-toolkit..."
if [ -f "$PROJECT_ROOT/simulink-agentic-toolkit/tools/tools.json" ]; then
  pass "simulink-agentic-toolkit/tools/tools.json exists"
else
  fail "simulink-agentic-toolkit/tools/tools.json not found — clone https://github.com/matlab/simulink-agentic-toolkit into project root"
fi

# ---------- 3. Python 3.11+ ----------
echo "Checking Python..."
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
fi

if [ -n "$PYTHON_CMD" ]; then
  PY_VER=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
  PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
  if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
    pass "Python $($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
  else
    fail "Python $PY_VER found — version 3.11+ required"
  fi
else
  fail "Python not found — install Python 3.11+"
fi

# ---------- 4. Polarion MCP venv ----------
echo "Checking Polarion MCP virtual environment..."
POLARION_VENV="$PROJECT_ROOT/polarion-integration/polarion-mcp/.venv/bin/python"
if [ -x "$POLARION_VENV" ]; then
  pass "Polarion MCP venv exists at polarion-integration/polarion-mcp/.venv/"
else
  fail "Polarion MCP venv not found — run: cd polarion-integration/polarion-mcp && python3 -m venv .venv && .venv/bin/pip install -e ."
fi

# ---------- 5. .ecu-test-remote.json (optional) ----------
echo "Checking .ecu-test-remote.json..."
if [ -f "$PROJECT_ROOT/.ecu-test-remote.json" ]; then
  pass ".ecu-test-remote.json present (remote mode configured)"
else
  warn ".ecu-test-remote.json not found — remote ECU-TEST execution unavailable (OK for local-only mode)"
fi

# ---------- 6. AWS CLI (optional) ----------
echo "Checking AWS CLI..."
if command -v aws &>/dev/null; then
  AWS_VER=$(aws --version 2>&1 | head -1)
  pass "AWS CLI found ($AWS_VER)"
else
  warn "AWS CLI not found — required only for infrastructure provisioning (CloudFormation)"
fi

# ---------- Summary ----------
echo ""
echo "=== Summary ==="
echo "  PASS: $PASS   FAIL: $FAIL   WARN: $WARN"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "Some required prerequisites are missing. See FAIL items above."
  exit 1
else
  echo "All required prerequisites satisfied."
  exit 0
fi
