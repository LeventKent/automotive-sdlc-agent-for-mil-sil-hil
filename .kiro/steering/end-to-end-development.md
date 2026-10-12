---
inclusion: auto
name: Model in the loop software development flow
description: Software development flow to implement and test models using model-in-the-loop based on given requirements.
---

# End-to-End Development

## Overview

This steering file defines a reusable MIL/SIL/HIL development workflow. Because
it uses `inclusion: auto`, it loads automatically whenever you ask to run a
model-in-the-loop project.

Before starting Phase 1, resolve a runtime project context from, in priority
order: values supplied by the user; the referenced requirements; the current
workspace's `.ecu-test-remote.json`, TCF, TBC, XAM, and Simulink model files; and
a focused user question when a required value remains ambiguous. The context
must provide the requirements source, workspace paths, model and FMU names,
TBC/TCF names, ECU-TEST model key, signal mappings, thresholds, and traceability
needed by the requested phases. Derive expected behavior and thresholds from the
requirements rather than examples or generated artifacts. Do not print
credentials, license values, tokens, or private keys while resolving the
context.

To run a project, follow the ordered **End-to-End Workflow** below phase by
phase. Whenever a phase refers to a concrete model value, use the resolved
runtime project context; do not hardcode project-specific values in this file.
If a required value cannot be resolved unambiguously, ask the user for that
value before starting a dependent phase.

## End-to-End Workflow

Run the project by working through the following phases in order. Each phase
names the artifact it consumes (**Input**) and the artifact it produces
(**Produced artifact**). A later phase's input is the previous phase's produced
artifact, so the sequence must be followed top to bottom. Use the resolved
**runtime project context** for every concrete model value referenced by a
phase.

### Phase 1: Create Simulink Model from Requirements

- **Input:** the requirements given by the user via prompt (ex: `requirements in sample-requirements`).
- **Produced artifact:** a Simulink model that satisfies those requirements.

Read every requirement and build a Simulink model
that satisfies them. Follow the `building-simulink-models` skill for the model
construction procedure. Where the work involves the physical/environment plant
portion of the model, follow the `specifying-plant-models` skill; where it
involves the control or monitoring algorithm (model-based design) portion,
follow the `specifying-mbd-algorithms` skill. Use the base model name and other
concrete model details from the runtime project context — do not invent or
hardcode them here.

### Phase 2: Export Source-Only FMU

- **Input:** the Simulink model produced in Phase 1.
- **Produced artifact:** a source-only FMU.

Export the Simulink model to a Functional Mock-up Unit using `exportToFMU` with
**FMI 2.0 Co-Simulation** and `BuildConfiguration` set to `source-code`, so the
FMU ships source rather than a pre-built binary. This is a source-only FMU that
is compiled later on the remote (Phase 4). For the toolbox/support-package
prerequisites, the FMU naming convention, and the mandatory always-build-fresh
policy, see the **MATLAB/Simulink Setup** section of this file. Take the base
model name from the runtime project context.

### Phase 3: Transfer FMU to Remote ECU-TEST Instance

- **Input:** the source-only FMU produced in Phase 2.
- **Produced artifact:** the source-only FMU present on the remote ECU-TEST
  instance.

Transfer the source-only FMU to the remote ECU-TEST instance by syncing the
workspace to the remote using the `ecu-test` skill (`--sync`). Confirm the
transfer succeeded before proceeding: verify that the synced FMU is present at
its expected location on the remote instance (the `--sync` operation reports the
transferred files, and the FMU must be listed and present remotely). Do not
start Phase 4 until the FMU's presence on the remote is confirmed. Use the
remote workspace location from the runtime project context.

### Phase 4: Compile FMU on Remote

- **Input:** the transferred source-only FMU present on the remote (from Phase
  3).
- **Produced artifact:** a compiled FMU on the remote instance.

