# Webhook Reliability Platform

A transport-agnostic webhook delivery core with event idempotency, subscription routing, HMAC signatures, bounded retries, and a dead-letter state. The FastAPI layer exposes subscription and event-ingestion endpoints; delivery transport is injected so tests never make real network requests.

## Capabilities

- Route events to matching subscriptions
- Idempotent event ingestion by caller-provided event ID
- Canonical JSON payloads and timestamped HMAC-SHA256 signatures
- Delivery lifecycle: queued, retry, delivered, dead-letter
- Bounded retries and observable attempt/error metadata
- Injectable sender interface for HTTP clients, queues, or test doubles
- FastAPI endpoints and deterministic unit/API tests

## Quick start

```bash
python -m venv .venv
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Visit `/docs` for the API.

## API

- `GET /health`
- `POST /subscriptions`
- `POST /events`
- `GET /deliveries`
- `POST /deliveries/{delivery_id}/dispatch`

The default API intentionally has no network sender configured. Supply a sender when constructing the application (see `create_app`) to connect a real transport. The core uses a small in-memory store for clarity; it is not durable across restarts.

## Security and production notes

Subscriptions require HTTPS URLs and secrets of at least 16 characters. HMAC signatures authenticate payload integrity; consumers should verify signatures and enforce timestamp/replay windows. Before production, use an outbound hostname/IP allowlist and network egress policy to prevent SSRF, store secrets in a secret manager, persist delivery state, add distributed worker leases, and implement delayed exponential backoff. This educational implementation does not perform outbound network requests by default.
