# RelayForge — Durable Webhook Delivery Engine

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

RelayForge accepts events, routes them to subscriptions, signs canonical payloads with HMAC-SHA256, and delivers them through an allowlisted HTTP transport. Events and delivery state are persisted in SQLite using a transactional outbox.

## Implemented capabilities

- Durable event and subscription storage in SQLite; state survives process restarts.
- Transactional event idempotency: same event ID and content returns the original delivery IDs; conflicting content is rejected.
- Transactional outbox records for every matching subscription.
- Real HTTPX webhook sender with TLS verification, explicit hostname allowlist, bounded timeout, no environment proxy inheritance, and redirects disabled.
- HMAC-SHA256 signatures with timestamp and stable delivery ID headers.
- Automatic background worker, when explicitly enabled and configured with an outbound allowlist.
- Exponential retry backoff with jitter, attempt limits, delivery attempt history, and dead-letter state.
- Atomic worker claims with leases; expired sending leases become eligible for recovery after a worker crash.
- Bounded delivery listing, per-delivery status inspection, and operator-controlled dead-letter redrive.
- Payload limits, HTTPS-only subscriptions, and secret omission from subscription-list responses.

## Delivery semantics

RelayForge provides **at-least-once delivery attempts**, not universal exactly-once delivery.

A process may crash after the receiver accepts a webhook but before RelayForge records the acknowledgement. In that case, the expired lease is retried and the receiver may see the same delivery again. The X-Webhook-Delivery value is stable across attempts; receivers should store it as an idempotency key and return success for duplicates.

A 2xx response marks a delivery as delivered. Non-2xx responses and transport exceptions schedule another attempt using exponential backoff and jitter. Once the configured attempt limit is reached, the delivery enters dead_letter for inspection and manual resolution.

## Architecture

```text
Event Producer
     |
     v
FastAPI + Request Validation
     |
     v
SQLite Transaction (event + delivery outbox)
     |
     v
Background Worker / Manual Dispatch
     |
     v
Atomic Claim + Lease + Attempt Record
     |
     v
Allowlisted HTTPX Sender + HMAC Headers
     |
     +---- 2xx ----> DELIVERED
     |
     +---- failure -> BACKOFF -> RETRY
                              |
                              +---- max attempts -> DEAD LETTER
```

## Run locally

Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

For a real sender, configure the allowed receiver hostnames before starting the service:

```bash
# PowerShell
$env:RELAYFORGE_ALLOWED_HOSTS = "hooks.example.com"
$env:RELAYFORGE_API_TOKEN = "<at-least-32-random-characters>"
$env:RELAYFORGE_OPERATOR_TOKEN = "<a-different-at-least-32-random-characters>"
$env:RELAYFORGE_ENABLE_WORKER = "true"
$env:RELAYFORGE_DATABASE_PATH = "data/relayforge.sqlite3"

# macOS/Linux
export RELAYFORGE_ALLOWED_HOSTS="hooks.example.com"
export RELAYFORGE_API_TOKEN="<at-least-32-random-characters>"
export RELAYFORGE_OPERATOR_TOKEN="<a-different-at-least-32-random-characters>"
export RELAYFORGE_ENABLE_WORKER="true"
export RELAYFORGE_DATABASE_PATH="data/relayforge.sqlite3"

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The allowlist is exact-host matching; do not use broad wildcards. The sender rejects non-HTTPS URLs, non-allowlisted hostnames, and DNS answers containing non-public IP addresses. It disables redirects and environment proxies and verifies TLS certificates. Network-level egress filtering is still required to defend against DNS rebinding and infrastructure-specific routing risks.

## API workflow

All write/read API routes require authentication. Event producers use `X-RelayForge-API-Key`; subscription and delivery administration uses the separate `X-RelayForge-Operator-Key`. Both secrets must be at least 32 characters. If either is missing or too short, its protected routes fail closed with HTTP 503. Keep the operator token restricted to trusted operators.

Register a subscription (operator token):

```bash
curl -X POST http://127.0.0.1:8000/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"subscription_id":"orders","event_type":"order.created","url":"https://hooks.example.com/orders","secret":"replace-with-a-long-random-secret"}'
```

Submit an event (producer token):

```bash
curl -X POST http://127.0.0.1:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_id":"evt-1001","event_type":"order.created","payload":{"order_id":1001},"timestamp":1700000000}'
```

Inspect deliveries: GET /deliveries?status=queued

Inspect one delivery: GET /deliveries/{delivery_id}\n\nRequeue a dead-letter delivery after operator review: POST /deliveries/{delivery_id}/redrive

When the background worker is enabled, queued deliveries and due retries are sent automatically. When it is disabled, an operator can dispatch an item manually using POST /deliveries/{delivery_id}/dispatch. Manual dispatch respects the scheduled retry time.

## Configuration

| Variable | Default | Description |
|---|---|---|
| RELAYFORGE_DATABASE_PATH | data/relayforge.sqlite3 in the service entrypoint | Persistent SQLite database path |
| RELAYFORGE_ALLOWED_HOSTS | empty | Comma-separated exact hostnames permitted for outbound webhooks |
| RELAYFORGE_API_TOKEN | empty | Producer API token; minimum 32 characters; protected routes fail closed if unset |
| RELAYFORGE_OPERATOR_TOKEN | empty | Separate operator token for subscription and delivery administration; minimum 32 characters |
| RELAYFORGE_ENABLE_WORKER | false | Enable automatic background dispatch |
| RELAYFORGE_MAX_ATTEMPTS | 5 | Maximum attempts per delivery (1–10) |
| RELAYFORGE_RETRY_BASE_DELAY_SECONDS | 2 | Base delay for exponential retry backoff |

The Compose deployment mounts relayforge-data at /srv/app/data so SQLite state survives container replacement.

## Tests

```bash
python -m pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

Tests cover durable restart recovery, event idempotency, HMAC signing, retry/dead-letter transitions, automatic worker delivery, outbound hostname restrictions, and API validation.

## Operational security and limitations

- Treat subscription signing secrets as sensitive. SQLite stores them locally; use encrypted disks and restrict database/backup access. A production multi-tenant service should move secrets to a dedicated secret manager or encrypted column store.
- Producer and operator routes enforce separate constant-time-checked bearer-style custom header tokens. The operator token grants administrative access; distribute it only to trusted operators. Keep the service behind authenticated ingress/API access controls as an additional boundary.
- Maintain a strict outbound hostname allowlist and network egress policy. Do not accept arbitrary user-controlled callback destinations in an internet-facing deployment.
- SQLite WAL is a durable single-node store, not a distributed queue. Do not run multiple independent replicas against separate local database files and assume shared state. For multi-node scale, move the outbox and leases to PostgreSQL and use a dedicated worker fleet.
- Delivery is at-least-once. Exactly-once side effects require receiver-side idempotency and cannot be guaranteed by the sender alone.
- Dead-letter deliveries block subscription removal until resolved; redrive also verifies the subscription still exists.
- The Compose port binds to loopback only. Do not publish the service directly to the internet; place it behind authenticated ingress and network egress controls.
- Dead-letter review, metrics/alerts, backup/restore drills, retention policy, and operational dashboards remain deployment responsibilities.

This is a production-oriented reference implementation, not a claim that a public multi-tenant delivery platform has been deployed or independently security-audited.
