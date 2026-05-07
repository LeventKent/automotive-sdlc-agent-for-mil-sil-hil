# Create Test Package

Creates an ecu.test package (.pkg) from explicit precondition, action, and postcondition steps.

## When to use

- User wants to create a test package from a requirement
- User provides acceptance criteria or a specification to turn into a test
- User says "create package", "build test case", "transform requirement into test"

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Precondition steps | `--pre-step` | `[]` | Repeat for each precondition. Optional. |
| Action steps | `--action-step` | *(at least one required)* | Repeat for each action/verification step. |
| Postcondition steps | `--post-step` | `[]` | Repeat for each cleanup step. Optional. |
| Output path | `--output` | `.scratch/generated_package.pkg` | Absolute path recommended. Relative paths go to `.scratch/`. |

## Running the script

```bash
python scripts/create_package.py \
  --pre-step "Set the vehicle state to 'D' (driving)." \
  --pre-step "Set vehicle traction standby to 'on'." \
  --action-step "Press the accelerator pedal to 50%%." \
  --action-step "Verify the vehicle reaches more than 50 km/h within 9 seconds." \
  --post-step "Set vehicle traction standby to 'off'." \
  --output "C:\workspace\Packages\my_test.pkg"
```

## Requirement decomposition rules

- **Keep the test minimal.** No generic boilerplate unless the requirement depends on it.
- Every step must be a useful, verifiable test step.
- `precondition`: only setup states that must be true before the test starts.
- `action`: the core test procedure and verification points. At least one action step is required.
- `postcondition`: only cleanup or end-state restoration if the test changes system state.
- Omit any category that is not needed. Empty lists are valid.
- If the requirement is ambiguous, ask the user before proceeding.

## Example

For a requirement:
> When terminal 15 is switched on, the control unit shall transmit CAN message VehicleStatus within 100 ms.

```bash
python scripts/create_package.py \
  --action-step "Switch terminal 15 on." \
  --action-step "Measure the time until CAN message VehicleStatus is first transmitted." \
  --action-step "Verify VehicleStatus is transmitted within 100 ms after terminal 15 is switched on." \
  --output "C:\workspace\Packages\vehicle_status_test.pkg"
```

## Notes

- The script uses the ecu.test ApiClient to create a proper package structure.
- Relative output names are written to the workspace `.scratch` folder.
- Use concise, imperative step text so the package is directly usable inside ecu.test.
