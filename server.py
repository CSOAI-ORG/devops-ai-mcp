#!/usr/bin/env python3
"""
DevOps AI MCP Server
=======================
Infrastructure and DevOps toolkit for AI agents: Docker Compose generation,
CI/CD pipeline building, log analysis, incident classification, and runbook generation.

By MEOK AI Labs | https://meok.ai

Install: pip install mcp
Run:     python server.py
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 30
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade: https://mcpize.com/devops-ai-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------
def _docker_compose(services: list[dict], network_name: str,
                    include_volumes: bool) -> dict:
    """Generate a Docker Compose configuration."""
    if not services:
        return {"error": "Provide at least one service"}

    compose = {"version": "3.8", "services": {}, "networks": {network_name: {"driver": "bridge"}}}
    if include_volumes:
        compose["volumes"] = {}

    for svc in services:
        name = svc.get("name", "app")
        image = svc.get("image", "")
        build_context = svc.get("build", "")
        ports = svc.get("ports", [])
        env_vars = svc.get("environment", {})
        depends = svc.get("depends_on", [])
        replicas = svc.get("replicas", 1)
        health_check = svc.get("health_check", "")

        service_def = {"networks": [network_name], "restart": "unless-stopped"}

        if build_context:
            service_def["build"] = {"context": build_context, "dockerfile": "Dockerfile"}
        elif image:
            service_def["image"] = image
        else:
            service_def["image"] = f"{name}:latest"

        if ports:
            service_def["ports"] = [f"{p}" for p in ports]

        if env_vars:
            service_def["environment"] = env_vars

        if depends:
            service_def["depends_on"] = depends

        if replicas > 1:
            service_def["deploy"] = {"replicas": replicas, "restart_policy": {"condition": "on-failure"}}

        if health_check:
            service_def["healthcheck"] = {
                "test": ["CMD-SHELL", health_check],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "40s",
            }

        if include_volumes:
            vol_name = f"{name}_data"
            service_def["volumes"] = [f"{vol_name}:/data"]
            compose["volumes"][vol_name] = {"driver": "local"}

        compose["services"][name] = service_def

    # Generate YAML-like output
    yaml_lines = ["version: '3.8'", "", "services:"]
    for svc_name, svc_def in compose["services"].items():
        yaml_lines.append(f"  {svc_name}:")
        if "image" in svc_def:
            yaml_lines.append(f"    image: {svc_def['image']}")
        if "build" in svc_def:
            yaml_lines.append(f"    build:")
            yaml_lines.append(f"      context: {svc_def['build']['context']}")
            yaml_lines.append(f"      dockerfile: {svc_def['build']['dockerfile']}")
        if "ports" in svc_def:
            yaml_lines.append(f"    ports:")
            for p in svc_def["ports"]:
                yaml_lines.append(f"      - \"{p}\"")
        if "environment" in svc_def:
            yaml_lines.append(f"    environment:")
            for k, v in svc_def["environment"].items():
                yaml_lines.append(f"      {k}: {v}")
        if "depends_on" in svc_def:
            yaml_lines.append(f"    depends_on:")
            for d in svc_def["depends_on"]:
                yaml_lines.append(f"      - {d}")
        if "volumes" in svc_def:
            yaml_lines.append(f"    volumes:")
            for v in svc_def["volumes"]:
                yaml_lines.append(f"      - {v}")
        if "healthcheck" in svc_def:
            hc = svc_def["healthcheck"]
            yaml_lines.append(f"    healthcheck:")
            yaml_lines.append(f"      test: {hc['test']}")
            yaml_lines.append(f"      interval: {hc['interval']}")
            yaml_lines.append(f"      timeout: {hc['timeout']}")
            yaml_lines.append(f"      retries: {hc['retries']}")
        yaml_lines.append(f"    networks:")
        yaml_lines.append(f"      - {network_name}")
        yaml_lines.append(f"    restart: unless-stopped")
        yaml_lines.append("")

    yaml_lines.append(f"networks:")
    yaml_lines.append(f"  {network_name}:")
    yaml_lines.append(f"    driver: bridge")

    if include_volumes and compose.get("volumes"):
        yaml_lines.append("")
        yaml_lines.append("volumes:")
        for vol in compose["volumes"]:
            yaml_lines.append(f"  {vol}:")
            yaml_lines.append(f"    driver: local")

    return {
        "service_count": len(compose["services"]),
        "network": network_name,
        "has_volumes": include_volumes,
        "compose_yaml": "\n".join(yaml_lines),
        "compose_json": compose,
        "commands": {
            "start": "docker compose up -d",
            "stop": "docker compose down",
            "logs": "docker compose logs -f",
            "rebuild": "docker compose up -d --build",
            "status": "docker compose ps",
        },
    }


def _cicd_pipeline(platform: str, language: str, stages: list[str],
                   deploy_target: str, branch: str) -> dict:
    """Generate CI/CD pipeline configuration."""
    platforms = {
        "github_actions": {"file": ".github/workflows/ci.yml", "format": "yaml"},
        "gitlab_ci": {"file": ".gitlab-ci.yml", "format": "yaml"},
        "jenkins": {"file": "Jenkinsfile", "format": "groovy"},
        "circleci": {"file": ".circleci/config.yml", "format": "yaml"},
    }

    if platform not in platforms:
        return {"error": f"Unknown platform. Use: {list(platforms.keys())}"}

    lang_configs = {
        "python": {"setup": "pip install -r requirements.txt", "test": "pytest --cov", "lint": "ruff check .", "build": "python -m build", "image": "python:3.12-slim"},
        "node": {"setup": "npm ci", "test": "npm test", "lint": "npx eslint .", "build": "npm run build", "image": "node:20-alpine"},
        "go": {"setup": "go mod download", "test": "go test ./...", "lint": "golangci-lint run", "build": "go build -o app .", "image": "golang:1.22-alpine"},
        "rust": {"setup": "cargo fetch", "test": "cargo test", "lint": "cargo clippy", "build": "cargo build --release", "image": "rust:1.77-slim"},
        "java": {"setup": "mvn install -DskipTests", "test": "mvn test", "lint": "mvn checkstyle:check", "build": "mvn package", "image": "maven:3.9-eclipse-temurin-21"},
    }

    lang = lang_configs.get(language, lang_configs["python"])
    deploy_configs = {
        "aws": {"cmd": "aws ecs update-service --cluster prod --service app --force-new-deployment", "env_vars": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]},
        "gcp": {"cmd": "gcloud run deploy app --image gcr.io/$PROJECT_ID/app --region us-central1", "env_vars": ["GCP_PROJECT_ID", "GCP_SA_KEY"]},
        "azure": {"cmd": "az webapp deployment source config-zip -g rg-prod -n app --src app.zip", "env_vars": ["AZURE_CREDENTIALS"]},
        "kubernetes": {"cmd": "kubectl apply -f k8s/ && kubectl rollout status deployment/app", "env_vars": ["KUBECONFIG"]},
        "docker": {"cmd": "docker push registry.example.com/app:latest", "env_vars": ["DOCKER_USERNAME", "DOCKER_PASSWORD"]},
    }

    deploy = deploy_configs.get(deploy_target, deploy_configs["docker"])

    if platform == "github_actions":
        pipeline = f"""name: CI/CD Pipeline

