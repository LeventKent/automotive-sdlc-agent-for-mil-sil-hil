# Test Execution Summary Report

**Date:** 2026-05-12  
**Model:** TemperatureMonitoringSystem  
**Platform:** ECU-TEST 2026.1 on EC2 (remote)  
**Configuration:** fmu.tbc / fmu.tcf  

## Model Equations (Simulink → FMU)

```
TemperatureOut = 20000 + 8000·t + 3000·sin(π·t)   [mC]
AlertOut       = 1  if TemperatureOut > 80000, else 0
SensorStatus   = 1  (always healthy)
```

## Results Summary

| Test ID | Requirement | Verdict | Key Observation |
|---------|-------------|---------|-----------------|
| TM-601 | Initial temperature in plausible range [0, 125000] mC | ✅ PASS | TemperatureOut = 28000 mC at t=1s |
| TM-602 | AlertOut transitions to non-zero when temp > 80000 | ✅ PASS | AlertOut = 1.0 after 8s wait |
| TM-603 | SensorStatus remains healthy (=1) | ✅ PASS | SensorStatus = 1.0 after 5s |
| TM-604 | TemperatureOut changes over time (model is dynamic) | ✅ PASS | Temp rose from 20000 → 60000 mC over 5s |
| TM-605 | AlertOut = 0 when temperature within thresholds | ✅ PASS | AlertOut = 0.0 at t=1s (temp = 28000 < 80000) |

**Overall: 5/5 PASSED**

## Workflow Executed

1. **Simulink model created** — `TemperatureMonitoringSystem.slx` built in MATLAB with Clock, Gain, Sum, Sin, Compare-to-Constant, and Data Type Conversion blocks.
2. **Model verified via simulation** — outputs confirmed at t=0, t=5, t=8 matching expected equations.
3. **FMU C source confirmed** — `build_fmu.py` implements identical equations (`20000 + 8000*t + 3000*sin(π*t)`).
4. **Workspace synced** — Configurations, Parameters, FMU sources, and .workspace uploaded to remote.
5. **FMU built on remote** — `build_fmu.py` compiled `TemperatureMonitoringSystem.so` (linux64) and packaged the FMU (6.5 KB).
6. **Configuration restarted** — ECU-TEST loaded the fresh FMU binary (status: FINISHED).
7. **Test packages created** — 5 packages (TM-601 through TM-605) with precondition/action/postcondition steps.
8. **Test scripts generated** — AI-based script generation for all 5 packages.
9. **Tests executed** — all 5 tests ran successfully against the live FMU simulation.
10. **Reports analyzed** — all assertions passed with expected signal values.

## Report Locations (Remote)

- `/opt/ecu-test-workspace/TestReports/TM-601_2026-05-12_095957/TM-601.trf`
- `/opt/ecu-test-workspace/TestReports/TM-602_2026-05-12_100007/TM-602.trf`
- `/opt/ecu-test-workspace/TestReports/TM-603_2026-05-12_100024/TM-603.trf`
- `/opt/ecu-test-workspace/TestReports/TM-604_2026-05-12_100039/TM-604.trf`
- `/opt/ecu-test-workspace/TestReports/TM-605_2026-05-12_100053/TM-605.trf`
