# MATLAB Skill Versions — Comparison Against Upstream

**Last verified:** 2026-08-21
**Upstream source:** [matlab/simulink-agentic-toolkit](https://github.com/matlab/simulink-agentic-toolkit) (latest release: v2026.08.19)
**Local skills path:** `.kiro/skills/`

## Version Summary

| Skill | Local Version | Upstream Version | Status |
|-------|:---:|:---:|--------|
| building-simulink-models | 1.1 | 1.4 | OUTDATED — 3 versions behind |
| simulating-simulink-models | 1.1 | 1.2 | OUTDATED — 1 version behind |
| testing-simulink-models | 1.2 | 2.0 | OUTDATED — major version behind |
| specifying-mbd-algorithms | 1.0 | 1.1 | OUTDATED — 1 version behind |
| specifying-plant-models | 1.0 | 1.1 | OUTDATED — 1 version behind |
| generate-requirement-drafts | 2.1 | 2.2 | OUTDATED — 1 version behind |
| filing-bug-reports | 1.0 | 1.2 | OUTDATED — 2 versions behind |

**Verdict: All 7 local skills are behind upstream.** The most significant gaps are `testing-simulink-models` (local v1.2 vs upstream v2.0 — the skill was substantially reworked to support persistent Simulink Test cases alongside ephemeral Gherkin tests) and `building-simulink-models` (v1.1 vs v1.4 — now includes `model_check` validation).

## Manifest Schema Drift

The local manifests use an older manifest field naming convention:

| Field | Local (old) | Upstream (current) |
|-------|-------------|-------------------|
| Schema version | `schema_version` | `schema-version` |
| Tool dependencies | `requires-tools` | `required-tools` |
| Skill dependencies | `requires-skills` | `required-skills` |
| Product dependencies | `requires-products` | `required-products` |
| License | `MathWorks BSD-3-Clause` (string) | URL to license file |
| Human description | (absent) | `human-description` field present |

The upstream manifests also include `optional-products` for skills that can leverage additional toolboxes.

## Tool Dependency (requires-tools) Comparison

### building-simulink-models

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| model_edit | model_edit | Yes |
| model_overview | model_overview | Yes |
| model_read | model_read | Yes |
| model_query_params | model_query_params | Yes |
| model_resolve_params | model_resolve_params | Yes |
| — | **model_check** | MISSING locally |

**Note:** Upstream v1.4 added `model_check` (structural validation tool). The local SKILL.md doesn't reference this tool since it pre-dates the addition.

### simulating-simulink-models

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| (empty) | (empty) | Yes |

**Note:** Both declare no tool dependencies. The skill teaches `sim()`/`parsim` patterns via `evaluate_matlab_code` but doesn't call Simulink-specific MCP tools directly.

### testing-simulink-models

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| model_test | model_test | Yes |
| — | **model_overview** | MISSING locally |
| — | **model_read** | MISSING locally |

**Note:** Upstream v2.0 explicitly declares `model_overview` and `model_read` as dependencies. The local SKILL.md step 1 already tells agents to use these tools ("Use model_overview and model_read on the target subsystem") but they are not listed in the manifest.

### specifying-mbd-algorithms

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| model_overview | model_overview | Yes |
| model_read | model_read | Yes |
| model_query_params | model_query_params | Yes |
| **model_resolve_params** | — | EXTRA locally |

**Note:** Upstream v1.1 dropped `model_resolve_params` from required-tools (likely because the skill only reads/overviews, doesn't need to resolve variable references). Local still lists it.

### specifying-plant-models

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| model_overview | model_overview | Yes |
| model_read | model_read | Yes |
| model_query_params | model_query_params | Yes |
| **model_resolve_params** | — | EXTRA locally |
| — | **model_test** | MISSING locally |

**Note:** Upstream v1.1 added `model_test` (for test plan validation) and removed `model_resolve_params`.

### generate-requirement-drafts

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| model_overview | model_overview | Yes |
| model_read | model_read | Yes |
| model_query_params | model_query_params | Yes |
| model_resolve_params | model_resolve_params | Yes |
| evaluate_matlab_code | evaluate_matlab_code | Yes |

**Note:** Tool lists match between local and upstream. The upstream manifest additionally adds `optional-products: [Requirements Toolbox]`.

### filing-bug-reports

| Local `requires-tools` | Upstream `required-tools` | Match? |
|---|---|---|
| evaluate_matlab_code | evaluate_matlab_code | Yes |

**Note:** Tool lists match.

## SKILL.md Content vs Manifest Consistency

Checking whether the SKILL.md text references tools that are NOT listed in the manifest:

| Skill | Tools used in SKILL.md but NOT in manifest |
|-------|----------------------------------------------|
| building-simulink-models | `evaluate_matlab_code` (Stateflow API fallback) — intentional, it's a secondary path |
| simulating-simulink-models | None (uses evaluate_matlab_code implicitly via sim() but doesn't call model-specific MCP tools) |
| testing-simulink-models | `model_overview`, `model_read` — referenced in workflow step 1 but absent from manifest |
| specifying-mbd-algorithms | `evaluate_matlab_code`, `web_search` — used in workflow steps but not in manifest |
| specifying-plant-models | `web_search`, `read_web_page` — used for domain research but not in manifest |
| generate-requirement-drafts | None — all referenced tools are listed |
| filing-bug-reports | None — all referenced tools are listed |

## Upstream Skill Catalog Changes

Since the local copy was taken, the upstream repo has reorganized:
- `testing-simulink-models` moved from "Model-Based Design Core" to "Verification, Validation, and Test"
- Several new skills added that don't exist locally:
  - `configuring-block-policy` (MBD core)
  - `curating-library-kg` (MBD core)
  - `managing-simulink-projects` (MBD core)
  - `setup-custom-libraries` (MBD core)
  - `building-architecture-models` (MBSE)
  - `checking-model-compliance` (VVT)
  - `resolve-design-errors` (VVT)
  - `inject-faults` (VVT)
  - `manage-safety-analysis` (VVT)
  - `author-modeladvisor-checks` (VVT)
  - `authoring-simulink-inputs` (Simulation)
  - `create-sdi-run` (Simulation)
  - `simulink-single-precision-conversion` (Code Gen)
  - `simulink-use-c-function-block` (Modeling)
  - `simulink-linearize` (Control)
  - `simulink-frequency-response` (Control)
  - `simulink-control-motors` (Control)

## Reference Files Drift

| Skill | Local `reference-files` | Upstream `reference-files` |
|-------|---|---|
| building-simulink-models | `reference/stateflow.md`, `reference/system-composer.md`, `reference/simscape.md` | `references/stateflow.md`, `references/system-composer.md`, `references/simscape.md` |

**Note:** Upstream renamed `reference/` to `references/` (plural). This may cause file resolution issues if the toolkit expects the upstream path convention.

## Recommendations

1. **Update all 7 skills** by re-copying from the latest upstream `skills-catalog/`. This is the simplest path — MathWorks skills should be treated as an upstream dependency, not forked.

2. **Priority updates:**
   - `testing-simulink-models` (v1.2 → v2.0) — significant functionality addition (persistent Simulink Test cases)
   - `building-simulink-models` (v1.1 → v1.4) — adds `model_check` for structural validation post-edit

3. **Manifest format migration:** When updating, the field naming will change from underscore to hyphenated convention. Verify Kiro's manifest parser handles `required-tools` vs `requires-tools`.

4. **Toolkit path:** The local `tools.json` reference in `mcp.json` should point to a fresh clone of the toolkit. Run `setupAgenticToolkit("update")` in MATLAB or re-clone the repo to get the latest tools alongside skills.

## How to Update

```bash
# Clone or update the upstream toolkit
cd /path/to/simulink-agentic-toolkit
git pull origin main

# Copy skills to .kiro/skills/ (replace existing)
for skill in building-simulink-models simulating-simulink-models specifying-mbd-algorithms specifying-plant-models generate-requirement-drafts filing-bug-reports; do
  cp -R skills-catalog/model-based-design-core/$skill/ .kiro/skills/$skill/
done

# testing-simulink-models moved to a different catalog group
cp -R skills-catalog/verification-validation-and-test/testing-simulink-models/ .kiro/skills/testing-simulink-models/
```

After updating, verify skills load correctly in Kiro.
