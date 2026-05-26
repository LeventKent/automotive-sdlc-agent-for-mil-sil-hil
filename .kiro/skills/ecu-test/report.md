# Analyze TRF Report

Analyzes an ecu.test report file (.trf) and outputs a markdown table of **all** test steps (by default), or a filtered subset.

## When to use

- User wants to review test results or summarize all steps
- User says "analyze report", "show results", "show failures", "test feedback", "trf report"
- After test execution, to understand the full test outcome

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to report | `--report-path` | *(required)* | Absolute path to the .trf file |
| Filter results | `--filter` | *(none — all steps)* | Space-separated list of result types to include (e.g. `FAILED ERROR INCONCLUSIVE PASSED NONE`) |

## Running the script

```bash
# All test steps (default):
python scripts/report.py \
  --report-path "C:\workspace\TestReports\my_test_2026-05-07\my_test.trf"

# Only failed/error/inconclusive steps:
python scripts/report.py \
  --report-path "C:\workspace\TestReports\my_test_2026-05-07\my_test.trf" \
  --filter FAILED ERROR INCONCLUSIVE

# Via adapter (handles local/remote routing):
./scripts/ecu-test-adapter.sh report.py \
  --report-path "/opt/ecu-test-workspace/TestReports/my_test.trf"
```

## Environment override

If the ApiClient cannot be found automatically:

```bash
set ECU_TEST_API_CLIENT_PATH=C:\Program Files\ecu.test 2026.x\Templates\ApiClient
python scripts/report.py --report-path "C:\path\to\report.trf"
```

## What the script does

1. Resolves the ecu.test ApiClient path (env var → Program Files → LocalAppData).
2. Opens the .trf report using the ecu.test Object API.
3. Recursively walks all test steps under each top-level package.
4. Collects **all** test steps (or only those matching `--filter` if specified).
5. Prints a markdown table with columns: Test Step, Result, Value, Expected Value, Comment.

## Output format

```
| Test Step | Result | Value | Expected Value | Comment |
|-----------|--------|-------|----------------|---------|
| Package > Precondition > Step1 | PASSED | | | |
| Package > Action > Step2 | PASSED | 52 km/h | > 50 km/h | |
| Package > Action > Step3 | FAILED | 45 km/h | > 50 km/h | Velocity not reached |
```

If no steps are found: `No test steps found.`

## Saving the report

After generating the markdown table, save it to `ecu.test-integration/reports/` as a `.md` file named after the test (e.g. `TM-601-report.md`). Do not store raw `.trf` files locally — only the markdown summary belongs in this directory.

## Notes

- The output keeps full hierarchical test step paths to make steps traceable.
- Comments are escaped for markdown table safety.
- To get the previous behavior (only failures), use `--filter FAILED ERROR INCONCLUSIVE`.
