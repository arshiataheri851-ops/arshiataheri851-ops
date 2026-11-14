"""Backfill missing AtlasRAG vectors in a bounded, repeatable operation."""

import argparse

from app.config import get_settings
from app.embeddings import FastEmbedder
from app.postgres_store import PostgresStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("RAG_DATABASE_URL must point to PostgreSQL.")
    embedder = FastEmbedder(
        model_name=settings.embedding_model,
        cache_dir=settings.embedding_cache_dir,
    )
    store = PostgresStore(settings.database_url, embedder=embedder)
    try:
        updated = store.backfill_embeddings(batch_size=args.batch_size)
        print(f"Embedded {updated} previously unindexed chunks.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
