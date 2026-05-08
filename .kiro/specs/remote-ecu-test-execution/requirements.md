# Requirements Document

## Introduction

This feature moves the ecu.test execution environment from a local machine (co-located with Kiro) to a remote EC2 instance. Kiro will use SSH to invoke the ecu-test skill scripts on the remote machine, enabling a decoupled architecture where the test execution environment is independently provisioned, scaled, and managed. The solution includes infrastructure-as-code (CloudFormation) for provisioning the EC2 instance, adapted remote scripts, file transfer mechanisms for FMU artifacts, and modifications to the existing ecu-test skill to support remote execution via SSH.

## Glossary

- **Kiro**: The AI-powered development environment that orchestrates the SDLC workflow
- **ECU_TEST**: The ecu.test application that defines and executes automotive tests using FMU models, installed from the .deb package at https://files.tracetronic.de/d/aec99b8eb51041d9827d/?p=%2F2026.2.0&mode=list
- **Remote_EC2**: The AWS EC2 instance (t3.large or equivalent, Ubuntu/Linux) hosting the ECU_TEST application
- **Remote_Skill_Scripts**: The Python scripts (start.py, create_package.py, generate.py, execute.py, report.py, configure_tcf.py) deployed on Remote_EC2 that interact with ECU_TEST
- **FMU**: Functional Mock-up Unit file exported from a Simulink model, used by ECU_TEST for test execution
- **ECU_Test_Workspace**: The directory on Remote_EC2 where FMU files and test artifacts (packages, configurations, reports) are stored
- **CloudFormation_Template**: The AWS CloudFormation infrastructure-as-code template that provisions and configures Remote_EC2
- **SSH_Connection**: The secure shell connection from Kiro to Remote_EC2 used to invoke Remote_Skill_Scripts
- **ECU_TEST_REST_API**: The HTTP REST API exposed by ECU_TEST on port 5050 (localhost on Remote_EC2)
- **Skill_Adapter**: The component within the ecu-test skill that routes script execution to either local or remote mode

## Requirements

### Requirement 1: EC2 Infrastructure Provisioning

**User Story:** As a DevOps engineer, I want a CloudFormation template that provisions a properly configured EC2 instance for ECU_TEST, so that the remote test environment can be created and destroyed reproducibly.

#### Acceptance Criteria

1. WHEN the CloudFormation_Template is deployed, THE CloudFormation_Template SHALL provision a Remote_EC2 instance with at least 8 GiB of memory and 2 vCPUs (t3.large or equivalent) and an EBS root volume of at least 30 GiB
2. WHEN the CloudFormation_Template is deployed, THE CloudFormation_Template SHALL configure the Remote_EC2 instance with Ubuntu 22.04 LTS or later
3. WHEN the CloudFormation_Template is deployed, THE CloudFormation_Template SHALL create a security group that allows inbound SSH (port 22) from a configurable CIDR range passed as a template parameter
4. WHEN the CloudFormation_Template is deployed, THE CloudFormation_Template SHALL accept an SSH key pair name as a parameter for instance access
5. WHEN the Remote_EC2 instance launches, THE CloudFormation_Template SHALL install ECU_TEST on the instance by downloading the .deb package from https://files.tracetronic.de/d/aec99b8eb51041d9827d/?p=%2F2026.2.0&mode=list and installing it via dpkg, then signal successful completion using a CloudFormation WaitCondition with a timeout of 600 seconds
6. WHEN the Remote_EC2 instance launches, THE CloudFormation_Template SHALL create the directory /opt/ecu-test-scripts for Remote_Skill_Scripts with read and execute permissions for the SSH login user
7. WHEN the Remote_EC2 instance launches, THE CloudFormation_Template SHALL create the directory /opt/ecu-test-workspace as the ECU_Test_Workspace with read and write permissions for the SSH login user
8. WHEN the Remote_EC2 instance launches, THE CloudFormation_Template SHALL install Python 3.11 or later and the requests library on the instance
9. WHEN the CloudFormation stack creation completes, THE CloudFormation_Template SHALL output the public IP address and the public DNS name of Remote_EC2
10. IF the instance initialization (user-data or cfn-init) fails, THEN THE CloudFormation_Template SHALL signal a WaitCondition failure causing the stack creation to roll back

### Requirement 2: Remote Skill Scripts Deployment

**User Story:** As a developer, I want the ecu-test skill scripts deployed and functional on the remote EC2 instance, so that ECU_TEST operations can be invoked remotely.

#### Acceptance Criteria

