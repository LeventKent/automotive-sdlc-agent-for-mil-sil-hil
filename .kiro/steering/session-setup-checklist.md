---
inclusion: manual
---

# Session Pre-Flight Checklist

Quick verification commands. Run at session start to confirm prerequisites.

## 1. MATLAB

- [ ] MCP responds: `mcp_matlab_detect_matlab_toolboxes`
- [ ] Simulink Coder licensed: `license('test', 'Real-Time_Workshop')` → 1
- [ ] FMU Builder available: `exist('exportToFMU', 'file')` → non-zero

## 2. Remote ECU-TEST (from `.ecu-test-remote.json`)

- [ ] SSH OK: `ssh -i "<key_path>" <user>@<host> "echo OK"`
- [ ] ECU-TEST alive: `ssh ... "curl -s http://localhost:5050/api/v2/live"` → `{"message":"Alive"}`
- [ ] Scripts deployed: `ssh ... "ls /opt/ecu-test-scripts/execute.py"`
- [ ] Workspace dirs exist: `ssh ... "ls /opt/ecu-test-workspace/Configurations/fmu.tcf /opt/ecu-test-workspace/fmu/"`
- [ ] FMU compiled: `ssh ... "unzip -l /opt/ecu-test-workspace/fmu/TemperatureMonitoringSystem.fmu | grep linux64"`
- [ ] ApiClient symlink: `ssh ... "ls /opt/ecu.test/Templates/ApiClient/ApiClient.py"`

## 3. Known Gotchas

| Symptom | Quick Fix |
|---------|-----------|
| ECU-TEST not responding | Wait 30-45s after start, poll `/api/v2/live` |
| Configuration 409 (busy) | Wait 10s and retry; `execute.py` handles this |
| FMU cache stale | Clear `/home/ubuntu/.cache/ecu.test_FMI/` |

## Remediation

If any check fails, consult the authoritative source:

- **MATLAB / FMU issues** → activate `#matlab-simulink-setup`
- **ECU-TEST operations** (install, start, sync, compile) → ecu-test skill
- **Model details** (signals, thresholds, test phrasing) → activate `#ecu-test-project-config`
