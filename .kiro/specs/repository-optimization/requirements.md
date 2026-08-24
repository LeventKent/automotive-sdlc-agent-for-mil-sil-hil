# Repository Optimization Requirements

## Introduction

This document captures all identified optimization points from a full repository scan of the `automotive-sdlc-agent-for-mil-sil-hil` project. The goal is to clean up the repository, consolidate overlapping configurations, remove dead/outdated content, fix security concerns, and reorganize agent configurations (skills vs steering) to ensure the project runs cleanly in a local environment with a MATLAB license.

### Key Design Decisions

- **Skills** = reusable procedural capabilities (HOW to do something, tool invocations, scripts, workflows)
- **Steering** = contextual knowledge injected into sessions (WHAT to know, project-specific facts, constraints, policies). All steering files in this project use `inclusion: manual` — they are explicitly activated by the user, not auto-loaded.
- **MATLAB skills sit on top of MCP tools** — the skills provide workflow guidance and guardrails for the underlying MATLAB MCP server tools. They are authored by MathWorks and should be treated as an upstream dependency.

---

## Area 1: MCP Configuration Cleanup

### Problem

The `.kiro/settings/mcp.json` contains hardcoded user-specific paths (`/Users/levkent/...`), an exposed JWT token in plaintext, and references to a `simulink-agentic-toolkit` path that is gitignored (meaning the path won't resolve for new clones).

A duplicate MCP config exists at `polarion-integration/temp-monitor/.kiro/settings/mcp.json` with the same hardcoded paths and exposed token.

### Requirement 1.1: Remove Hardcoded User Paths from MCP Config

**Acceptance Criteria:**
1. THE mcp.json SHALL use relative paths or environment variable placeholders instead of absolute user-specific paths (e.g., `/Users/levkent/...`)
2. THE matlab MCP server command SHALL reference a relative or configurable path that works across developer machines
3. THE polarion MCP server command SHALL use a relative path (`./polarion-integration/polarion-mcp/.venv/bin/python`) consistently

### Requirement 1.2: Remove Exposed Credentials from MCP Config

**Acceptance Criteria:**
1. THE `POLARION_TOKEN` value SHALL be replaced with a placeholder (e.g., `"YOUR_POLARION_TOKEN"`) in the committed config
2. A `.env.example` or comment SHALL document how to set the actual token via environment variable or local override
3. THE mcp.json SHALL reference environment variables for sensitive values where possible

### Requirement 1.3: Consolidate Duplicate MCP Configs

**Acceptance Criteria:**
1. THE duplicate MCP config at `polarion-integration/temp-monitor/.kiro/settings/mcp.json` SHALL be removed or replaced with documentation pointing to the root config
2. IF the temp-monitor sub-project needs its own config, IT SHALL use relative paths and no exposed credentials

### Requirement 1.4: Fix simulink-agentic-toolkit Reference

**Acceptance Criteria:**
1. THE `--extension-file` argument in the matlab MCP config SHALL use a path that is resolvable relative to the workspace
2. THE README SHALL document that `simulink-agentic-toolkit/` must be cloned into the project (it is gitignored)
3. A setup script or clear instructions SHALL exist for first-time setup of the MATLAB MCP server binary path

---

## Area 2: Steering Files Consolidation

### Problem

Four steering files exist with significant content overlap. All use `inclusion: manual` (user must explicitly activate them). The overlap creates confusion about which file to activate and risks content diverging when one is updated but not the other.

| Steering File | Size | Overlap With |
|---|---|---|
| `session-setup-checklist.md` | Large | ecu-test SKILL.md, ecu-test-project-config |
| `ecu-test-project-config.md` | Large | session-setup-checklist, ecu-test SKILL.md |
| `fmu-build-requirement.md` | Medium | matlab-simulink-setup |
| `matlab-simulink-setup.md` | Medium | fmu-build-requirement |

### Requirement 2.1: Merge fmu-build-requirement into matlab-simulink-setup

**Acceptance Criteria:**
1. The "Always Build a New FMU" policy and its workflow steps SHALL be merged as a section within `matlab-simulink-setup.md`
2. `fmu-build-requirement.md` SHALL be deleted after merge
3. The merged file SHALL retain the mandatory language ("you MUST build a fresh FMU") as a clearly marked policy section
4. References in other files to `fmu-build-requirement.md` SHALL be updated to point to the new location

### Requirement 2.2: Reduce session-setup-checklist to Verification-Only

**Acceptance Criteria:**
1. `session-setup-checklist.md` SHALL contain only a compact list of verification commands (one-liner checks)
2. Full remediation procedures (installation steps, ECU-TEST startup commands) SHALL be removed — they are maintained in the ecu-test SKILL.md
3. Each check item SHALL link to the authoritative source for remediation (skill or steering file)
4. The file SHALL be under 50 lines — a quick pre-flight reference, not a setup guide

### Requirement 2.3: Remove Duplication from ecu-test-project-config

**Acceptance Criteria:**
1. Operational procedures (FMU compilation commands, configuration restart commands) SHALL be removed from `ecu-test-project-config.md` — they belong in the skill
2. The file SHALL contain ONLY project-specific knowledge: signal names, thresholds, test step examples, Polarion mapping, deployment-specific instance details
3. A note at the top SHALL say: "For operational procedures, see the ecu-test skill"

---

## Area 3: MATLAB Skills Double-Check (Skills on Top of MCPs)

### Problem

Eight skills exist:
1. `building-simulink-models` — MathWorks-authored (v1.1) — layers on `model_edit`, `model_overview`, `model_read`, `model_query_params`, `model_resolve_params`
2. `simulating-simulink-models` — MathWorks-authored (v1.1) — layers on `evaluate_matlab_code` (sim workflow)
3. `testing-simulink-models` — MathWorks-authored (v1.2) — layers on `model_test`
4. `specifying-mbd-algorithms` — MathWorks-authored (v1.0) — spec-writing guidance, uses `model_overview`, `model_read`, `web_search`
5. `specifying-plant-models` — MathWorks-authored (v1.0) — spec-writing guidance, uses `model_overview`, `model_read`, `web_search`
6. `generate-requirement-drafts` — MathWorks-authored (v2.1) — layers on `evaluate_matlab_code` (slreq API)
7. `filing-bug-reports` — MathWorks-authored (v1.0) — generic defect documentation
8. `ecu-test` — Project-specific (comprehensive) — layers on bash scripts / SSH adapter

**Key insight:** Skills 1-7 are from the Simulink Agentic Toolkit. They provide workflow structure, guardrails, and best practices **on top of** the raw MATLAB MCP tools. The MCP tools (`model_edit`, `model_test`, `evaluate_matlab_code`, etc.) are the execution layer; the skills are the knowledge layer that tells the agent WHEN and HOW to use those tools correctly.

**What needs checking:**
- Are the skill versions current with the latest `simulink-agentic-toolkit` release?
- Do the `manifest.yaml` files correctly declare their MCP tool dependencies (`requires-tools`)?
- Are there skills that don't map to any MCP tool (pure guidance) — and should those be steering instead?
- Is the `filing-bug-reports` skill relevant to this project's core workflow?

### Requirement 3.1: Verify MATLAB Skills Against Toolkit Source

**Acceptance Criteria:**
1. Each of the 7 MathWorks skills SHALL be compared against the latest `simulink-agentic-toolkit` repository to confirm they are up-to-date
2. Any local drift (modifications made after copying from toolkit) SHALL be identified and either committed upstream or documented as intentional overrides
3. The `manifest.yaml` in each skill SHALL correctly list `requires-tools` matching the MCP tools the skill actually uses
4. The `toolkit: simulink-agentic-toolkit` declaration in manifests SHALL be verified to actually correlate with the cloned toolkit at `simulink-agentic-toolkit/tools/tools.json`

### Requirement 3.2: Classify MATLAB Skills by Function

**Acceptance Criteria:**

Skills that wrap MCP tools with workflow guidance (KEEP as skills):
- `building-simulink-models` — wraps `model_edit` with layout_mode, naming conventions, operation chaining, domain-specific rules → **KEEP**
- `simulating-simulink-models` — wraps `evaluate_matlab_code` for sim() with guardrails on SimulationInput/Output → **KEEP**
- `testing-simulink-models` — wraps `model_test` with Gherkin syntax reference, draft mode guidance → **KEEP**
- `generate-requirement-drafts` — wraps `evaluate_matlab_code` for slreq API with EARS patterns → **KEEP**

Skills that are pure specification guidance (EVALUATE for steering migration):
- `specifying-mbd-algorithms` — does not invoke MCP tools directly; provides spec-writing templates and review gates → **EVALUATE**: could be steering if specs are not being actively generated in sessions
- `specifying-plant-models` — same pattern as above → **EVALUATE**: same consideration
- `filing-bug-reports` — generic defect documentation, no MCP tool dependency → **EVALUATE**: remove if not used in this project's workflow

### Requirement 3.3: Document Skill-MCP Layering

**Acceptance Criteria:**
1. A brief section in README (or a new `docs/skill-architecture.md`) SHALL explain the layering: MCP tools provide execution, skills provide workflow intelligence on top
2. Each skill's relationship to its underlying MCP tools SHALL be clear from the manifest
3. For new developers: it SHALL be obvious that you need BOTH the MATLAB MCP server configured AND the skills installed for the full workflow to function

---

## Area 3B: ECU-TEST Steering vs Skill Collision

### Problem

The ecu-test configuration is split across **1 skill + 3 steering files** with significant overlap and unclear boundaries:

| Content | In Skill (`ecu-test/SKILL.md`) | In Steering |
|---------|------|-----------|
| Script invocation mechanics (adapter, CLI) | ✅ | ❌ |
| Test step phrasing rules | ✅ (generic rules) | ✅ `ecu-test-project-config.md` (project examples) |
| Signal names, thresholds | ❌ | ✅ `ecu-test-project-config.md` |
| FMU build mandate | ❌ | ✅ `fmu-build-requirement.md` |
| FMU export instructions | ❌ | ✅ `matlab-simulink-setup.md` |
| Remote compilation steps | ✅ (in FMU Sync section) | ✅ `ecu-test-project-config.md` + `session-setup-checklist.md` |
| Remote instance details (version, license, URLs) | ✅ (in Remote Setup) | ✅ `ecu-test-project-config.md` |
| Prerequisite checks | ❌ | ✅ `session-setup-checklist.md` |
| TCF/TBC conventions | ✅ | ✅ `ecu-test-project-config.md` + `session-setup-checklist.md` |

**The collision:** Remote instance details, FMU compilation steps, and TCF/TBC conventions appear in BOTH the skill and steering files. A developer reading one doesn't know the other exists. Worse, if one is updated and the other isn't, they diverge.

**Design principle:** Since all steering files are `inclusion: manual`, they are only loaded when explicitly activated. The skill is loaded when ecu-test work is triggered. This means:
- The **skill** must be self-sufficient for execution mechanics (it's always loaded when needed)
- The **steering** provides supplementary project-specific context (only loaded on request)

### Requirement 3B.1: Define Clear Boundary Between ecu-test Skill and Steering

**Acceptance Criteria:**

The split SHALL be:

**SKILL (`ecu-test/SKILL.md`) — "How to operate ecu.test":**
- Adapter usage patterns (all `--sync`, `--upload`, `--download`, script routing)
- Script invocation syntax and arguments
- Golden rules (absolute paths, sequential execution, start-first)
- FMU Sync & Build Order (operational procedure)
- Test step phrasing rules (generic patterns, never-use list)
- Remote setup configuration schema (`.ecu-test-remote.json` fields)
- Capability table (which script does what)

**STEERING (`ecu-test-project-config.md`) — "What this project's model looks like":**
- Model-specific signal names (`Plant model.TemperatureOut`, etc.)
- Model-specific thresholds (80000 mC, 10000 mC, etc.)
- Project-specific test step examples (phrasing for this model)
- Polarion traceability mapping (TM-601 → TM-511, etc.)
- Remote instance specifics that are deployment-dependent (license string, ecu.test version, download URL, ApiClient symlink path)

### Requirement 3B.2: Eliminate Duplicate Content

**Acceptance Criteria:**
1. Remote compilation steps SHALL appear in exactly ONE place — the skill (since it's the operational reference)
2. TCF/TBC path conventions SHALL appear in exactly ONE place — the skill
3. The steering SHALL NOT repeat operational procedures; it SHALL only provide project-specific VALUES that the skill procedures operate on
4. Cross-references SHALL be added: skill says "see steering for model-specific signal names", steering says "see ecu-test skill for execution procedures"

### Requirement 3B.3: Justify and Consolidate Remaining Steering Files

**Acceptance Criteria:**

| Steering File | Verdict | Justification |
|---|---|---|
| `ecu-test-project-config.md` | **KEEP** | Project-specific model knowledge (signals, thresholds, Polarion mapping). Manual inclusion is correct — user activates when working on this specific model. |
| `fmu-build-requirement.md` | **MERGE into `matlab-simulink-setup.md`** | The "always build fresh FMU" policy is an FMU workflow rule, not a standalone document. It fits naturally as a section in the MATLAB/Simulink setup steering. |
| `matlab-simulink-setup.md` | **KEEP** | Environment setup + FMU export workflow. Manual inclusion is correct — user activates when setting up MATLAB or doing FMU work. After merge, this becomes the single source for all FMU-related guidance. |
| `session-setup-checklist.md` | **REDUCE** | Most content duplicates the skill or other steering. Reduce to a compact checklist of verification commands only. Remediation procedures link to the skill/steering where they are maintained. |

### Requirement 3B.4: Ensure Manual Inclusion Strategy Is Correct

**Acceptance Criteria:**
1. All steering files SHALL remain `inclusion: manual` — this is intentional because each covers a distinct context that should only be loaded when relevant
2. The README or a steering index SHALL document when to activate each steering file:
   - Activate `matlab-simulink-setup.md` when: starting a session involving model creation or FMU export
   - Activate `ecu-test-project-config.md` when: running tests against the Temperature Monitoring System model
   - Activate `session-setup-checklist.md` when: troubleshooting connectivity or verifying prerequisites
3. The ecu-test skill does NOT need manual activation — it is automatically triggered by the skill matching description

---

## Area 4: Outdated/Stale Content (Review — Do Not Remove)

### Problem

Several files appear outdated or duplicative. These should be reviewed and reconsidered but **NOT removed** — they may still have value as reference or may be repurposed.

- `architecture-prompt.md` — describes the "target architecture" for remote ECU-TEST execution as something to be built, but this is already implemented. Still useful as historical context.
- The spec `remote-ecu-test-execution/tasks.md` — all tasks marked unchecked despite implementation existing. Status is stale.
- `scripts/build_fmu_remote.sh` — duplicates adapter functionality but may be useful as a standalone convenience script.
- `example-test-execution-summary.md` and `examplePrompt.md` — demo artifacts in root, could be better organized.

### Requirement 4.1: Review and Update architecture-prompt.md

**Acceptance Criteria:**
1. `architecture-prompt.md` SHALL be reviewed and updated to reflect current state (mark "target" as "implemented", add date)
2. It SHALL NOT be deleted — it serves as historical design context
3. Consider adding a note at the top: "This architecture is now implemented. See README.md for current state."

### Requirement 4.2: Update Spec Task Status

**Acceptance Criteria:**
1. The `remote-ecu-test-execution/tasks.md` SHALL be updated to reflect actual implementation status
2. Tasks that are implemented (adapter_logic.py, CloudFormation template, remote scripts, adapter, config template) SHALL be marked as complete
3. Any tasks that remain unimplemented SHALL be clearly noted with their current blockers

### Requirement 4.3: Document build_fmu_remote.sh Purpose

**Acceptance Criteria:**
1. `scripts/build_fmu_remote.sh` SHALL be kept — it provides a standalone convenience for FMU compilation without needing the full adapter
2. A comment at the top SHALL clarify its relationship to the adapter: "Standalone convenience script. For full workflow, use ecu-test-adapter.sh --sync + compile."
3. The README SHALL reference it under a "Convenience Scripts" section

### Requirement 4.4: Organize Example/Demo Files

**Acceptance Criteria:**
1. `example-test-execution-summary.md` and `examplePrompt.md` SHALL be moved to a `docs/examples/` directory for better organization
2. These files SHALL NOT be deleted — they serve as demo reference material
3. A brief index in `docs/examples/README.md` SHALL describe what each example shows

---

## Area 5: Security and Credential Hygiene

### Problem

- A full JWT token is committed in both `mcp.json` files (root and temp-monitor)
- The token appears to be a real Polarion access token with an expiration date
- SSH key paths are referenced but the `.gitignore` correctly excludes `.pem` files
- `.ecu-test-remote.json` is correctly gitignored

### Requirement 5.1: Remove Committed Tokens

**Acceptance Criteria:**
1. All JWT tokens SHALL be removed from committed files and replaced with placeholder text
2. A `.env.example` file SHALL document the required environment variables
3. The MCP config SHALL support reading `POLARION_TOKEN` from an environment variable
4. Git history should be noted as containing the token (recommend token rotation)

### Requirement 5.2: Add Secret Scanning Guidance

**Acceptance Criteria:**
1. The `.gitignore` SHALL be reviewed to ensure all credential-bearing files are excluded
2. A comment in `mcp.json` SHALL warn users not to commit real tokens
3. Consider adding a pre-commit hook or `.gitattributes` pattern to prevent credential commits

---

## Area 6: Infrastructure Template Gaps

### Problem

The `infra/ecu-test-ec2.yaml` CloudFormation template:
- Missing WaitCondition/WaitConditionHandle (required by Requirement 1.5 and 1.10 in the spec)
- AMI IDs are hardcoded and will become stale over time
- UserData doesn't signal success/failure to CloudFormation
- No cfn-signal or cfn-init integration

### Requirement 6.1: Add WaitCondition to CloudFormation Template

**Acceptance Criteria:**
1. THE template SHALL include a `WaitCondition` and `WaitConditionHandle` resource with a 600-second timeout
2. THE UserData script SHALL signal success upon completion using `cfn-signal` or `curl` to the WaitConditionHandle URL
3. IF UserData fails, THE script SHALL signal failure causing stack rollback

### Requirement 6.2: Use SSM Parameter for AMI Lookup

**Acceptance Criteria:**
1. THE template SHALL use AWS SSM Parameter Store for Ubuntu AMI lookup instead of hardcoded AMI IDs per region
2. This eliminates the need to update the template when AMIs are rotated
3. Example: `resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id`

### Requirement 6.3: Add Error Handling to UserData

**Acceptance Criteria:**
1. THE UserData script SHALL use `set -e` and a trap to catch errors (partially implemented)
2. THE script SHALL log all output to `/var/log/ecu-test-init.log` (already done)
3. THE script SHALL signal the WaitConditionHandle on both success and failure paths

---

## Area 7: polarion-integration/temp-monitor Cleanup

### Problem

The `polarion-integration/temp-monitor/` subfolder contains:
- Its own `.kiro/` folder with hooks and MCP settings — creating a nested Kiro workspace that may conflict
- Hook files use a legacy format (`.kiro.hook` extension, non-standard schema)
- The MCP config duplicates the root config with hardcoded paths

### Requirement 7.1: Remove or Migrate Legacy Hooks

**Acceptance Criteria:**
1. The hook files at `polarion-integration/temp-monitor/.kiro/hooks/` use a legacy format — they SHALL be migrated to the v1 JSON format at the root `.kiro/hooks/` or deleted
2. IF the hooks provide value for the overall project, migrate them to root-level hooks
3. IF they are demo-specific artifacts for the temp-monitor sub-project, document this clearly

### Requirement 7.2: Remove Nested .kiro Folder

**Acceptance Criteria:**
1. The `polarion-integration/temp-monitor/.kiro/` folder creates a nested workspace — evaluate whether this is intentional
2. IF the temp-monitor is meant to be a standalone sub-project, it should be documented as such
3. IF it's part of the main project, its `.kiro/` folder SHALL be removed and relevant config merged into the root `.kiro/`

---

## Area 8: Repository Hygiene

### Problem

- The `matlab-models/` directory is empty (only `.keep`) — this is by design (generated during demo) but could confuse users
- The `ecu.test-integration/reports/` directory only has `.keep` — also by design
- No `tests/` directory exists in the file tree despite being referenced in the README project structure
- The README references `tests/unit/test_adapter_logic.py` but this file doesn't exist at that path

### Requirement 8.1: Verify README Project Structure Matches Reality

**Acceptance Criteria:**
1. The README's "Project Structure" section SHALL accurately reflect the actual file tree
2. Files/directories referenced in README that don't exist SHALL either be created or removed from the README
3. The `tests/unit/test_adapter_logic.py` reference SHALL be verified — if tests exist elsewhere, update the path; if they don't exist, remove the reference or note it as planned

### Requirement 8.2: Add .keep File Documentation

**Acceptance Criteria:**
1. Empty directories with `.keep` files SHALL have a brief README or comment explaining they are generated at runtime
2. This prevents confusion for new developers cloning the repo

### Requirement 8.3: Review .gitignore Coverage

**Acceptance Criteria:**
1. THE `.gitignore` SHALL be reviewed for completeness — currently it covers macOS, Python, IDE, AWS, MATLAB artifacts appropriately
2. Verify no generated files are accidentally committed
3. Ensure `session-summary*` pattern catches all session artifacts

---

## Area 9: Local Environment Setup Optimization

### Problem

The project requires multiple external tools (MATLAB, Xcode, Python, AWS CLI) and the setup is documented across README, steering files, and skill docs. There is no single "getting started" workflow for a new developer.

### Requirement 9.1: Create a Setup Verification Script

**Acceptance Criteria:**
1. A `scripts/verify-setup.sh` (or similar) SHALL exist that checks all prerequisites:
   - MATLAB installed and licensed
   - Required toolboxes available
   - Python 3.11+ available
   - `simulink-agentic-toolkit/` cloned
   - `.ecu-test-remote.json` present (or skipped for local-only mode)
   - Polarion MCP server dependencies installed
2. The script SHALL output clear pass/fail for each prerequisite
3. The script SHALL be referenced in the README's Prerequisites section

### Requirement 9.2: Document Local-Only vs Remote Mode

**Acceptance Criteria:**
1. THE README SHALL clearly distinguish between local-only setup (MATLAB + local ecu.test) and remote setup (MATLAB locally + ecu.test on EC2)
2. A minimal "local-only" path SHALL be documented for developers without AWS access
3. The MCP config SHALL work in both modes without modification (remote config is in `.ecu-test-remote.json`, not `mcp.json`)

---

## Priority Matrix

| Requirement | Priority | Effort | Impact |
|-------------|----------|--------|--------|
| 5.1 Remove Committed Tokens | **Critical** | Low | Security |
| 1.1 Remove Hardcoded User Paths | **High** | Low | Portability |
| 1.2 Remove Exposed Credentials | **High** | Low | Security |
| 1.3 Consolidate Duplicate MCP Configs | **High** | Low | Maintainability |
| 3B.1 Define Skill vs Steering Boundary | **High** | Medium | Clarity / Maintainability |
| 3B.2 Eliminate Duplicate Content | **High** | Medium | Maintainability |
| 3.1 Verify MATLAB Skills Against Toolkit | **High** | Low | Correctness |
| 2.1 Merge fmu-build-requirement | Medium | Low | Consolidation |
| 2.2 Reduce session-setup-checklist | Medium | Low | Clarity |
| 2.3 Remove Duplication from ecu-test-project-config | Medium | Medium | Clarity |
| 3B.3 Justify/Consolidate Steering Files | Medium | Medium | Organization |
| 3B.4 Confirm Manual Inclusion Strategy | Medium | Low | Usability |
| 3.2 Classify MATLAB Skills by Function | Medium | Low | Organization |
| 6.1 Add WaitCondition to CFN | Medium | Medium | Reliability |
| 7.1 Remove/Migrate Legacy Hooks | Medium | Low | Correctness |
| 7.2 Remove Nested .kiro Folder | Medium | Low | Clarity |
| 4.1 Review architecture-prompt.md | Low | Low | Cleanliness |
| 4.2 Update Spec Task Status | Low | Low | Accuracy |
| 4.3 Document build_fmu_remote.sh | Low | Low | Cleanliness |
| 4.4 Organize Example Files | Low | Low | Organization |
| 6.2 Use SSM for AMI Lookup | Low | Low | Maintainability |
| 8.1 Verify README Structure | Low | Low | Accuracy |
| 9.1 Create Setup Verification Script | Medium | Medium | Onboarding |
| 9.2 Document Local-Only Mode | Medium | Low | Usability |

---

## Summary

Total optimization points identified: **24 requirements across 9 areas**

**Critical (do first):**
- Remove committed JWT tokens from MCP configs

**High (do next):**
- Fix hardcoded user paths in MCP configs
- Consolidate duplicate MCP configs
- Define clear skill vs steering boundary for ECU-TEST (the collision)
- Eliminate duplicate content between skill and steering
- Verify MATLAB skills match the toolkit source (double-check)

**Medium (planned):**
- Merge `fmu-build-requirement.md` into `matlab-simulink-setup.md`
- Reduce `session-setup-checklist.md` to compact verification-only
- Classify MATLAB skills (which wrap MCPs vs which are pure guidance)
- Consolidate steering file decisions
- Fix CloudFormation template gaps
- Clean up legacy hooks and nested .kiro folders
- Create setup verification tooling

**Low (backlog):**
- Review/update outdated files (keep, don't remove)
- Update spec status
- Organize example files
- Fix README accuracy
