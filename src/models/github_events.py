"""GitHub webhook event models for workflow-orchestration-queue.

This module defines Pydantic models for parsing and validating GitHub
webhook payloads, including issues, issue comments, and pull request events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class GitHubLabel(BaseModel):
    """GitHub label model."""

    id: int
    name: str
    color: str | None = None
    description: str | None = None

    model_config = {"extra": "ignore"}


class GitHubUser(BaseModel):
    """GitHub user model."""

    login: str
    id: int
    type: str | None = None
    avatar_url: str | None = None

    model_config = {"extra": "ignore"}


class GitHubRepository(BaseModel):
    """GitHub repository model."""

    id: int
    name: str
    full_name: str
    owner: GitHubUser
    private: bool = False
    html_url: str | None = None

    model_config = {"extra": "ignore"}


class GitHubIssue(BaseModel):
    """GitHub issue model."""

    id: int
    number: int
    title: str
    body: str | None = None
    state: Literal["open", "closed"] = "open"
    user: GitHubUser
    labels: list[GitHubLabel] = Field(default_factory=list)
    assignees: list[GitHubUser] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    html_url: str | None = None

    model_config = {"extra": "ignore"}

    def label_names(self) -> list[str]:
        """Extract label names from the issue."""
        return [label.name for label in self.labels]

    def assignee_logins(self) -> list[str]:
        """Extract assignee logins from the issue."""
        return [assignee.login for assignee in self.assignees]


class GitHubPullRequest(BaseModel):
    """GitHub pull request model."""

    id: int
    number: int
    title: str
    body: str | None = None
    state: Literal["open", "closed"] = "open"
    draft: bool = False
    user: GitHubUser
    html_url: str | None = None
    head_ref: str | None = Field(None, alias="head")
    base_ref: str | None = Field(None, alias="base")

    model_config = {"extra": "ignore", "populate_by_name": True}


class GitHubComment(BaseModel):
    """GitHub comment model."""

    id: int
    body: str | None = None
    user: GitHubUser
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"extra": "ignore"}


class GitHubIssueEvent(BaseModel):
    """GitHub issue event webhook payload."""

    action: Literal["opened", "edited", "closed", "reopened", "labeled", "unlabeled"]
    issue: GitHubIssue
    repository: GitHubRepository
    sender: GitHubUser
    label: GitHubLabel | None = None  # Only present for labeled/unlabeled actions

    model_config = {"extra": "ignore"}


class GitHubIssueCommentEvent(BaseModel):
    """GitHub issue comment event webhook payload."""

    action: Literal["created", "edited", "deleted"]
    issue: GitHubIssue
    comment: GitHubComment
    repository: GitHubRepository
    sender: GitHubUser

    model_config = {"extra": "ignore"}


class GitHubPullRequestEvent(BaseModel):
    """GitHub pull request event webhook payload."""

    action: Literal["opened", "edited", "closed", "reopened", "synchronize", "review_requested"]
    pull_request: GitHubPullRequest
    repository: GitHubRepository
    sender: GitHubUser

    model_config = {"extra": "ignore"}


class GitHubPullRequestReviewEvent(BaseModel):
    """GitHub pull request review event webhook payload."""

    action: Literal["submitted", "edited", "dismissed"]
    review: dict[str, Any]  # Review object with state, body, etc.
    pull_request: GitHubPullRequest
    repository: GitHubRepository
    sender: GitHubUser

    model_config = {"extra": "ignore"}


class GitHubWebhookPayload(BaseModel):
    """Generic GitHub webhook payload wrapper.

    This model serves as a container for all GitHub webhook event types.
    The specific event type is determined by the X-GitHub-Event header.
    """

    # Common fields present in most events
    repository: GitHubRepository | None = None
    sender: GitHubUser | None = None
    action: str | None = None

    # Event-specific payloads (only one will be populated)
    issue: GitHubIssue | None = None
    comment: GitHubComment | None = None
    pull_request: GitHubPullRequest | None = None

    # Raw payload for events we don't have specific models for
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @classmethod
    def from_issue_event(cls, event: GitHubIssueEvent) -> "GitHubWebhookPayload":
        """Create a WebhookPayload from an issue event."""
        return cls(
            action=event.action,
            issue=event.issue,
            repository=event.repository,
            sender=event.sender,
        )

    @classmethod
    def from_pr_event(cls, event: GitHubPullRequestEvent) -> "GitHubWebhookPayload":
        """Create a WebhookPayload from a pull request event."""
        return cls(
            action=event.action,
            pull_request=event.pull_request,
            repository=event.repository,
            sender=event.sender,
        )
