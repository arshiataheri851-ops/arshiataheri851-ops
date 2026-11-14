# AtlasRAG — Tenant-Isolated Evidence Retrieval Platform

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

AtlasRAG is an authenticated, multi-tenant document retrieval API. It ingests documents, indexes passages with SQLite FTS5, and returns source-linked citations. Every API key maps to one tenant, and all document operations are filtered by that tenant.

**Scope is explicit:** AtlasRAG performs lexical retrieval and extractive evidence selection. It does not call an LLM to generate answers. If no matching evidence exists, it abstains instead of inventing a response.

## Security model

- Every protected endpoint requires `X-API-Key`; missing or invalid keys receive HTTP 401.
- Each API key maps to exactly one configured tenant ID through `RAG_TENANT_API_KEYS_JSON`.
- API keys must be independently generated random secrets of at least 32 characters. Comparisons use constant-time `hmac.compare_digest`.
- Ingestion, batch ingestion, listing, deletion, retrieval, citations, and evaluation are all tenant-scoped.
- A tenant cannot retrieve, list, overwrite, or delete another tenant's documents. Cross-tenant document-ID collisions return HTTP 409; foreign or missing deletes both return 404.
- Tenant-wide counts are not exposed by the unauthenticated health endpoint.
- Authentication is enabled by default. Startup fails if authentication is enabled but no valid tenant keys are configured.
- Existing database records found during migration are quarantined under tenant ID `legacy`; they are not visible to newly configured tenants unless an administrator explicitly provisions that tenant.
- Use HTTPS at the ingress/reverse proxy, store API keys in a secrets manager, rotate keys, restrict network access, and back up the database. SQLite is a single-node storage backend, not a distributed multi-replica database.

The API-key mapping is configuration-based, not a self-service identity or key-management system. Do not expose the API directly to browsers; put a trusted backend/API gateway in front of it so tenant credentials are not embedded in client-side code.

## Capabilities

- Document create/upsert, listing, deletion, and atomic batch ingestion (up to 100 documents).
- Configurable chunking with overlap.
- SQLite transactions, foreign keys, WAL mode, bounded cache, and persistent FTS5 indexing.
- Persian/Arabic Unicode normalization (including common Yeh/Kaf variants and ZWNJ handling).
- Indexed top-k retrieval without loading the full corpus into application memory per query.
- Extractive answers, source-linked citations, and explicit no-evidence responses.
- Tenant-scoped Hit Rate@k and Mean Reciprocal Rank evaluation.
- Paginated document listing and automated tests for cross-tenant access isolation.

## Architecture

```text
                   FastAPI
                     |
             X-API-Key authentication
                     |
              API key -> tenant ID
                     |
          Tenant-scoped service layer
             /       |        \
        Ingest     Query    Evaluation
           |         |          |
           +---- SQLite / FTS5 --+
             tenant-filtered rows
                     |
          Extractive answer + citations
```

## Run locally

Python 3.11+ with SQLite compiled with FTS5 support.

From the repository root, copy `.env.example` to `.env`, replace the AtlasRAG example mapping with your own tenant ID and independently generated random API key (minimum 32 characters), then start the service:

```bash
docker compose up --build -d atlasrag
docker compose ps atlasrag
```

The API is bound to `127.0.0.1:8002` and persists its database in the `atlasrag-data` named volume. The service fails to start if `ATLASRAG_TENANT_API_KEYS_JSON` is missing or invalid. Do not use the example placeholder as a real credential.

Check health:

```bash
curl http://127.0.0.1:8002/health
```

Run the end-to-end authenticated smoke check (set `ATLASRAG_API_KEY` to a configured tenant key):

```python
python projects/production-rag-service/scripts/smoke_test.py --base-url http://127.0.0.1:8002 --api-key "$ATLASRAG_API_KEY"
```

Open `http://127.0.0.1:8002/docs` for the interactive API. Stop the service with `docker compose down`; the named volume remains. To remove demo data too, use `docker compose down -v`.

## API workflow

Send the tenant's API key in the `X-API-Key` header on every protected request.

Create or replace a document:

```bash
curl -X POST http://127.0.0.1:8002/v1/documents \
  -H "X-API-Key: $ATLASRAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"guide-1","title":"Database Guide","source":"internal://guide","text":"Database indexes improve lookup performance by reducing the number of rows scanned."}'
```

Batch ingestion (maximum 100 documents) uses `POST /v1/documents/batch` with a JSON body containing a `documents` array.

Search only the authenticated tenant's documents:

```bash
curl -X POST http://127.0.0.1:8002/v1/query \
  -H "X-API-Key: $ATLASRAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do database indexes improve lookup performance?","top_k":3}'
```

- List this tenant's documents: `GET /v1/documents?limit=100&offset=0`
- Delete this tenant's document: `DELETE /v1/documents/guide-1`
- Evaluate retrieval against this tenant's labeled cases: `POST /v1/evaluate`

## Large-corpus benchmark

Run the reproducible controlled benchmark:

```bash
python projects/production-rag-service/scripts/benchmark_retrieval.py --documents 1000 --queries 100
```

The script reports Hit Rate@5, MRR@5, p50 latency, p95 latency, and corpus size. GitHub Actions runs it on changes and uploads the JSON report as an artifact.

**Important:** this benchmark uses generated synthetic documents and unique lexical anchors. It verifies index correctness and gives a repeatable scale/latency baseline; it is not evidence of semantic relevance on customer content. A representative, permission-cleared document corpus and human-judged query/relevance labels are still required for a genuine domain-quality evaluation.

## Configuration

All settings use the `RAG_` prefix:

| Variable | Default | Description |
|---|---:|---|
| `RAG_AUTH_REQUIRED` | `true` | Require API-key authentication; production must keep this enabled |
| `RAG_TENANT_API_KEYS_JSON` | empty | JSON object mapping tenant IDs to unique API keys; required when auth is enabled |
| `RAG_DATABASE_PATH` | `./data/rag.sqlite3` | SQLite file path |
| `RAG_CHUNK_SIZE` | `700` | Maximum words per chunk |
| `RAG_CHUNK_OVERLAP` | `100` | Overlapping words |
| `RAG_MAX_DOCUMENT_CHARS` | `100000` | Document size ceiling |
| `RAG_MAX_QUERY_CHARS` | `2000` | Query size ceiling |
| `RAG_DEFAULT_TOP_K` | `5` | Default retrieved chunks |
| `RAG_MAX_TOP_K` | `20` | Maximum retrieved chunks |

## Quality checks

```bash
ruff check app tests scripts
pytest -q
python scripts/benchmark_retrieval.py --documents 1000 --queries 100
```

## Operational boundaries

- SQLite is suitable for a single service instance. Multi-node deployment requires a shared transactional database and a tenant-aware search backend.
- Configure HTTPS, ingress allowlists, rate limits, request-size limits, monitoring, log redaction, backups, and a tested restore/rollback procedure before production exposure.
- API keys are configured out of band. A production control plane for tenant provisioning, key rotation/revocation, audit events, and usage quotas remains a separate operational component.
- The retrieval engine is lexical, not semantic/vector or hybrid search.
- Answer selection is extractive, not LLM generation.
- Representative judged relevance evaluation and target-host load testing are still required before making customer-facing quality or capacity claims.

Do not claim unrestricted production readiness solely from passing CI or synthetic benchmark results.
