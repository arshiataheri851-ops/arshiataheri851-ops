"""Copy an existing AtlasRAG SQLite database into PostgreSQL.

The source database is read-only from this script's perspective and is never
deleted or modified. All PostgreSQL inserts/updates run in one transaction;
any ownership conflict or database error rolls back the complete migration.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.postgres_store import PostgresStore  # noqa: E402
from app.retrieval import normalize_text  # noqa: E402
from app.store import TenantDocumentConflict  # noqa: E402


def migrate(sqlite_path: str, database_url: str) -> dict[str, int]:
    source_path = Path(sqlite_path).expanduser()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source database does not exist: {source_path}")

    # Ensure the destination schema and its indexes exist before copying.
    PostgresStore(database_url)
    source = sqlite3.connect(f"file:{source_path.resolve()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    document_columns = {
        row["name"] for row in source.execute("PRAGMA table_info(documents)")
    }
    tenant_expression = "tenant_id" if "tenant_id" in document_columns else "'legacy' AS tenant_id"
    documents = source.execute(
        f"SELECT document_id, {tenant_expression}, title, source, metadata_json, "
        "created_at, updated_at FROM documents ORDER BY document_id"
    )

    document_count = 0
    chunk_count = 0
    try:
        with psycopg.connect(
            database_url,
            connect_timeout=5,
            row_factory=dict_row,
            application_name="atlasrag-sqlite-migration",
        ) as destination:
            for document in documents:
                tenant_id = document["tenant_id"]
                metadata = json.loads(document["metadata_json"] or "{}")
                existing = destination.execute(
                    "SELECT tenant_id FROM documents WHERE document_id=%s FOR UPDATE",
                    (document["document_id"],),
                ).fetchone()
                if existing and existing["tenant_id"] != tenant_id:
                    raise TenantDocumentConflict(
                        f"Destination document ID belongs to a different tenant: "
                        f"{document['document_id']}"
                    )
                saved = destination.execute(
                    """
                    INSERT INTO documents(
                        document_id, tenant_id, title, source, metadata_json,
                        created_at, updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        COALESCE(NULLIF(%s, '')::timestamptz, CURRENT_TIMESTAMP),
                        COALESCE(NULLIF(%s, '')::timestamptz, CURRENT_TIMESTAMP)
                    )
                    ON CONFLICT(document_id) DO UPDATE SET
                        title=EXCLUDED.title,
                        source=EXCLUDED.source,
                        metadata_json=EXCLUDED.metadata_json,
                        updated_at=EXCLUDED.updated_at
                    WHERE documents.tenant_id=EXCLUDED.tenant_id
                    RETURNING document_id
                    """,
                    (
                        document["document_id"],
                        tenant_id,
                        document["title"],
                        document["source"],
                        Jsonb(metadata),
                        document["created_at"],
                        document["updated_at"],
                    ),
                ).fetchone()
                if saved is None:
                    raise TenantDocumentConflict(
                        f"Destination document ID belongs to a different tenant: "
                        f"{document['document_id']}"
                    )

                destination.execute(
                    "DELETE FROM chunks WHERE document_id=%s",
                    (document["document_id"],),
                )
                chunks = source.execute(
                    "SELECT chunk_id, chunk_index, text FROM chunks "
                    "WHERE document_id=? ORDER BY chunk_index",
                    (document["document_id"],),
                ).fetchall()
                destination.executemany(
                    """
                    INSERT INTO chunks(
                        chunk_id, document_id, chunk_index, text, search_text
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            chunk["chunk_id"],
                            document["document_id"],
                            chunk["chunk_index"],
                            chunk["text"],
                            normalize_text(chunk["text"]),
                        )
                        for chunk in chunks
                    ],
                )
                document_count += 1
                chunk_count += len(chunks)
    finally:
        source.close()

    return {"documents": document_count, "chunks": chunk_count}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", required=True)
    parser.add_argument(
        "--database-url",
        default=os.getenv("RAG_DATABASE_URL"),
        help="Destination PostgreSQL URL; defaults to RAG_DATABASE_URL.",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Provide --database-url or set RAG_DATABASE_URL.")
    result = migrate(args.sqlite_path, args.database_url)
    print(json.dumps({"status": "migrated", **result}, indent=2))


if __name__ == "__main__":
    main()
