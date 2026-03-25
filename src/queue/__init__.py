"""Queue implementations for workflow-orchestration-queue.

This module provides the abstract task queue interface and concrete
implementations for different backend providers (GitHub Issues, etc.).
"""

from src.queue.github_queue import GitHubQueue, ITaskQueue

__all__ = [
    "ITaskQueue",
    "GitHubQueue",
]
