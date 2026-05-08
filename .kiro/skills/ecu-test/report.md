# Analyze TRF Report

Analyzes an ecu.test report file (.trf) and outputs a markdown table of failed, error, and inconclusive test steps.

## When to use

- User wants to review test results or summarize failures
- User says "analyze report", "show failures", "test feedback", "trf report"
- After test execution, to understand what went wrong

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to report | `--report-path` | *(required)* | Absolute path to the .trf file |

## Running the script

```bash
# Via adapter (handles local/remote routing):
./scripts/ecu-test-adapter.sh report.py \
  --report-path "C:\workspace\TestReports\my_test_2026-05-07\my_test.trf"

# Direct local invocation:
python scripts/report.py \
  --report-path "C:\workspace\TestReports\my_test_2026-05-07\my_test.trf"
```

## Environment override

If the ApiClient cannot be found automatically:

```bash
set ECU_TEST_API_CLIENT_PATH=C:\Program Files\ecu.test 2026.2\Templates\ApiClient
python scripts/report.py --report-path "C:\path\to\report.trf"
```

## What the script does

1. Resolves the ecu.test ApiClient path (env var → Program Files → LocalAppData).
2. Opens the .trf report using the ecu.test Object API.
3. Recursively walks all test steps under each top-level package.
4. Collects steps with result in FAILED, ERROR, or INCONCLUSIVE.
5. Prints a markdown table with columns: Test Step, Result, Value, Expected Value, Comment.

## Output format

```
| Test Step | Result | Value | Expected Value | Comment |
|-----------|--------|-------|----------------|---------|
| Package > Action > Step1 | FAILED | 45 km/h | > 50 km/h | Velocity not reached |
```

If no failed steps are found: `All test steps passed successfully.`

## Notes

- The output keeps full hierarchical test step paths to make failures traceable.
- Comments are escaped for markdown table safety.
