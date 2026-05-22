# End-to-End Workflow

Orchestrates the full workflow from a textual requirement to a fully generated and optionally executed test script.

## When to use

- User wants the full workflow from requirement to generated test
- User says "generate a test from this requirement", "end to end test", "create and generate test", "full test workflow"
- Any request that involves both creating a package specification AND generating the test script

## CRITICAL: All paths must be absolute

**Every file path must be an absolute path.** Relative paths have caused failures in the past.

## Workflow

Execute the following steps **in order**:

### Step 1 — Create the package specification

1. Read the user's requirement and decompose it into `precondition`, `action`, and `postcondition` step lists following the [decomposition rules](create-package.md).
2. Run the create-package script via the adapter:

```bash
./scripts/ecu-test-adapter.sh create_package.py \
  --pre-step "..." \
  --action-step "..." \
  --post-step "..." \
  --output "<ABSOLUTE path to the .pkg file>"
```

3. Confirm the package was created and note its absolute path.

### Step 2 — Configure TCF and generate the test script

1. Run the generate script via the adapter with the **TCF filename** and the **absolute** package path from Step 1:

```bash
./scripts/ecu-test-adapter.sh generate.py \
  --tcf "<TCF filename>" \
  --package "<ABSOLUTE path to the .pkg file from Step 1>"
```

2. Report whether configuration and AI generation succeeded.

### Step 3 (optional) — Execute the test case

Only perform this step if the user wants to run/execute the test.

```bash
./scripts/ecu-test-adapter.sh execute.py \
  --test-case "<ABSOLUTE path to the .pkg file from Step 1>" \
  --tbc "<TBC filename>" \
  --tcf "<TCF filename>"
```

### Step 4 (optional) — Analyze the report

After execution, analyze the TRF report:

```bash
./scripts/ecu-test-adapter.sh report.py \
  --report-path "<ABSOLUTE path to the .trf file from the test report directory>"
```

## Example

For a requirement:
> In state 'vehicle traction standby', the electrified vehicle must reach a velocity of more than
> 50 km/h after at most 9 seconds when the accelerator is pressed 50%.

**Step 1:**
```bash
./scripts/ecu-test-adapter.sh create_package.py \
  --pre-step "Set the vehicle state to 'D' (driving)." \
  --pre-step "Set vehicle traction standby to 'on'." \
  --action-step "Press the accelerator pedal to 50%%." \
  --action-step "Measure the time until the vehicle velocity exceeds 50 km/h." \
  --action-step "Verify the vehicle reaches more than 50 km/h within 9 seconds." \
  --action-step "Release the accelerator pedal." \
  --action-step "Verify the vehicle recuperates (negative drive torque or regenerative braking active)." \
  --post-step "Release the accelerator pedal." \
  --post-step "Set vehicle traction standby to 'off'." \
  --output "/opt/ecu-test-workspace/Packages/ev_traction_test.pkg"
```

**Step 2:**
```bash
./scripts/ecu-test-adapter.sh generate.py \
  --tcf "ElectricVehicle.tcf" \
  --package "/opt/ecu-test-workspace/Packages/ev_traction_test.pkg"
```

**Step 3:**
```bash
./scripts/ecu-test-adapter.sh execute.py \
  --test-case "/opt/ecu-test-workspace/Packages/ev_traction_test.pkg" \
  --tbc "HiL_157.tbc" \
  --tcf "ElectricVehicle.tcf"
```

**Step 4:**
```bash
./scripts/ecu-test-adapter.sh report.py \
  --report-path "/opt/ecu-test-workspace/TestReports/ev_traction_test_2026-05-07/ev_traction_test.trf"
```

## Requirement decomposition rules

- Keep the test minimal. No generic boilerplate unless the requirement depends on it.
- Every step must be a useful, verifiable test step.
- `precondition`: only setup states that must be true before the test starts.
- `action`: the core test procedure and verification points. At least one action step is required.
- `postcondition`: only cleanup or end-state restoration if the test changes system state.
- Omit any category that is not needed. Empty lists are valid.
- If the requirement is ambiguous, ask the user before proceeding.

## Remote Execution Notes

When running in remote mode:

### FMU Generation from MATLAB/Simulink

Before tests can run, the FMU must be exported from the Simulink model:

```matlab
exportToFMU('ModelName', ...
    'FMIVersion', '2.0', ...
    'FMUType', 'CS', ...
    'CreateModelReport', 'on', ...
    'SaveDirectory', fullfile(pwd, 'path/to/workspace/fmu'));
```

The exported FMU contains C sources but only native binaries. It must be cross-compiled for the target platform on the remote instance.

### Pre-flight checklist
1. FMU exported and placed in the workspace `fmu/` folder
2. Workspace synced to remote via `--sync`
3. FMU cross-compiled on remote (see SKILL.md "FMU Cross-Compilation" section)
4. ECU-TEST started (via `./scripts/ecu-test-adapter.sh start.py`)
5. Remote scripts are auto-provisioned — no manual upload needed

### Path conventions (remote)
- `--tcf` and `--tbc`: use **filenames only** (e.g., `MyConfig.tcf`, `MyBench.tbc`)
- `--test-case`: use **absolute path** (e.g., `/opt/ecu-test-workspace/Packages/MyTest.pkg`)
- `--output` for create_package: use **absolute path** on the remote
- `--report-path`: use **absolute path** to the `.trf` file

### AI Generation
- Requires `.workspace/agent.xml` with a reachable AI agent URL and API token
- The agent URL must be reachable from the remote instance (public endpoints work; internal/VPN endpoints do not)
