# API Documentation

This directory contains API documentation for the workflow-orchestration-queue system.

## Endpoints

### Notifier Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/webhooks/github` | POST | GitHub webhook receiver |

## OpenAPI

When running the notifier service locally, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication

- Webhook endpoint requires valid `X-Hub-Signature-256` header
- Signature is HMAC-SHA256 of request body using `WEBHOOK_SECRET`
