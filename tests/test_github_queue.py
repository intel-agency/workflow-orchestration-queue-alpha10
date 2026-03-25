"""Tests for GitHub queue implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.work_item import WorkItem, WorkItemStatus
from src.queue.github_queue import GitHubQueue


class TestGitHubQueue:
    """Tests for GitHubQueue implementation."""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def queue(self, mock_http_client):
        """Create a GitHubQueue with mocked client."""
        return GitHubQueue(
            github_token="fake-token-for-testing",
            repository="owner/repo",
            http_client=mock_http_client,
        )

    def test_queue_initialization(self, queue):
        """Test queue initialization."""
        assert queue.repository == "owner/repo"
        assert queue.owner == "owner"
        assert queue.repo == "repo"

    @pytest.mark.asyncio
    async def test_fetch_queued_items(self, queue, mock_http_client):
        """Test fetching queued items."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "number": 42,
                    "title": "Test Issue",
                    "body": "Test body",
                    "state": "open",
                    "labels": [{"name": "agent:queued"}],
                    "assignees": [],
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "html_url": "https://github.com/owner/repo/issues/42",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        items = await queue.fetch_queued_items()

        assert len(items) == 1
        assert items[0].id == "42"
        assert items[0].title == "Test Issue"
        assert WorkItemStatus.QUEUED.value in items[0].labels

    @pytest.mark.asyncio
    async def test_post_comment(self, queue, mock_http_client):
        """Test posting a comment."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await queue.post_comment(42, "Test comment")

        assert result is True
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_label(self, queue, mock_http_client):
        """Test adding a label."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await queue._add_label(42, "agent:queued")

        assert result is True

    def test_parse_issue(self, queue):
        """Test parsing GitHub API issue response."""
        data = {
            "number": 42,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [
                {"name": "enhancement"},
                {"name": "agent:queued"},
            ],
            "assignees": [{"login": "developer"}],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "html_url": "https://github.com/owner/repo/issues/42",
        }

        work_item = queue._parse_issue(data)

        assert work_item.id == "42"
        assert work_item.title == "Test Issue"
        assert work_item.body == "Test body"
        assert work_item.status == WorkItemStatus.QUEUED
        assert "enhancement" in work_item.labels
        assert "agent:queued" in work_item.labels
        assert "developer" in work_item.assignees
