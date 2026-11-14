# RelayForge — Durable Webhook Delivery Engine

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

RelayForge accepts events, routes them to subscriptions, signs canonical payloads with HMAC-SHA256, and delivers them through an allowlisted HTTPS transport. Events and delivery state are persisted in SQLite using a transactional outbox.

## Implemented capabilities

- Durable event and subscription storage in SQLite; state survives process restarts.
- Transactional event idempotency and outbox creation.
- Exact-host allowlisting and DNS-pinned TCP connections.
- Every DNS answer is checked; mixed public/private answers are rejected.
- The TCP socket connects to the validated numeric IP, so the HTTP layer cannot perform a second hostname lookup.
- TLS SNI and certificate hostname verification continue to use the original allowlisted hostname.
- HTTPS only, port 443 only, redirects disabled, bounded connection/read timeout, and no environment proxy inheritance.
- HMAC-SHA256 signatures with timestamp and stable delivery ID headers.
- Optional background worker, exponential retry backoff, leases, attempt history, and dead-letter redrive.
- Separate producer and operator authentication tokens; protected routes fail closed when tokens are missing or too short.

## Delivery semantics

RelayForge provides **at-least-once delivery attempts**, not exactly-once delivery. A crash after remote acceptance but before local acknowledgement can produce a duplicate. Receivers should deduplicate by the stable `X-Webhook-Delivery` header.

## Run locally

Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

For real delivery, configure an exact hostname allowlist and two independent secrets (each at least 32 random characters):

```powershell
$env:RELAYFORGE_ALLOWED_HOSTS = "hooks.example.com"
$env:RELAYFORGE_API_TOKEN = "<producer-secret>"
$env:RELAYFORGE_OPERATOR_TOKEN = "<different-operator-secret>"
$env:RELAYFORGE_ENABLE_WORKER = "true"
$env:RELAYFORGE_DATABASE_PATH = "data/relayforge.sqlite3"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use port 443 for registered webhook destinations. Wildcards, IP-literal destinations, credentials in URLs, redirects, and non-public DNS answers are rejected.

## Security model and deployment requirements

The sender resolves the allowlisted hostname once per delivery, checks **all** A/AAAA answers, rejects the destination if any answer is non-public, and connects directly to one validated numeric address. TLS SNI and certificate validation remain bound to the allowlisted DNS hostname. This closes the application-level DNS-rebinding gap caused by validating one DNS lookup and then allowing the HTTP client to resolve the hostname again.

Network egress policy remains necessary as defense in depth. In production, permit outbound TCP only to the approved receiver addresses/ports where practical, keep the API behind authenticated HTTPS ingress, and do not accept arbitrary user-controlled callback URLs. The service is not independently security-audited.

Producer routes use `X-RelayForge-API-Key`; subscription and delivery administration uses `X-RelayForge-Operator-Key`. The operator token grants administrative access and must be restricted to trusted operators. Store signing secrets and API tokens in a secret manager, not in source control.

SQLite WAL is a durable single-node store, not a distributed queue. Multi-node deployments require a shared PostgreSQL outbox/lease store and coordinated workers. Dead-letter review, monitoring/alerts, backup/restore drills, and retention policies remain operational responsibilities.

## Tests

```bash
python -m pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

Tests cover persistence/recovery, retries, worker dispatch, authentication, hostname allowlisting, mixed public/private DNS rejection, pinned-address selection, and destination port restrictions.