1. THE Remote_Skill_Scripts SHALL include adapted versions of start.py, create_package.py, generate.py, execute.py, report.py, and configure_tcf.py deployed to /opt/ecu-test-scripts on Remote_EC2
2. THE Remote_Skill_Scripts SHALL use Linux-compatible file paths (forward slashes, /opt/ecu-test-workspace as base directory)
3. THE Remote_Skill_Scripts SHALL communicate with ECU_TEST_REST_API on localhost:5050 within Remote_EC2
4. THE Remote_Skill_Scripts SHALL use the ecu.test ApiClient installed at /opt/ecu.test/Templates/ApiClient on Remote_EC2
5. WHEN a Remote_Skill_Script completes execution successfully, THE Remote_Skill_Script SHALL return a zero exit code and write a line beginning with "SUCCESS:" followed by a result summary to stdout
6. WHEN a Remote_Skill_Script fails execution, THE Remote_Skill_Script SHALL return a non-zero exit code and write a line beginning with "ERROR:" followed by a failure reason to stdout, regardless of whether the failure is caused by invalid input, an unreachable ECU_TEST_REST_API, or a misconfigured environment
7. THE Remote_Skill_Scripts SHALL write status information and results to stdout as plain text lines, where each script outputs at minimum a final line prefixed with "SUCCESS:" or "ERROR:" that the Skill_Adapter uses to determine execution outcome
8. IF the ECU_TEST_REST_API on localhost:5050 is unreachable when a Remote_Skill_Script is invoked, THEN THE Remote_Skill_Script SHALL return a non-zero exit code within 10 seconds and write an error line indicating the API is not available

### Requirement 3: File Transfer to Remote EC2

**User Story:** As a developer, I want to transfer FMU files and test configurations from my local machine to the remote EC2 instance, so that ECU_TEST can execute tests against the correct model.

#### Acceptance Criteria

1. WHEN Kiro needs to execute a test that requires an FMU file, THE Skill_Adapter SHALL transfer the FMU file to the ECU_Test_Workspace on Remote_EC2 via SCP or SFTP over the SSH_Connection within a configurable timeout (default 300 seconds)
2. WHEN a file is transferred to Remote_EC2, THE Skill_Adapter SHALL place the file in the ECU_Test_Workspace directory (/opt/ecu-test-workspace), overwriting any existing file with the same name at the destination
3. WHEN a file transfer completes, THE Skill_Adapter SHALL verify the file exists at the destination on Remote_EC2 and that the remote file size in bytes matches the source file size
4. IF a file transfer fails, times out, or verification of file placement fails, THEN THE Skill_Adapter SHALL report the failure to Kiro via stdout including the source file path, destination file path, and error reason
5. WHEN a test report is generated on Remote_EC2, THE Skill_Adapter SHALL retrieve the TRF report file from Remote_EC2 to the local working directory via SCP or SFTP over the SSH_Connection
6. IF the SSH_Connection is lost during a file transfer, THEN THE Skill_Adapter SHALL remove any partially transferred file at the destination and report the transfer failure with the file path and error reason

### Requirement 4: SSH-Based Remote Script Execution

**User Story:** As a developer, I want the ecu-test skill to execute scripts on the remote EC2 instance via SSH, so that I can run ECU_TEST operations without ecu.test installed locally.

#### Acceptance Criteria

1. WHEN the Skill_Adapter is requested to execute a script in remote mode, THE Skill_Adapter SHALL establish an SSH_Connection to Remote_EC2 using a configurable hostname, username, and private key path
2. WHEN the Skill_Adapter executes a remote script, THE Skill_Adapter SHALL invoke the script at /opt/ecu-test-scripts/{script_name} on Remote_EC2 via the SSH_Connection using the Python interpreter
3. WHEN the Skill_Adapter executes a remote script, THE Skill_Adapter SHALL forward all command-line arguments to the remote script in the same order as provided by the caller
4. WHEN the remote script execution completes, THE Skill_Adapter SHALL capture the exit code, stdout, and stderr from the SSH_Connection and return all three to Kiro
5. IF the remote script returns a non-zero exit code, THEN THE Skill_Adapter SHALL report the execution as failed and include the captured stderr output in the error report
6. WHEN the SSH_Connection cannot be established within 30 seconds, THE Skill_Adapter SHALL report a connection timeout error with the target hostname
7. WHEN the remote script execution exceeds a configurable timeout (default 600 seconds, minimum 1 second, maximum 3600 seconds), THE Skill_Adapter SHALL terminate the SSH session and report a timeout error indicating the script name and elapsed duration
8. WHEN the Skill_Adapter forwards file path arguments to a remote script, THE Skill_Adapter SHALL replace the local workspace base path with /opt/ecu-test-workspace and convert backslash path separators to forward slashes

