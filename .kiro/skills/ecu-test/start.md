# Start ECU-TEST

Launches the ECU-TEST application and confirms it is reachable via its REST API.

## When to use

- User wants to launch, start, or boot ECU-TEST
- User says "start ecu-test", "launch ecu-test", "ecu-test starten"
- ECU-TEST is not running and needs to be started before other operations

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to ECU-TEST executable | `--exe-path` | from config `exe_path` | Overrides the configured executable path |
| REST API port | `--port` | `5050` | Must match ECU-TEST's configured port |
| Startup timeout (seconds) | `--timeout` | `60` | How long to wait for the `/live` endpoint to respond |
| Workspace directory | `--workspace-dir` | from config `remote_workspace` | ECU-TEST workspace directory |

## Running the script

```bash
# Via adapter (recommended — passes config values automatically):
./scripts/ecu-test-adapter.sh start.py

# With explicit overrides:
./scripts/ecu-test-adapter.sh start.py \
  --exe-path "/usr/bin/ecu.test" \
  --port 5050 \
  --timeout 60

# Direct local invocation (Windows):
python scripts/start.py \
  --exe-path "C:\Program Files\ecu.test 2026.2\ecu.test.exe" \
  --port 5050 \
  --timeout 60
```

## What the script does

1. Checks if ECU-TEST is already running via `GET /api/v2/live`.
2. If not running, launches `ecu.test.exe --start-web-api --restApiPort <port>` as a detached subprocess.
3. Polls the `/live` endpoint every second until HTTP 200 or timeout.
4. Exits with code `0` on success, `1` on failure.

## Notes

- If ECU-TEST is already running, the script detects this immediately and reports success.
- The ECU-TEST process is launched detached — it continues running after the script exits.
- This capability only starts ECU-TEST. Configuration and execution are separate capabilities.
- **Remote mode**: The adapter checks if ECU-TEST is already running via SSH before invoking start.py. If running, it skips the start and reports success immediately.
