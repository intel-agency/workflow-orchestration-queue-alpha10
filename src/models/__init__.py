"""Pydantic models for workflow-orchestration-queue.

This module exports the core data structures used throughout the system:
- WorkItem: Unified task representation
- TaskType: Enumeration of task categories
- WorkItemStatus: State machine states for tasks
"""

from src.models.github_events import (
    GitHubIssue,
    GitHubIssueEvent,
    GitHubLabel,
    GitHubPullRequestEvent,
    GitHubWebhookPayload,
)
from src.models.work_item import (
    TaskType,
    WorkItem,
    WorkItemStatus,
    scrub_secrets,
)

__all__ = [
    # WorkItem models
    "WorkItem",
    "TaskType",
    "WorkItemStatus",
    "scrub_secrets",
    # GitHub event models
    "GitHubWebhookPayload",
    "GitHubIssue",
    "GitHubLabel",
    "GitHubIssueEvent",
    "GitHubPullRequestEvent",
]
