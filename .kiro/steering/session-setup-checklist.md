---
inclusion: manual
---

# Session Setup Checklist

Use this checklist at the start of any session involving MATLAB model creation, FMU export, or ECU-TEST execution. The goal is to verify all prerequisites without user interaction.

## 1. MATLAB MCP Server

- [ ] Check `matlab-models/matlab-mcp-core-server-win64.exe` exists
- [ ] If missing: download from `https://github.com/matlab/matlab-mcp-core-server/releases/latest/download/matlab-mcp-core-server-win64.exe`
- [ ] Verify MATLAB responds: call `mcp_matlab_detect_matlab_toolboxes`
- [ ] Note: only MATLAB + Simulink are licensed. No Simulink Coder/Compiler.

## 2. Remote EC2 Instance (ECU-TEST)

Read `.ecu-test-remote.json` for connection details:
- `hostname`: EC2 public DNS
- `username`: SSH user (typically `ubuntu`)
- `key_path`: path to SSH private key
- `remote_workspace`: `/opt/ecu-test-workspace`

### 2.1 SSH Connectivity
```bash
ssh -i "<key_path>" -o StrictHostKeyChecking=no <username>@<hostname> "echo OK"
```

### 2.2 ECU-TEST Installation
```bash
ssh ... "which ecu.test || echo NOT_INSTALLED"
```

If NOT_INSTALLED, install:
```bash
ssh ... "sudo apt-get update && sudo apt-get install -y libsdl1.2debian libgtk-3-0t64 libpcre2-32-0 libsm6 libnotify4 libjpeg62 libopenjp2-7 libgif7 libwebpmux3 libsndfile1 libportaudio2 libxtst6"
ssh ... "sudo curl -fSL -o /tmp/ecu-test.deb 'https://files.tracetronic.de/d/69f0752af57b469d9a1a/files/?p=%2F2026.1.3%2Fecu.test-2026.1.3_runner.deb&dl=1'"
ssh ... "sudo dpkg -i /tmp/ecu-test.deb"
ssh ... "echo 'TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc' | sudo tee -a /etc/environment"
```

> Note: Ubuntu 26.04 needs `libgtk-3-0t64` (not `libgtk-3-0`). The deb is ~800MB.

### 2.3 ECU-TEST Running
```bash
ssh ... "curl -s http://localhost:5050/api/v2/live"
```

Expected: `{"message": "Alive"}`

If not running:
```bash
ssh ... "export TRACET_LICENSE=2060@license01.tracetronic.de@AWS@cz47cbjc && nohup /usr/bin/ecu.test --start-web-api --restApiPort=5050 --workspaceDir=/opt/ecu-test-workspace > /tmp/ecu-test.log 2>&1 &"
```

Wait ~30-45 seconds for startup, then re-check `/api/v2/live`.

### 2.4 Remote Scripts Deployed
```bash
ssh ... "ls /opt/ecu-test-scripts/execute.py"
```

If missing:
```bash
scp -i "<key_path>" -r .kiro/skills/ecu-test/scripts/remote/* <username>@<hostname>:/opt/ecu-test-scripts/
```

### 2.5 Workspace Directories
```bash
ssh ... "ls /opt/ecu-test-workspace/Configurations/fmu.tcf /opt/ecu-test-workspace/fmu/ /opt/ecu-test-workspace/Packages/ 2>&1"
```

If missing, upload:
```bash
scp -r ecu.test-integration/ecu.test_agent_fmu_demo/.workspace <host>:/opt/ecu-test-workspace/
scp -r ecu.test-integration/ecu.test_agent_fmu_demo/Configurations <host>:/opt/ecu-test-workspace/
scp -r ecu.test-integration/ecu.test_agent_fmu_demo/Parameters <host>:/opt/ecu-test-workspace/
scp -r ecu.test-integration/ecu.test_agent_fmu_demo/fmu <host>:/opt/ecu-test-workspace/
ssh ... "mkdir -p /opt/ecu-test-workspace/Packages"
```

### 2.6 FMU Deployed and Compiled
```bash
ssh ... "unzip -l /opt/ecu-test-workspace/fmu/TemperatureMonitoringSystem.fmu | grep linux64"
```

Should show `binaries/linux64/TemperatureMonitoringSystem.so`. If missing, run `build_fmu.py` on remote.

### 2.7 ApiClient Path
The remote scripts need:
```
ECU_TEST_API_CLIENT_PATH=/opt/ecu.test-2026.1/Templates/ApiClient
```

Verify: `ssh ... "ls /opt/ecu.test-2026.1/Templates/ApiClient/ApiClient.py"`

## 3. ECU-TEST Configuration Notes

### TBC/TCF Auto-Start
- TBC has `START-OPTION=1` and `AUTOSTART=1` → FMI tool starts automatically with configuration
- TBC has `AutoSimulation=True` (default) → simulation starts/stops automatically per test
- Therefore: test packages should NOT include a "Start the simulation" action step

### TCF/TBC Path Convention (REST API)
- Use **filenames only** for TCF and TBC: `--tcf 'fmu.tcf' --tbc 'fmu.tbc'`
- Use **absolute paths** for test cases: `--test-case "/opt/ecu-test-workspace/Packages/TM-601.pkg"`

### Configuration Must Be Started Before Execution
The `execute.py` script handles this automatically — it calls `start_configuration()` if the TCF isn't already running. But if calling the REST API directly:
1. `PUT /api/v2/configuration` with `{"action": "Start", "tcf": {"tcfPath": "fmu.tcf"}, "tbc": {"tbcPath": "fmu.tbc"}}`
2. Poll `GET /api/v2/configuration` until `status.key` is `RUNNING`
3. Then `PUT /api/v2/execution` with `{"testCasePath": "/opt/ecu-test-workspace/Packages/TM-601.pkg"}`

## 4. Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| PowerShell mangles quotes in SSH heredocs | Write scripts to files, SCP them, then execute |
| ECU-TEST takes 30-45s to start | Wait and poll `/api/v2/live` |
| `nohup` in SSH doesn't background properly | Command may time out but process still runs; check with `ps aux` |
| FMU cache on remote | Clear `/home/ubuntu/.cache/ecu.test_FMI/` if FMU was rebuilt |
| Configuration 409 (busy) | Wait 10s and retry; `execute.py` handles this automatically |
