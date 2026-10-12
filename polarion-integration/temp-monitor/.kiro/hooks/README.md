# Legacy Demo Hooks

These hook files are **legacy demo artifacts** from the Temperature Monitoring System Polarion integration prototype. They are kept for reference only.

## Status

These hooks use the `.kiro.hook` format which is not the current Kiro v1 JSON hook format. They are **not active** and will not be executed by the Kiro IDE.

## Contents

| File | Purpose |
|------|---------|
| `check-traceability.kiro.hook` | On C file save, checks for ASPICE doxygen traceability tags (`@implements`, `@trace`) |
| `post-task-verify.kiro.hook` | After spec task completion, verifies Polarion work items and traceability links |

## Why Kept

These demonstrate the intended ASPICE traceability workflow for automotive projects:

1. **Pre-commit quality gate** — ensuring C source has proper doxygen traceability before leaving the developer machine
2. **Post-task verification** — confirming Polarion sync after spec-driven development tasks

They serve as a reference for implementing equivalent hooks in the current v1 JSON format at the root `.kiro/hooks/` directory if needed.

## Migration

To use these concepts in the current project, migrate them to root-level hooks:
- Root path: `.kiro/hooks/<hook-name>.json`
- Format: v1 JSON (see Kiro documentation)
