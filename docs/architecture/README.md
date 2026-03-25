# Architecture Documentation

This directory contains architecture documentation for the workflow-orchestration-queue system.

## Documents

- [Architecture Overview](./architecture-overview.md) - High-level system architecture
- [ADR Template](./adr-template.md) - Architecture Decision Record template

## The Four Pillars

The system is built on four conceptual pillars:

1. **The Ear (Work Event Notifier)** - FastAPI webhook receiver
2. **The State (Work Queue)** - GitHub Issues as state management
3. **The Brain (Sentinel Orchestrator)** - Background polling and task coordination
4. **The Hands (Opencode Worker)** - AI-driven code execution

## Key Design Decisions

- **Polling-First Resiliency**: Webhooks are an optimization, not a requirement
- **Markdown as Database**: GitHub Issues provide transparent state management
- **Shell-Bridge Execution**: All worker interactions via scripts for parity
- **Provider-Agnostic Queue**: ITaskQueue interface enables backend swapping
