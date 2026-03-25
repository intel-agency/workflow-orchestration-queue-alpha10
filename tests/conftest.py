"""Test configuration and fixtures for workflow-orchestration-queue."""

import pytest


@pytest.fixture
def sample_issue_data():
    """Sample GitHub issue data for testing."""
    return {
        "id": 123456,
        "number": 42,
        "title": "[Feature] Add authentication module",
        "body": "Create a new authentication module with OAuth2 support.",
        "state": "open",
        "user": {
            "login": "developer",
            "id": 789,
        },
        "labels": [
            {"id": 1, "name": "enhancement"},
            {"id": 2, "name": "agent:queued"},
        ],
        "assignees": [],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "html_url": "https://github.com/owner/repo/issues/42",
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload for testing."""
    return {
        "action": "opened",
        "issue": {
            "id": 123456,
            "number": 42,
            "title": "[Application Plan] Create API Service",
            "body": "Build a REST API service for user management.",
            "state": "open",
            "user": {"login": "product-manager", "id": 101},
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "html_url": "https://github.com/owner/repo/issues/42",
        },
        "repository": {
            "id": 999,
            "name": "repo",
            "full_name": "owner/repo",
            "owner": {"login": "owner", "id": 1},
            "private": False,
            "html_url": "https://github.com/owner/repo",
        },
        "sender": {"login": "product-manager", "id": 101},
    }
