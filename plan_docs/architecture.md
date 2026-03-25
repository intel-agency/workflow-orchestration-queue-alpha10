# Architecture Overview: workflow-orchestration-queue (OS-APOW)

## Executive Summary

workflow-orchestration-queue represents a paradigm shift from **Interactive AI Coding** to **Headless Agentic Orchestration**. Traditional AI developer tools require a human-in-the-loop to navigate files, provide context, and trigger executions. This system replaces manual overhead with a persistent, event-driven infrastructure that transforms GitHub Issues into "Execution Orders" autonomously fulfilled by specialized AI agents.

The system is designed to be **Self-Bootstrapping** - once initialized, the AI manages all further development of the system itself.

---

## The Four Pillars

### 1. The Ear (Work Event Notifier)

**Technology:** Python 3.12, FastAPI, Pydantic

**Role:** Primary gateway for external stimuli and asynchronous triggers.

**Responsibilities:**
- **Secure Webhook Ingestion:** Hardened endpoint receives `issues`, `issue_comment`, and `pull_request` events from GitHub App
- **Cryptographic Verification:** HMAC SHA256 validation against `WEBHOOK_SECRET` to prevent prompt injection via spoofed webhooks
- **Intelligent Event Triage:** Parses issue body and labels using Pydantic models, maps payloads to unified `WorkItem` objects
- **Queue Initialization:** Applies `agent:queued` label to trigger Sentinel processing

**Key Endpoint:** `/webhooks/github`

---

### 2. The State (Work Queue)

**Implementation:** GitHub Issues, Labels, and Milestones

**Philosophy:** "Markdown as a Database"

**Benefits:**
- World-class audit logs
- Transparent versioning of requirements
- Out-of-box UI for human supervision
- Real-time intervention via commenting

**State Machine (Label Logic):**

| Label | Meaning |
|-------|---------|
| `agent:queued` | Task validated, awaiting Sentinel |
| `agent:in-progress` | Sentinel claimed the issue |
| `agent:reconciling` | Stale task being recovered |
| `agent:success` | Workflow completed successfully |
| `agent:error` | Technical failure occurred |
| `agent:infra-failure` | Infrastructure failure (timeout, OOM) |
| `agent:stalled-budget` | Budget/token limit exceeded |

**Concurrency Control:** GitHub "Assignees" as distributed lock. Sentinel uses **assign-then-verify** pattern:
1. Attempt to assign `SENTINEL_BOT_LOGIN` to issue
2. Re-fetch the issue
3. Verify assignment before proceeding

---

### 3. The Brain (Sentinel Orchestrator)

**Technology:** Python (Async), PowerShell Core, Docker CLI

**Role:** Persistent supervisor managing Worker lifecycle and intent-to-command mapping.

**Lifecycle:**

1. **Polling Discovery:** Every 60 seconds, scan for `agent:queued` issues via GitHub REST API
2. **Auth Synchronization:** Run `scripts/gh-auth.ps1` and `scripts/common-auth.ps1`
3. **Shell-Bridge Execution:** Invoke `devcontainer-opencode.sh` commands
4. **Workflow Mapping:** Translate issue type to specific prompt string
5. **Telemetry:** Capture stdout, post heartbeat comments every 5 minutes
6. **Environment Reset:** Stop worker container between tasks
7. **Graceful Shutdown:** Handle `SIGTERM`/`SIGINT`, finish current task, exit cleanly

**Shell-Bridge Commands:**
- `./scripts/devcontainer-opencode.sh up` - Provision network and volumes
- `./scripts/devcontainer-opencode.sh start` - Launch opencode-server
- `./scripts/devcontainer-opencode.sh prompt "{workflow}"` - Dispatch work

---

### 4. The Hands (Opencode Worker)

**Technology:** opencode CLI, LLM (GLM-5 or Claude 3.5 Sonnet)

**Environment:** High-fidelity DevContainer from workflow-orchestration-queue-alpha10

**Capabilities:**
- **Contextual Awareness:** Accesses local project structure, runs `update-remote-indices.ps1` for vector-indexed codebase view
- **Instructional Logic:** Reads/executes `.md` workflow modules from `/local_ai_instruction_modules/`
- **Verification:** Runs local test suites before submitting PR

---

## Key Architectural Decisions (ADRs)

### ADR 07: Standardized Shell-Bridge Execution

