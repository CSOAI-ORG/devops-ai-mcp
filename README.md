# DevOps AI MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

Infrastructure and DevOps toolkit: Docker Compose generation, CI/CD pipeline building, log analysis, incident classification, and runbook generation.

## Tools

| Tool | Description |
|------|-------------|
| `docker_compose_generator` | Generate Docker Compose configs with networking and health checks |
| `cicd_pipeline_builder` | Generate CI/CD pipelines for GitHub Actions, GitLab CI, etc. |
| `log_analyzer` | Analyze log lines for error patterns, anomalies, and status codes |
| `incident_classifier` | Classify incidents by severity (P1-P4) with escalation paths |
| `runbook_generator` | Generate operational runbooks with step-by-step commands |

## Installation

```bash
pip install mcp
```

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "devops": {
      "command": "python",
      "args": ["/path/to/devops-ai-mcp/server.py"]
    }
  }
}
```

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 30 calls/day | $0 |
| Pro | Unlimited + premium features | $9/mo |
| Enterprise | Custom + SLA + support | Contact us |

## License

MIT
