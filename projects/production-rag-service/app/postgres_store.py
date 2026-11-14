"""Tenant-scoped PostgreSQL persistence with lexical and pgvector retrieval."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .retrieval import normalize_text, tokenize
from .store import TenantDocumentConflict

EMBEDDING_DIMENSION = 384
RRF_K = 60


def _vector_literal(vector: list[float]) -> str:
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(f"Embedding vectors must have {EMBEDDING_DIMENSION} dimensions.")
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


class PostgresStore:
    """Transactional PostgreSQL store with tenant-filtered hybrid retrieval."""

    def __init__(
        self,
        database_url: str,
        connect_timeout: int = 5,
        passage_embedding_function: Callable[[list[str]], list[list[float]]] | None = None,
        query_embedding_function: Callable[[str], list[float]] | None = None,
    ):
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("AtlasRAG DATABASE_URL must use the PostgreSQL scheme.")
        if (passage_embedding_function is None) != (query_embedding_function is None):
            raise ValueError("Passage and query embedding functions must be configured together.")
        self.database_url = database_url
        self.connect_timeout = connect_timeout
        self.passage_embedding_function = passage_embedding_function
        self.query_embedding_function = query_embedding_function
        self.retrieval_method = (
            "postgresql_hybrid_rrf" if query_embedding_function else "postgresql_fts"
        )
        self.pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=10,
            timeout=connect_timeout,
            kwargs={"row_factory": dict_row, "application_name": "atlasrag"},
            open=False,
        )
        self.pool.open(wait=True)
        try:
            self._initialize()
        except Exception:
            self.pool.close()
            raise

    def _connect(self):
        return self.pool.connection()

    def close(self) -> None:
        self.pool.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("CREATE EXTENSION IF NOT EXISTS vector")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT,
                    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    search_text TEXT NOT NULL,
                    embedding vector(384),
                    UNIQUE(document_id, chunk_index)
                )
                """
            )
            db.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(384)")
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_tenant_updated "
                "ON documents(tenant_id, updated_at DESC, document_id)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)"
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_search_vector
                ON chunks USING GIN (to_tsvector('simple', search_text))
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
                ON chunks USING hnsw (embedding vector_cosine_ops)
                WHERE embedding IS NOT NULL
                """
            )

    def health_check(self) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 AS healthy, "
                "EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector') AS vector_ready"
            ).fetchone()
            return row["healthy"] == 1 and row["vector_ready"] is True

    def upsert_document(
        self,
        document_id: str,
        title: str,
        source: str | None,
        metadata: dict[str, Any],
        chunks: list[str],
        tenant_id: str = "default",
    ) -> bool:
        return self.upsert_documents_batch(
            [{
                "document_id": document_id,
                "title": title,
                "source": source,
                "metadata": metadata,
                "chunks": chunks,
            }],
            tenant_id=tenant_id,
        )[0]

    def upsert_documents_batch(
        self,
        documents: list[dict[str, Any]],
        tenant_id: str = "default",
    ) -> list[bool]:
        """Atomically upsert one tenant's documents and all their indexed chunks."""
        if not documents:
            return []
        identifiers = [item["document_id"] for item in documents]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("A batch cannot contain duplicate document_id values.")
        if any(not item["chunks"] for item in documents):
            raise ValueError("Every document must contain at least one indexable chunk.")

        all_chunks = [chunk for item in documents for chunk in item["chunks"]]
        embeddings = (
            self.passage_embedding_function(all_chunks)
            if self.passage_embedding_function
            else [None] * len(all_chunks)
        )
        if len(embeddings) != len(all_chunks):
            raise ValueError("Embedding provider returned an unexpected number of vectors.")
        embedding_literals = [
            _vector_literal(vector) if vector is not None else None for vector in embeddings
        ]

        replaced: list[bool] = []
        embedding_offset = 0
        with self._connect() as db:
            for item in documents:
                document_id = item["document_id"]
                existing = db.execute(
                    "SELECT tenant_id FROM documents WHERE document_id=%s FOR UPDATE",
                    (document_id,),
                ).fetchone()
                if existing and existing["tenant_id"] != tenant_id:
                    raise TenantDocumentConflict(
                        "Document ID is already owned by another tenant."
                    )
                replaced.append(existing is not None)
                saved = db.execute(
                    """
                    INSERT INTO documents(
                        document_id, tenant_id, title, source, metadata_json
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(document_id) DO UPDATE SET
                        title=EXCLUDED.title,
                        source=EXCLUDED.source,
                        metadata_json=EXCLUDED.metadata_json,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE documents.tenant_id=EXCLUDED.tenant_id
                    RETURNING document_id
                    """,
                    (
                        document_id,
                        tenant_id,
                        item["title"],
                        item.get("source"),
                        Jsonb(item.get("metadata", {})),
                    ),
                ).fetchone()
                if saved is None:
                    raise TenantDocumentConflict(
                        "Document ID is already owned by another tenant."
                    )

                db.execute("DELETE FROM chunks WHERE document_id=%s", (document_id,))
                rows = []
                for index, chunk in enumerate(item["chunks"]):
                    rows.append((
                        f"{document_id}:{index}",
                        document_id,
                        index,
                        chunk,
                        normalize_text(chunk),
                        embedding_literals[embedding_offset + index],
                    ))
                embedding_offset += len(item["chunks"])
                with db.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO chunks(
                            chunk_id, document_id, chunk_index, text, search_text, embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::vector)
                        """,
                        rows,
                    )
        return replaced

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT d.document_id, d.title, d.source, d.created_at, d.updated_at,
                       COUNT(c.chunk_id)::int AS chunk_count
                FROM documents d
                LEFT JOIN chunks c USING(document_id)
                WHERE d.tenant_id=%s
                GROUP BY d.document_id
                ORDER BY d.updated_at DESC, d.document_id
                LIMIT %s OFFSET %s
                """,
                (tenant_id, limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_chunks(self, tenant_id: str = "default") -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT c.chunk_id, c.document_id, c.chunk_index, c.text,
                       d.title, d.source, d.metadata_json
                FROM chunks c
                JOIN documents d USING(document_id)
                WHERE d.tenant_id=%s
                ORDER BY c.document_id, c.chunk_index
                """,
                (tenant_id,),
            ).fetchall()
        return [
            {**dict(row), "metadata": row["metadata_json"]}
            for row in rows
        ]

    def _lexical_search(
        self, query: str, top_k: int, tenant_id: str
    ) -> list[dict[str, Any]]:
        terms = list(dict.fromkeys(tokenize(query)))
        if not terms or top_k < 1:
            return []
        tsquery = " | ".join(terms)
        with self._connect() as db:
            rows = db.execute(
                """
                WITH query AS (
                    SELECT to_tsquery('simple', %s) AS value
                )
                SELECT c.chunk_id, c.document_id, c.chunk_index, c.text,
                       d.title, d.source, d.metadata_json,
                       (ts_rank_cd(
                           to_tsvector('simple', c.search_text), query.value
                       ) * 100.0)::double precision AS score
                FROM chunks c
                JOIN documents d USING(document_id)
                CROSS JOIN query
                WHERE d.tenant_id=%s
                  AND to_tsvector('simple', c.search_text) @@ query.value
                ORDER BY score DESC, c.chunk_id
                LIMIT %s
                """,
                (tsquery, tenant_id, top_k),
            ).fetchall()
        return [{**dict(row), "metadata": row["metadata_json"]} for row in rows]

    def _semantic_search(
        self, query: str, top_k: int, tenant_id: str
    ) -> list[dict[str, Any]]:
        if not self.query_embedding_function or top_k < 1:
            return []
        vector = _vector_literal(self.query_embedding_function(query))
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT c.chunk_id, c.document_id, c.chunk_index, c.text,
                       d.title, d.source, d.metadata_json,
                       (1.0 - (c.embedding <=> %s::vector))::double precision AS score
                FROM chunks c
                JOIN documents d USING(document_id)
                WHERE d.tenant_id=%s AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector, c.chunk_id
                LIMIT %s
                """,
                (vector, tenant_id, vector, top_k),
            ).fetchall()
        return [{**dict(row), "metadata": row["metadata_json"]} for row in rows]

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Fuse tenant-scoped lexical and semantic rankings using reciprocal rank fusion."""
        if top_k < 1:
            return []
        candidate_k = min(max(top_k * 4, top_k), 100)
        lexical = self._lexical_search(query, candidate_k, tenant_id)
        if not self.query_embedding_function:
            return lexical[:top_k]

        semantic = self._semantic_search(query, candidate_k, tenant_id)
        fused: dict[str, dict[str, Any]] = {}
        for ranked in (lexical, semantic):
            for rank, item in enumerate(ranked, start=1):
                chunk_id = item["chunk_id"]
                if chunk_id not in fused:
                    fused[chunk_id] = {**item, "score": 0.0}
                fused[chunk_id]["score"] += 100.0 / (RRF_K + rank)
        return sorted(
            fused.values(), key=lambda item: (-item["score"], item["chunk_id"])
        )[:top_k]

    def delete_document(self, document_id: str, tenant_id: str = "default") -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM documents WHERE document_id=%s AND tenant_id=%s",
                (document_id, tenant_id),
            )
            return cursor.rowcount > 0

    def delete_documents(self, document_ids: list[str], tenant_id: str = "default") -> int:
        if not document_ids:
            return 0
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM documents WHERE tenant_id=%s AND document_id = ANY(%s)",
                (tenant_id, document_ids),
            )
            return cursor.rowcount

    def count_documents(self, tenant_id: str = "default") -> int:
        with self._connect() as db:
            return int(
                db.execute(
                    "SELECT COUNT(*)::int AS total FROM documents WHERE tenant_id=%s",
                    (tenant_id,),
                ).fetchone()["total"]
            )

    def count_chunks(self, tenant_id: str = "default") -> int:
        with self._connect() as db:
            return int(
                db.execute(
                    """
                    SELECT COUNT(*)::int AS total
                    FROM chunks c JOIN documents d USING(document_id)
                    WHERE d.tenant_id=%s
                    """,
                    (tenant_id,),
                ).fetchone()["total"]
            )
