# AtlasRAG — Evidence Retrieval Platform

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/engineering-projects-ci.yml)

AtlasRAG is a citation-first document retrieval API. It ingests documents, chunks and persists them in SQLite, retrieves matching passages through a persistent SQLite FTS5 index, and returns source-linked citations with every grounded response.

**Scope is explicit:** AtlasRAG implements lexical retrieval and extractive evidence selection. It does not call an LLM to generate answers. If no matching evidence exists, it abstains instead of inventing a response.

## Capabilities

- Document create/upsert, listing, deletion, and bounded batch ingestion (up to 100 documents per request).
- Configurable word-based chunking with overlap.
- SQLite transactions, foreign keys, WAL mode, bounded cache, and persistent FTS5 indexing.
- Persian/Arabic Unicode normalization (including common Yeh/Kaf variants and ZWNJ handling).
- Indexed top-k retrieval without loading the entire chunk corpus into application memory per query.
- Extractive answer selection and per-chunk citations.
- Explicit no-evidence response.
- Hit Rate@k and Mean Reciprocal Rank evaluation endpoint.
- Paginated document listing and automated tests.

## Architecture

```text
                    +-----------------------+
                    |   FastAPI / Pydantic  |
                    +-----------+-----------+
                                |
               +----------------+----------------+
               |                |                |
          Document API      Query API       Evaluation API
               |                |                |
          Chunker + Batch    FTS5 indexed      Retrieval metrics
               |             retrieval
               v                |
          SQLite tables <--- FTS5 index
               |                |
               +----------------+
                                v
                  Extractive answer + citations
```

## Run locally

Python 3.11+ with SQLite compiled with FTS5 support.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The database is created automatically at `./data/rag.sqlite3`. Override it with `RAG_DATABASE_PATH`. Open http://127.0.0.1:8000/docs.

## Quick start with Docker Compose

From the repository root:

```bash
docker compose up --build -d atlasrag
docker compose ps atlasrag
```

The API is bound to `127.0.0.1:8002` and persists its SQLite database in the `atlasrag-data` named volume. Wait until the container health status is `healthy`, then run the end-to-end smoke check:

```bash
python projects/production-rag-service/scripts/smoke_test.py --base-url http://127.0.0.1:8002
```

Open `http://127.0.0.1:8002/docs` for the interactive API. Stop the service with `docker compose down`; the named volume remains. To remove demo data too, use `docker compose down -v`.

The Compose setup binds demo services to loopback only. AtlasRAG currently has no user authentication or tenant isolation; do not expose it beyond the local machine or load confidential customer documents. FarsiPulse in the shared stack requires a configured `SENTIMENT_API_KEY` and fails closed if it is missing. RelayForge also fails closed on protected routes until its independent producer and operator tokens are configured.

## API workflow

Create or replace one document:

```bash
curl -X POST http://127.0.0.1:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"document_id":"guide-1","title":"Database Guide","source":"internal://guide","text":"Database indexes improve lookup performance by reducing the number of rows scanned."}'
```

Ingest a batch (maximum 100 documents):

```json
{
  "documents": [
    {"document_id":"guide-2","title":"Search Guide","text":"Full-text indexes accelerate lexical search."},
    {"document_id":"guide-3","title":"Storage Guide","text":"SQLite WAL allows concurrent readers."}
  ]
}
```

Send that JSON to `POST /v1/documents/batch`.

Search indexed documents:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How do database indexes improve lookup performance?","top_k":3}'
```

List documents with pagination: `GET /v1/documents?limit=100&offset=0`

Delete a document and its indexed chunks: `DELETE /v1/documents/guide-1`

Evaluate a labeled set:

```bash
curl -X POST http://127.0.0.1:8000/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"top_k":3,"cases":[{"question":"How do indexes help?","expected_document_id":"guide-1"}]}'
```

## Large-corpus benchmark

Run the reproducible controlled benchmark:

```bash
python scripts/benchmark_retrieval.py --documents 1000 --queries 100
```

The script reports Hit Rate@5, MRR@5, p50 latency, p95 latency, and corpus size. GitHub Actions runs it on changes and uploads the JSON report as an artifact.

**Important:** this benchmark uses generated synthetic documents and unique lexical anchors. It verifies index correctness and gives a repeatable scale/latency baseline; it is not evidence of semantic relevance on customer content. A representative, permission-cleared document corpus and human-judged query/relevance labels are still required for a genuine domain-quality evaluation.

## Configuration

Environment variables use the `RAG_` prefix:

| Variable | Default | Description |
|---|---:|---|
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

## Storage and scaling boundaries

- FTS5 avoids a full-corpus Python scan on every query; document changes update the index transactionally.
- SQLite WAL and connection-level timeouts improve single-node concurrency and restart durability.
- SQLite remains a single-node database. Multiple API replicas sharing one local file are not a supported distributed deployment.
- For multi-node scale, the next storage adapter should target PostgreSQL plus a dedicated search index (or a managed vector/hybrid search service), with background ingestion and tenant-aware access controls.
- Authentication, tenant isolation, asynchronous ingestion, distributed workers, vector embeddings, and semantic/hybrid ranking are not implemented.
- Answer selection is extractive, not LLM generation.

These boundaries are intentional: benchmark results and production capabilities must not be overstated.
