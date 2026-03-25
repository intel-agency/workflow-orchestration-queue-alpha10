# Architecture Decision Record: Shell-Bridge Execution Pattern

## ADR-002

## Status

Accepted

## Context

The Sentinel needs to interact with Docker containers, DevContainers, and the opencode CLI. Direct use of Docker SDK or complex orchestration libraries could create drift between local development and production environments.

## Decision

The Orchestrator interacts with the agentic environment exclusively via shell scripts (`scripts/devcontainer-opencode.sh`). This "script-first" approach ensures parity between what the AI does and what human developers can reproduce.

## Consequences

**Benefits:**
- Human engineers can debug the exact same scripts the AI uses
- Local development and production use identical execution paths
- Shell scripts are simple, well-understood, and easy to modify
- Python code stays lightweight and focused on orchestration logic

**Trade-offs:**
- Subprocess management adds some complexity
- Error handling must parse shell output
- Shell scripts must be maintained alongside Python code

## Implementation

All worker interactions go through the shell bridge:
- `./scripts/devcontainer-opencode.sh up` - Provision environment
- `./scripts/devcontainer-opencode.sh start` - Launch opencode server
- `./scripts/devcontainer-opencode.sh prompt "{workflow}"` - Dispatch work
- `./scripts/devcontainer-opencode.sh stop` - Clean up
