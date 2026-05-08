# Implementation Plan: Remote ECU-TEST Execution

## Overview

This plan implements the remote ECU-TEST execution feature in incremental steps: first the pure-logic Python module (testable independently), then the CloudFormation infrastructure template, then the remote skill scripts, then the Bash adapter that wires everything together, and finally the skill guide updates. Property-based tests and unit tests are placed close to the code they validate.

## Tasks

- [ ] 1. Create adapter logic module and tests
  - [ ] 1.1 Create `adapter_logic.py` with pure functions for path translation, config resolution, mode validation, and argument construction
    - Create file at `.kiro/skills/ecu-test/scripts/adapter_logic.py`
    - Implement `translate_path(local_path, local_workspace, remote_workspace)` — replaces local workspace prefix with remote workspace, converts `\` to `/`
    - Implement `validate_mode(mode_value)` — returns True only for "local" or "remote", raises ValueError with message listing invalid value and accepted values
    - Implement `resolve_config(env_vars, config_file_dict)` — merges config with env vars taking precedence over config file values
    - Implement `check_missing_params(config)` — returns list of missing required remote params (hostname, username, key_path)
    - Implement `build_ssh_command(user, host, key, script_path, args, timeout)` — constructs SSH command list preserving argument order and content
    - Implement `parse_script_output(stdout_text)` — extracts SUCCESS/ERROR status from last matching line
    - _Requirements: 4.8, 5.1, 5.4, 5.6, 5.7, 4.3, 7.5_

  - [ ]* 1.2 Write property tests for adapter logic (Property 1: Path translation round-trip)
    - **Property 1: Path translation round-trip preserves relative structure**
    - **Validates: Requirements 4.8, 7.5**
    - Create `tests/unit/test_adapter_logic.py`
    - Use Hypothesis to generate paths with mixed separators, spaces, unicode, nested dirs, trailing slashes
    - Assert: relative path segments after workspace root are preserved unchanged
    - Assert: all backslashes converted to forward slashes
    - Assert: remote workspace prefix replaces local workspace prefix

  - [ ]* 1.3 Write property tests for adapter logic (Property 2: Mode validation)
    - **Property 2: Mode validation accepts only valid modes**
    - **Validates: Requirements 5.1, 5.6**
    - Use Hypothesis to generate arbitrary strings including near-misses ("Local", "REMOTE", " remote", empty, whitespace)
    - Assert: only "local" and "remote" are accepted
    - Assert: error message contains the invalid value and both accepted values

  - [ ]* 1.4 Write property tests for adapter logic (Property 3: Config precedence)
    - **Property 3: Configuration resolution precedence**
    - **Validates: Requirements 5.4**
    - Use Hypothesis to generate config dicts and env var dicts with overlapping/disjoint keys
    - Assert: env var value used when both present
    - Assert: config file value used when env var is unset/empty

  - [ ]* 1.5 Write property tests for adapter logic (Property 4: Missing parameter detection)
    - **Property 4: Missing parameter detection is complete**
    - **Validates: Requirements 5.7**
    - Use Hypothesis to generate all subsets of {hostname, username, key_path} as missing
    - Assert: error message lists exactly the missing parameter names — no more, no fewer

  - [ ]* 1.6 Write property tests for adapter logic (Property 5: Argument forwarding)
    - **Property 5: Argument forwarding preserves order and content**
    - **Validates: Requirements 4.3**
    - Use Hypothesis to generate lists of strings with shell metacharacters, quotes, spaces, newlines
    - Assert: constructed SSH command preserves all arguments in original order with original content

  - [ ]* 1.7 Write unit tests for edge cases
    - Test path translation: empty path, path without workspace prefix, path that IS the workspace prefix, Windows UNC paths
    - Test config parsing: valid JSON, empty file, missing file, malformed JSON
    - Test output parsing: SUCCESS/ERROR lines, multi-line output, no matching prefix
    - Test timeout validation: boundary values (0, 1, 3600, 3601)
    - _Requirements: 4.8, 5.4, 5.6, 5.7_

- [ ] 2. Checkpoint - Ensure adapter logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Create CloudFormation template
  - [ ] 3.1 Create `infra/ecu-test-ec2.yaml` CloudFormation template
    - Define Parameters: `KeyPairName`, `AllowedSSHCidr`, `InstanceType` (default t3.large), `EcuTestDebUrl`
    - Define SecurityGroup resource allowing inbound SSH (port 22) from `AllowedSSHCidr`
    - Define EC2Instance resource: Ubuntu 22.04 LTS AMI, t3.large, 30 GiB gp3 EBS root volume
    - Define WaitCondition + WaitConditionHandle with 600s timeout
    - Write UserData script: install Python 3.11 + requests, download and install ECU_TEST .deb, create `/opt/ecu-test-scripts` (chmod 755) and `/opt/ecu-test-workspace` (chmod 777), signal WaitCondition success/failure
    - Define Outputs: `InstancePublicIp`, `InstancePublicDns`, `InstanceId`
    - Use `set -e` and trap in UserData to signal failure on any error
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

- [ ] 4. Create remote skill scripts
  - [ ] 4.1 Create `api_client_setup.py` for remote (Linux-only version)
    - Create file at `.kiro/skills/ecu-test/scripts/remote/api_client_setup.py`
    - Simplify path resolution to only check `/opt/ecu.test/Templates/ApiClient`
    - Keep `ECU_TEST_API_CLIENT_PATH` env var override
    - _Requirements: 2.4_

  - [ ] 4.2 Create remote `start.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/start.py`
    - Adapt from local version: use Linux process launch (no Windows `creationflags`)
    - Use `/opt/ecu.test/bin/ecu-test` as default executable path
    - Poll REST API at localhost:5050 every 2 seconds, max 60 seconds
    - Output `SUCCESS: ECU-TEST started and REST API ready` or `ERROR: <reason>`
    - Return non-zero exit within 10s if API unreachable on health check
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8, 6.4, 6.5_

  - [ ] 4.3 Create remote `configure_tcf.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/configure_tcf.py`
    - Adapt from local version: add SUCCESS:/ERROR: output protocol
    - Add 10s timeout on initial API reachability check
    - _Requirements: 2.1, 2.3, 2.5, 2.6, 2.7, 2.8_

  - [ ] 4.4 Create remote `create_package.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/create_package.py`
    - Adapt from local version: use `/opt/ecu-test-workspace` as base path
    - Use Linux paths (forward slashes)
    - Add SUCCESS:/ERROR: output protocol
    - Add 10s timeout on API reachability check
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8_

  - [ ] 4.5 Create remote `generate.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/generate.py`
    - Adapt from local version: Linux paths, ApiClient at `/opt/ecu.test/Templates/ApiClient`
    - Add SUCCESS:/ERROR: output protocol
    - Add 10s timeout on API reachability check
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [ ] 4.6 Create remote `execute.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/execute.py`
    - Adapt from local version: Linux paths
    - Add SUCCESS:/ERROR: output protocol
    - Add 10s timeout on API reachability check
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8_

  - [ ] 4.7 Create remote `report.py`
    - Create file at `.kiro/skills/ecu-test/scripts/remote/report.py`
    - Adapt from local version: Linux paths
    - Add SUCCESS:/ERROR: output protocol
    - Add 10s timeout on API reachability check
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8_

- [ ] 5. Checkpoint - Verify remote scripts are consistent
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create the Skill Adapter shell script
  - [ ] 6.1 Create `ecu-test-adapter.sh` with configuration loading and mode routing
    - Create file at `.kiro/skills/ecu-test/scripts/ecu-test-adapter.sh`
    - Read config from env vars with `.ecu-test-remote.json` fallback (using `adapter_logic.py` via Python one-liner for JSON parsing and config resolution)
    - Validate mode is "local" or "remote"; exit with error if invalid
    - Validate required remote params when mode=remote; exit with error listing missing params
    - Route to local execution: `python3 <local_script_dir>/<script_name> <args>`
    - Route to remote execution: build SSH command with path-translated args
    - Handle SSH connection timeout (30s default)
    - Handle script execution timeout (configurable, default 600s)
    - Capture and relay stdout/stderr, propagate exit code
    - Make script executable (`chmod +x`)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ] 6.2 Implement file transfer functions in the adapter
    - Add `upload_file` function: SCP upload with configurable timeout, verify remote file size matches local
    - Add `download_file` function: SCP download for TRF report retrieval
    - Add cleanup on failure: remove partial files on remote
    - Add file existence check before upload
    - Report errors with source path, destination path, and error reason
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 6.3 Implement ECU_TEST lifecycle check in the adapter
    - Add pre-start check: SSH to remote, curl localhost:5050/api/v2/live, check for HTTP 200
    - If already running, skip start.py invocation and report to Kiro
    - If not running, invoke start.py via SSH
    - Handle SSH failure during check: report connection error, do not attempt start
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

- [ ] 7. Create configuration file template
  - [ ] 7.1 Create `.ecu-test-remote.json` example configuration file
    - Create `.ecu-test-remote.json.example` in project root with all fields documented
    - Include mode, remote_host, remote_user, remote_key, local_workspace, remote_workspace, timeouts
    - Add to `.gitignore`: `.ecu-test-remote.json` (contains credentials)
    - _Requirements: 5.4_

- [ ] 8. Checkpoint - Ensure adapter and config are complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update skill guides to use the adapter
  - [ ] 9.1 Update ecu-test skill SKILL.md and guide markdown files
    - Update SKILL.md Quick Start section to show adapter invocation instead of direct script calls
    - Update each guide file (start.md, create-package.md, generate.md, execute.md, report.md, end-to-end.md) to reference `ecu-test-adapter.sh` as the entry point
    - Document both local and remote usage patterns
    - Add a "Remote Setup" section explaining configuration requirements
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The adapter logic is extracted into a Python module (`adapter_logic.py`) to enable property-based testing with Hypothesis while keeping the Bash adapter thin
- Remote scripts are placed in a `remote/` subdirectory to keep them separate from local scripts
- Integration tests (SSH connectivity, file transfer, end-to-end) are not included as tasks because they require a deployed EC2 instance and cannot be performed by a coding agent alone

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "4.1"] },
    { "id": 2, "tasks": ["4.2", "4.3", "4.4", "4.5", "4.6", "4.7"] },
    { "id": 3, "tasks": ["6.1", "7.1"] },
    { "id": 4, "tasks": ["6.2", "6.3"] },
    { "id": 5, "tasks": ["9.1"] }
  ]
}
```
