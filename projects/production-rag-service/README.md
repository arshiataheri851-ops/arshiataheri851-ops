# Production RAG Service

[![CI](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/production-rag-service.yml/badge.svg)](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/workflows/production-rag-service.yml)
A citation-first document retrieval API. It ingests text, chunks and stores it in SQLite, ranks passages with BM25, returns an extractive answer with source citations, and evaluates retrieval quality.

> Scope is intentionally explicit: this project implements retrieval and evidence handling. It does not claim to be an LLM-powered generator. Answers are extracted from indexed text; unsupported questions return an explicit no-evidence response.

## Architecture

```text
Client -> FastAPI validation
          |-- POST /v1/documents -> chunker -> SQLite
          |-- POST /v1/query ----> BM25 -> evidence sentence -> answer + citations
          |-- POST /v1/evaluate -> Hit Rate@k + Mean Reciprocal Rank
```

## Features

- Document upsert with stable IDs, source, and metadata.
- Word-boundary chunking with configurable overlap.
- SQLite persistence.
- BM25 ranking with English and Persian Unicode token support.
- Citations include source, document, chunk, text, and score.
- Explicit ungrounded response when no evidence matches.
- Retrieval evaluation using Hit Rate@k and MRR.
- Request-size limits, Pydantic validation, Docker, and GitHub Actions CI.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

## API

Ingest:

```bash
curl -X POST http://127.0.0.1:8000/v1/documents \\
  -H 'Content-Type: application/json' \\
  -d '{"document_id":"guide-1","title":"Database Guide","source":"internal://guide","text":"Database indexes improve lookup performance by reducing scanned rows."}'
```

Query:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \\
  -H 'Content-Type: application/json' \\
  -d '{"question":"How do database indexes improve lookup performance?","top_k":3}'
```

Evaluate:

```bash
curl -X POST http://127.0.0.1:8000/v1/evaluate \\
  -H 'Content-Type: application/json' \\
  -d '{"top_k":3,"cases":[{"question":"What is retrieval augmented generation?","expected_document_id":"rag-basics"}]}'
```

## Sample corpus

`data/sample_documents.jsonl` contains illustrative documents. Ingest each JSONL record through the document endpoint. This sample is not a benchmark.

## Tests

```bash
ruff check app tests
pytest -q
```

Tests cover chunking and overlap, Persian/English tokenization, ranking, persistence/upsert, API validation, citations, ungrounded questions, and evaluation metrics.

## Configuration

Settings use the `RAG_` environment prefix; defaults are listed in `.env.example`. SQLite is suitable for a single-instance demo. Multi-replica deployment should use a shared database and a dedicated search index.

## Limitations

- BM25 is lexical; semantic embedding retrieval is not implemented.
- Answer generation is extractive, not an LLM call.
- Authentication, tenant isolation, background ingestion, and distributed indexing are out of scope.
- The sample corpus is synthetic documentation, not a real-world benchmark.

These boundaries avoid implying capabilities or performance that have not been measured.