on:
  push:
    branches: [{branch}]
  pull_request:
    branches: [{branch}]

jobs:"""
        for stage in stages:
            if stage == "lint":
                pipeline += f"""
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: {lang['setup']}
      - run: {lang['lint']}
"""
            elif stage == "test":
                pipeline += f"""
  test:
    runs-on: ubuntu-latest
    needs: [lint]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: {lang['setup']}
      - run: {lang['test']}
"""
            elif stage == "build":
                pipeline += f"""
  build:
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4
      - run: {lang['setup']}
      - run: {lang['build']}
"""
            elif stage == "deploy":
                pipeline += f"""
  deploy:
    runs-on: ubuntu-latest
    needs: [build]
    if: github.ref == 'refs/heads/{branch}'
    steps:
      - uses: actions/checkout@v4
      - run: {deploy['cmd']}
    env:"""
                for env in deploy["env_vars"]:
                    pipeline += f"""
      {env}: ${{{{ secrets.{env} }}}}"""
                pipeline += "\n"
    else:
        pipeline = f"# {platform} pipeline for {language} - configure based on platform docs"

    return {
        "platform": platform,
        "language": language,
        "stages": stages,
        "deploy_target": deploy_target,
        "branch": branch,
        "config_file": platforms[platform]["file"],
        "pipeline_config": pipeline,
        "required_secrets": deploy.get("env_vars", []),
        "base_image": lang["image"],
        "commands": {
            "setup": lang["setup"],
            "test": lang["test"],
            "lint": lang["lint"],
            "build": lang["build"],
            "deploy": deploy["cmd"],
        },
    }


def _log_analyzer(log_lines: list[str], time_window_minutes: int) -> dict:
    """Analyze log lines for patterns, errors, and anomalies."""
    if not log_lines:
        return {"error": "No log lines provided"}

    levels = Counter()
    error_messages = []
    warning_messages = []
    timestamps = []
    ip_addresses = Counter()
    status_codes = Counter()
    paths = Counter()

    level_patterns = {
        "ERROR": r'\b(?:ERROR|ERR|FATAL|CRITICAL)\b',
        "WARNING": r'\b(?:WARNING|WARN)\b',
        "INFO": r'\b(?:INFO)\b',
        "DEBUG": r'\b(?:DEBUG|TRACE)\b',
    }

    for line in log_lines:
        # Detect log level
        detected = "UNKNOWN"
        for level, pattern in level_patterns.items():
            if re.search(pattern, line, re.I):
                detected = level
                break
        levels[detected] += 1

        if detected == "ERROR":
            error_messages.append(line[:200])
        elif detected == "WARNING":
            warning_messages.append(line[:200])

        # Extract timestamps
        ts_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if ts_match:
            timestamps.append(ts_match.group())

        # Extract IPs
        ip_match = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', line)
        for ip in ip_match:
            ip_addresses[ip] += 1

        # Extract HTTP status codes
        status_match = re.search(r'\b([1-5]\d{2})\b', line)
        if status_match:
            status_codes[status_match.group(1)] += 1

        # Extract URL paths
        path_match = re.search(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/\S+)', line)
        if path_match:
            paths[path_match.group(1)] += 1

    total = len(log_lines)
    error_rate = (levels.get("ERROR", 0) / max(total, 1)) * 100

    # Anomaly detection
    anomalies = []
    if error_rate > 10:
        anomalies.append({"type": "high_error_rate", "value": f"{error_rate:.1f}%", "severity": "HIGH"})
    if any(c > total * 0.3 for c in ip_addresses.values()):
        top_ip = ip_addresses.most_common(1)[0]
        anomalies.append({"type": "ip_concentration", "value": f"{top_ip[0]}: {top_ip[1]} requests", "severity": "MEDIUM"})
    if status_codes.get("500", 0) > total * 0.05:
        anomalies.append({"type": "server_errors", "value": f"{status_codes['500']} 500 errors", "severity": "HIGH"})
    if status_codes.get("429", 0) > 0:
        anomalies.append({"type": "rate_limiting", "value": f"{status_codes['429']} 429 responses", "severity": "MEDIUM"})

    # Error patterns
    error_patterns = Counter()
    for err in error_messages:
        # Normalize error messages
        normalized = re.sub(r'\d+', 'N', err)
        normalized = re.sub(r'[0-9a-f]{8,}', 'HASH', normalized, flags=re.I)
        error_patterns[normalized[:80]] += 1

    return {
        "total_lines": total,
        "log_levels": dict(levels),
        "error_rate_pct": round(error_rate, 2),
        "time_window_minutes": time_window_minutes,
        "anomalies": anomalies,
        "top_errors": [{"pattern": p, "count": c} for p, c in error_patterns.most_common(5)],
        "top_ips": dict(ip_addresses.most_common(10)),
        "status_codes": dict(status_codes.most_common(10)),
        "top_paths": dict(paths.most_common(10)),
        "error_samples": error_messages[:5],
        "warning_samples": warning_messages[:5],
        "health": "CRITICAL" if error_rate > 20 else "DEGRADED" if error_rate > 5 else "HEALTHY",
    }


def _incident_classifier(title: str, description: str,
                          affected_services: list[str],
                          error_count: int, user_reports: int) -> dict:
    """Classify an incident by severity and category."""
    desc_lower = description.lower()

    # Category detection
    categories = {
        "outage": ["down", "unavailable", "outage", "unreachable", "offline", "502", "503"],
        "performance": ["slow", "latency", "timeout", "degraded", "high load", "response time"],
        "data": ["data loss", "corruption", "inconsistent", "missing data", "wrong data"],
        "security": ["breach", "unauthorized", "vulnerability", "exploit", "attack", "ddos"],
        "deployment": ["deploy", "rollback", "release", "broken build", "regression"],
        "infrastructure": ["disk", "memory", "cpu", "network", "dns", "ssl", "certificate"],
    }

    detected_category = "unknown"
    category_confidence = 0
    for cat, keywords in categories.items():
        matches = sum(1 for k in keywords if k in desc_lower)
        if matches > category_confidence:
            category_confidence = matches
            detected_category = cat

    # Severity scoring
    severity_score = 0

    if error_count > 1000:
        severity_score += 4
    elif error_count > 100:
        severity_score += 3
    elif error_count > 10:
        severity_score += 2
    else:
        severity_score += 1

    if user_reports > 100:
        severity_score += 4
    elif user_reports > 10:
        severity_score += 3
    elif user_reports > 0:
        severity_score += 2

    severity_score += min(3, len(affected_services))

    if detected_category in ["outage", "security", "data"]:
        severity_score += 2

    if severity_score >= 10:
        severity = "P1 - Critical"
        response_time = "15 minutes"
        escalation = "VP Engineering + On-call lead + Comms team"
    elif severity_score >= 7:
        severity = "P2 - High"
        response_time = "30 minutes"
        escalation = "Engineering lead + On-call engineer"
    elif severity_score >= 4:
        severity = "P3 - Medium"
        response_time = "2 hours"
        escalation = "On-call engineer"
    else:
        severity = "P4 - Low"
        response_time = "Next business day"
        escalation = "Team backlog"

    return {
        "title": title,
        "category": detected_category,
        "severity": severity,
        "severity_score": severity_score,
        "response_time": response_time,
        "escalation": escalation,
        "affected_services": affected_services,
        "impact": {
            "error_count": error_count,
            "user_reports": user_reports,
            "services_affected": len(affected_services),
        },
        "immediate_actions": [
            f"Acknowledge incident within {response_time}",
            "Create incident channel and war room",
            f"Assess impact on {', '.join(affected_services[:3])}",
            "Begin root cause investigation",
            f"{'Notify customers' if severity_score >= 7 else 'Monitor for escalation'}",
        ],
    }


def _runbook_generator(service_name: str, incident_type: str,
                       tech_stack: list[str], alert_threshold: str) -> dict:
    """Generate an operational runbook for a service and incident type."""
    runbook_templates = {
        "high_cpu": {
            "title": f"{service_name} - High CPU Usage Runbook",
            "trigger": f"CPU usage exceeds {alert_threshold}",
            "steps": [
                {"step": 1, "action": "Check current CPU usage", "command": f"top -b -n 1 | head -20", "expected": "Identify top processes"},
                {"step": 2, "action": "Check application metrics", "command": f"curl -s localhost:9090/metrics | grep cpu", "expected": "Application-level CPU metrics"},
                {"step": 3, "action": "Check for runaway processes", "command": f"ps aux --sort=-%cpu | head -10", "expected": "Identify abnormal processes"},
                {"step": 4, "action": "Check application logs", "command": f"journalctl -u {service_name} --since '30 min ago' | grep -i error", "expected": "Recent errors"},
                {"step": 5, "action": "Scale if needed", "command": f"kubectl scale deployment {service_name} --replicas=3", "expected": "Pods scaling up"},
                {"step": 6, "action": "Restart if unresolved", "command": f"systemctl restart {service_name}", "expected": "Service restarts, CPU drops"},
            ],
        },
        "high_memory": {
            "title": f"{service_name} - High Memory Usage Runbook",
            "trigger": f"Memory usage exceeds {alert_threshold}",
            "steps": [
                {"step": 1, "action": "Check memory usage", "command": "free -h && cat /proc/meminfo | head -5", "expected": "Current memory state"},
                {"step": 2, "action": "Identify memory consumers", "command": "ps aux --sort=-%mem | head -10", "expected": "Top memory processes"},
                {"step": 3, "action": "Check for memory leaks", "command": f"curl -s localhost:9090/metrics | grep memory", "expected": "Memory growth pattern"},
                {"step": 4, "action": "Clear caches if safe", "command": "sync && echo 3 > /proc/sys/vm/drop_caches", "expected": "Cache memory freed"},
                {"step": 5, "action": "Restart application", "command": f"systemctl restart {service_name}", "expected": "Memory usage drops"},
            ],
        },
        "service_down": {
            "title": f"{service_name} - Service Down Runbook",
            "trigger": f"Health check fails for {service_name}",
            "steps": [
                {"step": 1, "action": "Verify service status", "command": f"systemctl status {service_name}", "expected": "Check if active/failed"},
                {"step": 2, "action": "Check logs", "command": f"journalctl -u {service_name} -n 50 --no-pager", "expected": "Identify crash reason"},
                {"step": 3, "action": "Check dependencies", "command": "curl -s localhost:5432/health && curl -s localhost:6379/health", "expected": "DB and cache reachable"},
                {"step": 4, "action": "Check disk space", "command": "df -h", "expected": "Adequate disk space"},
                {"step": 5, "action": "Check network", "command": "netstat -tlnp | grep -E '(80|443|8080)'", "expected": "Ports available"},
                {"step": 6, "action": "Restart service", "command": f"systemctl restart {service_name}", "expected": "Service comes back online"},
                {"step": 7, "action": "Verify recovery", "command": f"curl -s localhost:8080/health", "expected": "200 OK response"},
            ],
        },
        "high_latency": {
            "title": f"{service_name} - High Latency Runbook",
            "trigger": f"P99 latency exceeds {alert_threshold}",
            "steps": [
                {"step": 1, "action": "Check current latency metrics", "command": f"curl -s localhost:9090/metrics | grep latency", "expected": "Current latency values"},
                {"step": 2, "action": "Check database performance", "command": "PGPASSWORD=$DB_PASS psql -h localhost -U app -c 'SELECT * FROM pg_stat_activity WHERE state != \\'idle\\';'", "expected": "Active queries"},
                {"step": 3, "action": "Check connection pools", "command": f"curl -s localhost:9090/metrics | grep pool", "expected": "Pool utilization"},
                {"step": 4, "action": "Check downstream services", "command": "for svc in api-gateway auth-service; do curl -w '%{time_total}' -o /dev/null -s http://$svc:8080/health; echo \" $svc\"; done", "expected": "Response times"},
                {"step": 5, "action": "Scale horizontally", "command": f"kubectl scale deployment {service_name} --replicas=5", "expected": "Load distributed"},
            ],
        },
        "disk_full": {
            "title": f"{service_name} - Disk Full Runbook",
            "trigger": f"Disk usage exceeds {alert_threshold}",
            "steps": [
                {"step": 1, "action": "Check disk usage", "command": "df -h", "expected": "Identify full partition"},
                {"step": 2, "action": "Find large files", "command": "du -sh /var/log/* | sort -rh | head -10", "expected": "Largest files"},
                {"step": 3, "action": "Rotate logs", "command": "logrotate -f /etc/logrotate.conf", "expected": "Logs rotated"},
                {"step": 4, "action": "Clean old containers", "command": "docker system prune -f", "expected": "Docker space freed"},
                {"step": 5, "action": "Clean package cache", "command": "apt clean && rm -rf /tmp/*", "expected": "Temp files removed"},
            ],
        },
    }

    if incident_type not in runbook_templates:
        incident_type = "service_down"

    template = runbook_templates[incident_type]

    return {
        "runbook_title": template["title"],
        "service": service_name,
        "incident_type": incident_type,
        "trigger": template["trigger"],
        "tech_stack": tech_stack,
        "alert_threshold": alert_threshold,
        "steps": template["steps"],
        "escalation_policy": {
            "level_1": {"time": "15 min", "who": "On-call engineer", "action": "Follow runbook steps"},
            "level_2": {"time": "30 min", "who": "Team lead", "action": "Assist with troubleshooting"},
            "level_3": {"time": "60 min", "who": "Engineering manager", "action": "Coordinate response, customer comms"},
        },
        "post_incident": [
            "Update incident timeline",
            "Write root cause analysis",
            "Create follow-up tickets for permanent fixes",
            "Schedule post-mortem meeting within 48 hours",
            "Update monitoring and alerting if gaps found",
        ],
        "available_incident_types": list(runbook_templates.keys()),
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "DevOps AI MCP",
    instructions="Infrastructure and DevOps toolkit: Docker Compose generation, CI/CD pipeline building, log analysis, incident classification, and runbook generation. By MEOK AI Labs.")


@mcp.tool()
def docker_compose_generator(services: list[dict], network_name: str = "app-network",
                             include_volumes: bool = True) -> dict:
    """Generate a Docker Compose configuration with networking, health checks,
    and volume management.

    Args:
        services: List of services as [{"name": "api", "image": "node:20", "ports": ["3000:3000"], "environment": {"NODE_ENV": "production"}, "depends_on": ["db"], "health_check": "curl -f http://localhost:3000/health"}]
        network_name: Docker network name
        include_volumes: Whether to create named volumes for services
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _docker_compose(services, network_name, include_volumes)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def cicd_pipeline_builder(platform: str = "github_actions", language: str = "python",
                          stages: list[str] = ["lint", "test", "build", "deploy"],
                          deploy_target: str = "docker",
                          branch: str = "main") -> dict:
    """Generate a CI/CD pipeline configuration for common platforms and languages.

    Args:
        platform: CI platform (github_actions, gitlab_ci, jenkins, circleci)
        language: Project language (python, node, go, rust, java)
        stages: Pipeline stages to include (lint, test, build, deploy)
        deploy_target: Deployment target (aws, gcp, azure, kubernetes, docker)
        branch: Branch that triggers deployment
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _cicd_pipeline(platform, language, stages, deploy_target, branch)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def log_analyzer(log_lines: list[str], time_window_minutes: int = 60) -> dict:
    """Analyze log lines to extract error patterns, anomalies, status code
    distributions, and top IP addresses.

    Args:
        log_lines: List of raw log lines to analyze
        time_window_minutes: Time window the logs cover (for rate calculations)
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _log_analyzer(log_lines, time_window_minutes)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def incident_classifier(title: str, description: str,
                        affected_services: list[str] = [],
                        error_count: int = 0,
                        user_reports: int = 0) -> dict:
    """Classify an incident by severity (P1-P4) and category with recommended
    response actions and escalation paths.

    Args:
        title: Incident title
        description: Detailed incident description
        affected_services: List of affected service names
        error_count: Number of errors observed
        user_reports: Number of user-reported issues
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _incident_classifier(title, description, affected_services, error_count, user_reports)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def runbook_generator(service_name: str, incident_type: str = "service_down",
                      tech_stack: list[str] = [],
                      alert_threshold: str = "90%") -> dict:
    """Generate an operational runbook with step-by-step commands, expected
    outcomes, and escalation policies.

    Args:
        service_name: Name of the service
        incident_type: Type of incident (high_cpu, high_memory, service_down, high_latency, disk_full)
        tech_stack: Technologies used (e.g. ["python", "postgres", "redis"])
        alert_threshold: Alert threshold that triggered the runbook
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _runbook_generator(service_name, incident_type, tech_stack, alert_threshold)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
