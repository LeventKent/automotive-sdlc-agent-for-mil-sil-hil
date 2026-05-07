# Generate Test Script (AI)

Configures a TCF in a running ECU-TEST instance and then generates a test package using the ecu.test AI agent.

## When to use

- User wants to generate test steps via AI for an existing package
- User says "generate test", "run AI generation", "generate ecu-test package"
- A package has been created (via create-package) and needs its empty blocks filled with test logic

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to TCF | `--tcf` | *(required)* | Absolute path to the test configuration file (.tcf) |
| Path to package | `--package` | *(required)* | Absolute path to the ECU-TEST package file (.pkg) |
| REST API port | `--port` | `5050` | Must match ECU-TEST's configured port |
| TCF timeout (seconds) | `--timeout` | `120` | How long to wait for the TCF to reach RUNNING state |

## Running the script

```bash
python scripts/generate.py \
  --tcf "C:\workspace\Configurations\ElectricVehicle.tcf" \
  --package "C:\workspace\Packages\my_test.pkg" \
  --port 5050 \
  --timeout 120
```

## What the script does

1. **Configure TCF** — Checks if ECU-TEST is reachable, then loads the TCF via `PUT /api/v2/configuration` and polls until the configuration is RUNNING.
2. **Generate package** — Opens the package via the ecu.test ApiClient, iterates over precondition, action, and postcondition blocks, and calls `GenerateViaAi()` on any empty TsBlock test steps.
3. Saves the package and exits with code `0` on success, `1` on failure.

## Using as a Python module

```python
from generate import run_workflow

result = run_workflow(
    tcf="C:/workspace/Configurations/ElectricVehicle.tcf",
    package="C:/workspace/Packages/my_test.pkg",
)
if result.success:
    print(result.message)
```

## Notes

- ECU-TEST must already be running (use the start capability first).
- The AI generation may take time depending on the complexity of the test steps.
- ECU-TEST processes requests sequentially — wait for generation to finish before executing.
