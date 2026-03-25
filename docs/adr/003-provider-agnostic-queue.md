# Architecture Decision Record: Provider-Agnostic Queue Interface

## ADR-003

## Status

Accepted

## Context

The current implementation uses GitHub Issues as the task queue. However, future requirements may need different backends:
- Linear for project management
- Notion for documentation-heavy teams
- SQL databases for high-volume scenarios

Hardcoding GitHub-specific logic would make future migrations expensive.

## Decision

All queue interactions are abstracted behind the `ITaskQueue` interface using the Strategy Pattern. The concrete `GitHubQueue` implementation handles GitHub-specific details while the orchestrator only depends on the interface.

## Consequences

**Benefits:**
- Enables future "ticket provider swapping" without rewriting orchestrator logic
- Makes testing easier (can mock the queue interface)
- Clear separation of concerns between orchestration and queue implementation

**Trade-offs:**
- Additional abstraction layer adds complexity
- Interface must be designed to support multiple backends
- Some backend-specific features may not be exposed

## Implementation

```python
class ITaskQueue(ABC):
    @abstractmethod
    async def fetch_queued_items(self) -> list[WorkItem]: ...
    
    @abstractmethod
    async def claim_task(self, issue_id: int, sentinel_id: str) -> bool: ...
    
    @abstractmethod
    async def update_status(self, issue_id: int, status: WorkItemStatus, ...) -> bool: ...
    
    @abstractmethod
    async def post_comment(self, issue_id: int, body: str) -> bool: ...
    
    @abstractmethod
    async def get_issue(self, issue_id: int) -> WorkItem | None: ...
```
