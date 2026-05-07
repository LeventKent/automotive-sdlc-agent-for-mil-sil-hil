---
name: ecu-test
description: >
  Comprehensive skill for automating ecu.test — start the application, create test packages from
  requirements, generate test scripts via AI, execute tests, and analyze test reports.
  Use this skill when the user mentions ecu.test, ECU-TEST, test generation, test execution,
  test packages, TRF reports, TCF/TBC configuration, or any end-to-end test workflow involving
  ecu.test. Covers: starting ECU-TEST, creating packages, generating scripts, executing tests,
  and analyzing results.
---

# ecu.test Automation Skill

Comprehensive CLI-driven automation for ecu.test — create packages, generate test scripts,
execute tests, and analyze reports without leaving the IDE.

## Prerequisites

- **ECU-TEST** must be installed on the system.
- The **ecu.test ApiClient** must be available (installed with ecu.test, resolved automatically).
- The `requests` Python library is needed for the start capability.
- All file paths passed to scripts **must be absolute**.

## Quick Start

```bash
# Start ECU-TEST
python scripts/start.py --exe-path "C:\Program Files\ecu.test 2026.2\ecu.test.exe"

# Create a package from requirement steps
python scripts/create_package.py \
  --pre-step "Set vehicle state to 'D'." \
  --action-step "Press accelerator to 50%." \
  --action-step "Verify velocity > 50 km/h within 9s." \
  --output "C:\workspace\Packages\my_test.pkg"

# Generate test script via AI
python scripts/generate.py \
  --tcf "C:\workspace\Configurations\ElectricVehicle.tcf" \
  --package "C:\workspace\Packages\my_test.pkg"

# Execute a test
python scripts/execute.py \
  --test-case "C:\workspace\Packages\my_test.pkg" \
  --tbc "C:\workspace\Configurations\HiL_157.tbc" \
  --tcf "C:\workspace\Configurations\ElectricVehicle.tcf"

# Analyze test report
python scripts/report.py \
  --report-path "C:\workspace\TestReports\my_test_2026-05-07\my_test.trf"
```

## Golden Rules

1. **Always use absolute paths** — relative paths cause failures.
2. **Start ECU-TEST first** — all other capabilities require a running instance.
3. **One capability at a time** — ECU-TEST processes requests sequentially; wait for one to finish before starting the next.
4. **Decompose requirements carefully** — split into precondition, action, postcondition. Keep it minimal.
5. **Check reports after execution** — use the report capability to understand failures.

## Capabilities

| Capability | Script | Guide |
|---|---|---|
| Start ECU-TEST | `scripts/start.py` | [start.md](start.md) |
| Create test package | `scripts/create_package.py` | [create-package.md](create-package.md) |
| Generate test script (AI) | `scripts/generate.py` | [generate.md](generate.md) |
| Execute test case | `scripts/execute.py` | [execute.md](execute.md) |
| Analyze TRF report | `scripts/report.py` | [report.md](report.md) |
| End-to-end workflow | *(orchestration)* | [end-to-end.md](end-to-end.md) |

## Guide Index

### Getting Started

| Topic | File |
|---|---|
| Starting ECU-TEST | [start.md](start.md) |
| Creating test packages from requirements | [create-package.md](create-package.md) |

### Test Generation & Execution

| Topic | File |
|---|---|
| AI-based test script generation | [generate.md](generate.md) |
| Executing tests and collecting results | [execute.md](execute.md) |

### Analysis & Reporting

| Topic | File |
|---|---|
| Analyzing TRF reports for failures | [report.md](report.md) |

### Workflows

| Topic | File |
|---|---|
| Full end-to-end: requirement → package → generate → execute → report | [end-to-end.md](end-to-end.md) |
