# Technology Stack: workflow-orchestration-queue (OS-APOW)

## Overview

This document defines the complete technology stack for the workflow-orchestration-queue system, a headless agentic orchestration platform that transforms GitHub Issues into automated execution orders for AI-driven development.

---

## Languages

| Language | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Primary language for Orchestrator, API Webhook receiver, and all system logic |
| PowerShell Core (pwsh) | 7.x | Shell Bridge Scripts, Auth synchronization |
| Bash | 5.x | Cross-platform CLI interactions, Docker orchestration |

---

## Core Frameworks

| Framework | Version | Purpose |
|-----------|---------|---------|
| FastAPI | Latest | High-performance async web framework for the Webhook Notifier ("The Ear") |
| Uvicorn | Latest | ASGI web server for serving the FastAPI application |
| Pydantic | Latest | Data validation, settings management, and schema definitions |

---

## HTTP & API Clients

| Library | Version | Purpose |
|---------|---------|---------|
| httpx | Latest | Fully asynchronous HTTP client for GitHub REST API calls |

---

## Package Management

| Tool | Version | Purpose |
|------|---------|---------|
| uv | 0.10.x+ | Rust-based Python package installer and dependency resolver |
| pip | Latest | Fallback package installer |

---

## Containerization & Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Core worker execution engine providing sandboxing and environment consistency |
| Docker Compose | Multi-container orchestration for complex test environments |
| DevContainers | Reproducible development and execution environments |

---

## AI/LLM Integration

| Component | Purpose |
|-----------|---------|
| opencode CLI | AI agent runtime for executing instruction modules |
| GLM-5 (ZhipuAI) | Primary LLM model for agent reasoning |
| Claude 3.5 Sonnet | Alternative LLM model option |

---

## External Services

| Service | Purpose |
|---------|---------|
| GitHub API | Task queue state management, issue/PR operations |
| GitHub App | Webhook delivery and authentication |
| GitHub Projects | Project tracking and visibility |

---

## Development Tools

| Tool | Purpose |
|------|---------|
| git | Version control |
| gh CLI | GitHub API interactions from command line |
| ngrok / tailscale | Local-to-cloud tunneling for webhook development |

---

## Key Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
]
```

---

## Environment Variables

### Required (Core)

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub App Installation Token for API access |
| `GITHUB_REPO` | Target repository (format: `owner/repo`) |
| `SENTINEL_BOT_LOGIN` | GitHub login of the bot account for task locking |

### Optional (Tuning)

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTINEL_POLL_INTERVAL` | 60 | Polling interval in seconds |
| `SENTINEL_HEARTBEAT_INTERVAL` | 300 | Heartbeat comment interval in seconds |
| `WEBHOOK_SECRET` | - | HMAC secret for webhook signature verification |

---

## Architecture Pattern

The system follows an **event-driven, decoupled architecture** with four conceptual pillars:

1. **The Ear** (FastAPI Webhook) - Event ingestion
2. **The State** (GitHub Issues) - Distributed state management
3. **The Brain** (Sentinel Orchestrator) - Task coordination
4. **The Hands** (Opencode Worker) - Code execution

---

## References

- [Architecture Guide v3.2](./OS-APOW%20Architecture%20Guide%20v3.2.md)
- [Development Plan v4.2](./OS-APOW%20Development%20Plan%20v4.2.md)
- [Implementation Specification v1.2](./OS-APOW%20Implementation%20Specification%20v1.2.md)
