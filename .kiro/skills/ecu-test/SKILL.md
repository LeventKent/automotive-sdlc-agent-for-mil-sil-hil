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
- For remote mode: SSH key access to the remote EC2 instance and a `.ecu-test-remote.json` config file (see [Remote Setup](#remote-setup)).

## Session Startup: Check for Provisioned EC2 Instance (Remote Mode Only)

When working in **remote mode**, read `.ecu-test-remote.json`** in the project root at the start of the session. If the file exists and contains `"mode": "remote"` with a `hostname`, a remote EC2 instance has already been provisioned and is ready to use — **skip any EC2 provisioning steps** and go straight to using the instance.

The file is written automatically when the EC2 instance is deployed via the CloudFormation stack. It contains:
- `hostname` — the public DNS name of the EC2 instance
- `username` — SSH username (typically `ubuntu`)
- `key_path` — path to the SSH private key (e.g. `~/.ssh/ecu-test-key.pem`)
- `local_workspace` — absolute path to the local ecu.test workspace directory
- `remote_workspace` — path on the remote instance (default: `/opt/ecu-test-workspace`)

The adapter scripts (`ecu-test-adapter.sh`) pick up this config automatically.

## Quick Start

All scripts are invoked through the adapter, which handles local/remote routing automatically:

```bash
# Start ECU-TEST (remote mode skips if already running)
./scripts/ecu-test-adapter.sh start.py --exe-path "/opt/ecu.test/bin/ecu-test"

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
6. **Do NOT include "Start the simulation" steps** — the TBC has `AutoSimulation=True` and `START-OPTION=1`, so the FMI tool and simulation start automatically when the configuration is loaded. Adding a "Start the simulation" action step will always fail with "No relevant signal or function found".
7. **Configuration must be started before execution** — the `execute.py` script handles this automatically by calling `start_configuration()` with the TCF/TBC before running the test. If calling the API directly, ensure `PUT /api/v2/configuration` is called first.
8. **Sync workspace before first execution** — in remote mode, always run `--sync` before the first test execution in a session to ensure the remote has the latest Configurations, Parameters, and FMU files. Use `--sync --restart-config` if the configuration is already running and you need ECU-TEST to pick up the changes.
9. **Build FMU on remote AFTER sync** — `--sync` overwrites the compiled FMU with the local source-only version. Always rebuild on the remote after syncing, then restart the configuration. See [FMU Sync & Build Order](#fmu-sync--build-order).
10. **Never use simulation-lifecycle or variable-storage language in package steps** — the AI script generator will emit broken code. See [Test Step Phrasing Rules](#test-step-phrasing-rules).
11. **Remote scripts are auto-provisioned** — the adapter automatically uploads scripts from `.kiro/skills/ecu-test/scripts/remote/` to `/opt/ecu-test-scripts/` on the EC2 instance before the first remote execution. You do NOT need to manually upload them. If you suspect they are stale, run `--ensure-scripts` to force a re-check.
12. **Never invoke SSH directly to work around the adapter** — the adapter handles SSH key path resolution (Windows → WSL mount translation, permission fixes) and remote script provisioning. Bypassing it leads to permission errors and missing scripts. Always use the adapter for all remote operations.


## FMU Sync & Build Order

The `--sync` command uploads the local `fmu/` directory to the remote, which **overwrites the compiled FMU** with the local source-only version. The correct sequence is:

1. `--sync` (uploads Configurations, Parameters, FMU sources, .workspace)
2. Build FMU on remote: `ssh ... "cd /opt/ecu-test-workspace/fmu && python3 build_fmu.py"`
3. Stop configuration: `PUT /api/v2/configuration` with `action: Stop`
4. Wait 5 seconds
5. Start configuration: `PUT /api/v2/configuration` with `action: Start`
6. Wait 15 seconds for FMU to load and port to connect
7. Verify configuration status is `FINISHED` with `action: Start`

**Never** start or restart the configuration between sync and FMU build. The FMI port will fail with `Port not available or not connected: MDL01` if the FMU has no `binaries/linux64/*.so`.

**Do NOT use `--sync --restart-config`** — it restarts the config before the FMU is rebuilt. Always use `--sync` alone, then build, then manually restart.

```bash
# Correct sequence:
./scripts/ecu-test-adapter.sh --sync
ssh -i "$KEY" ubuntu@$HOST "cd /opt/ecu-test-workspace/fmu && python3 build_fmu.py"
ssh -i "$KEY" ubuntu@$HOST 'curl -s -X PUT -H "Content-Type: application/json" \
  -d "{\"action\":\"Stop\",\"tbc\":{\"tbcPath\":\"fmu.tbc\"},\"tcf\":{\"tcfPath\":\"fmu.tcf\"}}" \
  http://127.0.0.1:5050/api/v2/configuration'
sleep 5
ssh -i "$KEY" ubuntu@$HOST 'curl -s -X PUT -H "Content-Type: application/json" \
  -d "{\"action\":\"Start\",\"tbc\":{\"tbcPath\":\"fmu.tbc\"},\"tcf\":{\"tcfPath\":\"fmu.tcf\"}}" \
  http://127.0.0.1:5050/api/v2/configuration'
sleep 15
```


## Test Step Phrasing Rules

The AI test script generator interprets natural language steps literally. Certain phrases cause it to emit `MDL01.StartSimulation` calls or undefined variable references, which fail at runtime.

### NEVER use these phrases in package steps:

| Forbidden phrase | Why it fails |
|---|---|
| "Start the simulation" | AutoSimulation=True handles this; explicit calls fail |
| "Set simulation time to ..." | Interpreted as StartSimulation |
| "Wait 0 seconds for simulation to initialize" | Interpreted as needing to start simulation |
| "Store value as ..." / "save as variable" | Generates undefined variable references |
| "Compare to previous reading" | Generates cross-step variable references that aren't scoped |
| "Read X at t=0 then read X at t=5 and compare" | Same variable scoping issue |

### ALWAYS use these patterns instead:

**For preconditions (verify connectivity):**
- ✅ "Read signal Plant model.SensorStatus to confirm model is connected."
- ✅ "Read signal Plant model.TemperatureOut to confirm model is connected."

**For time-based actions:**
- ✅ "Wait 8 seconds for temperature to rise."
- ✅ "Wait 5 seconds."

**For postconditions (assertions):**
- ✅ "Verify TemperatureOut is between 0 and 125000 mC."
- ✅ "Verify AlertOut is not equal to 0."
- ✅ "Verify AlertOut equals 0."
- ✅ "Verify SensorStatus equals 1."
- ✅ "Verify TemperatureOut is greater than 20000." (proves value changed from known initial)

### Testing "value changed over time" without variables:

Instead of comparing two readings (which requires variable storage), use knowledge of the model's initial conditions:
- The model starts at TemperatureOut = 20000 at t=0
- After waiting N seconds, assert `value > 20000` to prove it changed
- This avoids cross-step variable references entirely

### Testing "AlertOut = 0 when temp is in range":

Read both signals in the postcondition at a time when temperature is known to be below threshold:
- At t=0, temperature is 20000 (well below 80000)
- Simply verify AlertOut == 0 without conditional logic
- The precondition read confirms the model is connected and temp is below threshold


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
  "local_workspace": "/path/to/ecu.test-integration/ecu.test_agent_fmu_demo",
  "remote_workspace": "/opt/ecu-test-workspace",
  "ssh_timeout": 30,
  "exec_timeout": 600,
  "transfer_timeout": 300
}
```

> **Note:** `local_workspace` should point to the ecu.test workspace directory (the folder containing `Configurations/`, `Parameters/`, etc.), not the project root.

### SSH Key Path Handling

The adapter automatically resolves `key_path` from multiple formats commonly encountered on Windows:

| Format in config | Resolved to (in WSL/Git Bash) |
|---|---|
| `~/.ssh/key.pem` | `$HOME/.ssh/key.pem` |
| `C:\Users\me\.ssh\key.pem` | `/mnt/c/Users/me/.ssh/key.pem` |
| `C:/Users/me/.ssh/key.pem` | `/mnt/c/Users/me/.ssh/key.pem` |
| `/c/Users/me/.ssh/key.pem` (Git Bash) | `/mnt/c/Users/me/.ssh/key.pem` |
| `/mnt/c/Users/me/.ssh/key.pem` | `/mnt/c/Users/me/.ssh/key.pem` (unchanged) |

**Permission auto-fix:** SSH keys on Windows mounts (`/mnt/c/...`) always show `0777` permissions, which SSH rejects. The adapter automatically copies the key to `/tmp/.ecu-test-ssh-key-<uid>` with `chmod 600`. This is transparent and requires no user action.

> **Tip:** You can use any of the above formats in `.ecu-test-remote.json`. The adapter handles the translation.

Or use environment variables (take precedence over config file):

| Variable | Description |
|---|---|
| `ECU_TEST_MODE` | `local` or `remote` |
| `ECU_TEST_REMOTE_HOST` | Hostname/IP of remote EC2 |
| `ECU_TEST_REMOTE_USER` | SSH username (default: `ubuntu`) |
| `ECU_TEST_REMOTE_KEY` | Path to SSH private key |
| `ECU_TEST_LOCAL_WORKSPACE` | Local workspace base path |
| `ECU_TEST_REMOTE_WORKSPACE` | Remote workspace path (default: `/opt/ecu-test-workspace`) |
| `ECU_TEST_SSH_TIMEOUT` | SSH connection timeout in seconds (default: `30`) |
| `ECU_TEST_EXEC_TIMEOUT` | Script execution timeout in seconds (default: `600`) |
| `ECU_TEST_TRANSFER_TIMEOUT` | File transfer timeout in seconds (default: `300`) |

### Infrastructure Deployment

Deploy the remote EC2 instance using the CloudFormation template:

```bash
aws cloudformation deploy \
  --template-file infra/ecu-test-ec2.yaml \
  --stack-name ecu-test-remote \
  --parameter-overrides \
    KeyPairName=ecu-test-key \
    AllowedSSHCidr="<your-ip>/16" \
    EcuTestDebUrl="https://files.tracetronic.de/d/69f0752af57b469d9a1a/files/?p=%2F2026.1.3%2Fecu.test-2026.1.3_runner.deb&dl=1"
```

> **Important:** Use ecu.test **2026.1.x** (not 2026.2) — the license `TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc` only covers 2026.1.

After deployment, set up the instance:

```bash
# Get instance IP from stack outputs
INSTANCE_IP=$(aws cloudformation describe-stacks --stack-name ecu-test-remote \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIp`].OutputValue' --output text)

# Remote scripts are auto-provisioned by the adapter on first use.
# To manually force provisioning (e.g., after updating scripts):
./scripts/ecu-test-adapter.sh --ensure-scripts

# Set the license
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP \
  "echo 'TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc' | sudo tee -a /etc/environment"
```

> **Note:** You no longer need to manually `scp` scripts to the remote. The adapter's `ensure_remote_scripts()` function handles this automatically before the first remote command execution. It compares local and remote script counts and uploads if needed.

### Uploading the ecu.test Workspace

The full workspace must be uploaded to `/opt/ecu-test-workspace/` on the remote instance:

```bash
scp -i ~/.ssh/ecu-test-key.pem -r \
  ecu.test-integration/ecu.test_agent_fmu_demo/.workspace \
  ecu.test-integration/ecu.test_agent_fmu_demo/Configurations \
  ecu.test-integration/ecu.test_agent_fmu_demo/Parameters \
  ecu.test-integration/ecu.test_agent_fmu_demo/fmu \
  ubuntu@$INSTANCE_IP:/opt/ecu-test-workspace/
```

Create the Packages directory:
```bash
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP "mkdir -p /opt/ecu-test-workspace/Packages"
```

### FMU Cross-Compilation for Linux

#### Option A: With Simulink Coder/Compiler (if licensed)

```matlab
exportToFMU('TemperatureMonitoringSystem', ...
    'FMIVersion', '2.0', ...
    'FMUType', 'CS', ...
    'CreateModelReport', 'on', ...
    'SaveDirectory', fullfile(pwd, 'ecu.test-integration/ecu.test_agent_fmu_demo/fmu'));
```

Then cross-compile on the remote instance (the exported FMU contains C sources):

```bash
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP "
  sudo apt-get install -y gcc unzip zip
  cd /opt/ecu-test-workspace/fmu
  mkdir -p /tmp/fmu_build
  unzip -o TemperatureMonitoringSystem.fmu -d /tmp/fmu_build
  cd /tmp/fmu_build/sources
  gcc -shared -fPIC -o TemperatureMonitoringSystem.so *.c -I. -lm
  mkdir -p /tmp/fmu_build/binaries/linux64
  cp TemperatureMonitoringSystem.so /tmp/fmu_build/binaries/linux64/
  cd /tmp/fmu_build
  zip -r /opt/ecu-test-workspace/fmu/TemperatureMonitoringSystem.fmu \
    modelDescription.xml binaries/ sources/
  rm -rf /tmp/fmu_build
"
```

#### Option B: Without Simulink Coder (hand-coded FMU)

If only base MATLAB + Simulink are licensed, use the build script:

```bash
# Upload and run on remote:
scp -i ~/.ssh/ecu-test-key.pem \
  ecu.test-integration/ecu.test_agent_fmu_demo/fmu/build_fmu.py \
  ubuntu@$INSTANCE_IP:/opt/ecu-test-workspace/fmu/

ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP \
  "cd /opt/ecu-test-workspace/fmu && python3 build_fmu.py"
```

Or generate source-only locally and compile on remote:
```bash
# Local: generate FMU with source (no binary)
python ecu.test-integration/ecu.test_agent_fmu_demo/fmu/build_fmu.py --source-only

# Upload to remote
scp -i ~/.ssh/ecu-test-key.pem \
  ecu.test-integration/ecu.test_agent_fmu_demo/fmu/TemperatureMonitoringSystem.fmu \
  ubuntu@$INSTANCE_IP:/opt/ecu-test-workspace/fmu/

# Compile on remote
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP \
  "cd /opt/ecu-test-workspace/fmu && python3 build_fmu.py"
```

> **Important:** The FMU shared library must export ALL FMI2 functions (even as stubs) because ECU-TEST's `fmpy` resolves all symbols regardless of capability flags. See `build_fmu.py` for the complete list.

### Starting ECU-TEST on the Remote Instance

ECU-TEST must be started with the `--workspaceDir` flag and the `TRACET_LICENSE` environment variable:

```bash
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP "
  export TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc
  /usr/bin/ecu.test --start-web-api --restApiPort=5050 --workspaceDir=/opt/ecu-test-workspace &
"
```

Or via the adapter (which handles the lifecycle check):
```bash
./scripts/ecu-test-adapter.sh start.py
```

### Remote Script Environment Variable

The remote scripts need the ApiClient path set:
```
ECU_TEST_API_CLIENT_PATH=/opt/ecu.test-2026.1/Templates/ApiClient
```

This is required for `create_package.py`, `generate.py`, and `report.py`.

### TCF/TBC Path Convention

When configuring or executing via the REST API, use **filenames only** (not full paths) for TCF and TBC:
- ✅ `--tcf 'fmu.tcf' --tbc 'fmu.tbc'`
- ❌ `--tcf '/opt/ecu-test-workspace/Configurations/fmu.tcf'`

ECU-TEST resolves these relative to the workspace's `Configurations/` folder.

For `--test-case` (execution), use the **absolute path**:
- ✅ `--test-case "/opt/ecu-test-workspace/Packages/TM-601.pkg"`
