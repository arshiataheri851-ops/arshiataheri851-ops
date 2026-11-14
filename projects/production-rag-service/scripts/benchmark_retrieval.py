"""Reproducible large-corpus retrieval benchmark (synthetic, not production data)."""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.postgres_store import PostgresStore  # noqa: E402
from app.store import SQLiteStore  # noqa: E402


def run_benchmark(document_count: int, query_count: int, database_url: str | None = None) -> dict:
    if document_count < query_count or query_count < 1:
        raise ValueError("document_count must be >= query_count >= 1")

    temporary_directory = None
    if database_url:
        store = PostgresStore(database_url)
        backend = "postgresql_gin_fts"
    else:
        temporary_directory = tempfile.TemporaryDirectory()
        store = SQLiteStore(str(Path(temporary_directory.name) / "benchmark.sqlite3"))
        backend = "sqlite_fts5_reference"
    tenant_id = f"benchmark_{uuid4().hex}"
    document_ids = [f"doc-{uuid4().hex}-{index:05d}" for index in range(document_count)]
    try:
        for index, document_id in enumerate(document_ids):
            anchor = f"atlasanchor{index:05d}"
            text = (
                f"Reference {anchor}. This document describes retrieval indexing, "
                "persistent document storage, query processing, and evidence citations. "
                "The corpus includes English and فارسی content for mixed-language checks. "
            ) * 3
            store.upsert_document(
                document_id, f"Benchmark document {index}", "synthetic://benchmark",
                {"benchmark": "synthetic"}, [text], tenant_id=tenant_id,
            )

        latencies_ms: list[float] = []
        reciprocal_ranks: list[float] = []
        hits = 0
        for index in range(query_count):
            question = f"Find reference atlasanchor{index:05d}"
            started = time.perf_counter()
            results = store.search_chunks(question, top_k=5, tenant_id=tenant_id)
            latencies_ms.append((time.perf_counter() - started) * 1000)
            rank = next(
                (position for position, item in enumerate(results, 1)
                 if item["document_id"] == document_ids[index]),
                None,
            )
            if rank:
                hits += 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

        ordered = sorted(latencies_ms)
        p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered)) - 1))
        return {
            "benchmark_type": "synthetic_controlled_corpus",
            "storage_backend": backend,
            "warning": "Synthetic lexical benchmark; not a substitute for evaluation on representative customer documents and judged queries.",
            "documents": document_count,
            "queries": query_count,
            "chunks": store.count_chunks(tenant_id=tenant_id),
            "hit_rate_at_5": hits / query_count,
            "mrr_at_5": sum(reciprocal_ranks) / query_count,
            "latency_ms_p50": round(statistics.median(latencies_ms), 3),
            "latency_ms_p95": round(ordered[p95_index], 3),
        }
    finally:
        for document_id in document_ids:
            store.delete_document(document_id, tenant_id=tenant_id)
        if temporary_directory:
            temporary_directory.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents", type=int, default=1000)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--output", default="reports/atlasrag-benchmark.json")
    parser.add_argument("--database-url", default=os.getenv("RAG_TEST_DATABASE_URL"))
    args = parser.parse_args()
    report = run_benchmark(args.documents, args.queries, args.database_url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