Compile the transferred source-only FMU on the remote instance using
`compile_fmu.py`, following the `ecu-test` skill. This turns the source-only FMU
into a compiled FMU with a native binary that ECU-TEST can execute. Use the base
model name from the runtime project context so the compiled shared library
matches the FMU naming convention described in the **MATLAB/Simulink Setup**
section.

### Phase 5: Create Test Packages from Requirements

- **Input:** the same requirements resolved at runtime and used in Phase 1.
- **Produced artifact:** the ECU-TEST test packages.

Read every requirement in the requirements directory and create ECU-TEST test
packages that exercise them, following the `ecu-test` skill. Each package maps
requirement behavior to test steps (preconditions, stimuli, and postconditions).
Take the concrete signal names, thresholds, precondition/postcondition phrasing
patterns, and traceability mappings from the runtime project context — do not
embed model-specific values here.

### Phase 6: Generate Test Scripts

- **Input:** the test packages produced in Phase 5.
- **Produced artifact:** the generated test scripts.

Generate the executable test scripts for the test packages, following the
`ecu-test` skill. Each test package yields one or more runnable test scripts that
ECU-TEST drives against the compiled FMU in the next phase. Use the workspace
location and configuration details (TBC, TCF, model key) from the runtime
project context.

### Phase 7: Execute Tests

- **Input:** the generated test scripts produced in Phase 6 and the compiled FMU
  produced in Phase 4.
- **Produced artifact:** the per-script execution results.

Execute the generated test scripts against the compiled FMU, following the
`ecu-test` skill for the ECU-TEST execution procedure and the
`testing-simulink-models` skill for how the model behavior is exercised and
checked. Run **every** generated test script — do not skip any. Each script runs
against the freshly compiled FMU from Phase 4; if the compiled FMU or the
ECU-TEST configuration was changed, restart the configuration first so the run
uses the current binary. Use the workspace, configuration, and signal details
from the runtime project context.

### Phase 8: Produce Summary Report

- **Input:** the per-script execution results produced in Phase 7.
- **Produced artifact:** a summary report of the test execution.

Produce a summary report of the test execution results. At a minimum, the report
records the pass or fail outcome of each executed test script and the aggregate
count of passed and failed tests across the whole run. This report is the final
artifact of the End-to-End Workflow.
### Remote-Operation Failure Handling

Phases 3 (transfer), 4 (compile), and 7 (execute) are remote ECU-TEST
operations that act on the FMU on the remote instance, so they can fail for
reasons outside the local model (a broken sync, a compile error on the remote,
or a failed test run). Handle those failures as follows:

- **The failure is reported to the developer.** When a remote transfer,
  compile, or execute operation fails, surface the failure explicitly — report
  which phase failed and the underlying error the remote operation returned
  (for example, the `--sync` error, the `compile_fmu.py` compile output, or the
  ECU-TEST execution error). Do not silently swallow the error or treat a failed
  remote operation as a success.
- **The workflow halts at the failing phase.** A failed remote operation stops
  the workflow at that phase; do not proceed to the dependent downstream phases.
  Because each of these phases produces an artifact that a later phase consumes,
  continuing past a failure would run a downstream phase against a missing or
  invalid artifact. Concretely: if Phase 3 (transfer) fails, do not compile
  (Phase 4); if Phase 4 (compile) fails, do not execute tests (Phase 7); if
  Phase 7 (execute) fails to run, do not produce a summary report (Phase 8) as
  if the run had completed. Halting lets the developer remediate the root cause
  and then re-run from the failing phase.

Note that a test script reporting a **fail** result is a normal, expected
outcome of a successful Phase 7 execution — it is recorded in the summary report
(Phase 8), not treated as a remote-operation failure. Remote-operation failure
here means the transfer, compile, or execute operation itself could not
complete.

For the operational procedures to diagnose and remediate these remote
failures — re-syncing the workspace, re-running the compile, and restarting the
ECU-TEST configuration — follow the `ecu-test` skill.

