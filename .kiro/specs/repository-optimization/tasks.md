# Implementation Plan: Repository Optimization

## Overview

This plan implements the repository cleanup and optimization in 7 phases, ordered by priority (security first, then portability, then consolidation, then everything else). Each phase produces a independently-verifiable state. Total: 19 tasks.

## Tasks

- [x] 1. Remove JWT tokens and hardcoded paths from root MCP config
  - Replace `POLARION_TOKEN` value in `.kiro/settings/mcp.json` with `"${POLARION_TOKEN}"`
  - Replace `POLARION_USER` value with `"${POLARION_USER}"`
  - Replace hardcoded matlab command path (`/Users/levkent/dev/matlab/matlab-mcp-core-server`) with `"./matlab-mcp-core-server"`
  - Replace `--extension-file` absolute path with `./simulink-agentic-toolkit/tools/tools.json`
  - Replace polarion command path with `./polarion-integration/polarion-mcp/.venv/bin/python`
  - Replace `POLARION_CONFIG_PATH` with `./polarion-integration/temp-monitor/polarion_config.yaml`
  - Add `_comment` fields documenting what users need to customize
  - _Requirements: 1.1, 1.2, 1.4, 5.1_

- [x] 2. Create `.env.example` and delete duplicate MCP config
  - Create `.env.example` in project root with `POLARION_USER` and `POLARION_TOKEN` placeholder lines
  - Add comment header explaining these are used by the MCP config
  - Delete `polarion-integration/temp-monitor/.kiro/settings/mcp.json` (duplicate with hardcoded paths and exposed token)
  - Verify `.env` and `.env.*` are in `.gitignore`
  - _Requirements: 1.2, 1.3, 5.1, 5.2_

- [x] 3. Merge fmu-build-requirement into matlab-simulink-setup
  - Append the full "FMU Build Requirement" content as a new section `## FMU Build Policy — MANDATORY` at the end of `.kiro/steering/matlab-simulink-setup.md`
  - Retain all mandatory language, workflow steps, and dependency notes
  - Delete `.kiro/steering/fmu-build-requirement.md`
  - _Requirements: 2.1, 3B.3_

- [x] 4. Reduce session-setup-checklist to verification-only
  - Rewrite `.kiro/steering/session-setup-checklist.md` to contain ONLY compact verification commands
  - Remove all remediation/installation procedures
  - Add a "Remediation" section with pointers: MATLAB → `#matlab-simulink-setup`, ECU-TEST → skill, Model details → `#ecu-test-project-config`
  - Keep `inclusion: manual` front-matter
  - Target: under 50 lines total
  - _Requirements: 2.2, 3B.3_

- [x] 5. Clean ecu-test-project-config (remove operational duplication)
  - Remove "FMU Compilation on Remote" section (SSH compile + restart commands)
  - Remove TCF/TBC path convention content that duplicates the skill
  - Add note at top: "For operational procedures (sync, compile, restart), see the ecu-test skill."
  - Keep: Model Details, Signal Names, Thresholds, Test Step Phrasing, Remote Instance Details, Polarion Traceability
  - _Requirements: 2.3, 3B.1, 3B.2_

- [x] 6. Update ecu-test SKILL.md with cross-references
  - Add note in "Test Step Phrasing Rules" section: "For project-specific signal names and threshold values, activate the `#ecu-test-project-config` steering."
  - Verify all operational content (adapter, golden rules, sync, remote setup schema) remains
  - Remove any project-specific hardcoded values (e.g., `Plant model.TemperatureOut`) if present in the skill — they belong only in steering
  - _Requirements: 3B.1, 3B.2_

- [x] 7. Verify MATLAB skills against simulink-agentic-toolkit source
  - Check the `simulink-agentic-toolkit` GitHub repo for latest skill versions
  - Compare each of the 7 MathWorks skills (SKILL.md + manifest.yaml) against source
  - Confirm `requires-tools` in each manifest matches actual MCP tool usage
  - Create `docs/skill-versions.md` documenting version status and any drift found
  - _Requirements: 3.1_

- [x] 8. Create skill architecture documentation
  - Create `docs/skill-architecture.md` explaining: MCP tools = execution layer, skills = knowledge/workflow layer on top
  - Include classification table: MCP-wrapping skills (keep) vs pure-guidance skills (evaluate)
  - Document which skills are upstream MathWorks vs project-specific
  - Add brief "Skills & MCP Architecture" reference in README
  - _Requirements: 3.2, 3.3, 3B.4_

