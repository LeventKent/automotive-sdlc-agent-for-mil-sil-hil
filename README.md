# Automotive SDLC Agent for MIL/SIL/HIL

An AI-assisted automotive software development lifecycle (SDLC) workflow integrating Polarion ALM, MATLAB/Simulink, and Kiro IDE for Model-in-the-Loop (MIL), Software-in-the-Loop (SIL), and Hardware-in-the-Loop (HIL) development.

## Overview

This project demonstrates an end-to-end automotive development workflow where:

1. **Requirements** are managed in Polarion ALM (system requirements, software requirements, test cases)
2. **Simulink models** are created from requirements using the Simulink Agentic Toolkit
3. **FMU export** packages models as Functional Mock-up Units for co-simulation and deployment
4. **Traceability** links requirements → models → tests across the toolchain

## Prerequisites

### macOS C Compiler (Xcode)

MATLAB requires a C compiler for code generation and FMU export. On macOS, this means installing **Xcode**:

1. Install **Xcode** from the Mac App Store (free, ~12 GB)
2. Open Xcode once and **accept the license agreement** when prompted
3. Verify from terminal:
   ```bash
   sudo xcodebuild -license accept
   xcode-select -p   # Should show /Applications/Xcode.app/Contents/Developer
   ```

> **Note:** The Command Line Tools alone (`xcode-select --install`) provide `clang`, but MATLAB's `mex -setup` requires the full Xcode.app license to be accepted. Without this, FMU export will fail with "Supported compiler not detected."

### MATLAB / Simulink

- **MATLAB R2025b** (or later)
- **Simulink** (included with MATLAB)
- **Simulink Coder** — code generation
- **Simulink Compiler** — FMU export support
- **Embedded Coder** — production code generation
- **FMU Builder for Simulink** — support package (install via Add-On Explorer)

#### Installing FMU Builder for Simulink

1. Open MATLAB
2. Go to **Home > Add-Ons > Get Add-Ons**
3. Search for **"FMU Builder for Simulink"**
4. Click **Install**

Alternatively, from the MATLAB command window:

```matlab
matlab.internal.addons.launchers.showExplorer('tripwire','identifier','FMUBUILDER');
```

### Simulink Agentic Toolkit (MCP Server)

