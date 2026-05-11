#!/usr/bin/env python3
"""
build_fmu.py — Build TemperatureMonitoringSystem.fmu for linux64.

This script generates a complete FMI 2.0 Co-Simulation FMU from scratch,
including C source code, modelDescription.xml, and compiled linux64 binary.

Run on the remote EC2 instance:
    python3 build_fmu.py

Or run locally to generate source + modelDescription only (no compilation):
    python3 build_fmu.py --source-only

The FMU implements:
    TemperatureOut = 20000 + 8000*t + 3000*sin(pi*t)
    AlertOut = 1.0 if TemperatureOut > 80000 else 0.0
    SensorStatus = 1.0 (always healthy)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

FMU_NAME = "TemperatureMonitoringSystem"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FMU_PATH = os.path.join(OUTPUT_DIR, f"{FMU_NAME}.fmu")

MODEL_DESCRIPTION_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription
  fmiVersion="2.0"
  modelName="{FMU_NAME}"
  guid="{{8c4e810f-3df3-4a00-8276-176fa3c9f003}}"
  description="Temperature Monitoring System - generates temperature signal with alert logic"
  generationTool="build_fmu.py"
  numberOfEventIndicators="0">

  <CoSimulation
    modelIdentifier="{FMU_NAME}"
    canHandleVariableCommunicationStepSize="true"
    canInterpolateInputs="false"
    maxOutputDerivativeOrder="0"
    canRunAsynchronuously="false"
    canBeInstantiatedOnlyOncePerProcess="false"
    canNotUseMemoryManagementFunctions="false"
    canGetAndSetFMUstate="false"
    canSerializeFMUstate="false"
    providesDirectionalDerivative="false"/>

  <DefaultExperiment startTime="0.0" stopTime="10.0" stepSize="0.01"/>

  <ModelVariables>
    <ScalarVariable name="TemperatureOut" valueReference="0" causality="output" variability="continuous" initial="calculated">
      <Real/>
    </ScalarVariable>
    <ScalarVariable name="AlertOut" valueReference="1" causality="output" variability="continuous" initial="calculated">
      <Real/>
    </ScalarVariable>
    <ScalarVariable name="SensorStatus" valueReference="2" causality="output" variability="continuous" initial="calculated">
      <Real/>
    </ScalarVariable>
  </ModelVariables>

  <ModelStructure>
    <Outputs>
      <Unknown index="1"/>
      <Unknown index="2"/>
      <Unknown index="3"/>
    </Outputs>
  </ModelStructure>

</fmiModelDescription>
'''

C_SOURCE = r'''#include <math.h>
#include <string.h>
#include <stdlib.h>

/* FMI 2.0 type definitions */
typedef unsigned int fmi2ValueReference;
typedef double fmi2Real;
typedef int fmi2Integer;
typedef int fmi2Boolean;
typedef char fmi2Char;
typedef const char* fmi2String;
typedef void* fmi2Component;
typedef void* fmi2ComponentEnvironment;
typedef void* fmi2FMUstate;
typedef unsigned int fmi2Status;
typedef size_t fmi2Size;
typedef unsigned char fmi2Byte;

#define fmi2OK 0
#define fmi2Warning 1
#define fmi2Discard 2
#define fmi2Error 3
#define fmi2Fatal 4
#define fmi2True 1
#define fmi2False 0

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

typedef void (*fmi2CallbackLogger)(fmi2ComponentEnvironment, fmi2String, fmi2Status, fmi2String, fmi2String, ...);
typedef void* (*fmi2CallbackAllocateMemory)(size_t, size_t);
typedef void (*fmi2CallbackFreeMemory)(void*);
typedef void (*fmi2StepFinished)(fmi2ComponentEnvironment, fmi2Status);

typedef struct {
    fmi2CallbackLogger logger;
    fmi2CallbackAllocateMemory allocateMemory;
    fmi2CallbackFreeMemory freeMemory;
    fmi2StepFinished stepFinished;
    fmi2ComponentEnvironment componentEnvironment;
} fmi2CallbackFunctions;

typedef struct {
    fmi2Real time;
    fmi2Real temperatureOut;
    fmi2Real alertOut;
    fmi2Real sensorStatus;
    fmi2CallbackFunctions callbacks;
    fmi2String instanceName;
    fmi2Boolean initialized;
} ModelInstance;

static void updateOutputs(ModelInstance* m) {
    /* TemperatureOut = 20000 + 8000*t + 3000*sin(pi*t) */
    m->temperatureOut = 20000.0 + 8000.0 * m->time + 3000.0 * sin(0.5 * 2.0 * M_PI * m->time);
    /* AlertOut = 1 when temp > 80000, else 0 */
    m->alertOut = (m->temperatureOut > 80000.0) ? 1.0 : 0.0;
    /* SensorStatus = always healthy */
    m->sensorStatus = 1.0;
}

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT __attribute__((visibility("default")))
#endif

/* === Required FMI2 Common Functions === */
DLL_EXPORT const char* fmi2GetTypesPlatform(void) { return "default"; }
DLL_EXPORT const char* fmi2GetVersion(void) { return "2.0"; }

DLL_EXPORT fmi2Component fmi2Instantiate(fmi2String instanceName, int fmuType,
    fmi2String fmuGUID, fmi2String fmuResourceLocation,
    const fmi2CallbackFunctions* functions, fmi2Boolean visible, fmi2Boolean loggingOn) {
    ModelInstance* m = (ModelInstance*)functions->allocateMemory(1, sizeof(ModelInstance));
    if (!m) return NULL;
    m->callbacks = *functions;
    m->instanceName = instanceName;
    m->time = 0.0;
    m->initialized = fmi2False;
    updateOutputs(m);
    return (fmi2Component)m;
}

DLL_EXPORT void fmi2FreeInstance(fmi2Component c) {
    if (c) {
        ModelInstance* m = (ModelInstance*)c;
        m->callbacks.freeMemory(m);
    }
}

DLL_EXPORT fmi2Status fmi2SetDebugLogging(fmi2Component c, fmi2Boolean loggingOn,
    size_t nCategories, const fmi2String categories[]) { return fmi2OK; }

DLL_EXPORT fmi2Status fmi2SetupExperiment(fmi2Component c, fmi2Boolean toleranceDefined,
    fmi2Real tolerance, fmi2Real startTime, fmi2Boolean stopTimeDefined, fmi2Real stopTime) {
    ModelInstance* m = (ModelInstance*)c;
    m->time = startTime;
    updateOutputs(m);
    return fmi2OK;
}

DLL_EXPORT fmi2Status fmi2EnterInitializationMode(fmi2Component c) { return fmi2OK; }

DLL_EXPORT fmi2Status fmi2ExitInitializationMode(fmi2Component c) {
    ModelInstance* m = (ModelInstance*)c;
    m->initialized = fmi2True;
    updateOutputs(m);
    return fmi2OK;
}

DLL_EXPORT fmi2Status fmi2Terminate(fmi2Component c) { return fmi2OK; }

DLL_EXPORT fmi2Status fmi2Reset(fmi2Component c) {
    ModelInstance* m = (ModelInstance*)c;
    m->time = 0.0;
    m->initialized = fmi2False;
    updateOutputs(m);
    return fmi2OK;
}

/* === Variable Getters/Setters === */
DLL_EXPORT fmi2Status fmi2GetReal(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, fmi2Real value[]) {
    ModelInstance* m = (ModelInstance*)c;
    size_t i;
    for (i = 0; i < nvr; i++) {
        switch (vr[i]) {
            case 0: value[i] = m->temperatureOut; break;
            case 1: value[i] = m->alertOut; break;
            case 2: value[i] = m->sensorStatus; break;
            default: return fmi2Error;
        }
    }
    return fmi2OK;
}

DLL_EXPORT fmi2Status fmi2SetReal(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2Real value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2GetInteger(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, fmi2Integer value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2SetInteger(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2Integer value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2GetBoolean(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, fmi2Boolean value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2SetBoolean(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2Boolean value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2GetString(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, fmi2String value[]) { return fmi2OK; }
DLL_EXPORT fmi2Status fmi2SetString(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2String value[]) { return fmi2OK; }

/* === Co-Simulation Interface === */
DLL_EXPORT fmi2Status fmi2DoStep(fmi2Component c, fmi2Real currentCommunicationPoint,
    fmi2Real communicationStepSize, fmi2Boolean noSetFMUStatePriorToCurrentPoint) {
    ModelInstance* m = (ModelInstance*)c;
    m->time = currentCommunicationPoint + communicationStepSize;
    updateOutputs(m);
    return fmi2OK;
}

DLL_EXPORT fmi2Status fmi2SetRealInputDerivatives(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2Integer order[], const fmi2Real value[]) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2GetRealOutputDerivatives(fmi2Component c, const fmi2ValueReference vr[],
    size_t nvr, const fmi2Integer order[], fmi2Real value[]) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2CancelStep(fmi2Component c) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2GetStatus(fmi2Component c, int s, int* value) { return fmi2Discard; }
DLL_EXPORT fmi2Status fmi2GetRealStatus(fmi2Component c, int s, fmi2Real* value) { return fmi2Discard; }
DLL_EXPORT fmi2Status fmi2GetIntegerStatus(fmi2Component c, int s, fmi2Integer* value) { return fmi2Discard; }
DLL_EXPORT fmi2Status fmi2GetBooleanStatus(fmi2Component c, int s, fmi2Boolean* value) { return fmi2Discard; }
DLL_EXPORT fmi2Status fmi2GetStringStatus(fmi2Component c, int s, fmi2String* value) { return fmi2Discard; }

/* === FMU State Management (stubs required by fmpy) === */
DLL_EXPORT fmi2Status fmi2GetFMUstate(fmi2Component c, fmi2FMUstate* state) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2SetFMUstate(fmi2Component c, fmi2FMUstate state) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2FreeFMUstate(fmi2Component c, fmi2FMUstate* state) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2SerializedFMUstateSize(fmi2Component c, fmi2FMUstate state, size_t* size) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2SerializeFMUstate(fmi2Component c, fmi2FMUstate state, fmi2Byte serializedState[], size_t size) { return fmi2Error; }
DLL_EXPORT fmi2Status fmi2DeSerializeFMUstate(fmi2Component c, const fmi2Byte serializedState[], size_t size, fmi2FMUstate* state) { return fmi2Error; }

/* === Directional Derivatives (stub) === */
DLL_EXPORT fmi2Status fmi2GetDirectionalDerivative(fmi2Component c,
    const fmi2ValueReference vUnknown_ref[], size_t nUnknown,
    const fmi2ValueReference vKnown_ref[], size_t nKnown,
    const fmi2Real dvKnown[], fmi2Real dvUnknown[]) { return fmi2Error; }
'''


def build_fmu(source_only: bool = False) -> str:
    """Build the FMU. Returns path to the created .fmu file."""
    tmp_dir = tempfile.mkdtemp(prefix="fmu_build_")
    src_dir = os.path.join(tmp_dir, "sources")
    bin_dir = os.path.join(tmp_dir, "binaries", "linux64")
    os.makedirs(src_dir)
    os.makedirs(bin_dir)

    # Write modelDescription.xml
    md_path = os.path.join(tmp_dir, "modelDescription.xml")
    with open(md_path, "w") as f:
        f.write(MODEL_DESCRIPTION_XML)

    # Write C source
    src_path = os.path.join(src_dir, f"{FMU_NAME}.c")
    with open(src_path, "w") as f:
        f.write(C_SOURCE)

    if source_only:
        # Just package source + modelDescription (no binary)
        if os.path.exists(FMU_PATH):
            os.remove(FMU_PATH)
        with zipfile.ZipFile(FMU_PATH, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(md_path, "modelDescription.xml")
            z.write(src_path, f"sources/{FMU_NAME}.c")
        shutil.rmtree(tmp_dir)
        print(f"FMU created (source only): {FMU_PATH}")
        return FMU_PATH

    # Compile for linux64
    so_path = os.path.join(bin_dir, f"{FMU_NAME}.so")
    compile_cmd = [
        "gcc", "-shared", "-fPIC",
        "-o", so_path,
        src_path,
        "-lm",
    ]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Compilation failed:\n{result.stderr}", file=sys.stderr)
        shutil.rmtree(tmp_dir)
        sys.exit(1)

    print(f"Compiled: {so_path}")

    # Package FMU
    if os.path.exists(FMU_PATH):
        os.remove(FMU_PATH)
    with zipfile.ZipFile(FMU_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(md_path, "modelDescription.xml")
        z.write(src_path, f"sources/{FMU_NAME}.c")
        z.write(so_path, f"binaries/linux64/{FMU_NAME}.so")

    shutil.rmtree(tmp_dir)
    size_kb = os.path.getsize(FMU_PATH) / 1024
    print(f"FMU created: {FMU_PATH} ({size_kb:.1f} KB)")
    return FMU_PATH


def main():
    parser = argparse.ArgumentParser(description=f"Build {FMU_NAME}.fmu")
    parser.add_argument(
        "--source-only", action="store_true",
        help="Generate source + modelDescription only (no compilation)"
    )
    args = parser.parse_args()
    build_fmu(source_only=args.source_only)


if __name__ == "__main__":
    main()
