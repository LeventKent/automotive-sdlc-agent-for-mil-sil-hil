---
inclusion: manual
---

# ECU-TEST Project Configuration — Temperature Monitoring Demo

> **For operational procedures (sync, compile, restart), see the ecu-test skill.**

This steering file contains project-specific knowledge for the Temperature Monitoring System
FMU demo. It supplements the generic ecu-test skill with signal names, thresholds, and
phrasing guidance specific to this model.

## Model Details

- **Model name**: TemperatureMonitoringSystem
- **FMU type**: FMI 2.0 Co-Simulation
- **Model key in ecu.test**: `Plant model`
- **TBC**: `fmu.tbc` (AutoSimulation=True, START-OPTION=1)
- **TCF**: `fmu.tcf`
- **Workspace**: `ecu.test-integration/ecu.test_agent_fmu_demo/`

## Signal Names

| Signal | Description | Unit | Range |
|--------|-------------|------|-------|
| `Plant model.TemperatureOut` | Current temperature reading | mC (milli-Celsius) | 0–125000 |
| `Plant model.AlertOut` | Alert output (0 = no alert) | — | 0 or non-zero |
| `Plant model.SensorStatus` | Sensor connectivity status | — | 0 or 1 |

## Thresholds

- **High temperature threshold**: 80000 mC (80°C)
- **Low temperature threshold**: 10000 mC (10°C)
- **Initial temperature at t=0**: 20000 mC (20°C)

## Test Step Phrasing (Project-Specific)

### Precondition patterns for this model:
- ✅ "Read signal Plant model.SensorStatus to confirm model is connected."
- ✅ "Read signal Plant model.TemperatureOut to confirm model is connected."

### Postcondition patterns for this model:
- ✅ "Verify TemperatureOut is between 0 and 125000 mC."
- ✅ "Verify AlertOut is not equal to 0."
- ✅ "Verify AlertOut equals 0."
- ✅ "Verify SensorStatus equals 1."
- ✅ "Verify TemperatureOut is greater than 20000." (proves value changed from known initial)

### Testing "AlertOut = 0 when temp is in range":

Read both signals in the postcondition at a time when temperature is known to be below threshold:
- At t=0, temperature is 20000 (well below 80000)
- Simply verify AlertOut == 0 without conditional logic
- The precondition read confirms the model is connected and temp is below threshold

### Testing "value changed over time":

Instead of comparing two readings (which requires variable storage), use knowledge of initial conditions:
- The model starts at TemperatureOut = 20000 at t=0
- After waiting N seconds, assert `value > 20000` to prove it changed

## Remote Instance Details

- **License**: Configured in `.ecu-test-remote.json` (field: `license`)
- **ecu.test version**: 2026.1.x (not 2026.2 — license only covers 2026.1)
- **Download URL pattern**: `https://files.tracetronic.de/d/69f0752af57b469d9a1a/` → `2026.1.3/ecu.test-2026.1.3_runner.deb`
- **ApiClient path on remote**: `/opt/ecu.test/Templates/ApiClient` (symlink — see below)
- **AI Agent URL**: `.workspace/agent.xml` must contain `https://agent.tracetronic.ai/`

### ApiClient Symlink Convention

ecu.test installs to a versioned directory (e.g., `/opt/ecu.test-2026.1/`). The remote scripts resolve the ApiClient from the generic path `/opt/ecu.test/Templates/ApiClient`. The CloudFormation template (`infra/ecu-test-ec2.yaml`) creates a symlink during provisioning:

```
/opt/ecu.test → /opt/ecu.test-2026.1
```

This decouples the scripts from the specific installed version. If the instance was provisioned before this symlink was added, create it manually:

```bash
sudo ln -sfn /opt/ecu.test-2026.1 /opt/ecu.test
```

## Polarion Traceability

| Test Case | Verifies Requirement | Description |
|-----------|---------------------|-------------|
| TM-601 | TM-511 | Temperature initial value at t=0 |
| TM-602 | TM-511 | AlertOut transitions on high threshold |
| TM-603 | TM-511 | AlertOut remains 0 when temp in range |
| TM-604 | TM-513 | Data logger records temperature changes |
| TM-605 | TM-514 | Application task periodic scheduling |
