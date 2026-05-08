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

# Copy remote scripts
scp -i ~/.ssh/ecu-test-key.pem -r .kiro/skills/ecu-test/scripts/remote/* \
  ubuntu@$INSTANCE_IP:/opt/ecu-test-scripts/

# Fix script directory ownership (created as root by cloud-init)
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP "sudo chown ubuntu:ubuntu /opt/ecu-test-scripts"

# Set the license
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP \
  "echo 'TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc' | sudo tee -a /etc/environment"
```

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

The FMU must first be generated from the Simulink model using MATLAB (via the MATLAB MCP tools or manually):

```matlab
exportToFMU('TemperatureMonitoringSystem', ...
    'FMIVersion', '2.0', ...
    'FMUType', 'CS', ...
    'CreateModelReport', 'on', ...
    'SaveDirectory', fullfile(pwd, 'ecu.test-integration/ecu.test_agent_fmu_demo/fmu'));
```

FMUs exported from MATLAB/Simulink on macOS or Windows contain only `win64` and/or `aarch64-darwin` binaries. The remote Linux EC2 instance needs a `linux64` shared library. The FMU includes C sources that must be compiled on the target:

```bash
ssh -i ~/.ssh/ecu-test-key.pem ubuntu@$INSTANCE_IP "
  # Install build tools (if not already present)
  sudo apt-get install -y gcc unzip zip

  # Download FMI2 headers
  mkdir -p /tmp/fmi2
  curl -sL https://raw.githubusercontent.com/modelica/fmi-standard/v2.0.4/headers/fmi2Functions.h -o /tmp/fmi2/fmi2Functions.h
  curl -sL https://raw.githubusercontent.com/modelica/fmi-standard/v2.0.4/headers/fmi2FunctionTypes.h -o /tmp/fmi2/fmi2FunctionTypes.h
  curl -sL https://raw.githubusercontent.com/modelica/fmi-standard/v2.0.4/headers/fmi2TypesPlatform.h -o /tmp/fmi2/fmi2TypesPlatform.h

  # Extract, compile, repackage
  cd /opt/ecu-test-workspace/fmu
  FMU_NAME=TemperatureMonitoringSystem_win64
  mkdir -p /tmp/fmu_build
  unzip -o \${FMU_NAME}.fmu -d /tmp/fmu_build
  cd /tmp/fmu_build/sources
  gcc -shared -fPIC -o TemperatureMonitoringSystem.so \
    TemperatureMonitoringSystem.c TemperatureMonitoringSystem_data.c \
    TemperatureMonitoringSystem_fmu.c RTWCG_FMU_util.c rt_nonfinite.c \
    -I. -I/tmp/fmi2 -lm
  mkdir -p /tmp/fmu_build/binaries/linux64
  cp TemperatureMonitoringSystem.so /tmp/fmu_build/binaries/linux64/
  cd /tmp/fmu_build
  zip -r /opt/ecu-test-workspace/fmu/\${FMU_NAME}.fmu \
    modelDescription.xml binaries/ sources/ model.png documentation/
  rm -rf /tmp/fmu_build /tmp/fmi2
"
```

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
