# Skills & MCP Architecture

## Overview

This project uses a two-layer architecture for AI-assisted development:

```
┌───────────────────────────────────────────────────────────┐
│  Skills (Knowledge & Workflow Layer)                       │
│  "WHEN and HOW to use tools correctly"                    │
│  ├── Workflow sequencing, guardrails, best practices      │
│  ├── Domain-specific rules (naming, patterns, syntax)     │
│  └── Auto-triggered by conversation context               │
├───────────────────────────────────────────────────────────┤
│  MCP Servers (Execution Layer)                            │
│  "Raw capability to DO things"                            │
│  ├── matlab: model_edit, model_test, evaluate_matlab_code │
│  └── polarion: search_workitems, create_workitem, etc.    │
└───────────────────────────────────────────────────────────┘
```

**MCP tools** provide raw execution capability — they can edit models, run simulations, query parameters, and interact with external systems. They have no opinion on workflow order or best practices.

**Skills** sit on top of MCP tools and provide the knowledge layer — they tell the agent when to use which tools, in what order, with what constraints, and following what conventions. Skills are auto-triggered when the conversation matches their description.

Both layers are required for the full workflow to function. The MCP server alone gives you tool access; the skill layer gives you correct, guided usage of those tools.

---

## Skill Classification

### MCP-Wrapping Skills (Keep as Skills)

These skills wrap one or more MCP tools with workflow guidance, guardrails, and domain-specific rules. They must remain as skills because they define execution procedures that depend on MCP tool invocation.

| Skill | Version | MCP Tools Used | What It Adds | Source |
|-------|---------|---------------|--------------|--------|
| `building-simulink-models` | v1.1 | `model_edit`, `model_overview`, `model_read`, `model_query_params`, `model_resolve_params` | Layout mode, naming conventions, operation chaining, domain-specific modeling rules | MathWorks |
| `simulating-simulink-models` | v1.1 | `evaluate_matlab_code` (sim workflow) | SimulationInput/Output guardrails, simulation execution patterns | MathWorks |
| `testing-simulink-models` | v1.2 | `model_test` | Gherkin syntax reference, draft mode guidance, test execution patterns | MathWorks |
| `generate-requirement-drafts` | v2.1 | `evaluate_matlab_code`, `model_overview`, `model_read`, `model_query_params`, `model_resolve_params` | EARS patterns, slreq API workflows, structured requirement formatting | MathWorks |
| `ecu-test` | — | Shell scripts / SSH adapter | Adapter invocation, golden rules, sync/compile/execute workflows, test step phrasing | Project-specific |

### Pure-Guidance Skills (Evaluate for Steering Migration)

These skills do not directly invoke MCP tools for their primary function. They provide specification-writing templates and review processes. Consider migrating to steering if spec-writing is not a frequent session activity.

| Skill | Version | MCP Tools Referenced | What It Provides | Source | Recommendation |
|-------|---------|---------------------|-----------------|--------|----------------|
| `specifying-mbd-algorithms` | v1.0 | `model_overview`, `model_read` (for reading existing models during spec review) | Specification templates, review gates for algorithm design | MathWorks | Evaluate — useful if writing algorithm specs; could be steering otherwise |
| `specifying-plant-models` | v1.0 | `model_overview`, `model_read` (same as above) | Specification templates, review gates for plant model design | MathWorks | Evaluate — same consideration as above |
| `filing-bug-reports` | v1.0 | `evaluate_matlab_code` (for gathering diagnostic info) | Generic defect documentation templates | MathWorks | Evaluate — remove if not used in this project's workflow |

---

## Source Attribution

### Upstream MathWorks (simulink-agentic-toolkit)

Seven skills are authored by MathWorks and distributed as part of the [Simulink Agentic Toolkit](https://github.com/matlab/simulink-agentic-toolkit). These are identified by the `toolkit: simulink-agentic-toolkit` declaration in their `manifest.yaml` and carry the `MathWorks BSD-3-Clause` license.

| Skill | Toolkit Version | License |
|-------|----------------|---------|
| `building-simulink-models` | v1.1 | MathWorks BSD-3-Clause |
| `simulating-simulink-models` | v1.1 | MathWorks BSD-3-Clause |
| `testing-simulink-models` | v1.2 | MathWorks BSD-3-Clause |
| `generate-requirement-drafts` | v2.1 | MathWorks BSD-3-Clause |
| `specifying-mbd-algorithms` | v1.0 | MathWorks BSD-3-Clause |
| `specifying-plant-models` | v1.0 | MathWorks BSD-3-Clause |
| `filing-bug-reports` | v1.0 | MathWorks BSD-3-Clause |

These skills should be treated as an upstream dependency. Local modifications should be avoided — if changes are needed, contribute upstream or document overrides explicitly.

### Project-Specific

| Skill | Purpose |
|-------|---------|
| `ecu-test` | Comprehensive ECU-TEST automation: adapter routing, remote execution, test package creation, AI generation, reporting. Built specifically for this project's remote EC2 workflow. |

---

## Steering Files (Manual Inclusion)

Steering files complement skills by providing project-specific values that skills operate on. All steering uses `inclusion: manual` — they are loaded only when explicitly activated by the user.

| Steering File | When to Activate | What It Provides |
|---------------|-----------------|-----------------|
| `matlab-simulink-setup.md` | Starting a session involving model creation or FMU export | MATLAB environment paths, toolbox requirements, FMU export workflow, FMU build policy |
| `ecu-test-project-config.md` | Running tests against the Temperature Monitoring System model | Signal names, thresholds, test step examples, Polarion mapping, remote instance details |
| `session-setup-checklist.md` | Troubleshooting connectivity or verifying prerequisites | Compact verification commands with pointers to remediation sources |

---

## How It All Fits Together

For a new developer to have the full workflow functional:

1. **MCP servers configured** — `mcp.json` points to working MATLAB and Polarion servers
2. **Skills installed** — `.kiro/skills/` contains the skill definitions (already in repo)
3. **Toolkit cloned** — `simulink-agentic-toolkit/` provides extended tool definitions
4. **Steering available** — `.kiro/steering/` files can be activated for project-specific context

The agent automatically loads skills when conversation context matches their trigger descriptions. MCP tools are always available once the server connects. Steering is loaded on-demand when the user needs project-specific context beyond what the skill provides.
