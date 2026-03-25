# Dockerfile for workflow-orchestration-queue
# Python 3.12+ FastAPI service with uv package manager

# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (pinned version)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Copy source code BEFORE installing (required for editable install)
COPY src/ ./src/

# Install dependencies using uv (editable mode)
RUN uv pip install --system -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port for FastAPI
EXPOSE 8000

# Health check using Python stdlib (no curl required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command runs the notifier service
CMD ["uvicorn", "src.notifier_service:app", "--host", "0.0.0.0", "--port", "8000"]
