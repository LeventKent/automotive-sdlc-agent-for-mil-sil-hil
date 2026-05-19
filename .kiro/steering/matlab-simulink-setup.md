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

## MATLAB MCP Core Server

The MATLAB MCP Core Server binary should be at:
```
matlab-models/matlab-mcp-core-server-win64.exe
```

If missing, download from GitHub:
```
https://github.com/matlab/matlab-mcp-core-server/releases/latest/download/matlab-mcp-core-server-win64.exe
```

The MCP config in `.kiro/settings/mcp.json` should reference this binary with args:
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

### macOS Configuration (alternate developer machine)

```json
"matlab": {
  "command": "<path-to>/matlab-mcp-core-server",
  "args": [
    "--matlab-root=/Applications/MATLAB_R2025b.app",
    "--extension-file=<path-to>/simulink-agentic-toolkit/tools/tools.json"
  ]
}
```

## Common MATLAB Paths

| OS | Default Install | Binary |
|----|----------------|--------|
| Windows | `C:\Program Files\MATLAB\R2025b` | `bin\matlab.exe` |
| macOS | `/Applications/MATLAB_R2025b.app` | `bin/matlab` |

## Available Toolboxes (this workspace)

Only **MATLAB** and **Simulink** are installed (license 40830250). The following are NOT available and NOT licensed:
- Simulink Coder (needed for native `slbuild` FMU export)
- Simulink Compiler (needed for the "FMU Builder for Simulink" support package)
- Simulink FMU Builder (standalone product, R2025a+)
- Embedded Coder

### Why `exportToFMU` is not available

`exportToFMU` requires either:
1. **Simulink Compiler** + the "FMU Builder for Simulink" support package (free add-on, but Simulink Compiler license required), OR
2. **Simulink FMU Builder** (standalone licensed product from R2025a+)

Both require additional paid licenses not included in this workspace's MATLAB installation. If these licenses become available in the future, install via:
```matlab
matlab.addons.install('FMU Builder for Simulink')  % requires Simulink Compiler license
```

## FMU Export Without Simulink Coder (Current Approach)

Since no code generation toolbox is licensed, FMUs are hand-coded in C. The model equations are simple enough to express directly. Use the FMU build script at:
```
ecu.test-integration/ecu.test_agent_fmu_demo/fmu/build_fmu.py
```

This script:
1. Generates C source implementing the model equations
2. Generates a compliant `modelDescription.xml`
3. Compiles for linux64 on the remote EC2 instance
4. Packages everything into a valid `.fmu` zip archive

### Critical FMU Requirements for ecu.test

ECU-TEST uses `fmpy` to load FMUs. `fmpy` attempts to resolve ALL FMI2 function symbols from the shared library, regardless of capability flags in modelDescription.xml. The FMU shared library MUST export ALL of these functions (even as stubs returning `fmi2Error`):

**Required (will crash with `undefined symbol` if missing):**
- `fmi2GetTypesPlatform`, `fmi2GetVersion`
- `fmi2Instantiate`, `fmi2FreeInstance`
- `fmi2SetDebugLogging`
- `fmi2SetupExperiment`, `fmi2EnterInitializationMode`, `fmi2ExitInitializationMode`
- `fmi2DoStep`, `fmi2Terminate`, `fmi2Reset`
- `fmi2GetReal`, `fmi2SetReal`, `fmi2GetInteger`, `fmi2SetInteger`
- `fmi2GetBoolean`, `fmi2SetBoolean`, `fmi2GetString`, `fmi2SetString`
- `fmi2GetFMUstate`, `fmi2SetFMUstate`, `fmi2FreeFMUstate`
- `fmi2SerializedFMUstateSize`, `fmi2SerializeFMUstate`, `fmi2DeSerializeFMUstate`
- `fmi2GetDirectionalDerivative`
- `fmi2SetRealInputDerivatives`, `fmi2GetRealOutputDerivatives`
- `fmi2CancelStep`
- `fmi2GetStatus`, `fmi2GetRealStatus`, `fmi2GetIntegerStatus`, `fmi2GetBooleanStatus`, `fmi2GetStringStatus`

### modelDescription.xml Requirements

Must include:
- `<DefaultExperiment startTime="0.0" stopTime="10.0" stepSize="0.01"/>`
- Full `<CoSimulation>` element with all boolean attributes explicitly set
- `initial="calculated"` on output ScalarVariables (not `initial="exact"` with `start` value)

## FMU Naming Convention

The FMU filename MUST match what the TCF references. All four of these must be consistent:
- TCF `MODEL-FILE`: `TemperatureMonitoringSystem.fmu`
- FMU file location: `fmu/TemperatureMonitoringSystem.fmu` (relative to workspace root)
- `modelIdentifier` in modelDescription.xml: `TemperatureMonitoringSystem`
- Shared library name: `binaries/linux64/TemperatureMonitoringSystem.so`