## MATLAB/Simulink Setup

This is the reusable reference material for the local MATLAB/Simulink side of the
workflow: the toolboxes and support package you need, how MATLAB MCP tools resolve
paths, how the MCP server is configured per operating system, the FMU naming
convention, and the mandatory always-build-fresh FMU policy with its ordered
build sequence. Concrete model values (the base model name, the workspace
location) live in the **runtime project context** — this section references that
name concept but never hardcodes it.

### Required Toolboxes and Support Package

The following must be installed and licensed for the FMU export workflow to work:

| Component | Kind | Purpose |
|---|---|---|
| MATLAB | Toolbox | Base environment |
| Simulink | Toolbox | Model creation and simulation |
| Simulink Coder | Toolbox (license feature `Real-Time_Workshop`) | C code generation from the model |
| **FMU Builder for Simulink** | Support package (free) | Provides the `exportToFMU` function |

Optionally, these additional toolboxes are available in this workspace but are
**not required** for the FMU export workflow:

| Toolbox | Purpose |
|---|---|
| Embedded Coder | Optimized code generation (not required for FMU export) |
| Simulink Test | Model testing |
| Simulink Coverage | Coverage analysis |
| Stateflow | State machine modeling |

The default MATLAB install locations and binaries per operating system are:

| OS | Default install | Binary |
|---|---|---|
| Windows | `C:\Program Files\MATLAB\R2025b` | `bin\matlab.exe` |
| macOS | `/Applications/MATLAB_R2025b.app` | `bin/matlab` |

The **FMU Builder for Simulink** is a free support package that provides
`exportToFMU`. Install it from within MATLAB:

```matlab
matlab.addons.install('FMU Builder for Simulink')
```

Or open the Add-On Explorer and search for "FMU Builder for Simulink":

```matlab
matlab.addons.explorer
```

Verify the installation succeeded (a non-zero result means `exportToFMU` is
available):

```matlab
exist('exportToFMU', 'file')  % should return 2 or 6
```

### Workspace Path Guidance

MATLAB MCP tools that require a project path resolve the `matlab-models/`
directory from the workspace root **at runtime**. Do **not** hardcode absolute
paths. Determine the workspace root at runtime (for example with `pwd` in the
shell, or the equivalent) and append `matlab-models` to it:

```
project_path = <workspace_root>/matlab-models
```

If the first MATLAB MCP call fails with a "path validation failed: resource not
found" error, run `pwd` in the terminal to discover the actual workspace root and
retry with the resolved path.

### MCP Configuration

The MATLAB MCP server is configured in `.kiro/settings/mcp.json`. The
configuration differs by operating system — use the matching example and replace
`<workspace>` and `<path-to>` placeholders with the actual absolute paths at
configuration time.

#### macOS Configuration

```json
"matlab": {
  "command": "<path-to>/matlab-mcp-core-server",
  "args": [
    "--matlab-root=/Applications/MATLAB_R2025b.app",
    "--extension-file=<path-to>/simulink-agentic-toolkit/tools/tools.json"
  ]
}
```

#### Windows Configuration

```json
"matlab": {
  "command": "<workspace>/matlab-models/matlab-mcp-core-server-win64.exe",
  "args": [
    "--matlab-root=C:\\Program Files\\MATLAB\\R2025b",
    "--initial-working-folder=<workspace>\\matlab-models"
  ]
}
```

### FMU Naming Convention

The FMU filename must match what the TCF references, and the same base model name
must be used consistently across every artifact. All of the following share one
**identical base model name**:

- the TCF `MODEL-FILE`,
- the FMU filename,
- the `modelIdentifier` in `modelDescription.xml`, and
- the compiled shared library produced on the remote (its `binaries/linux64/`
  `.so`).

To control the FMU filename, set the Simulink model name to that base model name
(or rename the exported `.fmu` after export). The concrete base model name for
the current project is given in the **runtime project context** — take it from
there rather than hardcoding it here.

