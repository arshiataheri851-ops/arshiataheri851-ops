# AtlasRAG — Evidence Retrieval Platform

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/production-rag-service.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/production-rag-service.yml)

AtlasRAG is a citation-first document retrieval API. It ingests text, chunks and persists it in SQLite, ranks passages with BM25, extracts evidence sentences, and returns citations with every grounded response.

**Scope is explicit:** AtlasRAG implements retrieval and extractive evidence selection. It does not call an LLM to generate answers. If no matching evidence exists, it abstains instead of inventing a response.

## Implemented capabilities

- Document create/upsert, listing, and deletion.
- Configurable word-based chunking with overlap.
- SQLite persistence, transactions, foreign keys, and WAL mode for file-backed databases.
- BM25 ranking with Persian and English Unicode tokenization.
- Extractive answer selection and per-chunk citations.
- Explicit no-evidence response.
- Hit Rate@k and Mean Reciprocal Rank evaluation endpoint.
- Request validation, configurable limits, Docker, and automated tests.

## Architecture

```text
                  +-----------------------+
                  |   FastAPI / Pydantic  |
                  +-----------+-----------+
                              |
            +-----------------+------------------+
            |                 |                  |
            v                 v                  v
       Document API       Query API         Evaluation API
            |                 |                  |
            v                 v                  v
        Chunker          BM25 Retriever      Retrieval Metrics
            |                 |
            v                 v
          SQLite <------- Evidence Chunks
                              |
                              v
                   Extractive Answer + Citations
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

The database is created automatically at `./data/rag.sqlite3`. Override it with `RAG_DATABASE_PATH`. Open http://127.0.0.1:8000/docs.

## API workflow

Create or replace a document:

```bash
curl -X POST http://127.0.0.1:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"document_id":"guide-1","title":"Database Guide","source":"internal://guide","text":"Database indexes improve lookup performance by reducing the number of rows scanned."}'
```

Search indexed documents:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How do database indexes improve lookup performance?","top_k":3}'
```

List documents: `GET /v1/documents`

Delete a document and its chunks: `DELETE /v1/documents/guide-1`

Evaluate retrieval:

```bash
curl -X POST http://127.0.0.1:8000/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"top_k":3,"cases":[{"question":"How do indexes help?","expected_document_id":"guide-1"}]}'
```

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
python -m pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

## Current boundaries

- BM25 is lexical retrieval; vector embeddings and semantic search are not implemented.
- Answer selection is extractive, not LLM generation.
- SQLite is appropriate for a single application instance; multi-replica deployments need shared persistence and coordinated indexing.
- Authentication, tenant isolation, background ingestion, and distributed workers are not included.
- The included sample corpus is illustrative, not a benchmark.

These boundaries are intentional: no unsupported quality or production-readiness claims are made.
