"""GitHub-based task queue implementation.

This module provides the ITaskQueue interface and GitHubQueue implementation
that uses GitHub Issues as the state management backend ("Markdown as a Database").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

import httpx

from src.models.work_item import WorkItem, WorkItemStatus

if TYPE_CHECKING:
    pass


class ITaskQueue(ABC):
    """Abstract interface for task queue operations.

    This interface abstracts the queue backend, enabling future
    provider swapping (GitHub Issues, Linear, Notion, SQL, etc.)
    without rewriting orchestrator logic.
    """

    @abstractmethod
    async def fetch_queued_items(self) -> list[WorkItem]:
        """Fetch all items currently in the queued state.

        Returns:
            List of WorkItems awaiting processing.
        """
        pass

    @abstractmethod
    async def claim_task(self, issue_id: int, sentinel_id: str) -> bool:
        """Attempt to claim a task using the assign-then-verify pattern.

        This implements distributed locking via GitHub assignees.

        Args:
            issue_id: The GitHub issue number.
            sentinel_id: The GitHub login of the sentinel bot.

        Returns:
            True if the task was successfully claimed, False otherwise.
        """
        pass

    @abstractmethod
    async def update_status(
        self, issue_id: int, status: WorkItemStatus, comment: str | None = None
    ) -> bool:
        """Update the status label on an issue.

        Args:
            issue_id: The GitHub issue number.
            status: The new status to apply.
            comment: Optional comment to post with the status change.

        Returns:
            True if the update was successful.
        """
        pass

    @abstractmethod
    async def post_comment(self, issue_id: int, body: str) -> bool:
        """Post a comment to an issue.

        Args:
            issue_id: The GitHub issue number.
            body: The comment body (markdown supported).

        Returns:
            True if the comment was posted successfully.
        """
        pass

    @abstractmethod
    async def get_issue(self, issue_id: int) -> WorkItem | None:
        """Fetch a single issue by number.

        Args:
            issue_id: The GitHub issue number.

        Returns:
            The WorkItem if found, None otherwise.
        """
        pass


class GitHubQueue(ITaskQueue):
    """GitHub Issues-based task queue implementation.

    Uses GitHub Issues as the state management layer, with labels
    representing task states and assignees providing distributed locking.
    """

    def __init__(
        self,
        github_token: str,
        repository: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the GitHub queue client.

        Args:
            github_token: GitHub API token with repo permissions.
            repository: Target repository in owner/repo format.
            http_client: Optional httpx.AsyncClient for testing.
        """
        self.github_token = github_token
        self.repository = repository
        self.owner, self.repo = repository.split("/")
        self._client = http_client
        self._base_url = "https://api.github.com"

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_queued_items(self) -> list[WorkItem]:
        """Fetch all issues with the agent:queued label.

        Returns:
            List of WorkItems in the queued state.
        """
        url = f"{self._base_url}/search/issues"
        params = {
            "q": f"repo:{self.repository} is:issue is:open label:{WorkItemStatus.QUEUED.value}",
            "per_page": 100,
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        work_items: list[WorkItem] = []
        for item in data.get("items", []):
            work_items.append(self._parse_issue(item))

        return work_items

    async def claim_task(self, issue_id: int, sentinel_id: str) -> bool:
        """Claim a task using the assign-then-verify pattern.

        This implements distributed locking:
        1. Assign the sentinel to the issue
        2. Re-fetch the issue
        3. Verify the sentinel is the assignee

        Args:
            issue_id: The GitHub issue number.
            sentinel_id: The GitHub login of the sentinel bot.

        Returns:
            True if the claim was successful, False if another sentinel won.
        """
        # Step 1: Attempt to assign
        assign_url = f"{self._base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}/assignees"
        assign_response = await self.client.post(assign_url, json={"assignees": [sentinel_id]})

        if assign_response.status_code not in (200, 201):
            return False

        # Step 2: Re-fetch to verify
        issue = await self.get_issue(issue_id)
        if issue is None:
            return False

        # Step 3: Verify assignment
        return issue.is_claimed(sentinel_id)

    async def update_status(
        self, issue_id: int, status: WorkItemStatus, comment: str | None = None
    ) -> bool:
        """Update the status label on an issue.

        Removes the current agent:* label and adds the new one.

        Args:
            issue_id: The GitHub issue number.
            status: The new status to apply.
            comment: Optional comment to post with the status change.

        Returns:
            True if the update was successful.
        """
        # Get current issue to find existing status labels
        issue = await self.get_issue(issue_id)
        if issue is None:
            return False

        # Remove old status labels
        for label in issue.labels:
            if label.startswith("agent:"):
                await self._remove_label(issue_id, label)

        # Add new status label
        if not await self._add_label(issue_id, status.value):
            return False

        # Post comment if provided
        if comment is not None:
            await self.post_comment(issue_id, comment)

        return True

    async def post_comment(self, issue_id: int, body: str) -> bool:
        """Post a comment to an issue.

        Args:
            issue_id: The GitHub issue number.
            body: The comment body (markdown supported).

        Returns:
            True if the comment was posted successfully.
        """
        url = f"{self._base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}/comments"
        response = await self.client.post(url, json={"body": body})

        return response.status_code in (200, 201)

    async def get_issue(self, issue_id: int) -> WorkItem | None:
        """Fetch a single issue by number.

        Args:
            issue_id: The GitHub issue number.

        Returns:
            The WorkItem if found, None otherwise.
        """
        url = f"{self._base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}"
        response = await self.client.get(url)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return self._parse_issue(response.json())

    async def add_to_queue(self, issue_id: int) -> bool:
        """Add the queued label to an issue.

        Args:
            issue_id: The GitHub issue number.

        Returns:
            True if the label was added successfully.
        """
        return await self._add_label(issue_id, WorkItemStatus.QUEUED.value)

    async def _add_label(self, issue_id: int, label: str) -> bool:
        """Add a label to an issue.

        Args:
            issue_id: The GitHub issue number.
            label: The label name to add.

        Returns:
            True if successful.
        """
        url = f"{self._base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}/labels"
        response = await self.client.post(url, json={"labels": [label]})

        return response.status_code in (200, 201)

    async def _remove_label(self, issue_id: int, label: str) -> bool:
        """Remove a label from an issue.

        Args:
            issue_id: The GitHub issue number.
            label: The label name to remove.

        Returns:
            True if successful.
        """
        url = f"{self._base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}/labels/{label}"
        response = await self.client.delete(url)

        return response.status_code in (200, 204)

    def _parse_issue(self, data: dict) -> WorkItem:
        """Parse a GitHub API issue response into a WorkItem.

        Args:
            data: The issue data from GitHub API.

        Returns:
            A WorkItem instance.
        """
        labels = [label["name"] for label in data.get("labels", [])]
        assignees = [a["login"] for a in data.get("assignees", [])]

        # Determine current status from labels
        status = WorkItemStatus.QUEUED
        for label in labels:
            try:
                status = WorkItemStatus(label)
                break
            except ValueError:
                continue

        return WorkItem(
            id=str(data["number"]),
            title=data.get("title", ""),
            body=data.get("body"),
            status=status,
            repository=self.repository,
            labels=labels,
            assignees=assignees,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if data.get("updated_at")
            else None,
            html_url=data.get("html_url"),
        )