### FMU Build Policy — Mandatory Always Build Fresh

Whenever the user asks to create, deploy, or test an FMU — or runs any workflow
that involves an FMU — you **MUST** build a fresh FMU from the Simulink model.
You are **NEVER** allowed to skip FMU generation by reusing a pre-existing `.fmu`
file, whether that file already exists locally in the workspace or on the remote
instance. Even if the FMU is already present on the remote, regenerate and
recompile it.

The Simulink model is the only source of truth. A stale FMU may not reflect the
latest requirements or model changes, and reusing one produces test results that
do not validate the actual model. Compiling on the remote also guarantees the
binary matches the target platform (linux64) regardless of the developer's local
OS.

### Ordered FMU Workflow (5 steps)

Building a fresh FMU is this exact ordered sequence. This is the canonical FMU
build sequence for the project; the End-to-End Workflow phases reference it.

1. **Create or update the Simulink model** in MATLAB using the MATLAB MCP tools,
   so it implements the behavior defined by the requirements.
2. **Export a source-only FMU** with `exportToFMU`, using FMI 2.0 Co-Simulation
   and a source-code build so the FMU ships C sources and `modelDescription.xml`
   with no compiled binaries:

   ```matlab
   exportToFMU(modelName, ...
       'FMIVersion', '2.0', ...
       'FMUType', 'CS', ...
       'BuildConfiguration', 'source-code', ...
       'SaveDirectory', fullfile(projectRoot, '<workspace-fmu-directory>'));
   ```

   | Parameter | Value | Notes |
   |---|---|---|
   | `FMIVersion` | `'2.0'` | FMI 2.0 Co-Simulation (required by ecu.test) |
   | `FMUType` | `'CS'` | Co-Simulation (not Model Exchange) |
   | `BuildConfiguration` | `'source-code'` | Generates C sources only, no compilation |
   | `SaveDirectory` | project FMU directory | Where the `.fmu` is saved (see runtime project context) |

3. **Sync the workspace to the remote** using the `ecu-test` skill (`--sync`),
   so the source-only FMU is transferred to the remote instance.
4. **Compile the FMU on the remote** by running `compile_fmu.py` on the remote
   instance, following the `ecu-test` skill. This compiles the C sources for
   linux64 and repackages the `.fmu` with the compiled binary.
5. **Restart the ECU-TEST configuration** so it loads the freshly compiled FMU.

**Dependencies:** locally, MATLAB with Simulink Coder plus the "FMU Builder for
Simulink" support package; on the remote, `gcc` (for compilation) and `python3`
(for `compile_fmu.py`).

## Session Pre-Flight Checklist

Run these checks at the start of a session to confirm the workflow's
prerequisites are in place before you begin. Each check lists **how to verify**
it and the **expected pass indicator** that confirms it succeeded. These checks
only confirm readiness — for the underlying setup details (toolboxes, support
package, MCP configuration) see the **MATLAB/Simulink Setup** section rather than
repeating them here. Where a check needs a concrete model value (a workspace
location, the base model name, a configuration file, remote connection details),
take it from the **runtime project context** — this checklist never hardcodes
model-specific values.

### MATLAB Checks

| Check | How to verify | Expected pass indicator |
|---|---|---|
| MCP responsiveness | Call the MATLAB MCP tool `mcp_matlab_detect_matlab_toolboxes` | The tool responds (the MCP server is reachable and answering) |
| Simulink Coder license | `license('test', 'Real-Time_Workshop')` | Returns `1` |
| FMU Builder availability | `exist('exportToFMU', 'file')` | Returns a non-zero result |

### Remote ECU-TEST Checks

Run these against the remote instance over SSH. Take the connection details (key
path, user, host) and the concrete workspace paths, configuration file names, and
base model name from the **runtime project context**; the placeholders below
stand in for those values.

