"""SQLite persistence and indexed retrieval for AtlasRAG."""

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from .retrieval import normalize_text, tokenize


class SQLiteStore:
    """Transactional SQLite store with a persistent FTS5 index.

    Each operation owns its connection. WAL supports concurrent readers and a
    serialized writer; this remains a single-node storage backend.
    """

    def __init__(self, database_path: str):
        self._memory_uri = None
        self._anchor = None
        if database_path == ":memory:":
            self.database_path = ":memory:"
            self._memory_uri = f"file:atlasrag-{uuid4().hex}?mode=memory&cache=shared"
            self._anchor = sqlite3.connect(self._memory_uri, uri=True, timeout=30)
        else:
            self.database_path = str(Path(database_path).expanduser())
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        if self.database_path != ":memory:":
            try:
                Path(self.database_path).chmod(0o600)
            except OSError:
                pass

    def _connect(self) -> sqlite3.Connection:
        if self._memory_uri:
            connection = sqlite3.connect(self._memory_uri, uri=True, timeout=30)
        else:
            connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        if not self._memory_uri:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute("PRAGMA cache_size = -20000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    search_text TEXT NOT NULL DEFAULT '',
                    UNIQUE(document_id, chunk_index)
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2'
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(chunks)")}
            needs_rebuild = "search_text" not in columns
            if needs_rebuild:
                db.execute("ALTER TABLE chunks ADD COLUMN search_text TEXT NOT NULL DEFAULT ''")

            db.executescript(
                """
                DROP TRIGGER IF EXISTS chunks_ai;
                DROP TRIGGER IF EXISTS chunks_ad;
                DROP TRIGGER IF EXISTS chunks_au;
                """
            )
            if needs_rebuild:
                chunk_rows = db.execute("SELECT chunk_id, text FROM chunks").fetchall()
                db.executemany(
                    "UPDATE chunks SET search_text=? WHERE chunk_id=?",
                    [(normalize_text(row["text"]), row["chunk_id"]) for row in chunk_rows],
                )
                db.execute("DELETE FROM chunks_fts")
                db.executemany(
                    "INSERT INTO chunks_fts(chunk_id, text) VALUES (?, ?)",
                    [(row["chunk_id"], normalize_text(row["text"])) for row in chunk_rows],
                )
            db.executescript(
                """
                CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(chunk_id, text) VALUES (new.chunk_id, new.search_text);
                END;
                CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
                    DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                END;
                CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
                    DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                    INSERT INTO chunks_fts(chunk_id, text) VALUES (new.chunk_id, new.search_text);
                END;
                """
            )

    def upsert_document(
        self,
        document_id: str,
        title: str,
        source: str | None,
        metadata: dict[str, Any],
        chunks: list[str],
    ) -> bool:
        return self.upsert_documents_batch([{
            "document_id": document_id,
            "title": title,
            "source": source,
            "metadata": metadata,
            "chunks": chunks,
        }])[0]

    def upsert_documents_batch(self, documents: list[dict[str, Any]]) -> list[bool]:
        """Upsert multiple documents atomically; return whether each already existed."""
        if not documents:
            return []
        identifiers = [item["document_id"] for item in documents]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("A batch cannot contain duplicate document_id values.")
        if any(not item["chunks"] for item in documents):
            raise ValueError("Every document must contain at least one indexable chunk.")

        replaced: list[bool] = []
        with self._connect() as db:
            for item in documents:
                document_id = item["document_id"]
                existed = db.execute(
                    "SELECT 1 FROM documents WHERE document_id=?", (document_id,)
                ).fetchone() is not None
                db.execute(
                    """
                    INSERT INTO documents(document_id,title,source,metadata_json)
                    VALUES(?,?,?,?)
                    ON CONFLICT(document_id) DO UPDATE SET
                        title=excluded.title, source=excluded.source,
                        metadata_json=excluded.metadata_json, updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        document_id,
                        item["title"],
                        item.get("source"),
                        json.dumps(item.get("metadata", {}), ensure_ascii=False),
                    ),
                )
                db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
                db.executemany(
                    "INSERT INTO chunks(chunk_id,document_id,chunk_index,text,search_text) VALUES(?,?,?,?,?)",
                    [
                        (f"{document_id}:{index}", document_id, index, chunk, normalize_text(chunk))
                        for index, chunk in enumerate(item["chunks"])
                    ],
                )
                replaced.append(existed)
        return replaced

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT d.document_id, d.title, d.source, d.created_at, d.updated_at,
                       COUNT(c.chunk_id) AS chunk_count
                FROM documents d LEFT JOIN chunks c USING(document_id)
                GROUP BY d.document_id
                ORDER BY d.updated_at DESC, d.document_id
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_chunks(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT c.chunk_id,c.document_id,c.chunk_index,c.text,
                       d.title,d.source,d.metadata_json
                FROM chunks c JOIN documents d USING(document_id)
                ORDER BY c.document_id,c.chunk_index
                """
            ).fetchall()
        return [{**dict(row), "metadata": json.loads(row["metadata_json"])} for row in rows]

    def search_chunks(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve only matching chunks from the persistent full-text index."""
        if top_k < 1:
            return []
        terms = tokenize(query)
        if not terms:
            return []
        match_query = " OR ".join(
            '"' + term.replace('"', '""') + '"'
            for term in dict.fromkeys(terms)
        )
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT c.chunk_id,c.document_id,c.chunk_index,c.text,
                       d.title,d.source,d.metadata_json,
                       1.0 / (1.0 + abs(bm25(chunks_fts, 0.0, 1.0))) AS score
                FROM chunks_fts
                JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts, 0.0, 1.0), c.chunk_id
                LIMIT ?
                """,
                (match_query, min(top_k, 100)),
            ).fetchall()
        return [
            {**dict(row), "metadata": json.loads(row["metadata_json"])}
            for row in rows
        ]

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
            return cursor.rowcount > 0

    def count_documents(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM documents").fetchone()[0])

    def count_chunks(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
