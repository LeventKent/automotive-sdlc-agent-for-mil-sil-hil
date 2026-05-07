#!/usr/bin/env bash
#
# Installs the Simulink Agentic Toolkit into this repo at ./simulink-agentic-toolkit
# by cloning https://github.com/matlab/simulink-agentic-toolkit at a pinned tag.
#
# The folder is gitignored on purpose — this script is the single source of truth
# for which version to install. Bump TOOLKIT_REF and re-run to update.
#
# Usage:
#   ./scripts/install-simulink-toolkit.sh                # install at pinned tag
#   TOOLKIT_REF=2026.05.06 ./scripts/install-simulink-toolkit.sh
#   FORCE=1 ./scripts/install-simulink-toolkit.sh         # re-install over existing
#
set -euo pipefail

# --- configuration -----------------------------------------------------------
TOOLKIT_REPO="${TOOLKIT_REPO:-https://github.com/matlab/simulink-agentic-toolkit.git}"
TOOLKIT_REF="${TOOLKIT_REF:-2026.05.06}"   # git tag, branch, or commit
TOOLKIT_DIR_NAME="simulink-agentic-toolkit"

# --- paths -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$REPO_ROOT/$TOOLKIT_DIR_NAME"

log() { printf '[install-simulink-toolkit] %s\n' "$*"; }
die() { printf '[install-simulink-toolkit] ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "git is required but not installed"

# --- handle existing install -------------------------------------------------
if [[ -e "$TARGET_DIR" ]]; then
  if [[ "${FORCE:-0}" == "1" ]]; then
    log "FORCE=1 set — removing existing $TARGET_DIR"
    rm -rf "$TARGET_DIR"
  elif [[ -d "$TARGET_DIR/.git" ]]; then
    log "Existing clone found at $TARGET_DIR — fetching and checking out $TOOLKIT_REF"
    git -C "$TARGET_DIR" fetch --tags --prune origin
    git -C "$TARGET_DIR" checkout --quiet "$TOOLKIT_REF"
    log "Updated to $(git -C "$TARGET_DIR" rev-parse --short HEAD) ($TOOLKIT_REF)"
    exit 0
  else
    die "$TARGET_DIR exists but is not a git clone. Re-run with FORCE=1 to overwrite."
  fi
fi

# --- fresh install -----------------------------------------------------------
log "Cloning $TOOLKIT_REPO at $TOOLKIT_REF -> $TARGET_DIR"
git clone --quiet --no-checkout "$TOOLKIT_REPO" "$TARGET_DIR"
if ! git -C "$TARGET_DIR" checkout --quiet "$TOOLKIT_REF"; then
  rm -rf "$TARGET_DIR"
  die "ref '$TOOLKIT_REF' not found in $TOOLKIT_REPO — no partial clone left behind"
fi

log "Installed $(git -C "$TARGET_DIR" rev-parse --short HEAD) ($TOOLKIT_REF)"
log "Next steps:"
log "  1. Install the MATLAB MCP Core Server binary (see simulink-agentic-toolkit/README.md)."
log "  2. Update .kiro/settings/mcp.json 'matlab' entry with the correct paths."
