# Design: Repository Optimization

## Overview

This design document defines the technical approach for cleaning and optimizing the `automotive-sdlc-agent-for-mil-sil-hil` repository. It covers 9 areas: MCP configuration portability, steering file consolidation, MATLAB skills verification, skill/steering boundary enforcement, stale content updates, infrastructure template improvements, nested workspace cleanup, repository hygiene, and setup tooling. The work is structured into 7 execution phases ordered by priority.

## Architecture

The repository optimization is a refactoring effort — no new runtime components are introduced. The architecture remains unchanged: Kiro IDE orchestrates MATLAB/Simulink (via MCP), ECU-TEST (via skill adapter), and Polarion (via MCP). This work reorganizes the configuration and documentation layer to eliminate redundancy, fix portability issues, and enforce a clear boundary between skills (execution procedures) and steering (project knowledge).

### Layering Model

```
┌───────────────────────────────────────────────────┐
│  User Session (Kiro IDE)                          │
├───────────────────────────────────────────────────┤
│  Steering (manual inclusion)                      │
│  ├── matlab-simulink-setup.md (env + FMU policy) │
│  ├── ecu-test-project-config.md (model values)   │
│  └── session-setup-checklist.md (pre-flight)     │
├───────────────────────────────────────────────────┤
│  Skills (auto-triggered by description match)     │
│  ├── building/simulating/testing-simulink-models │
│  ├── generate-requirement-drafts                 │
│  ├── specifying-mbd-algorithms / plant-models    │
│  └── ecu-test (adapter + scripts)               │
├───────────────────────────────────────────────────┤
│  MCP Servers (execution layer)                    │
│  ├── matlab (model_edit, model_test, sim, etc.)  │
│  └── polarion (work items, traceability)         │
├───────────────────────────────────────────────────┤
│  Infrastructure                                   │
│  └── infra/ecu-test-ec2.yaml (CloudFormation)    │
└───────────────────────────────────────────────────┘
```

### Key Boundary: Skill vs Steering

- **Skill** = always loaded when triggered; must be self-sufficient for execution mechanics
- **Steering** = manually loaded; provides supplementary project-specific values
- Operational procedures (how to sync, compile, restart) → Skill
- Project-specific values (signal names, thresholds, license strings) → Steering

---

## Components and Interfaces

### Component 1: MCP Configuration

**Files:** `.kiro/settings/mcp.json`, `.env.example`

**Interface:** Kiro reads `mcp.json` at startup to configure MCP server connections. Environment variables are resolved at runtime.

**Design:**
- Polarion token and user → `${POLARION_TOKEN}`, `${POLARION_USER}` (env var references)
- MATLAB binary path → relative `./matlab-mcp-core-server` (user symlinks into project root)
- Extension file → relative `./simulink-agentic-toolkit/tools/tools.json`
- Polarion command → relative `./polarion-integration/polarion-mcp/.venv/bin/python`
- All `_comment` fields document what needs customization
- Duplicate config at `polarion-integration/temp-monitor/.kiro/settings/` → deleted

### Component 2: Steering Files (3 files after consolidation)

**Files:** `matlab-simulink-setup.md`, `ecu-test-project-config.md`, `session-setup-checklist.md`

**Interface:** Each file has `inclusion: manual` — activated by user via `#filename` in chat.

**Design after consolidation:**

| File | Scope | Content |
|------|-------|---------|
| `matlab-simulink-setup.md` | MATLAB environment + FMU workflow | Paths, toolboxes, FMU export, FMU build policy (merged from `fmu-build-requirement.md`) |
| `ecu-test-project-config.md` | Project-specific model knowledge | Signal names, thresholds, test phrasing examples, Polarion mapping, instance details |
| `session-setup-checklist.md` | Quick pre-flight verification | One-liner checks only, links to remediation sources |

`fmu-build-requirement.md` → deleted (merged into `matlab-simulink-setup.md`)

### Component 3: ecu-test Skill

**Files:** `.kiro/skills/ecu-test/SKILL.md`

