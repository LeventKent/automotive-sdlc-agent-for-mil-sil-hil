# Execute Test Case

Loads a TBC and TCF configuration in a running ECU-TEST instance, then executes a test case and reports the result.

## When to use

- User wants to run, execute, or start a test case
- User says "run test", "execute test", "execute package", "start test execution"
- A generated package needs to be executed against a test bench

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to test case | `--test-case` | *(required)* | Absolute path to the ECU-TEST package file (.pkg) |
| Path to TBC | `--tbc` | *(required)* | Absolute path to the test bench configuration file (.tbc) |
| Path to TCF | `--tcf` | *(required)* | Absolute path to the test configuration file (.tcf) |
| REST API port | `--port` | `5050` | Must match ECU-TEST's configured port |
| Config timeout (seconds) | `--timeout` | `120` | How long to wait for TBC/TCF to reach RUNNING state |
| Execution timeout (seconds) | `--exec-timeout` | `600` | How long to wait for the test execution to finish |

## Running the script

```bash
python scripts/execute.py \
  --test-case "C:\workspace\Packages\my_test.pkg" \
  --tbc "C:\workspace\Configurations\HiL_157.tbc" \
  --tcf "C:\workspace\Configurations\ElectricVehicle.tcf" \
  --port 5050 \
  --timeout 120 \
  --exec-timeout 600
```

## What the script does

1. **Check reachability** — Verifies ECU-TEST is reachable via `GET /api/v2/live`.
2. **Configure TBC + TCF** — Loads the test bench and test configuration via `PUT /api/v2/configuration` and polls until RUNNING.
3. **Execute test case** — Triggers execution via `PUT /api/v2/execution` with the test case path.
4. **Poll for completion** — Polls `GET /api/v2/execution` until FINISHED or timeout.
5. **Report result** — Returns the test report ID and report directory on success, or an error message on failure.

## Using as a Python module

```python
from execute import run_workflow

result = run_workflow(
    test_case="C:/workspace/Packages/my_test.pkg",
    tbc="C:/workspace/Configurations/HiL_157.tbc",
    tcf="C:/workspace/Configurations/ElectricVehicle.tcf",
)
if result.success:
    print(f"Report ID: {result.test_report_id}")
```

## Notes

- ECU-TEST must already be running (use the start capability first).
- The test report directory is printed on completion — use it with the report capability.
- ECU-TEST can only run one execution at a time. If busy, it returns HTTP 409.
