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

- **ECU-TEST** must be installed locally OR on a remote EC2 instance.
- The **ecu.test ApiClient** must be available (installed with ecu.test, resolved automatically).
- The `requests` Python library is needed for the start capability.
- All file paths passed to scripts **must be absolute**.
- For remote mode: SSH key access to the remote instance and a `.ecu-test-remote.json` config file (see [Remote Setup](#remote-setup)).

## Session Startup: Check for Provisioned Remote Instance

When working in **remote mode**, read `.ecu-test-remote.json` in the project root at the start of the session. If the file exists and contains `"mode": "remote"` with a `hostname`, a remote instance has already been provisioned and is ready to use — **skip any provisioning steps** and go straight to using the instance.

The file contains:
- `hostname` — the public DNS name or IP of the remote instance
- `username` — SSH username (typically `ubuntu`)
- `key_path` — path to the SSH private key
- `local_workspace` — absolute path to the local ecu.test workspace directory
- `remote_workspace` — path on the remote instance (default: `/opt/ecu-test-workspace`)
- `remote_scripts_dir` — path for deployed scripts on remote (default: `/opt/ecu-test-scripts`)
- `exe_path` — path to the ecu.test executable on the remote
- `license` — the TRACET_LICENSE value for the remote instance
- `tbc_name` — filename of the test bench configuration (e.g., `MyBench.tbc`)
- `tcf_name` — filename of the test configuration (e.g., `MyConfig.tcf`)

The adapter scripts (`ecu-test-adapter.sh`) pick up this config automatically.

## Quick Start

All scripts are invoked through the adapter, which handles local/remote routing automatically:

```bash
# Start ECU-TEST (remote mode skips if already running)
./scripts/ecu-test-adapter.sh start.py

# Create a package from requirement steps
./scripts/ecu-test-adapter.sh create_package.py \
  --pre-step "Set vehicle state to 'D'." \
  --action-step "Press accelerator to 50%." \
  --output "/opt/ecu-test-workspace/Packages/my_test.pkg"

# Generate test script via AI
./scripts/ecu-test-adapter.sh generate.py \
  --tcf "/opt/ecu-test-workspace/Configurations/ElectricVehicle.tcf" \
  --package "/opt/ecu-test-workspace/Packages/my_test.pkg"

# Execute a test
./scripts/ecu-test-adapter.sh execute.py \
  --test-case "/opt/ecu-test-workspace/Packages/my_test.pkg" \
  --tbc "/opt/ecu-test-workspace/Configurations/HiL_157.tbc" \
  --tcf "/opt/ecu-test-workspace/Configurations/ElectricVehicle.tcf"

# Analyze test report
./scripts/ecu-test-adapter.sh report.py \
  --report-path "/opt/ecu-test-workspace/TestReports/my_test.trf"

# Upload FMU file to remote (remote mode only)
./scripts/ecu-test-adapter.sh --upload ./local/model.fmu

# Download report from remote (remote mode only)
./scripts/ecu-test-adapter.sh --download /opt/ecu-test-workspace/Reports/test.trf ./local/

# Check if ECU-TEST is running on remote
./scripts/ecu-test-adapter.sh --check-running

# Ensure remote scripts are deployed and up-to-date (remote mode only)
./scripts/ecu-test-adapter.sh --ensure-scripts

# Sync local workspace to remote (Configurations, Parameters, fmu, .workspace)
./scripts/ecu-test-adapter.sh --sync

# Sync and restart the ECU-TEST configuration (use after changing TCF/TBC/FMU)
./scripts/ecu-test-adapter.sh --sync --restart-config
```

## Golden Rules

1. **Always use absolute paths** — relative paths cause failures.
2. **Start ECU-TEST first** — all other capabilities require a running instance.
3. **One capability at a time** — ECU-TEST processes requests sequentially; wait for one to finish before starting the next.
4. **Decompose requirements carefully** — split into precondition, action, postcondition. Keep it minimal.
5. **Check reports after execution** — use the report capability to understand failures.
6. **Do NOT include "Start the simulation" steps** — if the TBC has `AutoSimulation=True` and `START-OPTION=1`, the FMI tool and simulation start automatically when the configuration is loaded. Adding a "Start the simulation" action step will fail.
7. **Configuration must be started before execution** — the `execute.py` script handles this automatically by calling `start_configuration()` with the TCF/TBC before running the test.
8. **Sync workspace before first execution** — in remote mode, always run `--sync` before the first test execution in a session to ensure the remote has the latest Configurations, Parameters, and FMU files. Use `--sync --restart-config` if the configuration is already running and you need ECU-TEST to pick up the changes.
9. **Compile FMU on remote AFTER sync** — `--sync` overwrites the compiled FMU with the local source-only version. Always compile on the remote after syncing, then restart the configuration. See [FMU Sync & Build Order](#fmu-sync--build-order).
10. **Never use simulation-lifecycle or variable-storage language in package steps** — the AI script generator will emit broken code. See [Test Step Phrasing Rules](#test-step-phrasing-rules).
11. **Remote scripts are auto-provisioned** — the adapter automatically uploads scripts from `.kiro/skills/ecu-test/scripts/remote/` to the configured `remote_scripts_dir` on the remote instance before the first remote execution. Run `--ensure-scripts` to force a re-check.
12. **Never invoke SSH directly to work around the adapter** — the adapter handles SSH key path resolution, permission fixes, and remote script provisioning. Always use the adapter for all remote operations.


## FMU Sync & Build Order

The `--sync` command uploads the local `fmu/` directory to the remote, which **overwrites the compiled FMU** with the local source-only version (produced by `exportToFMU`). The correct sequence is:

1. `--sync` (uploads Configurations, Parameters, source-only FMU, .workspace)
2. Compile FMU on remote: `ssh ... "cd <remote_workspace>/fmu && python3 compile_fmu.py"`
3. Stop configuration via REST API
4. Wait 5 seconds
5. Start configuration via REST API
6. Wait 15 seconds for FMU to load and port to connect
7. Verify configuration status is `FINISHED` with `action: Start`

**Never** start or restart the configuration between sync and FMU compilation. The FMI port will fail if the FMU has no compiled binaries for the target platform.

**Do NOT use `--sync --restart-config`** when the FMU needs recompiling — it restarts the config before the FMU is compiled. Use `--sync` alone, then compile, then manually restart.


## Test Step Phrasing Rules

The AI test script generator interprets natural language steps literally. Certain phrases cause it to emit broken code.

> **Note:** For project-specific signal names and threshold values, activate the `#ecu-test-project-config` steering.

### NEVER use these phrases in package steps:

| Forbidden phrase | Why it fails |
|---|---|
| "Start the simulation" | AutoSimulation handles this; explicit calls fail |
| "Set simulation time to ..." | Interpreted as StartSimulation |
| "Wait 0 seconds for simulation to initialize" | Interpreted as needing to start simulation |
| "Store value as ..." / "save as variable" | Generates undefined variable references |
| "Compare to previous reading" | Generates cross-step variable references that aren't scoped |
| "Read X at t=0 then read X at t=5 and compare" | Same variable scoping issue |

### ALWAYS use these patterns instead:

**For preconditions (verify connectivity):**
- ✅ "Read signal <ModelKey>.<SignalName> to confirm model is connected."

**For time-based actions:**
- ✅ "Wait N seconds for <condition>."
- ✅ "Wait N seconds."

**For postconditions (assertions):**
- ✅ "Verify <SignalName> is between <min> and <max>."
- ✅ "Verify <SignalName> is not equal to <value>."
- ✅ "Verify <SignalName> equals <value>."
- ✅ "Verify <SignalName> is greater than <value>."

### Testing "value changed over time" without variables:

Instead of comparing two readings (which requires variable storage), use knowledge of the model's initial conditions:
- Know the initial value at t=0
- After waiting N seconds, assert `value > initial_value` to prove it changed
- This avoids cross-step variable references entirely


## Capabilities

| Capability | Script | Guide |
|---|---|---|
| Start ECU-TEST | `scripts/start.py` | [start.md](start.md) |
| Create test package | `scripts/create_package.py` | [create-package.md](create-package.md) |
| Generate test script (AI) | `scripts/generate.py` | [generate.md](generate.md) |
| Execute test case | `scripts/execute.py` | [execute.md](execute.md) |
| Analyze TRF report | `scripts/report.py` | [report.md](report.md) |
| Generate XAM mapping | `scripts/generate_xam.py` | [generate-xam.md](generate-xam.md) |
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

## Remote Setup

The adapter supports two execution modes: **local** (default) and **remote**.

### Configuration

Create `.ecu-test-remote.json` in the project root (see `.ecu-test-remote.json.example`):

```json
{
  "mode": "remote",
  "hostname": "ec2-xx-xx-xx-xx.compute-1.amazonaws.com",
  "username": "ubuntu",
  "key_path": "~/.ssh/ecu-test-key.pem",
  "local_workspace": "/path/to/ecu.test-workspace",
  "remote_workspace": "/opt/ecu-test-workspace",
  "remote_scripts_dir": "/opt/ecu-test-scripts",
  "exe_path": "/usr/bin/ecu.test",
  "license": "YOUR_LICENSE_STRING",
  "tbc_name": "MyBench.tbc",
  "tcf_name": "MyConfig.tcf",
  "ssh_timeout": 30,
  "exec_timeout": 600,
  "transfer_timeout": 300
}
```

> **Note:** `local_workspace` should point to the ecu.test workspace directory (the folder containing `Configurations/`, `Parameters/`, etc.), not the project root.

### Configuration Fields

| Field | Required | Default | Description |
|---|---|---|---|
| `mode` | yes | `local` | Execution mode: `local` or `remote` |
| `hostname` | remote only | — | Public DNS or IP of the remote instance |
| `username` | remote only | `ubuntu` | SSH username |
| `key_path` | remote only | — | Path to SSH private key |
| `local_workspace` | yes | — | Absolute path to local ecu.test workspace |
| `remote_workspace` | no | `/opt/ecu-test-workspace` | Workspace path on remote |
| `remote_scripts_dir` | no | `/opt/ecu-test-scripts` | Script deployment path on remote |
| `exe_path` | no | `/usr/bin/ecu.test` | Path to ecu.test executable on remote |
| `license` | remote only | — | TRACET_LICENSE value for the remote instance |
| `tbc_name` | no | — | TBC filename for config restart (e.g., `MyBench.tbc`) |
| `tcf_name` | no | — | TCF filename for config restart (e.g., `MyConfig.tcf`) |
| `ssh_timeout` | no | `30` | SSH connection timeout in seconds |
| `exec_timeout` | no | `600` | Script execution timeout in seconds |
| `transfer_timeout` | no | `300` | File transfer timeout in seconds |

### SSH Key Path Handling

The adapter automatically resolves `key_path` from multiple formats:

| Format in config | Resolved to |
|---|---|
| `~/.ssh/key.pem` | `$HOME/.ssh/key.pem` |
| `C:\Users\me\.ssh\key.pem` | `/mnt/c/Users/me/.ssh/key.pem` |
| `C:/Users/me/.ssh/key.pem` | `/mnt/c/Users/me/.ssh/key.pem` |
| `/c/Users/me/.ssh/key.pem` (Git Bash) | `/mnt/c/Users/me/.ssh/key.pem` |
| `/mnt/c/Users/me/.ssh/key.pem` | unchanged |

**Permission auto-fix:** SSH keys on Windows mounts (`/mnt/c/...`) always show `0777` permissions, which SSH rejects. The adapter automatically copies the key to a temp location with `chmod 600`.

### Environment Variable Overrides

Environment variables take precedence over the config file:

| Variable | Description |
|---|---|
| `ECU_TEST_MODE` | `local` or `remote` |
| `ECU_TEST_REMOTE_HOST` | Hostname/IP of remote instance |
| `ECU_TEST_REMOTE_USER` | SSH username (default: `ubuntu`) |
| `ECU_TEST_REMOTE_KEY` | Path to SSH private key |
| `ECU_TEST_LOCAL_WORKSPACE` | Local workspace base path |
| `ECU_TEST_REMOTE_WORKSPACE` | Remote workspace path |
| `ECU_TEST_REMOTE_SCRIPTS_DIR` | Remote scripts directory |
| `ECU_TEST_EXE_PATH` | Path to ecu.test executable |
| `ECU_TEST_LICENSE` | TRACET_LICENSE value |
| `ECU_TEST_TBC_NAME` | TBC filename |
| `ECU_TEST_TCF_NAME` | TCF filename |
| `ECU_TEST_SSH_TIMEOUT` | SSH connection timeout in seconds |
| `ECU_TEST_EXEC_TIMEOUT` | Script execution timeout in seconds |
| `ECU_TEST_TRANSFER_TIMEOUT` | File transfer timeout in seconds |

### Infrastructure Deployment

Deploy the remote instance using the CloudFormation template:

```bash
aws cloudformation deploy \
  --template-file infra/ecu-test-ec2.yaml \
  --stack-name ecu-test-remote \
  --parameter-overrides \
    KeyPairName=my-key \
    AllowedSSHCidr="<your-ip>/24" \
    EcuTestDebUrl="<url-to-ecu-test-deb>"
```

After deployment, set up the instance:

```bash
# Get instance IP from stack outputs
INSTANCE_IP=$(aws cloudformation describe-stacks --stack-name ecu-test-remote \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIp`].OutputValue' --output text)

# Remote scripts are auto-provisioned by the adapter on first use.
# To manually force provisioning:
./scripts/ecu-test-adapter.sh --ensure-scripts

# Set the license (use the value from your .ecu-test-remote.json)
ssh -i ~/.ssh/my-key.pem ubuntu@$INSTANCE_IP \
  "echo 'TRACET_LICENSE=<your-license>' | sudo tee -a /etc/environment"
```

### Uploading the ecu.test Workspace

Use the adapter's `--sync` command to upload the workspace:

```bash
./scripts/ecu-test-adapter.sh --sync
```

This uploads `.workspace/`, `Configurations/`, `Parameters/`, and `fmu/` directories and creates the `Packages/` directory on the remote.

### FMU Compilation on Remote

FMUs exported from MATLAB/Simulink using `exportToFMU` with `'BuildConfiguration','source-code'` contain C sources but no compiled binaries. The sources must be compiled for linux64 on the remote instance:

```bash
# Sync workspace (uploads source-only .fmu) then compile on remote:
./scripts/ecu-test-adapter.sh --sync
ssh -i ~/.ssh/my-key.pem ubuntu@$INSTANCE_IP \
  "cd /opt/ecu-test-workspace/fmu && python3 compile_fmu.py"
```

The `compile_fmu.py` script extracts the C sources from the `.fmu`, compiles them with `gcc` for linux64, and repackages the `.fmu` with the compiled shared library.

### Starting ECU-TEST on the Remote Instance

```bash
# Via the adapter (recommended — handles lifecycle check):
./scripts/ecu-test-adapter.sh start.py
```

The adapter passes the configured `exe_path`, `license`, and `remote_workspace` automatically.

### TCF/TBC Path Convention

When configuring or executing via the REST API, use **filenames only** (not full paths) for TCF and TBC:
- ✅ `--tcf 'MyConfig.tcf' --tbc 'MyBench.tbc'`
- ❌ `--tcf '/opt/ecu-test-workspace/Configurations/MyConfig.tcf'`

ECU-TEST resolves these relative to the workspace's `Configurations/` folder.

For `--test-case` (execution), use the **absolute path**:
- ✅ `--test-case "/opt/ecu-test-workspace/Packages/MyTest.pkg"`
