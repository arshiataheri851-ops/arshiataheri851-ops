# Production deployment runbook

This runbook is the operational companion to AtlasRAG. It is intentionally
provider-neutral: it gives a secure Docker/PostgreSQL deployment shape and the
exact checks, but it does not pretend a cloud server, DNS zone, or certificate
has been provisioned.

## 1. Architecture and exposure boundaries

- AtlasRAG API: loopback only on host port 8002.
- PostgreSQL 16: private Compose network only; no host port is published.
- FTS: PostgreSQL `tsvector` with a GIN index and the `simple` text configuration.
  Persian/Arabic normalization happens before indexing and querying.
- Nginx: host-level HTTPS reverse proxy, rate limits, request-size limits.
- Prometheus: optional profile, loopback-only UI, bearer-token-protected scrape.
- RelayForge: loopback-only API; producer/operator keys are separate; worker stays
  disabled until egress controls have been verified.

The PostgreSQL FTS implementation is lexical, not semantic/vector search. It is
an indexed, multi-tenant production-capable baseline. Do not claim semantic
retrieval quality until an embedding model and hybrid/vector evaluation have
been selected and validated against representative judged data.

## 2. Create local deployment secrets

Requirements: Docker Compose v2, OpenSSL, and a Linux host with a supported
PostgreSQL 16 Docker image.

From the repository root, create a local `.env` and the Prometheus token file.
This command generates independent 256-bit random secrets and writes them
locally without printing their values:

```bash
umask 077
mkdir -p secrets migration backups
DB_PASSWORD="$(openssl rand -hex 32)"
TENANT_KEY="$(openssl rand -hex 32)"
METRICS_KEY="$(openssl rand -hex 32)"
SENTIMENT_KEY="$(openssl rand -hex 32)"
PRODUCER_KEY="$(openssl rand -hex 32)"
OPERATOR_KEY="$(openssl rand -hex 32)"

cat > .env <<EOF
SENTIMENT_API_KEY=$SENTIMENT_KEY
ATLASRAG_DB_PASSWORD=$DB_PASSWORD
ATLASRAG_TENANT_API_KEYS_JSON={"tenant-001":"$TENANT_KEY"}
ATLASRAG_METRICS_TOKEN=$METRICS_KEY
RELAYFORGE_API_TOKEN=$PRODUCER_KEY
RELAYFORGE_OPERATOR_TOKEN=$OPERATOR_KEY
RELAYFORGE_ALLOWED_HOSTS=
RELAYFORGE_ENABLE_WORKER=false
RELAYFORGE_MAX_ATTEMPTS=5
RELAYFORGE_RETRY_BASE_DELAY_SECONDS=2
EOF

printf '%s' "$METRICS_KEY" > secrets/atlasrag_metrics_token
chmod 600 .env secrets/atlasrag_metrics_token
unset DB_PASSWORD TENANT_KEY METRICS_KEY SENTIMENT_KEY PRODUCER_KEY OPERATOR_KEY
```

The initial `tenant-001` entry is an operator-owned bootstrap tenant, not a
real customer identity. When onboarding a customer, assign a stable tenant ID,
generate a new independent key, and add the mapping in the secret manager. Do
not reuse keys across customers or paste real keys into GitHub, tickets, or
ChatGPT. Keep `.env` and `secrets/` out of source control.

For a managed secret store, create separate entries for:
- `ATLASRAG_DB_PASSWORD`
- `ATLASRAG_TENANT_API_KEYS_JSON`
- `ATLASRAG_METRICS_TOKEN`
- `SENTIMENT_API_KEY`
- `RELAYFORGE_API_TOKEN`
- `RELAYFORGE_OPERATOR_TOKEN`

Use an independent rotation procedure and deploy after updating the secret
store. Revoke old tenant keys after clients have switched.

## 3. Start PostgreSQL and AtlasRAG

```bash
docker compose config --quiet
docker compose up --build -d atlasrag-db atlasrag
docker compose ps
docker compose logs --tail=100 atlasrag-db atlasrag
```

