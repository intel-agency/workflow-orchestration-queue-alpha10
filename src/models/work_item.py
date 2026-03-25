"""Work Item models for workflow-orchestration-queue.

This module defines the unified WorkItem data structure, TaskType enumeration,
and WorkItemStatus state machine used throughout the orchestration system.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Enumeration of task types supported by the orchestration system."""

    APPLICATION_PLAN = "application_plan"
    BUGFIX = "bugfix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TEST = "test"
    UNKNOWN = "unknown"


class WorkItemStatus(str, Enum):
    """State machine states for work items.

    These states correspond to GitHub issue labels used for task tracking.
    """

    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    RECONCILING = "agent:reconciling"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"


# Regex patterns for secret scrubbing
SECRET_PATTERNS = [
    # GitHub Personal Access Tokens
    (r"ghp_[A-Za-z0-9]{36}", "ghp_[REDACTED]"),
    (r"ghs_[A-Za-z0-9]{36}", "ghs_[REDACTED]"),
    (r"gho_[A-Za-z0-9]{36}", "gho_[REDACTED]"),
    (r"github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}", "github_pat_[REDACTED]"),
    # Generic Bearer tokens
    (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer [REDACTED]"),
    # OpenAI-style keys
    (r"sk-[A-Za-z0-9]{20,}", "sk-[REDACTED]"),
    # ZhipuAI keys
    (r"[A-Za-z0-9]{32}\.[A-Za-z0-9]{8}\.[A-Za-z0-9]{32}", "[ZHIPU_KEY_REDACTED]"),
    # Generic API key patterns (env var assignments)
    (r"(API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['\"]?[^'\"\s]+['\"]?", r"\1=[REDACTED]"),
]


def scrub_secrets(text: str) -> str:
    """Remove sensitive credentials from text.

    Uses regex patterns to identify and redact common secret formats
    including GitHub PATs, Bearer tokens, and API keys.

    Args:
        text: The text to scrub.

    Returns:
        The text with secrets replaced by [REDACTED] placeholders.
    """
    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


class WorkItem(BaseModel):
    """Unified work item representation.

    This model serves as the canonical task representation across all
    components of the orchestration system, abstracting away the specifics
    of the originating platform (GitHub Issues, PRs, etc.).
    """

    id: str = Field(..., description="Unique identifier (GitHub issue number)")
    title: str = Field(..., description="Task title/summary")
    body: str | None = Field(None, description="Task description/body")
    task_type: TaskType = Field(default=TaskType.UNKNOWN, description="Categorized task type")
    status: WorkItemStatus = Field(
        default=WorkItemStatus.QUEUED, description="Current state in the workflow"
    )
    repository: str = Field(..., description="Target repository (owner/repo format)")
    labels: list[str] = Field(default_factory=list, description="Associated labels")
    assignees: list[str] = Field(default_factory=list, description="Assigned users")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    html_url: str | None = Field(None, description="Web URL for the issue")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {
        "use_enum_values": False,  # Keep enum objects for type safety
        "extra": "forbid",
    }

    def is_claimed(self, sentinel_login: str) -> bool:
        """Check if this work item is claimed by the given sentinel.

        Args:
            sentinel_login: The GitHub login of the sentinel bot account.

        Returns:
            True if the sentinel is the sole assignee.
        """
        return sentinel_login in self.assignees and len(self.assignees) == 1

    def classify_task_type(self) -> TaskType:
        """Infer task type from title and body content.

        Analyzes the issue title and body for known patterns to determine
        the appropriate TaskType.

        Returns:
            The inferred TaskType.
        """
        content = f"{self.title} {self.body or ''}".lower()

        if "[application plan]" in content or "application plan" in content:
            return TaskType.APPLICATION_PLAN
        if "[bugfix]" in content or "bugfix" in content:
            return TaskType.BUGFIX
        if "[feature]" in content or "feature request" in content:
            return TaskType.FEATURE
        if "[refactor]" in content or "refactor" in content:
            return TaskType.REFACTOR
        if "[documentation]" in content or "docs:" in content:
            return TaskType.DOCUMENTATION
        if "[test]" in content or "test:" in content:
            return TaskType.TEST

        return TaskType.UNKNOWN
