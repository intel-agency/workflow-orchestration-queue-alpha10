# Architecture Decision Record: Polling-First Resiliency Model

## ADR-001

## Status

Accepted

## Context

Webhooks are "fire and forget" - if the server is down, events are lost. The system needs to reliably discover tasks even after downtime or failures.

## Decision

The Sentinel uses polling as the primary discovery mechanism. Webhooks are treated as an optimization layer that reduces latency but is not required for correctness.

## Consequences

**Benefits:**
- System is inherently self-healing and resilient against downtime
- No risk of lost work items due to missed webhooks
- Simpler deployment (no need for always-available webhook endpoint)

**Trade-offs:**
- Higher latency between task creation and discovery (up to poll interval)
- Increased API rate limit consumption from polling
- Webhook setup is optional, reducing complexity

## Implementation

- Default poll interval: 60 seconds (configurable via `SENTINEL_POLL_INTERVAL`)
- Polling uses GitHub Search API: `label:agent:queued is:issue is:open`
- On restart, Sentinel reconciles any stale `agent:in-progress` items