Wait until both PostgreSQL and AtlasRAG report healthy. The API health endpoint
checks the actual database connection; it does not merely report that the
process is running.

```bash
curl --fail http://127.0.0.1:8002/health
```

The database is not exposed on a host port. Do not add a public `5432` mapping.

## 4. Migrate an existing SQLite database

The migration is optional for a new installation. It is read-only against the
SQLite source and wraps the PostgreSQL import in one transaction. It preserves
tenant IDs, document IDs, metadata, timestamps, and chunk order, and rebuilds
the normalized PostgreSQL search index. A cross-tenant document ownership
conflict aborts the whole import. The source file is never deleted.

1. Stop writes to the old SQLite instance and take a separate copy of its
   database file.
2. Copy the database file into the ignored local `migration/` directory, for
   example `migration/atlasrag.sqlite3`.
3. Start the PostgreSQL-backed service as in section 3.
4. Run:

```bash
docker compose exec atlasrag python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /srv/app/migration/atlasrag.sqlite3
```

5. Verify document/chunk totals and test retrieval using the migrated tenant's
   key. Keep the original SQLite file and its backup until the restore plan has
   been tested and signed off.

The importer is idempotent for matching tenant/document IDs: rerunning it
replaces the destination document content from the source snapshot. Do not
rerun an old snapshot after new production writes have started unless that
overwrite is intended.

## 5. HTTPS, ingress authentication, and rate limits

The repository includes `deploy/nginx/stack.conf.example`. It is a **host-level
Nginx** configuration: the reverse proxy and Docker host must be the same
machine because the upstreams use loopback ports.

Before enabling it:

1. Choose the actual hostnames for FarsiPulse, AtlasRAG, and RelayForge.
2. Point their DNS A/AAAA records at the server. Remove stale AAAA records if
   the server does not serve IPv6.
3. Replace every `example.com` hostname and certificate path in the Nginx
   example.
4. Obtain valid certificates with your ACME client. For example, use a
   temporary HTTP-01 setup or DNS-01 validation before enabling the TLS server
   blocks.
5. Run `nginx -t`, then reload Nginx.
6. At the host firewall, allow inbound TCP 80/443 only. Do not expose ports
   8001, 8002, 8003, 5432, or 9090 to the internet.

The example applies HTTPS redirects, TLS 1.2/1.3, HSTS, request body ceilings,
connection caps, and per-IP request limits. Tune limits only after measuring
legitimate traffic. AtlasRAG and FarsiPulse still require their application API
keys; RelayForge requires its separate producer/operator tokens. TLS is not a
replacement for application authentication.

The hostname and certificate values cannot be completed until the actual
domain names and server IP are known.

## 6. RelayForge outbound egress policy

Read `deploy/ops/relayforge-egress-policy.md` before enabling deliveries.
The application now pins the validated DNS answer for the TLS connection, but
the host/cloud network must also deny outbound access by default and permit
only approved destinations. Use an FQDN-aware cloud firewall/CNI where
available, or a controlled, atomically refreshed IP allowlist for exact
approved webhook hostnames.

Keep `RELAYFORGE_ENABLE_WORKER=false` until the egress policy has been tested
from inside the deployed container. Do not allow the worker to contact
loopback, private, link-local, metadata, or internal service networks.

## 7. Metrics, audit events, and log retention

AtlasRAG exposes low-cardinality Prometheus request counts and latency at
`/metrics`. It requires `Authorization: Bearer <ATLASRAG_METRICS_TOKEN>` (or
the `X-Metrics-Token` header). Without a configured token, the route is hidden.
The API also emits JSON audit events for document writes, batches, listing,
deletion, retrieval, and evaluation. Audit records contain the tenant ID,
event/outcome, item count, and a one-way document reference hash only. They do
not contain API keys, document text, source URLs, or query text.

The Compose file rotates each service's local Docker JSON logs. These local
logs are not a durable central log service; forward them to a restricted log
platform with access control and retention policy before production.

To start the optional Prometheus profile:

