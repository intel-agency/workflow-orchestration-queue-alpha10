"""FastAPI Webhook Service - "The Ear" for workflow-orchestration-queue.

This module implements the FastAPI-based webhook receiver that serves as the
primary gateway for external stimuli (GitHub webhooks) and performs:
- Secure webhook ingestion with HMAC signature verification
- Intelligent event triage and WorkItem mapping
- Queue initialization via label application
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from src.models.github_events import GitHubIssueEvent, GitHubPullRequestEvent
from src.models.work_item import TaskType, WorkItem, WorkItemStatus, scrub_secrets
from src.queue.github_queue import GitHubQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required settings
    github_token: str = ""
    github_repo: str = ""
    webhook_secret: str = ""

    # Optional tuning
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    status: str
    message: str
    tracking_id: str | None = None


# Global queue client
_queue_client: GitHubQueue | None = None


def get_queue_client() -> GitHubQueue:
    """Get or create the GitHub queue client."""
    global _queue_client
    if _queue_client is None:
        settings = Settings()
        _queue_client = GitHubQueue(
            github_token=settings.github_token,
            repository=settings.github_repo,
        )
    return _queue_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = Settings()
    logging.getLogger().setLevel(settings.log_level.upper())
    logger.info("Starting notifier service")
    logger.info(f"Repository: {settings.github_repo}")
    yield
    # Cleanup
    if _queue_client is not None:
        await _queue_client.close()
    logger.info("Shutting down notifier service")


app = FastAPI(
    title="Workflow Orchestration Queue - Notifier Service",
    description="Webhook receiver for headless agentic orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the HMAC SHA256 signature of a GitHub webhook payload.

    Args:
        payload: The raw request body bytes.
        signature: The X-Hub-Signature-256 header value.
        secret: The webhook secret.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature or not secret:
        return False

    # Extract the hex digest from the signature header
    # Format: "sha256=<hex_digest>"
    if not signature.startswith("sha256="):
        return False

    expected_sig = signature[7:]  # Remove "sha256=" prefix

    # Compute the HMAC
    computed_sig = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_sig, computed_sig)


def classify_event_type(event_type: str, payload: dict[str, Any]) -> str | None:
    """Classify the event and determine if it should be queued.

    Args:
        event_type: The X-GitHub-Event header value.
        payload: The parsed JSON payload.

    Returns:
        The action to take, or None if the event should be ignored.
    """
    action = payload.get("action")

    if event_type == "issues":
        # Queue newly opened issues
        if action == "opened":
            return "queue"
        # Also handle labeled events (if someone adds agent:queued manually)
        if action == "labeled":
            label = payload.get("label", {}).get("name", "")
            if label == WorkItemStatus.QUEUED.value:
                return "process"

    elif event_type == "issue_comment":
        # Handle commands in comments
        comment_body = payload.get("comment", {}).get("body", "")
        if "/agent-queue" in comment_body or "/orchestrate" in comment_body:
            return "queue"

    elif event_type == "pull_request":
        # Handle PR review feedback for self-healing
        if action == "review_requested":
            return "process"

    return None


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "notifier"}


@app.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
) -> WebhookResponse:
    """Handle incoming GitHub webhook events.

    This endpoint:
    1. Verifies the HMAC signature
    2. Parses the event payload
    3. Classifies the event type
    4. Queues the task if appropriate

    Returns:
        WebhookResponse with status and tracking ID.
    """
    settings = Settings()

    # Get raw body for signature verification
    payload_bytes = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.webhook_secret and not verify_webhook_signature(
        payload_bytes, signature, settings.webhook_secret
    ):
        logger.warning("Invalid webhook signature - rejecting request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Parse the JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Get event type from header
    event_type = request.headers.get("X-GitHub-Event", "")

    # Log the event (scrubbed)
    logger.info(f"Received {event_type} event: {scrub_secrets(str(payload)[:500])}")

    # Classify and route the event
    action = classify_event_type(event_type, payload)

    if action is None:
        logger.info(f"Ignoring {event_type} event (no action needed)")
        return WebhookResponse(
            status="ignored",
            message=f"Event type {event_type} does not require processing",
        )

    # Create WorkItem and add to queue
    try:
        if event_type == "issues" and action == "queue":
            issue_data = payload.get("issue", {})
            repository = payload.get("repository", {}).get("full_name", "")

            work_item = WorkItem(
                id=str(issue_data.get("number")),
                title=issue_data.get("title", ""),
                body=issue_data.get("body"),
                repository=repository,
                labels=[l.get("name") for l in issue_data.get("labels", [])],
                assignees=[a.get("login") for a in issue_data.get("assignees", [])],
                html_url=issue_data.get("html_url"),
            )

            # Classify task type
            work_item.task_type = work_item.classify_task_type()

            # Add to queue
            queue = get_queue_client()
            await queue.add_to_queue(int(work_item.id))

            logger.info(f"Queued work item: {work_item.id} - {work_item.title}")

            return WebhookResponse(
                status="queued",
                message=f"Work item {work_item.id} added to queue",
                tracking_id=work_item.id,
            )

        return WebhookResponse(
            status="processed",
            message=f"Event {event_type} processed",
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {scrub_secrets(str(e))}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.notifier_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