The MATLAB MCP server enables AI-assisted Simulink model creation and manipulation. It is installed from the [simulink-agentic-toolkit](https://github.com/matlab/simulink-agentic-toolkit) repository.

**Installation:**

```bash
# Clone into this project (already done — lives at simulink-agentic-toolkit/)
git clone https://github.com/matlab/simulink-agentic-toolkit.git
```

The `simulink-agentic-toolkit/` folder **must remain in the project** — the MCP server references `tools/tools.json` at runtime for Simulink model editing, reading, testing, and parameter resolution tools.

**MCP Core Server binary:** Installed separately at a location like `/Users/<you>/dev/matlab/matlab-mcp-core-server`. See the [toolkit README](simulink-agentic-toolkit/README.md) for download instructions.

**Configuration** (in `.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "matlab": {
      "command": "/path/to/matlab-mcp-core-server",
      "args": [
        "--matlab-root=/Applications/MATLAB_R2025b.app",
        "--extension-file=/path/to/simulink-agentic-toolkit/tools/tools.json"
      ],
      "autoApprove": [
        "evaluate_matlab_code",
        "run_matlab_file",
        "run_matlab_test_file",
        "check_matlab_code",
        "detect_matlab_toolboxes",
        "model_edit",
        "model_overview"
      ]
    }
  }
}
```

### Polarion ALM Integration (MCP Server)

Connects to Polarion for requirements management and traceability.

**Setup:**

1. Navigate to `polarion-integration/polarion-mcp/`
2. Create a Python virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -e .`
4. Configure environment variables (see `.env.example`):
   - `POLARION_URL` — Polarion server URL
   - `POLARION_USER` — Username
   - `POLARION_TOKEN` — Personal access token
   - `POLARION_CONFIG_PATH` — Path to project config YAML

## Session Workflow (Reproduced Steps)

This section documents the exact workflow performed in the initial session:

### 1. Validate Toolchain Connectivity

```
- Verified MATLAB MCP server connection via detect_matlab_toolboxes
- Confirmed Simulink, Simulink Coder, Simulink Compiler, Embedded Coder available
- Verified Polarion MCP server connection via health_check and list_projects
```

### 2. Retrieve Requirements from Polarion

```
- Listed all work items in project TEMPMON004
- Retrieved TM-509: "Temperature Monitoring System" (top-level system requirement)
- Retrieved child requirements: TM-510 through TM-514 (SWE.2 architectural modules)
```

### 3. Create Simulink Model from TM-509

The model `TemperatureMonitoringSystem.slx` was created with 5 subsystems mapping to Polarion requirements:

| Subsystem | Polarion ID | Description |
|-----------|-------------|-------------|
| Sensor Interface | TM-510 | Simulated temperature sensor (sine + noise) |
| Threshold Monitor | TM-511 | High/low threshold evaluation with alarm output |
| Alert Dispatcher | TM-512 | Priority-weighted alert signal generation |
| Data Logger | TM-513 | Ring buffer simulation via unit delay |
| Application Task | TM-514 | Periodic task scheduler (clock + pulse generator) |

**Model parameters:**
- Solver: Fixed-step discrete
- Step size: 0.1s
- Stop time: 10s
- Thresholds: High > 70°C, Low < 10°C

### 4. Run Simulation

```matlab
simOut = sim('TemperatureMonitoringSystem', 'StopTime', '10');
```

**Results:**
- Temperature range: 23–80°C (mean ~54°C)
- Alert events: 24 out of 101 samples (high threshold breaches)

### 5. Export as FMU

```matlab
exportToFMU('TemperatureMonitoringSystem', ...
    'FMIVersion', '2.0', ...
    'FMUType', 'CS', ...
    'SaveDirectory', fullfile(pwd, 'fmu_export'));
```

Produces `TemperatureMonitoringSystem.fmu` — an FMI 2.0 Co-Simulation unit.

## Project Structure

```
├── .kiro/
│   ├── settings/
│   │   └── mcp.json                 # MCP server configuration
│   ├── skills/
│   │   └── ecu-test/                # ECU-TEST automation skill
│   │       ├── SKILL.md             # Skill definition and remote setup guide
│   │       ├── scripts/
│   │       │   ├── ecu-test-adapter.sh   # Adapter (local/remote routing)
│   │       │   ├── resolve_config.py     # Config resolution helper
│   │       │   ├── adapter_logic.py      # Pure logic (path translation, validation)
│   │       │   ├── remote/               # Linux-adapted scripts for EC2
│   │       │   └── *.py                  # Local scripts
│   │       └── *.md                 # Capability guides
│   └── specs/
│       └── remote-ecu-test-execution/   # Spec-driven design docs
│   └── steering/
│       └── ecu-test-project-config.md   # Project-specific ecu-test knowledge
├── ecu.test-integration/
│   ├── ecu.test_agent_fmu_demo/     # ECU-TEST workspace
│   │   ├── .workspace/             # Workspace config (agent.xml, etc.)
│   │   ├── Configurations/         # TBC and TCF files
│   │   ├── Parameters/FMU/         # XAM signal mapping
│   │   ├── fmu/                    # FMU model files
│   │   └── Packages/               # Generated test packages
│   └── requirements/               # Test case requirements (TM-601..TM-605)
├── infra/
│   └── ecu-test-ec2.yaml           # CloudFormation template for remote EC2
├── polarion-integration/
│   └── polarion-mcp/               # Polarion MCP server source
├── simulink-agentic-toolkit/       # Cloned from github.com/matlab/simulink-agentic-toolkit
├── tests/
│   └── unit/
│       └── test_adapter_logic.py   # Property-based + unit tests
├── .ecu-test-remote.json.example   # Remote config template
└── README.md                       # This file
```

## Remote ECU-TEST Execution

The project supports running ecu.test on a remote EC2 instance via SSH. This decouples the test execution environment from the development machine.

### Architecture

```
Developer Machine (Kiro)          AWS EC2 (Ubuntu 22.04, t3.large)
┌─────────────────────┐           ┌──────────────────────────────┐
│ ecu-test-adapter.sh │──── SSH ──│ remote scripts (configurable)│
│ .ecu-test-remote.json│──── SCP ──│ workspace (configurable)     │
└─────────────────────┘           │ ecu.test + REST API :5050    │
                                  └──────────────────────────────┘
```

### Configuration

All remote execution settings are centralized in `.ecu-test-remote.json` (see `.ecu-test-remote.json.example`):

```json
{
  "mode": "remote",
  "hostname": "ec2-xx-xx-xx-xx.compute-1.amazonaws.com",
  "username": "ubuntu",
  "key_path": "~/.ssh/my-key.pem",
  "local_workspace": "/path/to/ecu.test-workspace",
  "remote_workspace": "/opt/ecu-test-workspace",
  "remote_scripts_dir": "/opt/ecu-test-scripts",
  "exe_path": "/usr/bin/ecu.test",
  "license": "YOUR_LICENSE_STRING",
  "tbc_name": "MyBench.tbc",
  "tcf_name": "MyConfig.tcf"
}
```

### Key Operational Details

1. **ECU-TEST version**: Must match the license. Configure `exe_path` in `.ecu-test-remote.json` to point to the installed binary.

2. **License**: Set the `license` field in `.ecu-test-remote.json`. The adapter passes it as `TRACET_LICENSE` when starting ECU-TEST.

3. **FMU compilation on remote**: FMUs are exported from MATLAB/Simulink as source-only (using `exportToFMU` with `'BuildConfiguration','source-code'`). After syncing to the remote, compile with `python3 compile_fmu.py` which uses `gcc` to build the linux64 shared library.

4. **Workspace sync**: Use `./scripts/ecu-test-adapter.sh --sync` to upload the workspace (`.workspace/`, `Configurations/`, `Parameters/`, `fmu/`) to the remote.

5. **ECU-TEST start**: Use `./scripts/ecu-test-adapter.sh start.py` — the adapter passes `--workspaceDir` and license from config automatically.

6. **Path conventions**:
   - TCF/TBC: use filenames only (configured as `tbc_name`/`tcf_name`) — ECU-TEST resolves from workspace
   - Test case packages: use absolute paths on the remote
   - Package output: use absolute paths on the remote

7. **AI Agent**: The `.workspace/agent.xml` must contain a reachable agent URL for `GenerateViaAi()` to work.

See [SKILL.md](.kiro/skills/ecu-test/SKILL.md) for full setup instructions and the [steering file](.kiro/steering/ecu-test-project-config.md) for project-specific configuration details.

## License

See [LICENSE](LICENSE) for details.
