# AGENTS.md

> AI coding agent instructions for workflow-orchestration-queue (OS-APOW)

## Project Overview

workflow-orchestration-queue is a **headless agentic orchestration platform** that transforms GitHub Issues into automated execution orders for AI-driven development. The system replaces interactive AI coding with a persistent, event-driven infrastructure.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, httpx, uv, Docker, DevContainers

### The Four Pillars

| Pillar | Component | Technology | Purpose |
|--------|-----------|------------|---------|
| **The Ear** | Notifier Service | FastAPI, Pydantic | Webhook ingestion and HMAC verification |
| **The State** | GitHub Issues | Labels, Assignees | Distributed state management |
| **The Brain** | Sentinel | Python async | Polling, claiming, dispatching |
| **The Hands** | Worker | opencode CLI, Docker | Code execution in isolated containers |

## Setup Commands

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for worker containers)
- GitHub CLI (`gh`)

### Installation

```bash
# Install all dependencies (including dev dependencies)
uv sync --all-extras

# Or install with specific extra
uv sync --extra dev
```

### Running Services

```bash
# Start the notifier service (webhook receiver)
uv run uvicorn src.notifier_service:app --reload --port 8000

# Start the sentinel (polling orchestrator) in another terminal
uv run python -m src.orchestrator_sentinel
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub App Installation Token |
| `GITHUB_REPO` | Yes | Target repository (owner/repo) |
| `SENTINEL_BOT_LOGIN` | Yes | Bot account login for task locking |
| `WEBHOOK_SECRET` | No | HMAC secret for webhook verification |
| `SENTINEL_POLL_INTERVAL` | No | Polling interval in seconds (default: 60) |

## Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml               # uv dependencies, tool config (ruff, mypy, pytest)
├── uv.lock                      # Deterministic lockfile
├── src/
│   ├── __init__.py
│   ├── notifier_service.py      # FastAPI Webhook ("The Ear")
│   ├── orchestrator_sentinel.py # Background polling ("The Brain")
│   ├── models/
│   │   ├── __init__.py
│   │   ├── work_item.py         # WorkItem, TaskType, WorkItemStatus, scrub_secrets()
│   │   └── github_events.py     # GitHub webhook payload schemas (Pydantic)
│   └── queue/
│       ├── __init__.py
│       └── github_queue.py      # ITaskQueue interface + GitHubQueue implementation
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_work_item.py        # WorkItem and scrub_secrets tests
│   ├── test_github_events.py    # GitHub event parsing tests
│   └── test_github_queue.py     # GitHubQueue async tests
├── scripts/                     # Shell bridge and utility scripts
│   ├── devcontainer-opencode.sh # Worker container orchestration
│   ├── gh-auth.ps1              # GitHub App auth helper
│   └── validate.ps1             # Local validation script
├── local_ai_instruction_modules/ # Markdown workflow modules for AI
├── docs/                        # Architecture and API documentation
├── plan_docs/                   # Implementation specifications
└── .ai-repository-summary.md    # Comprehensive AI-readable summary
```

## Code Style

Configured in `pyproject.toml` under `[tool.ruff]` and `[tool.mypy]`.

### Key Conventions

- **Python Version:** 3.12+ (target-version: py312)
- **Line Length:** 100 characters
- **Type Hints:** Strict MyPy with `disallow_untyped_defs = true`
- **Pydantic Models:** Use Pydantic v2 with `model_config`
- **Async:** Use `async/await` with `httpx` for HTTP calls
- **Imports:** isort via Ruff (known-first-party: `["src"]`)

### Ruff Rules Enabled

- `E`, `W` - pycodestyle errors and warnings
- `F` - Pyflakes
- `I` - isort
- `B` - flake8-bugbear
- `C4` - flake8-comprehensions
- `UP` - pyupgrade
- `ARG` - flake8-unused-arguments
- `SIM` - flake8-simplify
- `TCH` - flake8-type-checking
- `PTH` - flake8-use-pathlib
- `ERA` - eradicate (commented code)
- `RUF` - Ruff-specific rules

### Formatting Commands

```bash
# Check linting
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check src/ tests/ --fix

# Check formatting
uv run ruff format --check src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

## Testing Instructions

### Run Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
uv run python -m pytest tests/test_work_item.py -v

# Run specific test
uv run python -m pytest tests/test_work_item.py::TestScrubSecrets -v
```

### Test Conventions

