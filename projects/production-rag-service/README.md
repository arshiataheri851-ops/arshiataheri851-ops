# AtlasRAG — Tenant-Isolated Evidence Retrieval

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)
[![PostgreSQL evaluation](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/atlasrag-evaluation.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/atlasrag-evaluation.yml)

AtlasRAG is an authenticated multi-tenant retrieval API. Each API key maps to
one tenant. Document ingestion, batch ingestion, listing, deletion, retrieval,
citations, and evaluation are scoped to that tenant.

## Architecture

- **Production database:** PostgreSQL 16.
- **Lexical search:** PostgreSQL full-text search with a GIN index over normalized
  `tsvector` content using the `simple` text configuration.
- **Semantic search:** pgvector cosine similarity with a 384-dimensional
  multilingual-e5-small embedding model; HNSW approximate-nearest-neighbour index.
- **Hybrid ranking:** reciprocal-rank fusion combines tenant-filtered lexical and
  dense candidates; citations retain the source chunk and document metadata.
- **Language handling:** NFKC normalization, Persian Yeh/Kaf normalization,
  Arabic character normalization, and ZWNJ handling before indexing/search.
- **Local fallback:** SQLite FTS5 remains available for unit tests and local-only
  development; Docker Compose runs PostgreSQL with pgvector.
- **API:** FastAPI with API-key authentication and fail-closed configuration.
- **Observability:** privacy-preserving JSON audit events and a
  bearer-token-protected Prometheus endpoint.

**Search scope:** PostgreSQL deployments can use hybrid lexical + dense semantic
retrieval. The default model is `intfloat/multilingual-e5-small` (384 dimensions),
run locally through FastEmbed/ONNX; no external embedding API receives document
text. The model is multilingual and suitable for Persian evaluation, but quality
must be measured on the target corpus before making customer-facing claims.
SQLite remains lexical-only.

## Security and tenant isolation

- Every protected API endpoint requires `X-API-Key`; missing/invalid keys return
  HTTP 401.
- `RAG_TENANT_API_KEYS_JSON` maps tenant IDs to unique 32-256 character ASCII
  secrets. Key comparisons use constant-time digest comparison.
- Authentication is enabled by default. Startup fails if no tenant keys are
  configured.
- Tenant filtering is enforced in SQL for all document operations and in the
  full-text retrieval query itself.
- Cross-tenant document replacement is rejected; foreign and missing document
  deletion both return HTTP 404.
- PostgreSQL batch ingestion is transactional: a conflict rolls back the entire
  batch.
- Public health checks disclose no tenant/corpus counts and verify database
  connectivity.
- `/metrics` is hidden unless `RAG_METRICS_TOKEN` is configured and requires
  `Authorization: Bearer ...` or `X-Metrics-Token`.
- Audit events never include API keys, document text, source URLs, or raw query
  text.
- The Compose stack binds API ports to loopback and does not publish PostgreSQL.

## Run locally with PostgreSQL

From the repository root:

1. Copy `.env.example` to `.env`.
2. Generate a random hexadecimal `ATLASRAG_DB_PASSWORD` and unique 32+ character
   tenant API key(s); fill `ATLASRAG_TENANT_API_KEYS_JSON`.
3. Optionally set `ATLASRAG_METRICS_TOKEN` to a separate random secret.
4. Start the database and API:

```bash
docker compose up --build -d atlasrag-db atlasrag
docker compose ps
curl http://127.0.0.1:8002/health
```

The API is bound to `127.0.0.1:8002`; PostgreSQL is private to the Compose
network and persists in the `atlasrag-postgres-data` volume. The database
password is required by Compose, and the API refuses to start without tenant
keys. Do not use placeholders as real credentials.

For a complete HTTPS, secret management, monitoring, backup/restore, egress,
load-test, and release procedure, see
[`deploy/PRODUCTION_RUNBOOK.md`](../../deploy/PRODUCTION_RUNBOOK.md).

## API usage

Send the authenticated tenant's API key on every protected request.

Create or replace a document:

```bash
curl -X POST http://127.0.0.1:8002/v1/documents \
  -H "X-API-Key: $ATLASRAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"guide-1","title":"Database Guide","source":"internal://guide","text":"Database indexes improve lookup performance by reducing the number of rows scanned."}'
```

Search the authenticated tenant's documents:

```bash
curl -X POST http://127.0.0.1:8002/v1/query \
  -H "X-API-Key: $ATLASRAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do database indexes improve lookup performance?","top_k":3}'
```

Other endpoints:

- `GET /v1/documents?limit=100&offset=0` — tenant-scoped, paginated listing.
- `DELETE /v1/documents/{document_id}` — tenant-scoped deletion.
- `POST /v1/documents/batch` — atomic batch ingestion, maximum 100 documents.
- `POST /v1/evaluate` — tenant-scoped Hit Rate@k and MRR evaluation.
- `GET /health` — database readiness without tenant data.
- `GET /metrics` — protected Prometheus metrics when a metrics token is set.

## PostgreSQL schema and migration

PostgreSQL tables are initialized idempotently at application startup. The
GIN index is created on `to_tsvector('simple', search_text)`. Each document
row has one tenant owner; chunks inherit ownership through the document
foreign key and are always joined with the tenant filter.

To migrate an existing SQLite file, place a copy under the ignored local
`migration/` directory and run:

```bash
docker compose exec atlasrag python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path /srv/app/migration/atlasrag.sqlite3
```

The source SQLite file is opened read-only and never modified. PostgreSQL
changes are wrapped in one transaction; a cross-tenant ID conflict aborts the
entire migration. The script preserves tenant IDs, document IDs, metadata,
timestamps, and chunk order, and rebuilds normalized search text. See the
production runbook for pre/post-migration checks and rollback precautions.

## Development and validation

```bash
cd projects/production-rag-service
python -m pip install -r requirements-dev.txt
ruff check app tests scripts
pytest -q
python scripts/benchmark_retrieval.py --documents 1000 --queries 100
```

PostgreSQL integration tests run when `RAG_TEST_DATABASE_URL` is set. GitHub
Actions starts PostgreSQL 16, runs those integration tests, and benchmarks
the GIN-indexed backend on a synthetic 1,000-document corpus. The separate
Docker Compose smoke test validates authenticated ingestion, retrieval,
citations, and PostgreSQL readiness.

For existing PostgreSQL data, run `python scripts/backfill_embeddings.py`
inside the AtlasRAG container after enabling semantic search. It fills missing
vectors in bounded batches without changing document text.

The synthetic benchmark is a reproducible index/latency regression baseline,
not evidence of semantic quality on customer data. It creates and deletes its
own uniquely named benchmark tenant and documents.

## Evaluation on real authorized data

Create a local JSONL file with 1-200 human-judged examples. Each line contains
`question` and `expected_document_id`. Use only data you are authorized to
process; do not commit customer documents or private evaluation questions.

```bash
ATLASRAG_BASE_URL=https://atlasrag.your-domain.example \
ATLASRAG_API_KEY="$ATLASRAG_STAGING_KEY" \
python scripts/evaluate_live.py --cases ./private-evaluation-cases.jsonl
```

The evaluation reports Hit Rate@5 and Mean Reciprocal Rank@5 for the tenant
authenticated by the API key. Review the sample size, domain, and labeling
quality before making a retrieval-quality claim.

## Operational limits

- PostgreSQL supports multi-connection deployment; high availability,
  replication, connection pooling, and point-in-time recovery still require
  provider/operations configuration.
- The API currently uses lexical full-text retrieval and extractive answers,
  not LLM-generated responses.
- Tenant key provisioning/rotation is configured out of band; a self-service
  tenant administration control plane is not included.
- Before public traffic, configure HTTPS ingress, edge rate/concurrency limits,
  request-size limits, secret storage/rotation, centralized log retention,
  alert notifications, encrypted off-host backups, restore drills, egress
  restrictions for RelayForge, and target-host load/relevance evaluation.
- Do not claim unrestricted production readiness based only on green CI or
  synthetic benchmarks.
