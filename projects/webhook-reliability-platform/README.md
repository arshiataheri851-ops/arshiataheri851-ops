# RelayForge — Reliable Webhook Delivery Engine

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

RelayForge is a transport-agnostic webhook delivery core. It accepts events, routes them to subscriptions, signs canonical payloads with HMAC-SHA256, and tracks bounded retry and dead-letter states.

## Implemented capabilities

- HTTPS-only subscription registration and secret-length validation.
- Event routing by event type.
- Idempotent event intake; reusing an event ID with different content is rejected.
- Canonical JSON serialization and timestamped HMAC-SHA256 signatures.
- Constant-time signature verification helper.
- Delivery lifecycle: queued, retry, delivered, dead-letter.
- Bounded retry attempts and status filtering.
- Subscription listing and safe removal checks.
- Injectable transport interface and deterministic API/unit tests.
- Payload size limits and strict request schemas.

## Architecture

```text
Event Producer
     |
     v
FastAPI + Request Validation
     |
     v
Idempotency Check ----> Event Fingerprint
     |
     v
Subscription Router
     |
     v
Delivery Queue (in-memory reference store)
     |
     v
Canonical JSON + HMAC-SHA256
     |
     v
Injected Sender / Transport Adapter
     |
     +---- 2xx ----> DELIVERED
     |
     +---- failure -> RETRY -> DEAD LETTER
```

## Run locally

Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

## API workflow

Register a subscription:

```bash
curl -X POST http://127.0.0.1:8000/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"subscription_id":"orders","event_type":"order.created","url":"https://example.com/hooks/orders","secret":"replace-with-a-long-random-secret"}'
```

Submit an event:

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_id":"evt-1001","event_type":"order.created","payload":{"order_id":1001},"timestamp":1700000000}'
```

Inspect deliveries: `GET /deliveries` or filter with `GET /deliveries?status=queued`.

Dispatch is deliberately disabled in the default server because no outbound transport is configured. In tests or an application embedding RelayForge, inject a sender into `create_app(sender=...)`. This avoids accidental network calls and lets a deployment supply its own HTTP client, queue, allowlist, and timeout policy.

## Tests

```bash
python -m pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

Tests cover idempotent intake, conflicting duplicate IDs, event routing, HMAC verification, retry/dead-letter transitions, request validation, and transport injection.

## Important engineering boundaries

- The current delivery and subscription store is in-memory: state is lost on restart and is not shared between workers.
- There is no background scheduler; retries are dispatched explicitly through the API when a sender is injected.
- A real transport adapter must enforce destination hostname/IP allowlists, block private/link-local destinations, disable unsafe redirects, apply timeouts, and use controlled network egress to mitigate SSRF.
- Production deployments should persist state, use atomic worker leases, add exponential backoff with jitter, protect secrets with a secret manager, and authenticate API callers.
- HMAC signatures authenticate payload integrity; consumers should verify the signature and enforce timestamp/replay windows.

The repository is an executable reference implementation, not a claim of a fully deployed multi-tenant delivery service.