### Requirement 5: Execution Mode Configuration

**User Story:** As a developer, I want to configure whether the ecu-test skill runs locally or remotely, so that I can switch between environments without modifying the skill scripts.

#### Acceptance Criteria

1. THE Skill_Adapter SHALL support exactly two execution modes: "local" and "remote"
2. WHILE the execution mode is set to "local", WHEN a script invocation is requested, THE Skill_Adapter SHALL invoke the script directly on the local machine and SHALL NOT establish any SSH_Connection to Remote_EC2
3. WHILE the execution mode is set to "remote", WHEN a script invocation is requested, THE Skill_Adapter SHALL invoke the script on Remote_EC2 via SSH_Connection
4. THE Skill_Adapter SHALL read execution mode and remote connection parameters from environment variables, falling back to a configuration file when an environment variable is not set, with environment variables taking precedence over configuration file values
5. WHEN the Skill_Adapter starts or receives a script invocation request, THE Skill_Adapter SHALL validate the execution mode configuration before proceeding with any script execution
6. IF the configured execution mode value is neither "local" nor "remote", THEN THE Skill_Adapter SHALL report a configuration error indicating the invalid value and the two accepted values, and SHALL not execute any script
7. IF the execution mode is "remote" and any required connection parameter (hostname, username, key path) is missing from both environment variables and the configuration file, THEN THE Skill_Adapter SHALL report a configuration error listing each missing parameter by name and SHALL block all script execution until the parameters are provided

### Requirement 6: ECU_TEST Lifecycle Management on Remote EC2

**User Story:** As a developer, I want ECU_TEST to be started and managed on the remote EC2 instance, so that it is ready to accept test commands when needed.

#### Acceptance Criteria

1. WHEN the start command is issued in remote mode, THE Skill_Adapter SHALL check if ECU_TEST is already running on Remote_EC2 by querying ECU_TEST_REST_API on localhost:5050 via SSH_Connection and treating an HTTP 200 response as confirmation that ECU_TEST is running
2. IF ECU_TEST is already running when the start command is issued in remote mode, THEN THE Skill_Adapter SHALL skip invoking start.py and report to Kiro that ECU_TEST is already available
3. IF ECU_TEST is not already running when the start command is issued in remote mode, THEN THE Skill_Adapter SHALL invoke the start.py Remote_Skill_Script on Remote_EC2 via SSH_Connection
4. WHEN ECU_TEST is started on Remote_EC2, THE Remote_Skill_Script SHALL poll ECU_TEST_REST_API on localhost:5050 at intervals of no more than 2 seconds and confirm readiness when an HTTP 200 response is received, within a maximum of 60 seconds from the start attempt
5. IF ECU_TEST_REST_API does not return an HTTP 200 response within 60 seconds after a start attempt, THEN THE Remote_Skill_Script SHALL return a non-zero exit code and an error message indicating startup failure
6. IF the SSH_Connection fails during the ECU_TEST running check, THEN THE Skill_Adapter SHALL report a connection error with the target hostname and SHALL NOT attempt to invoke start.py

### Requirement 7: End-to-End Remote Workflow

**User Story:** As a developer, I want the full end-to-end test workflow (create package, generate, execute, report) to work seamlessly in remote mode, so that the remote architecture is transparent to my workflow.

#### Acceptance Criteria

1. WHEN the end-to-end workflow is triggered in remote mode, THE Skill_Adapter SHALL transfer all FMU files referenced in the workflow arguments to Remote_EC2 and verify their presence in ECU_Test_Workspace before invoking create_package.py
2. WHEN the end-to-end workflow is triggered in remote mode, THE Skill_Adapter SHALL execute create_package.py, generate.py, execute.py, and report.py sequentially on Remote_EC2, proceeding to the next script only after the previous script returns a zero exit code
3. IF any script in the remote end-to-end workflow returns a non-zero exit code, THEN THE Skill_Adapter SHALL stop execution of subsequent scripts and report the name of the failed script along with its stdout and stderr output
4. WHEN the end-to-end workflow completes successfully in remote mode, THE Skill_Adapter SHALL retrieve the TRF report file from ECU_Test_Workspace on Remote_EC2 to the local machine and return the report file path and a pass/fail summary to the caller
5. THE Skill_Adapter SHALL map all local workspace paths referenced in the workflow to their corresponding paths in ECU_Test_Workspace (/opt/ecu-test-workspace) on Remote_EC2 by replacing the local workspace base path with the remote base path
