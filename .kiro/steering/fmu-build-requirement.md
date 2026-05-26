---
inclusion: manual
---

# FMU Build Requirement — Mandatory for Every Session

## Rule: Always Build a New FMU from the Simulink Model

When the user asks to create, deploy, or test an FMU (or any workflow that involves an FMU), you **MUST** build a fresh FMU from the Simulink model. You are **NEVER** allowed to skip FMU generation by relying on a pre-existing `.fmu` file in the workspace or on the remote instance.

### Required Workflow

1. **Create or update the Simulink model** in MATLAB using the MATLAB MCP tools. The model must implement the behavior defined by the requirements.
2. **Export the FMU as source-only** using `exportToFMU`:
   ```matlab
   exportToFMU(modelName, ...
       'FMIVersion', '2.0', ...
       'FMUType', 'CS', ...
       'BuildConfiguration', 'source-code', ...
       'SaveDirectory', '<workspace>/ecu.test-integration/ecu.test_agent_fmu_demo/fmu');
   ```
   This produces a `.fmu` containing C sources and `modelDescription.xml` but **no compiled binaries**. The FMU is platform-independent at this stage.
3. **Sync the workspace to the remote** (`--sync`).
4. **Compile the FMU on the remote** by running `compile_fmu.py` on the EC2 instance via SSH:
   ```bash
   ssh ... "cd /opt/ecu-test-workspace/fmu && python3 compile_fmu.py"
   ```
   This compiles the C sources for linux64 and repackages the `.fmu` with the compiled binary.
5. **Restart the ECU-TEST configuration** so it loads the freshly compiled FMU.

### Why This Matters

- A stale FMU may not reflect the latest requirements or model changes.
- The Simulink model is the source of truth. The FMU must be derived from it every time.
- Skipping the build leads to test results that don't validate the actual model.
- Compiling on the remote ensures the binary matches the target platform (linux64) regardless of the developer's local OS.

### What "Build a New FMU" Means

It means:
- `exportToFMU` is called from the Simulink model to produce a source-only `.fmu`.
- The source-only `.fmu` is synced to the remote.
- `compile_fmu.py` is executed on the remote Linux instance to compile a fresh `.so` and repackage the `.fmu`.
- The ECU-TEST configuration is restarted to pick up the new binary.

### Never Skip This Step

Even if the FMU file already exists on the remote, you must regenerate and recompile it. The only source of truth is the Simulink model created in MATLAB during the current session.

### Dependencies

- **Local:** MATLAB with Simulink Coder + "FMU Builder for Simulink" support package
- **Remote:** `gcc` (for compilation), `python3` (for `compile_fmu.py`)