- **Location:** All tests in `tests/` directory
- **Naming:** `test_*.py` files, `Test*` classes, `test_*` functions
- **Fixtures:** Shared fixtures in `conftest.py`
- **Async:** Use `pytest-asyncio` with `asyncio_mode = "auto"`
- **Coverage:** Track branch coverage, exclude `TYPE_CHECKING` blocks

### Writing Tests

- Add tests for all new functionality
- Use Pydantic models for test data construction
- Use `FAKE-KEY-FOR-TESTING-*` format for test secrets (never real prefixes like `sk-`, `ghp_`)
- Mock external HTTP calls with `respx` or `pytest-httpx`

## Architecture Notes

### State Machine (GitHub Labels)

| Label | Meaning |
|-------|---------|
| `agent:queued` | Task validated, awaiting Sentinel |
| `agent:in-progress` | Sentinel claimed the issue |
| `agent:reconciling` | Stale task being recovered |
| `agent:success` | Workflow completed successfully |
| `agent:error` | Technical failure occurred |
| `agent:infra-failure` | Infrastructure failure (timeout, OOM) |
| `agent:stalled-budget` | Budget/token limit exceeded |

### Assign-Then-Verify Pattern (Distributed Locking)

The Sentinel uses this pattern to claim tasks:

1. Assign sentinel bot to issue
2. Re-fetch the issue
3. Verify assignment before proceeding

### Shell-Bridge Execution

All worker interactions go through `scripts/devcontainer-opencode.sh`:

```bash
./scripts/devcontainer-opencode.sh up      # Provision network and volumes
./scripts/devcontainer-opencode.sh start   # Launch opencode server
./scripts/devcontainer-opencode.sh prompt "{workflow}"  # Dispatch work
./scripts/devcontainer-opencode.sh stop    # Clean up
```

### Secret Scrubbing

The `scrub_secrets()` function in `src/models/work_item.py` removes:
- GitHub PATs (`ghp_*`, `ghs_*`, `gho_*`, `github_pat_*`)
- Bearer tokens
- OpenAI keys (`sk-*`)
- ZhipuAI keys
- Generic API key patterns

## PR and Commit Guidelines

### Before Committing

1. Run linting: `uv run ruff check src/ tests/`
2. Format code: `uv run ruff format src/ tests/`
3. Run tests: `uv run python -m pytest tests/ -v`
4. Type check: `uv run mypy src/`

### Commit Message Format

```
type(scope): brief description

# Examples:
feat(notifier): add HMAC signature verification
fix(sentinel): correct assign-then-verify race condition
test(work_item): add scrub_secrets test cases
docs(readme): update installation instructions
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates

### CI Pipeline

The CI workflow (`.github/workflows/ci.yml`) runs on push to `main`/`develop` and PRs to `main`:

1. **Lint:** Ruff linter + formatter check + MyPy
2. **Test:** pytest with coverage
3. **Docker Build:** Build and validate Dockerfile
4. **Security Scan:** Gitleaks for secret detection

## Common Pitfalls

### Dev Dependencies Not Installed

Running `uv sync` without `--all-extras` or `--extra dev` will skip test/lint dependencies. Always use:

```bash
uv sync --all-extras
```

### Async Test Failures

Tests using `async def` require `pytest-asyncio`. Ensure dev dependencies are installed.

### Secret Patterns in Tests

Never use real secret prefixes in test fixtures. Use synthetic values like `FAKE-KEY-FOR-TESTING-00000000`.

### Type Checking Strictness

MyPy is configured in strict mode. All functions must have type hints. Use `TYPE_CHECKING` block for circular imports.

## Local Validation

Use the provided validation script for comprehensive checks:

```bash
# Run all validation (lint, scan, test)
pwsh -NoProfile -File ./scripts/validate.ps1 -All

# Individual checks
pwsh -NoProfile -File ./scripts/validate.ps1 -Lint
pwsh -NoProfile -File ./scripts/validate.ps1 -Scan
pwsh -NoProfile -File ./scripts/validate.ps1 -Test
```

## References

- [Architecture Documentation](./plan_docs/architecture.md) - Detailed system architecture
- [Tech Stack](./plan_docs/tech-stack.md) - Complete technology stack
- [AI Repository Summary](./.ai-repository-summary.md) - Comprehensive AI-readable overview
- [README.md](./README.md) - User-facing documentation

---

*This file follows the [AGENTS.md](https://agents.md/) specification for AI coding agent compatibility.*
