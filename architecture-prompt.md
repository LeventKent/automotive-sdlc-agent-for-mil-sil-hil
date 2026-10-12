# Architecture Prompt

> **Status: IMPLEMENTED** (as of 2026-07). See README.md for current operational details.

## Context

I am building an agentic SDLC demo, where Kiro pulls requirements from a Polarion server using an MCP server. Then Kiro can use the MATLAB skill to create a Simulink model. Then Kiro uses a skill for ecu.test (a program which can define tests based on requirements and execute tests using a Matlab Simulink model exported as FMU) to start the ecu.test program locally, generate test steps (see generate.md), create tests (see create-package.md) and execute test (execute.md).

## Current Architecture

Currently ecu.test program is running locally along with Kiro.

## Target Architecture

I want the ecu.test program to run remotely on a separate EC2 machine (at least t3.large or any other EC2 instance with equal or more memory, no accelerator needed, Linux/Ubuntu dist).

Kiro will use the ecu-test skill to SSH into the remote machine to call the skill-scripts (which are currently being called locally, see .kiro/skills/ecu-test/scripts). We call these remote-skill-scripts.

## Implementation Hints

I believe this can be achieved by (these are probably not all of the steps):

- Creating a CloudFormation template 
-- to ramp up an EC2 machine and installing ecu.test 
-- create a local folder which includes the remote-skill-scripts 
-- create another local folder (ecu-test-workspace) for the FMU files.
-- Adjust the current ecu-test-skill to have the option to run the remote-skill-scripts via ssh.
