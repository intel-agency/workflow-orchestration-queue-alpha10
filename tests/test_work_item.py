"""Tests for WorkItem model and related utilities."""

import pytest

from src.models.work_item import (
    TaskType,
    WorkItem,
    WorkItemStatus,
    scrub_secrets,
)


class TestScrubSecrets:
    """Tests for the scrub_secrets utility function."""

    def test_scrub_github_pat(self):
        """Test that GitHub PATs are redacted."""
        text = "Token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
        result = scrub_secrets(text)
        assert "ghp_[REDACTED]" in result
        assert "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789" not in result

    def test_scrub_bearer_token(self):
        """Test that Bearer tokens are redacted."""
        text = "Authorization: Bearer abc123xyz789"
        result = scrub_secrets(text)
        assert "Bearer [REDACTED]" in result
        assert "abc123xyz789" not in result

    def test_scrub_openai_key(self):
        """Test that OpenAI-style keys are redacted."""
        text = "API key: sk-proj-abcdefghijklmnopqrstuvwx"
        result = scrub_secrets(text)
        assert "sk-[REDACTED]" in result
        assert "proj-abcdefghijklmnopqrstuvwx" not in result

    def test_preserve_normal_text(self):
        """Test that normal text is preserved."""
        text = "This is a normal log message with no secrets."
        result = scrub_secrets(text)
        assert result == text


class TestTaskType:
    """Tests for TaskType enumeration."""

    def test_task_type_values(self):
        """Test that TaskType has expected values."""
        assert TaskType.APPLICATION_PLAN.value == "application_plan"
        assert TaskType.BUGFIX.value == "bugfix"
        assert TaskType.FEATURE.value == "feature"
        assert TaskType.UNKNOWN.value == "unknown"


class TestWorkItemStatus:
    """Tests for WorkItemStatus enumeration."""

    def test_status_values(self):
        """Test that WorkItemStatus has expected label values."""
        assert WorkItemStatus.QUEUED.value == "agent:queued"
        assert WorkItemStatus.IN_PROGRESS.value == "agent:in-progress"
        assert WorkItemStatus.SUCCESS.value == "agent:success"
        assert WorkItemStatus.ERROR.value == "agent:error"


class TestWorkItem:
    """Tests for WorkItem model."""

    def test_work_item_creation(self):
        """Test creating a basic WorkItem."""
        item = WorkItem(
            id="42",
            title="Test Issue",
            repository="owner/repo",
        )
        assert item.id == "42"
        assert item.title == "Test Issue"
        assert item.repository == "owner/repo"
        assert item.status == WorkItemStatus.QUEUED
        assert item.task_type == TaskType.UNKNOWN

    def test_is_claimed_true(self):
        """Test is_claimed returns True when sentinel is sole assignee."""
        item = WorkItem(
            id="42",
            title="Test",
            repository="owner/repo",
            assignees=["sentinel-bot"],
        )
        assert item.is_claimed("sentinel-bot") is True

    def test_is_claimed_false_multiple_assignees(self):
        """Test is_claimed returns False when multiple assignees."""
        item = WorkItem(
            id="42",
            title="Test",
            repository="owner/repo",
            assignees=["sentinel-bot", "developer"],
        )
        assert item.is_claimed("sentinel-bot") is False

    def test_is_claimed_false_not_assigned(self):
        """Test is_claimed returns False when not assigned."""
        item = WorkItem(
            id="42",
            title="Test",
            repository="owner/repo",
            assignees=["developer"],
        )
        assert item.is_claimed("sentinel-bot") is False

    def test_classify_task_type_application_plan(self):
        """Test classification of application plan tasks."""
        item = WorkItem(
            id="1",
            title="[Application Plan] New Service",
            body="Create a new microservice",
            repository="owner/repo",
        )
        assert item.classify_task_type() == TaskType.APPLICATION_PLAN

    def test_classify_task_type_bugfix(self):
        """Test classification of bugfix tasks."""
        item = WorkItem(
            id="2",
            title="[Bugfix] Fix login bug",
            body="Login fails on mobile",
            repository="owner/repo",
        )
        assert item.classify_task_type() == TaskType.BUGFIX

    def test_classify_task_type_feature(self):
        """Test classification of feature tasks."""
        item = WorkItem(
            id="3",
            title="[Feature] Add dark mode",
            repository="owner/repo",
        )
        assert item.classify_task_type() == TaskType.FEATURE

    def test_classify_task_type_unknown(self):
        """Test classification falls back to unknown."""
        item = WorkItem(
            id="4",
            title="Some random task",
            repository="owner/repo",
        )
        assert item.classify_task_type() == TaskType.UNKNOWN
