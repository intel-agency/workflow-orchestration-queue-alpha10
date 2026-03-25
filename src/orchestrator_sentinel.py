"""Orchestrator Sentinel - "The Brain" for workflow-orchestration-queue.

This module implements the persistent background service that:
- Polls GitHub Issues for queued tasks
- Claims tasks using distributed locking (assign-then-verify)
- Dispatches work to opencode worker containers
- Manages task lifecycle and error handling
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

from src.models.work_item import WorkItem, WorkItemStatus, scrub_secrets
from src.queue.github_queue import GitHubQueue

if TYPE_CHECKING:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(sentinel_id)s] %(message)s",
)


class SentinelFormatter(logging.Formatter):
    """Custom formatter that includes sentinel_id in log records."""

    def format(self, record: logging.LogRecord) -> str:
        record.sentinel_id = getattr(record, "sentinel_id", "unknown")
        return super().format(record)


# Apply custom formatter
handler = logging.StreamHandler()
handler.setFormatter(
    SentinelFormatter("%(asctime)s - %(name)s - %(levelname)s - [%(sentinel_id)s] %(message)s")
)
logger = logging.getLogger(__name__)
logger.handlers = [handler]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required settings
    github_token: str = ""
    github_repo: str = ""
    sentinel_bot_login: str = ""

    # Optional tuning
    sentinel_poll_interval: int = 60
    sentinel_heartbeat_interval: int = 300
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


class OrchestratorSentinel:
    """The Brain - persistent orchestrator managing worker lifecycle.

    This service:
    1. Polls for agent:queued issues
    2. Claims tasks via assign-then-verify
    3. Dispatches work to devcontainer-opencode.sh
    4. Handles failures and updates status
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the sentinel.

        Args:
            settings: Optional settings instance (uses env vars if not provided).
        """
        self.settings = settings or Settings()
        self.sentinel_id = self.settings.sentinel_bot_login
        self._running = False
        self._current_task: WorkItem | None = None
        self._queue_client: GitHubQueue | None = None

        # Set log level
        logging.getLogger().setLevel(self.settings.log_level.upper())

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    @property
    def queue_client(self) -> GitHubQueue:
        """Get or create the GitHub queue client."""
        if self._queue_client is None:
            self._queue_client = GitHubQueue(
                github_token=self.settings.github_token,
                repository=self.settings.github_repo,
            )
        return self._queue_client

    def _handle_shutdown(self, signum: int, frame: object) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(
            f"Received signal {signum}, initiating graceful shutdown",
            extra={"sentinel_id": self.sentinel_id},
        )
        self._running = False

    async def start(self) -> None:
        """Start the sentinel polling loop."""
        logger.info(
            f"Starting sentinel for repository: {self.settings.github_repo}",
            extra={"sentinel_id": self.sentinel_id},
        )
        logger.info(
            f"Poll interval: {self.settings.sentinel_poll_interval}s",
            extra={"sentinel_id": self.sentinel_id},
        )

        self._running = True

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error(
                    f"Error in poll cycle: {e}",
                    extra={"sentinel_id": self.sentinel_id},
                )

            # Wait for next poll interval
            await asyncio.sleep(self.settings.sentinel_poll_interval)

        # Cleanup
        if self._queue_client is not None:
            await self._queue_client.close()

        logger.info(
            "Sentinel shutdown complete",
            extra={"sentinel_id": self.sentinel_id},
        )

    async def _poll_cycle(self) -> None:
        """Execute a single polling cycle."""
        logger.debug(
            "Starting poll cycle",
            extra={"sentinel_id": self.sentinel_id},
        )

        # Fetch queued items
        queued_items = await self.queue_client.fetch_queued_items()

        if not queued_items:
            logger.debug(
                "No queued items found",
                extra={"sentinel_id": self.sentinel_id},
            )
            return

        logger.info(
            f"Found {len(queued_items)} queued item(s)",
            extra={"sentinel_id": self.sentinel_id},
        )

        # Try to claim and process each item
        for item in queued_items:
            if not self._running:
                break

            claimed = await self._claim_and_process(item)
            if claimed:
                # Only process one item per cycle (can be changed for parallelism)
                break

    async def _claim_and_process(self, item: WorkItem) -> bool:
        """Attempt to claim and process a work item.

        Args:
            item: The work item to process.

        Returns:
            True if the item was claimed and processed, False otherwise.
        """
        issue_id = int(item.id)

        # Attempt to claim using assign-then-verify
        claimed = await self.queue_client.claim_task(issue_id, self.sentinel_id)

        if not claimed:
            logger.info(
                f"Failed to claim item {issue_id} (likely claimed by another sentinel)",
                extra={"sentinel_id": self.sentinel_id},
            )
            return False

        logger.info(
            f"Successfully claimed item {issue_id}: {item.title}",
            extra={"sentinel_id": self.sentinel_id},
        )

        self._current_task = item

        try:
            # Update status to in-progress
            await self.queue_client.update_status(
                issue_id,
                WorkItemStatus.IN_PROGRESS,
                comment=f"Sentinel `{self.sentinel_id}` claimed this task.",
            )

            # Execute the work
            success = await self._execute_work(item)

            # Update final status
            if success:
                await self.queue_client.update_status(
                    issue_id,
                    WorkItemStatus.SUCCESS,
                    comment="Task completed successfully.",
                )
                logger.info(
                    f"Item {issue_id} completed successfully",
                    extra={"sentinel_id": self.sentinel_id},
                )
            else:
                await self.queue_client.update_status(
                    issue_id,
                    WorkItemStatus.ERROR,
                    comment="Task execution failed. Check logs for details.",
                )
                logger.error(
                    f"Item {issue_id} failed",
                    extra={"sentinel_id": self.sentinel_id},
                )

        except Exception as e:
            error_msg = scrub_secrets(str(e))
            logger.error(
                f"Error processing item {issue_id}: {error_msg}",
                extra={"sentinel_id": self.sentinel_id},
            )
            await self.queue_client.update_status(
                issue_id,
                WorkItemStatus.ERROR,
                comment=f"Error: {error_msg}",
            )

        finally:
            self._current_task = None

        return True

    async def _execute_work(self, item: WorkItem) -> bool:
        """Execute work by dispatching to the devcontainer-opencode.sh bridge.

        Args:
            item: The work item to execute.

        Returns:
            True if execution succeeded, False otherwise.
        """
        issue_id = int(item.id)

        try:
            # Run authentication sync
            await self._run_auth_sync()

            # Bring up the devcontainer environment
            up_result = await self._run_shell_bridge("up")
            if up_result.returncode != 0:
                logger.error(
                    f"Failed to bring up devcontainer: {up_result.stderr}",
                    extra={"sentinel_id": self.sentinel_id},
                )
                return False

            # Start the opencode server
            start_result = await self._run_shell_bridge("start")
            if start_result.returncode != 0:
                logger.error(
                    f"Failed to start opencode server: {start_result.stderr}",
                    extra={"sentinel_id": self.sentinel_id},
                )
                return False

            # Dispatch the prompt based on task type
            workflow_prompt = self._build_workflow_prompt(item)
            prompt_result = await self._run_shell_bridge("prompt", workflow_prompt)

            # Capture output for logging
            stdout = scrub_secrets(prompt_result.stdout)
            stderr = scrub_secrets(prompt_result.stderr)

            logger.info(
                f"Work execution output for {issue_id}:\n{stdout}",
                extra={"sentinel_id": self.sentinel_id},
            )

            if prompt_result.returncode != 0:
                logger.error(
                    f"Work execution failed for {issue_id}:\n{stderr}",
                    extra={"sentinel_id": self.sentinel_id},
                )
                return False

            return True

        except Exception as e:
            logger.error(
                f"Exception during work execution: {e}",
                extra={"sentinel_id": self.sentinel_id},
            )
            return False

        finally:
            # Stop the worker container between tasks
            await self._run_shell_bridge("stop")

    async def _run_auth_sync(self) -> None:
        """Run the GitHub authentication sync scripts."""
        scripts = ["scripts/common-auth.ps1", "scripts/gh-auth.ps1"]

        for script in scripts:
            if os.path.exists(script):
                try:
                    result = subprocess.run(
                        ["pwsh", "-NoProfile", "-File", script],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if result.returncode != 0:
                        logger.warning(
                            f"Auth sync script {script} failed: {result.stderr}",
                            extra={"sentinel_id": self.sentinel_id},
                        )
                except Exception as e:
                    logger.warning(
                        f"Error running auth sync {script}: {e}",
                        extra={"sentinel_id": self.sentinel_id},
                    )

    async def _run_shell_bridge(
        self, command: str, arg: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run a devcontainer-opencode.sh command.

        Args:
            command: The command to run (up, start, prompt, stop).
            arg: Optional argument for the command.

        Returns:
            The subprocess result.
        """
        script_path = "scripts/devcontainer-opencode.sh"
        cmd = [script_path, command]
        if arg:
            cmd.append(arg)

        logger.debug(
            f"Running shell bridge: {' '.join(cmd)}",
            extra={"sentinel_id": self.sentinel_id},
        )

        # Run in subprocess to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout for long-running tasks
            ),
        )

        return result

    def _build_workflow_prompt(self, item: WorkItem) -> str:
        """Build the workflow prompt based on task type.

        Args:
            item: The work item to build a prompt for.

        Returns:
            The workflow prompt string.
        """
        # Map task types to workflow modules
        workflow_map = {
            "application_plan": "orchestrate-new-project",
            "feature": "perform-task",
            "bugfix": "fix-bug",
            "refactor": "refactor-code",
            "documentation": "write-docs",
            "test": "write-tests",
        }

        workflow = workflow_map.get(item.task_type.value, "perform-task")

        # Build prompt with issue context
        prompt = f"""
/workflow {workflow}

**Issue:** #{item.id} - {item.title}

**Description:**
{item.body or "No description provided."}

**Labels:** {", ".join(item.labels)}
**Task Type:** {item.task_type.value}
"""
        return prompt.strip()


async def main() -> None:
    """Main entry point for the sentinel service."""
    settings = Settings()

    if not settings.github_token:
        logger.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    if not settings.github_repo:
        logger.error("GITHUB_REPO environment variable is required")
        sys.exit(1)

    if not settings.sentinel_bot_login:
        logger.error("SENTINEL_BOT_LOGIN environment variable is required")
        sys.exit(1)

    sentinel = OrchestratorSentinel(settings)
    await sentinel.start()


if __name__ == "__main__":
    asyncio.run(main())
