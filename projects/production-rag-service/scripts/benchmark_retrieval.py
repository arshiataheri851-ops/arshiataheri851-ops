"""Reproducible large-corpus retrieval benchmark (synthetic, not production data)."""

import argparse
import json
import statistics
import time
import tempfile
from pathlib import Path

from app.store import SQLiteStore


def run_benchmark(document_count: int, query_count: int) -> dict:
    if document_count < query_count or query_count < 1:
        raise ValueError("document_count must be >= query_count >= 1")

    temporary_directory = tempfile.TemporaryDirectory()
    store = SQLiteStore(str(Path(temporary_directory.name) / "benchmark.sqlite3"))
    for index in range(document_count):
        anchor = f"atlasanchor{index:05d}"
        text = (
            f"Reference {anchor}. This document describes retrieval indexing, "
            "persistent document storage, query processing, and evidence citations. "
            "The corpus includes English and فارسی content for mixed-language checks. "
        ) * 3
        store.upsert_document(
            f"doc-{index:05d}", f"Benchmark document {index}", "synthetic://benchmark",
            {"benchmark": "synthetic"}, [text],
        )

    latencies_ms: list[float] = []
    reciprocal_ranks: list[float] = []
    hits = 0
    for index in range(query_count):
        question = f"Find reference atlasanchor{index:05d}"
        started = time.perf_counter()
        results = store.search_chunks(question, top_k=5)
        latencies_ms.append((time.perf_counter() - started) * 1000)
        rank = next(
            (position for position, item in enumerate(results, 1)
             if item["document_id"] == f"doc-{index:05d}"),
            None,
        )
        if rank:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    ordered = sorted(latencies_ms)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered)) - 1))
    report = {
        "benchmark_type": "synthetic_controlled_corpus",
        "warning": "Synthetic lexical benchmark; not a substitute for evaluation on representative customer documents and judged queries.",
        "documents": document_count,
        "queries": query_count,
        "chunks": store.count_chunks(),
        "hit_rate_at_5": hits / query_count,
        "mrr_at_5": sum(reciprocal_ranks) / query_count,
        "latency_ms_p50": round(statistics.median(latencies_ms), 3),
        "latency_ms_p95": round(ordered[p95_index], 3),
    }
    temporary_directory.cleanup()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents", type=int, default=1000)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--output", default="reports/atlasrag-benchmark.json")
    args = parser.parse_args()
    report = run_benchmark(args.documents, args.queries)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