**Interface:** Auto-triggered when user mentions ecu.test, test execution, test packages, etc.

**Design change:** Add cross-references to steering for project-specific values. Remove any hardcoded model-specific content (signal names). Keep all operational content.

### Component 4: MATLAB Skills (7 upstream)

**Files:** `.kiro/skills/{building,simulating,testing}-simulink-models/`, `specifying-{mbd-algorithms,plant-models}/`, `generate-requirement-drafts/`, `filing-bug-reports/`

**Interface:** Auto-triggered by description match. Layer on top of MATLAB MCP tools.

**Design:** Verify against upstream toolkit source. Document layering in `docs/skill-architecture.md`. No modifications to upstream skills.

### Component 5: Infrastructure Template

**Files:** `infra/ecu-test-ec2.yaml`

**Interface:** Deployed via `aws cloudformation deploy`.

**Design changes:**
- Replace hardcoded AMI mappings → SSM Parameter lookup
- Add WaitCondition/WaitConditionHandle for deployment signaling
- Add cfn-signal in UserData (success + failure paths)

### Component 6: Documentation & Hygiene

**Files:** `README.md`, `docs/skill-architecture.md`, `docs/examples/`, `matlab-models/README.md`, `scripts/verify-setup.sh`

**Interface:** Human-readable documentation and developer tooling.

---

## Data Models

No runtime data models are introduced or modified. The optimization work operates on:

### Configuration Schema: `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "<relative-path-to-binary>",
      "args": ["<flag>=<value>"],
      "env": {
        "<KEY>": "${ENV_VAR_NAME} | <literal-value>"
      },
      "disabled": false,
      "autoApprove": ["<tool-name>"]
    }
  }
}
```

### Configuration Schema: `.env.example`

```
POLARION_USER=<your-email>
POLARION_TOKEN=<your-jwt-token>
```

### Steering File Front-Matter Schema

```yaml
---
inclusion: manual
---
```

All steering files use this exact front-matter. No conditional (`fileMatch`) or auto-inclusion is used.

---

## Correctness Properties

### Property 1: No committed secrets
**Validates: Requirements 5.1, 1.2**
 After Phase 1, `git grep` for JWT patterns (`eyJ`) in tracked files returns zero results
### Property 2: No hardcoded user paths
**Validates: Requirements 1.1, 1.3, 1.4**
 After Phase 2, `git grep '/Users/'` in tracked files returns zero results
### Property 3: Single source of truth
**Validates: Requirements 2.1, 2.2, 2.3, 3B.2**
 After Phase 2+3, no content block appears verbatim in more than one file
### Property 4: Skill self-sufficiency
**Validates: Requirements 3B.1**
 The ecu-test skill can be used without any steering file activated (operational procedures are complete within the skill)
### Property 5: Steering adds value
**Validates: Requirements 3B.4**
 Each steering file provides information NOT available in the skill (project-specific values, environment setup)

---

## Error Handling

This is a documentation/configuration refactoring — no runtime error handling is introduced.

**Verification approach:**
- After each phase, verify the affected files are syntactically valid (JSON parseable, YAML front-matter correct, markdown renders)
- After Phase 1: confirm MCP config loads without errors (Kiro shows servers in panel)
- After Phase 5: CloudFormation template validates with `aws cloudformation validate-template`

---

## Testing Strategy

No automated tests are needed for this work. Verification is manual:

| Phase | Verification |
|-------|-------------|
| 1 (Security) | `git grep 'eyJ'` returns 0 results; MCP servers connect |
| 2 (Steering) | Each steering file has non-overlapping content; under 50 lines for checklist |
| 3 (Skills) | `docs/skill-versions.md` documents comparison results |
| 4 (Content) | Files exist in expected locations; headers added |
| 5 (Infra) | `aws cloudformation validate-template --template-body file://infra/ecu-test-ec2.yaml` succeeds |
| 6 (Cleanup) | No nested mcp.json; hooks have README |
| 7 (Hygiene) | `scripts/verify-setup.sh` runs and produces output; README matches file tree |