```bash
docker compose --profile monitoring up -d prometheus
```

Prometheus listens only on `127.0.0.1:9090`. The sample configuration scrapes
AtlasRAG over the private Compose network and loads availability, 5xx-rate, and
p95-latency alert rules. The scrape token file must match
`ATLASRAG_METRICS_TOKEN`. Alert rules are evaluated locally; configure an
Alertmanager receiver (email/Slack/PagerDuty) in your monitoring environment
before relying on notifications.

## 8. Backups and restore drills

Create a compressed PostgreSQL backup:

```bash
bash deploy/ops/backup_atlasrag_postgres.sh
```

The script writes a mode-600 dump and SHA-256 checksum under `backups/`.
Encrypt and copy backups to a separate account/region or immutable object
storage; a backup on the same host is not disaster recovery. Define a retention
policy and test restores on a separate staging database regularly.

A restore is destructive and requires explicit confirmation:

```bash
CONFIRM_RESTORE=YES bash deploy/ops/restore_atlasrag_postgres.sh backups/atlasrag-YYYYMMDDTHHMMSSZ.dump
```

After restore, verify database health, tenant-specific document counts, sample
citations, and the tenant-isolation tests. Do not restore over the only copy of
the production database.

## 9. Target-host load test

The load test requires an HTTPS target, a configured tenant key, and an
explicit acknowledgement flag. It is capped at 5,000 requests and concurrency
50; begin much lower on staging:

```bash
ATLASRAG_BASE_URL=https://atlasrag.your-domain.example \
ATLASRAG_API_KEY="$ATLASRAG_STAGING_KEY" \
python projects/production-rag-service/scripts/load_test.py \
  --requests 100 --concurrency 5 --allow-target-load
```

Record p50/p95 latency, error rate, CPU, memory/RSS, database connections, and
container restarts. Increase concurrency gradually; do not extrapolate the
synthetic CI benchmark into a customer-facing capacity promise.

## 10. Real-corpus relevance evaluation

The synthetic benchmark checks index correctness and regression latency only.
It is not a quality evaluation.

Create a local JSONL file with 1-200 human-judged examples. Each line must
contain a question and the ID of a document judged relevant. Use only documents
you are authorized to process and remove personal/confidential text from the
evaluation prompts where possible.

Example shape (replace with your own judged data; do not commit customer text):

```json
{"question":"Which policy describes account recovery?","expected_document_id":"policy-account-recovery"}
{"question":"What is the support escalation window?","expected_document_id":"support-escalation"}
```

Run the evaluation against staging:

```bash
ATLASRAG_BASE_URL=https://atlasrag.your-domain.example \
ATLASRAG_API_KEY="$ATLASRAG_STAGING_KEY" \
python projects/production-rag-service/scripts/evaluate_live.py \
  --cases ./private-evaluation-cases.jsonl
```

Review Hit Rate@5 and MRR@5 with the domain owner. Use a held-out set, avoid
tuning on the final test cases, and report sample size and domain. Do not claim
semantic search quality: current retrieval is PostgreSQL lexical full-text
search. Select an embedding model and hybrid/vector strategy only after a
separate Persian/multilingual relevance study.

## 11. Release checklist

- [ ] DNS records and HTTPS certificates verified for all public hostnames.
- [ ] Host firewall exposes only 80/443; database and app ports remain private.
- [ ] Real tenant keys and independent service secrets stored in a secret manager.
- [ ] Key rotation/revocation procedure tested.
- [ ] Nginx rate, connection, and body limits tested with expected client traffic.
- [ ] RelayForge egress policy verified from inside its container.
- [ ] Prometheus scrape succeeds; Alertmanager notifications are tested.
- [ ] Audit logs contain no API keys, document text, or raw queries.
- [ ] Encrypted off-host backups and restore drill completed.
- [ ] Target-host load test and resource limits reviewed.
- [ ] Representative human-judged retrieval evaluation reviewed.
- [ ] FarsiPulse staging/pilot controls and rollback tested.
- [ ] Public deployment explicitly approved by the owner.
