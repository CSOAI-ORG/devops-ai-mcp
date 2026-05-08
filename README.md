<div align="center">

# Devops Ai MCP

**MCP server for devops ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-devops-ai-mcp)](https://pypi.org/project/meok-devops-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Devops Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `docker_compose_generator` | Generate a Docker Compose configuration with networking, health checks, |
| `cicd_pipeline_builder` | Generate a CI/CD pipeline configuration for common platforms and languages. |
| `log_analyzer` | Analyze log lines to extract error patterns, anomalies, status code |
| `incident_classifier` | Classify an incident by severity (P1-P4) and category with recommended |
| `runbook_generator` | Generate an operational runbook with step-by-step commands, expected |

## Installation

```bash
pip install meok-devops-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "devops-ai-mcp": {
      "command": "python",
      "args": ["-m", "meok_devops_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