| Check | How to verify | Expected pass indicator |
|---|---|---|
| SSH connectivity | `ssh -i "<key_path>" <user>@<host> "echo OK"` | Prints `OK` |
| `/api/v2/live` liveness | `ssh ... "curl -s http://localhost:<port>/api/v2/live"` | Returns `{"message":"Alive"}` |
| Deployed scripts present | `ssh ... "ls <remote-scripts-dir>/execute.py"` | The deployed script is listed (no "No such file" error) |
| Workspace directories present | `ssh ... "ls <remote-workspace>/Configurations/<TCF> <remote-workspace>/fmu/"` | The configuration and FMU workspace directories are listed |
| Compiled FMU present (linux64 binary) | `ssh ... "unzip -l <remote-workspace>/fmu/<base-model-name>.fmu \| grep linux64"` | A `binaries/linux64/` entry is listed inside the FMU archive |
| ApiClient symlink present | `ssh ... "ls <apiclient-symlink>/Templates/ApiClient/ApiClient.py"` | The `ApiClient.py` file is listed via the symlinked path |

### Known Gotchas

| Symptom | Quick fix |
|---|---|
| ECU-TEST not responding | Wait 30–45s after start, then poll `/api/v2/live` until it returns the alive response |
| Configuration 409 (busy) | Wait ~10s and retry; `execute.py` already handles this transient conflict |
| FMU cache stale | Clear the ecu.test FMI cache directory on the remote |

### Remediation Routing

When a pre-flight check fails, route to the authoritative source for the fix:

- **MATLAB or FMU check failures** → see the **MATLAB/Simulink Setup** section of
  this file (toolboxes, the "FMU Builder for Simulink" support package, MCP
  configuration, and the always-build-fresh FMU workflow).
- **ECU-TEST operational check failures** (SSH, liveness, deployed scripts,
  workspace, compiled FMU, symlink) → follow the `ecu-test` skill for the
  install, start, sync, compile, and restart procedures.
- **Model-detail check failures** (a wrong workspace path, configuration file,
  base model name, or other concrete value) → resolve the value again using the
  runtime project context rules in the Overview.

## Skill References

For detailed operational procedures, reference the skills below **by their exact
name** rather than restating their internal steps here. Each skill lives under
`.kiro/skills/<name>/` and is the authoritative source for the procedure it
covers. The table maps each available skill to a one-line summary and the
End-to-End Workflow phase(s) it supports.

| Skill (exact name) | Covers | Workflow phase(s) |
|---|---|---|
| `building-simulink-models` | Constructing the Simulink model from requirements | Phase 1 |
| `specifying-plant-models` | Specifying the physical/environment plant portion of the model | Phase 1 (plant portion) |
| `specifying-mbd-algorithms` | Specifying the control/monitoring algorithm (model-based design) portion | Phase 1 (algorithm portion) |
| `simulating-simulink-models` | Running Simulink simulations to validate model behavior locally | Phase 1 (model validation) |
| `ecu-test` | ECU-TEST operational procedures — **sync**, **compile**, and **restart** — plus test package/script creation and execution against the compiled FMU on the remote instance | Phases 3, 4, 5, 6, 7 |
| `testing-simulink-models` | Exercising and checking model behavior during test execution | Phase 7 |
| `generate-requirement-drafts` | Drafting requirements (supporting task when requirements need authoring) | Supports Phases 1 & 5 (requirements input) |
| `filing-bug-reports` | Filing a bug report when a defect is found | On defect discovery (any phase) |

The `ecu-test` skill is the single reference for the remote ECU-TEST operational
procedures — **sync** (transfer the workspace/FMU to the remote), **compile**
(build the source-only FMU on the remote via `compile_fmu.py`), and **restart**
(reload the ECU-TEST configuration so it picks up the freshly compiled FMU).
Whenever a workflow phase, the pre-flight checklist, or the remediation routing
points to an ECU-TEST operational step, follow the `ecu-test` skill rather than
duplicating those procedures elsewhere in this file.

