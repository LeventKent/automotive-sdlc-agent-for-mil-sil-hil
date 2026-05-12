---
inclusion: always
---

# FMU Build Requirement — Mandatory for Every Session

## Rule: Always Build a New FMU from the Simulink Model

When the user asks to create, deploy, or test an FMU (or any workflow that involves an FMU), you **MUST** build a fresh FMU from the Simulink model. You are **NEVER** allowed to skip FMU generation by relying on a pre-existing `.fmu` file in the workspace or on the remote instance.

### Required Workflow

1. **Create or update the Simulink model** in MATLAB using the MATLAB MCP tools. The model must implement the equations defined by the requirements.
2. **Generate the FMU artifacts from the model** — since Simulink Coder is not licensed, this means:
   - Extract the model equations from the Simulink model (verify via simulation).
   - Update `build_fmu.py` so its C source code and `modelDescription.xml` match the Simulink model's behavior exactly (same signals, same equations, same initial conditions).
   - If `build_fmu.py` already matches, confirm this explicitly by comparing the model equations to the C source.
3. **Sync the workspace to the remote** (`--sync`).
4. **Build the FMU on the remote** by running `build_fmu.py` on the EC2 instance via SSH.
5. **Restart the ECU-TEST configuration** so it loads the freshly built FMU.

### Why This Matters

- A stale FMU may not reflect the latest requirements or model changes.
- The Simulink model is the source of truth. The FMU must be derived from it every time.
- Skipping the build leads to test results that don't validate the actual model.

### What "Build a New FMU" Means

It does NOT mean simply uploading an existing `.fmu` file. It means:
- The C source in `build_fmu.py` is verified/updated to match the Simulink model.
- `build_fmu.py` is executed on the remote Linux instance to compile a fresh `.so` and package a new `.fmu`.
- The ECU-TEST configuration is restarted to pick up the new binary.

### Never Skip This Step

Even if the FMU file already exists on the remote, you must rebuild it. The only source of truth is the Simulink model created in MATLAB during the current session.
