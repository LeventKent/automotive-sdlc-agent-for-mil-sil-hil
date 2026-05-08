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
│ ecu-test-adapter.sh │──── SSH ──│ /opt/ecu-test-scripts/*.py   │
│ .ecu-test-remote.json│──── SCP ──│ /opt/ecu-test-workspace/     │
└─────────────────────┘           │ /usr/bin/ecu.test (2026.1)   │
                                  │ REST API :5050               │
                                  └──────────────────────────────┘
```

### Key Operational Details

1. **ECU-TEST version**: Use **2026.1.x** (not 2026.2). The license only covers 2026.1.
   - Download: `https://files.tracetronic.de/d/69f0752af57b469d9a1a/` → `2026.1.3/ecu.test-2026.1.3_runner.deb`

2. **License**: `TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc` must be set in the environment before starting ECU-TEST.

3. **FMU cross-compilation**: FMUs from MATLAB contain only Windows/macOS binaries. The C sources inside the FMU must be compiled to `linux64/*.so` on the EC2 instance using `gcc` and FMI2 headers from the modelica/fmi-standard repository.

4. **Workspace upload**: The entire `ecu.test_agent_fmu_demo/` workspace (`.workspace/`, `Configurations/`, `Parameters/`, `fmu/`) must be uploaded to `/opt/ecu-test-workspace/` on the remote.

5. **ECU-TEST start command**: Must include `--workspaceDir=/opt/ecu-test-workspace` to load the workspace configuration, TBC/TCF, and XAM mappings.

6. **Path conventions**:
   - TCF/TBC: use filenames only (`fmu.tcf`, `fmu.tbc`) — ECU-TEST resolves from workspace
   - Test case packages: use absolute paths (`/opt/ecu-test-workspace/Packages/TM-601.pkg`)
   - Package output: use relative paths from workspace (`Packages/TM-601.pkg`)

7. **ApiClient path**: Remote scripts need `ECU_TEST_API_CLIENT_PATH=/opt/ecu.test-2026.1/Templates/ApiClient`

8. **AI Agent**: The `.workspace/agent.xml` must contain a reachable agent URL (e.g., `https://agent.tracetronic.ai/`) for `GenerateViaAi()` to work.

See [SKILL.md](.kiro/skills/ecu-test/SKILL.md) for full setup instructions.

## License

See [LICENSE](LICENSE) for details.
