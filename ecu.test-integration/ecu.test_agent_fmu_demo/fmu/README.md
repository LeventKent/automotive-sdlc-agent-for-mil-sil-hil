# FMU Directory

This directory holds:

- **`compile_fmu.py`** — Remote compilation script. Extracts C sources from a source-only `.fmu`, compiles for linux64, and repackages with the compiled binary.
- **`*.fmu`** — Generated FMU files (not committed, see `.gitignore`). Produced by `exportToFMU` in MATLAB.

## Workflow

1. In MATLAB, export the Simulink model as a source-only FMU:
   ```matlab
   exportToFMU(modelName, 'FMIVersion','2.0', 'FMUType','CS', 'BuildConfiguration','source-code', 'SaveDirectory', thisDir);
   ```
2. Sync to remote: `./scripts/ecu-test-adapter.sh --sync`
3. Compile on remote: `ssh ... "cd /opt/ecu-test-workspace/fmu && python3 compile_fmu.py"`
4. Restart ECU-TEST configuration to load the compiled FMU.