**Decision:** Orchestrator interacts with agentic environment exclusively via `devcontainer-opencode.sh`

**Rationale:** Reusing shell scripts ensures environment parity with local developers, avoids "Configuration Drift"

**Consequence:** Python code stays lightweight; Shell handles "Heavy Lifting" of container orchestration

---

### ADR 08: Polling-First Resiliency Model

**Decision:** Sentinel uses polling as primary discovery; Webhooks are "Optimization"

**Rationale:** Webhooks are "Fire and Forget" - if server is down, events are lost. Polling ensures "State Reconciliation" on restart

**Consequence:** System is inherently self-healing and resilient against downtime

---

### ADR 09: Provider-Agnostic Interface Layer

**Decision:** All queue interactions abstract behind `ITaskQueue` interface using Strategy Pattern

**Rationale:** Enables future "Ticket Provider Swapping" (Linear, Notion, SQL queues) without rewriting orchestrator logic

**Interface Methods:**
- `fetch_queued_items()`
- `claim_task(id, sentinel_id)`
- `update_progress(id, log_line)`
- `finish_task(id, artifacts)`

---

## Data Flow (Happy Path)

```
1. User opens GitHub Issue with application-plan.md template
2. GitHub Webhook hits Notifier (FastAPI)
3. Notifier verifies signature, confirms pattern, adds agent:queued label
4. Sentinel poller detects new label
5. Sentinel assigns issue to bot account, updates to agent:in-progress
6. Sentinel runs git clone/pull on target repo
7. Sentinel executes devcontainer-opencode.sh up
8. Sentinel dispatches prompt with workflow instructions
9. Worker reads issue, creates sub-tasks, implements features
10. Worker posts "Execution Complete" comment
11. Sentinel removes in-progress, adds agent:success
```

---

## Security Model

### Network Isolation
- Worker containers in dedicated Docker network
- Cannot access host network or local subnet
- Internet access for packages only

### Credential Scoping
- GitHub App Installation Token managed by Sentinel
- Passed via temporary environment variable
- Destroyed when session ends

### Credential Scrubbing
- All log output through `scrub_secrets()` regex utility
- Strips: `ghp_*`, `ghs_*`, `gho_*`, `github_pat_*`, `Bearer`, `sk-*`, ZhipuAI keys
- Produces sanitized logs for GitHub, raw logs for forensic audit

### Resource Constraints
- Worker containers: 2 CPUs, 4GB RAM hard cap
- Prevents rogue agent DoS on host

---

## Self-Bootstrapping Lifecycle

| Stage | Action | Controller |
|-------|--------|------------|
| 0. Seeding | Clone workflow-orchestration-queue-alpha10, seed plan docs | Developer |
| 1. Init | Run `devcontainer-opencode.sh up` | Developer |
| 2. Project Setup | Run orchestrate-project-setup workflow | Agent |
| 3. Handover | Start sentinel.py service | Developer |
| 4. Autonomous | AI builds remaining features via task tickets | Agent |

---

## Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml               # uv dependencies and metadata
├── uv.lock                      # Deterministic lockfile
├── src/
│   ├── notifier_service.py      # FastAPI Webhook ("The Ear")
│   ├── orchestrator_sentinel.py # Background polling ("The Brain")
│   ├── models/
│   │   ├── work_item.py         # Unified WorkItem, TaskType, WorkItemStatus
│   │   └── github_events.py     # GitHub webhook payload schemas
│   └── queue/
│       └── github_queue.py      # ITaskQueue + GitHubQueue implementation
├── scripts/
│   ├── devcontainer-opencode.sh # Shell bridge to worker
│   ├── gh-auth.ps1              # GitHub App auth sync
│   └── update-remote-indices.ps1# Vector index maintenance
├── local_ai_instruction_modules/ # Markdown workflow modules
│   ├── create-app-plan.md
│   ├── perform-task.md
│   └── analyze-bug.md
└── docs/                        # Architecture and user documentation
```

---

## References

- [Architecture Guide v3.2](./OS-APOW%20Architecture%20Guide%20v3.2.md)
- [Development Plan v4.2](./OS-APOW%20Development%20Plan%20v4.2.md)
- [Implementation Specification v1.2](./OS-APOW%20Implementation%20Specification%20v1.2.md)
- [Plan Review](./OS-APOW%20Plan%20Review.md)
- [Simplification Report v1](./OS-APOW%20Simplification%20Report%20v1.md)