- [x] 9. Update architecture-prompt.md status
  - Add status header: `> **Status: IMPLEMENTED** (as of 2026-07). See README.md for current operational details.`
  - Keep all existing content unchanged
  - _Requirements: 4.1_

- [x] 10. Update remote-ecu-test-execution spec task status
  - Mark Task 3 (CloudFormation template) as `[x]`
  - Mark Task 6 (adapter shell script) as `[x]`
  - Mark Task 7 (config template) as `[x]`
  - Mark Task 9 (skill guides) as `[x]`
  - Review remaining tasks and mark any completed subtasks
  - _Requirements: 4.2_

- [x] 11. Document build_fmu_remote.sh purpose
  - Add comment block at top: "Standalone convenience script for compiling FMU on remote. For the full workflow, use ecu-test-adapter.sh --sync then compile."
  - _Requirements: 4.3_

- [x] 12. Organize example/demo files
  - Create `docs/examples/` directory
  - Move `example-test-execution-summary.md` to `docs/examples/`
  - Move `examplePrompt.md` to `docs/examples/`
  - Create `docs/examples/README.md` with brief index describing each example
  - _Requirements: 4.4_

- [x] 13. Add WaitCondition and error handling to CloudFormation template
  - Add `WaitConditionHandle` resource to `infra/ecu-test-ec2.yaml`
  - Add `WaitCondition` resource with 600-second timeout
  - Add `cfn-signal` success call at end of UserData
  - Add trap at top of UserData to signal failure on error
  - Install `aws-cfn-bootstrap` package in UserData
  - _Requirements: 6.1, 6.3_

- [x] 14. Replace hardcoded AMI mappings with SSM parameter
  - Remove `Mappings.RegionAMI` section from `infra/ecu-test-ec2.yaml`
  - Add `LatestAmiId` parameter with type `AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>`
  - Set default to `/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id`
  - Update `EC2Instance.Properties.ImageId` to `!Ref LatestAmiId`
  - _Requirements: 6.2_

- [x] 15. Clean up polarion-integration nested .kiro
  - Create `polarion-integration/temp-monitor/.kiro/hooks/README.md` explaining these are legacy demo hooks kept for reference
  - Verify mcp.json deletion (from task 2) is complete
  - _Requirements: 7.1, 7.2_

- [x] 16. Fix README project structure and add steering guide
  - Compare README "Project Structure" against actual file tree
  - Remove `tests/unit/test_adapter_logic.py` reference if tests don't exist
  - Add "Steering Files" section documenting when to activate each
  - Add "Convenience Scripts" section
  - Clarify local-only vs remote mode in Prerequisites
  - _Requirements: 8.1, 9.2_

- [x] 17. Add directory documentation
  - Create `matlab-models/README.md`: "Populated at runtime during demo sessions. Gitignored."
  - Verify `.keep` files exist where needed
  - _Requirements: 8.2_

- [x] 18. Review .gitignore coverage
  - Verify no generated files are accidentally tracked
  - Confirm `session-summary*` pattern works
  - Confirm `.env` is covered
  - _Requirements: 8.3, 5.2_

- [x] 19. Create setup verification script
  - Create `scripts/verify-setup.sh` checking: MATLAB, simulink-agentic-toolkit, Python 3.11+, Polarion MCP venv, .ecu-test-remote.json (warn only), AWS CLI (warn only)
  - Output PASS/FAIL per prerequisite
  - Reference in README Prerequisites section
  - _Requirements: 9.1_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3", "4", "5", "6"] },
    { "id": 2, "tasks": ["7", "8", "9", "10", "11", "12"] },
    { "id": 3, "tasks": ["13", "14", "15"] },
    { "id": 4, "tasks": ["16", "17", "18", "19"] }
  ]
}
```

## Notes

- Wave 0 (tasks 1-2) must complete first — removes secrets before any commit
- Wave 1 (tasks 3-6) is the steering/skill consolidation — the core cleanup
- Wave 2 (tasks 7-12) can run in parallel — independent documentation/verification tasks
- Wave 3 (tasks 13-15) is infrastructure and nested cleanup
- Wave 4 (tasks 16-19) depends on earlier waves to finalize README and verification
- No automated tests required — verification is manual per the Testing Strategy in design.md
