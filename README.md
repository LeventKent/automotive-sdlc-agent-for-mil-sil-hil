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
│   └── settings/
│       └── mcp.json                 # MCP server configuration
├── polarion-integration/
│   └── polarion-mcp/               # Polarion MCP server source
├── simulink-agentic-toolkit/       # Cloned from github.com/matlab/simulink-agentic-toolkit
│   └── tools/                      # Runtime tool definitions (referenced by MCP server)
│       └── tools.json              # Extension file for --extension-file arg
├── fmu_export/                     # Generated FMU output
└── README.md                       # This file
```

## License

See [LICENSE](LICENSE) for details.
