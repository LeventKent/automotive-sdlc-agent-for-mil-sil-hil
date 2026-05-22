# Generate XAM Mapping

Generates an ecu.test XAM (Master Mapping) file from an FMU's modelDescription.xml. This is run **before** the TCF configuration is started. The script uses the TCF file (that will be started later) as input to check whether the XAM update is needed at all.

## When to use

- Before starting a TCF configuration that references an FMU model
- User says "generate mapping", "update XAM", "regenerate XAM from FMU"
- As part of the end-to-end workflow, before the generate/configure step
- When the FMU has changed and the mapping file needs to be refreshed

## How it decides if an update is needed

The script takes the TCF as input and:
1. Parses the TCF to check if it references an XAM mapping file and an FMU
2. If **no XAM or FMU is referenced** in the TCF → exits with success (no update needed for this config)
3. If both are referenced, compares the existing XAM content with what the FMU would produce
4. If the XAM **already matches** → exits with success ("already up-to-date")
5. If the XAM is **missing or differs** → regenerates it

## Parameters

| Argument | Flag | Default | Notes |
|---|---|---|---|
| Path to TCF | `--tcf` | *(required, or use --fmu)* | Reads XAM path and FMU from the TCF |
| Path to FMU | `--fmu` | *(alternative to --tcf)* | Direct path to the FMU file |
| Output XAM path | `--output` | *(required with --fmu)* | Where to write the XAM file |
| Model key | `--model-key` | Read from TCF | The model key used in mapping items (e.g., `"Plant model"`) |

## Running the script

### From a TCF (recommended)

The script parses the TCF to find the referenced XAM file and FMU automatically:

```bash
python scripts/generate_xam.py \
  --tcf "C:\workspace\Configurations\fmu.tcf"
```

### Direct FMU + output path

```bash
python scripts/generate_xam.py \
  --fmu "C:\workspace\fmu\MyModel.fmu" \
  --output "C:\workspace\Parameters\FMU\mapping.xam" \
  --model-key "Plant model"
```

## What the script does

1. **Parse TCF** (if `--tcf` is used) — checks if the TCF references an XAM mapping file and FMU. If neither is referenced, exits cleanly (no update needed for this configuration).
2. **Resolve FMU path** — locates the FMU file relative to the workspace (checks `fmu/`, root, and `Models/` directories).
3. **Extract modelDescription.xml** — opens the FMU (ZIP archive) and parses the FMI model description.
4. **Compare with existing XAM** — if the XAM file already exists and matches what would be generated, skips writing ("already up-to-date").
5. **Generate XAM** — creates a MAPPING-ITEM with `xaModelSignal` access for each ScalarVariable in the FMU.
6. **Write output** — saves the XAM file at the path referenced in the TCF (or the specified `--output`).

## Output format

The generated XAM contains one `MAPPING-ITEM` per FMU variable:

```xml
<MAPPING-ITEM format-rev="2" xsi:type="mappingItem">
    <ID xsi:type="string">Plant model.VehicleSpeed</ID>
    <DESCRIPTION xsi:type="string">VehicleSpeed</DESCRIPTION>
    <XACCESS format-rev="2" xsi:type="xaModelSignal">
        <MAPPING-ENUM xsi:type="vtabInfoEmpty"/>
        <MODEL-KEY xsi:type="string">Plant model</MODEL-KEY>
        <VARIABLE-PATH xsi:type="string">VehicleSpeed</VARIABLE-PATH>
    </XACCESS>
</MAPPING-ITEM>
```

## Integration with the workflow

This capability should be called **before** `generate.py` (which configures the TCF). The TCF configuration loads the XAM file, so it must be up-to-date at that point.

Typical sequence:
1. `generate_xam.py --tcf ...` — update the XAM from the FMU
2. `generate.py --tcf ... --package ...` — configure TCF and generate test

## Notes

- The script does **not** generate `xaJob` mapping items (StartSimulation/StopSimulation). Only model signal mappings are created.
- Supports FMI 2.0 and FMI 3.0 FMUs (reads `ModelVariables/ScalarVariable` elements).
- The model key defaults to the `dkey` attribute from the TCF's `MODEL-ACCESS/DATA` element.
- All paths must be absolute.
