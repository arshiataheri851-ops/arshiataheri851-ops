"""Backfill missing AtlasRAG chunk embeddings in bounded transactions."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.embeddings import FastEmbedder  # noqa: E402
from app.postgres_store import _vector_literal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 512:
        parser.error("--batch-size must be between 1 and 512")

    database_url = os.environ.get("RAG_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("Set RAG_DATABASE_URL before running the embedding backfill.")

    embedder = FastEmbedder(
        os.getenv(
            "RAG_EMBEDDING_MODEL_NAME",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ),
        os.getenv("RAG_EMBEDDING_CACHE_DIR", "/srv/app/.cache/fastembed"),
    )

    total = 0
    with psycopg.connect(database_url, row_factory=dict_row) as db:
        while True:
            rows = db.execute(
                """
                SELECT chunk_id, text
                FROM chunks
                WHERE embedding IS NULL
                ORDER BY chunk_id
                LIMIT %s
                """,
                (args.batch_size,),
            ).fetchall()
            if not rows:
                break
            vectors = embedder.embed_passages([row["text"] for row in rows])
            if len(vectors) != len(rows):
                raise RuntimeError("Embedding provider returned an unexpected number of vectors.")
            with db.cursor() as cursor:
                cursor.executemany(
                    "UPDATE chunks SET embedding=%s::vector WHERE chunk_id=%s AND embedding IS NULL",
                    [
                        (_vector_literal(vector), row["chunk_id"])
                        for row, vector in zip(rows, vectors, strict=True)
                    ],
                )
            total += len(rows)
            print(f"Backfilled {total} chunks")

    print(f"Embedding backfill complete: {total} chunks")


if __name__ == "__main__":
    main()
