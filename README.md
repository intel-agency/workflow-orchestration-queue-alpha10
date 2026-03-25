# Workflow Orchestration Queue (OS-APOW)

> **Headless Agentic Orchestration Platform** - Transform GitHub Issues into automated execution orders for AI-driven development.

[![CI](https://github.com/intel-agency/workflow-orchestration-queue-alpha10/actions/workflows/ci.yml/badge.svg)](https://github.com/intel-agency/workflow-orchestration-queue-alpha10/actions/workflows/ci.yml)

## Overview

workflow-orchestration-queue represents a paradigm shift from **Interactive AI Coding** to **Headless Agentic Orchestration**. Instead of requiring a human-in-the-loop to guide AI tools, this system autonomously:

1. **Ingests** GitHub webhooks (issues, comments, PRs)
2. **Queues** tasks via GitHub labels
3. **Dispatches** specialized AI agents to implement features
4. **Creates** Pull Requests for human review

The system is designed to be **Self-Bootstrapping** - once initialized, the AI manages all further development.

## Architecture

### The Four Pillars

| Pillar | Component | Technology | Purpose |
|--------|-----------|------------|---------|
| **The Ear** | Notifier Service | FastAPI, Pydantic | Webhook ingestion and HMAC verification |
| **The State** | GitHub Issues | Labels, Assignees | Distributed state management |
| **The Brain** | Sentinel | Python async | Polling, claiming, dispatching |
| **The Hands** | Worker | opencode CLI, Docker | Code execution in isolated containers |

### Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml               # uv dependencies and metadata
├── src/
│   ├── notifier_service.py      # FastAPI Webhook ("The Ear")
│   ├── orchestrator_sentinel.py # Background polling ("The Brain")
│   ├── models/
│   │   ├── work_item.py         # Unified WorkItem, TaskType, scrub_secrets()
│   │   └── github_events.py     # GitHub webhook payload schemas
│   └── queue/
│       └── github_queue.py      # ITaskQueue + GitHubQueue implementation
├── tests/                       # pytest test suite
├── scripts/                     # Shell bridge execution layer
├── local_ai_instruction_modules/# Markdown workflow modules for AI
├── docs/                        # Architecture and API documentation
└── .ai-repository-summary.md    # Comprehensive AI-readable summary
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for worker containers)
- GitHub CLI (`gh`)

### Installation

```bash
# Clone the repository
git clone https://github.com/intel-agency/workflow-orchestration-queue-alpha10.git
cd workflow-orchestration-queue-alpha10

# Install dependencies
uv pip install -e ".[dev]"
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your values
# Required: GITHUB_TOKEN, GITHUB_REPO, SENTINEL_BOT_LOGIN
```

### Running

```bash
# Start the notifier service (webhook receiver)
uvicorn src.notifier_service:app --reload --port 8000

# In another terminal, start the sentinel (polling orchestrator)
python -m src.orchestrator_sentinel
```

### Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Development

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Linting

```bash
# Run linter
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking
mypy src/
```

## State Machine

| Label | Meaning |
|-------|---------|
| `agent:queued` | Task validated, awaiting Sentinel |
| `agent:in-progress` | Sentinel claimed the issue |
| `agent:reconciling` | Stale task being recovered |
| `agent:success` | Workflow completed successfully |
| `agent:error` | Technical failure occurred |
| `agent:infra-failure` | Infrastructure failure (timeout, OOM) |

## Documentation

- [AI Repository Summary](./.ai-repository-summary.md) - Comprehensive overview for AI agents
- [Architecture Documentation](./docs/architecture/) - System architecture and ADRs
- [API Documentation](./docs/api/) - Endpoint documentation
- [Plan Documents](./plan_docs/) - Implementation specifications

## Security

- **HMAC Verification**: All webhooks verified with `X-Hub-Signature-256`
- **Credential Scrubbing**: Secrets automatically redacted from logs
- **Network Isolation**: Workers run in isolated Docker networks
- **Resource Constraints**: 2 CPU, 4GB RAM per worker

## Contributing

1. Create a feature branch
2. Make changes following the coding conventions
3. Run linting and tests
4. Submit a Pull Request

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

*For a comprehensive AI-readable summary, see [.ai-repository-summary.md](./.ai-repository-summary.md)*
