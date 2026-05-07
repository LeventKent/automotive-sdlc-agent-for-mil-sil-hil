# Polarion MCP Server

A Model Context Protocol (MCP) server that provides seamless integration between Polarion ALM and AI assistants like Kiro. Built with FastMCP 2.10.6, this server enables AI agents to interact with Polarion projects, work items, test runs, documents, and more.

## Features

- **Full MCP Protocol Support**: Implements tools, resources, and prompts
- **13 Powerful Tools**: Comprehensive access to Polarion data including plan support
- **Plan Project Support**: Special tools for projects organized around plans (releases/iterations)
- **Secure Authentication**: Token-based authentication with Polarion
- **Production Ready**: Robust error handling and logging

## Prerequisites

- Python 3.10+
- Access to a Polarion instance with:
  - Polarion URL
  - Username
  - Personal access token

## Installation

1. **Clone the Repository**

   Create a virtual environment under `polarion-mcp`:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

2. **Configure Polarion Credentials**

   Adjust `POLARION_URL`, `POLARION_USER`, `POLARION_TOKEN` in `mcp.json`.

3. **Configure the Polarion Project to Connect**

   Edit `polarion_config.yaml`:

   ```yaml
   projects:
     myproject:
       id: TEMPMON004
       name: TEMPMON004
   ```
