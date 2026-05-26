---
inclusion: manual
#fileMatchPattern: "matlab-models/**"
---

# MATLAB/Simulink Setup

## Workspace Path for MATLAB MCP Tools

When calling MATLAB MCP tools that require `project_path`, resolve the absolute path to the `matlab-models/` directory in this workspace at runtime. Do NOT hardcode paths — use the shell (`pwd`) or equivalent to determine the workspace root, then append `matlab-models`.

Example pattern:
```
project_path = <workspace_root>/matlab-models
```

If the first MATLAB MCP call fails with "path validation failed: resource not found", run `pwd` in the terminal to discover the actual workspace root and retry.

## Common MATLAB Paths

| OS | Default Install | Binary |
|----|----------------|--------|
| Windows | `C:\Program Files\MATLAB\R2025b` | `bin\matlab.exe` |
| macOS | `/Applications/MATLAB_R2025b.app` | `bin/matlab` |

## Required Toolboxes

The following must be installed and licensed:

| Toolbox | License Feature | Purpose |
|---------|----------------|---------|
| MATLAB | — | Base environment |
| Simulink | — | Model creation and simulation |
| Simulink Coder | `Real-Time_Workshop` | C code generation from models |
| **FMU Builder for Simulink** | *(support package, free)* | `exportToFMU` function |

### Installing the FMU Builder Support Package

The "FMU Builder for Simulink" is a free support package that provides `exportToFMU`. Install from within MATLAB:

```matlab
matlab.addons.install('FMU Builder for Simulink')
```

Or open the Add-On Explorer and search for "FMU Builder for Simulink":

```matlab
matlab.addons.explorer
```

Verify installation:
```matlab
exist('exportToFMU', 'file')  % should return 2 or 6
```

### Optional Toolboxes (available in this workspace)

| Toolbox | Purpose |
|---------|---------|
| Embedded Coder | Optimized code generation (not required for FMU export) |
| Simulink Test | Model testing |
| Simulink Coverage | Coverage analysis |
| Stateflow | State machine modeling |

## FMU Export (Source-Only)

Use `exportToFMU` to generate a source-only FMU from the Simulink model. This produces a `.fmu` zip containing C sources and `modelDescription.xml` but **no compiled binaries** — compilation happens on the remote EC2 instance.

```matlab
exportToFMU(modelName, ...
    'FMIVersion', '2.0', ...
    'FMUType', 'CS', ...
    'BuildConfiguration', 'source-code', ...
    'SaveDirectory', fullfile(projectRoot, 'ecu.test-integration/ecu.test_agent_fmu_demo/fmu'));
```

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `FMIVersion` | `'2.0'` | FMI 2.0 Co-Simulation (required by ecu.test) |
| `FMUType` | `'CS'` | Co-Simulation (not Model Exchange) |
| `BuildConfiguration` | `'source-code'` | Generates C sources only, no compilation |
| `SaveDirectory` | `<workspace>/ecu.test-integration/.../fmu` | Where the .fmu file is saved |

### What `exportToFMU` Produces

The output `.fmu` (a zip archive) contains:
- `modelDescription.xml` — FMI-compliant model description with variables, causality, etc.
- `sources/*.c`, `sources/*.h` — Generated C code implementing the model
- No `binaries/` directory (source-only mode)

This is then synced to the remote and compiled there using `compile_fmu.py`.

## FMU Naming Convention

The FMU filename MUST match what the TCF references. All of these must be consistent:
- TCF `MODEL-FILE`: `TemperatureMonitoringSystem.fmu`
- FMU file location: `fmu/TemperatureMonitoringSystem.fmu` (relative to workspace root)
- `modelIdentifier` in modelDescription.xml: `TemperatureMonitoringSystem`
- Shared library name (after remote compilation): `binaries/linux64/TemperatureMonitoringSystem.so`

To control the FMU filename, set the model name in Simulink to match (e.g., name the model `TemperatureMonitoringSystem`), or rename the exported `.fmu` file after export.

## MCP Configuration

The MCP config in `.kiro/settings/mcp.json` should reference the MATLAB MCP server:

### macOS Configuration

```json
"matlab": {
  "command": "<path-to>/matlab-mcp-core-server",
  "args": [
    "--matlab-root=/Applications/MATLAB_R2025b.app",
    "--extension-file=<path-to>/simulink-agentic-toolkit/tools/tools.json"
  ]
}
```

### Windows Configuration

```json
"matlab": {
  "command": "<workspace>/matlab-models/matlab-mcp-core-server-win64.exe",
  "args": [
    "--matlab-root=C:\\Program Files\\MATLAB\\R2025b",
    "--initial-working-folder=<workspace>\\matlab-models"
  ]
}
```

Replace `<workspace>` with the actual absolute workspace path at configuration time.
