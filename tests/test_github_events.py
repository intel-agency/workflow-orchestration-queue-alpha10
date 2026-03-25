"""Tests for GitHub event models."""

import pytest

from src.models.github_events import (
    GitHubIssue,
    GitHubLabel,
    GitHubRepository,
    GitHubUser,
)


class TestGitHubLabel:
    """Tests for GitHubLabel model."""

    def test_label_creation(self):
        """Test creating a GitHub label."""
        label = GitHubLabel(
            id=1,
            name="bug",
            color="ff0000",
            description="Something isn't working",
        )
        assert label.id == 1
        assert label.name == "bug"
        assert label.color == "ff0000"


class TestGitHubUser:
    """Tests for GitHubUser model."""

    def test_user_creation(self):
        """Test creating a GitHub user."""
        user = GitHubUser(
            login="developer",
            id=123,
            type="User",
            avatar_url="https://avatars.githubusercontent.com/u/123",
        )
        assert user.login == "developer"
        assert user.id == 123
        assert user.type == "User"


class TestGitHubRepository:
    """Tests for GitHubRepository model."""

    def test_repository_creation(self):
        """Test creating a GitHub repository."""
        owner = GitHubUser(login="owner", id=1)
        repo = GitHubRepository(
            id=100,
            name="my-repo",
            full_name="owner/my-repo",
            owner=owner,
            private=False,
            html_url="https://github.com/owner/my-repo",
        )
        assert repo.name == "my-repo"
        assert repo.full_name == "owner/my-repo"
        assert repo.owner.login == "owner"
        assert repo.private is False


class TestGitHubIssue:
    """Tests for GitHubIssue model."""

    def test_issue_creation(self, sample_issue_data):
        """Test creating a GitHub issue."""
        user = GitHubUser(login="developer", id=789)
        labels = [GitHubLabel(id=1, name="enhancement")]
        issue = GitHubIssue(
            id=sample_issue_data["id"],
            number=sample_issue_data["number"],
            title=sample_issue_data["title"],
            body=sample_issue_data["body"],
            state="open",
            user=user,
            labels=labels,
        )
        assert issue.number == 42
        assert issue.title == "[Feature] Add authentication module"
        assert issue.state == "open"

    def test_label_names(self):
        """Test extracting label names from issue."""
        labels = [
            GitHubLabel(id=1, name="bug"),
            GitHubLabel(id=2, name="priority"),
        ]
        user = GitHubUser(login="dev", id=1)
        issue = GitHubIssue(
            id=1,
            number=1,
            title="Test",
            user=user,
            labels=labels,
        )
        assert issue.label_names() == ["bug", "priority"]

    def test_assignee_logins(self):
        """Test extracting assignee logins from issue."""
        assignees = [
            GitHubUser(login="alice", id=1),
            GitHubUser(login="bob", id=2),
        ]
        user = GitHubUser(login="dev", id=1)
        issue = GitHubIssue(
            id=1,
            number=1,
            title="Test",
            user=user,
            assignees=assignees,
        )
        assert issue.assignee_logins() == ["alice", "bob"]
