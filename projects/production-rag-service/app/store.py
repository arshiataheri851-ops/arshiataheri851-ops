"""SQLite persistence for AtlasRAG documents and chunks."""

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteStore:
    """Small transactional SQLite store; each operation owns its connection."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        if self.database_path != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
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
                    UNIQUE(document_id, chunk_index)
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
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
        with self._connect() as db:
            existed = db.execute(
                "SELECT 1 FROM documents WHERE document_id=?", (document_id,)
            ).fetchone() is not None
            db.execute(
                """
                INSERT INTO documents(document_id,title,source,metadata_json)
                VALUES(?,?,?,?)
                ON CONFLICT(document_id) DO UPDATE SET
                    title=excluded.title,
                    source=excluded.source,
                    metadata_json=excluded.metadata_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (document_id, title, source, json.dumps(metadata, ensure_ascii=False)),
            )
            db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            db.executemany(
                "INSERT INTO chunks(chunk_id,document_id,chunk_index,text) VALUES(?,?,?,?)",
                [
                    (f"{document_id}:{index}", document_id, index, chunk)
                    for index, chunk in enumerate(chunks)
                ],
            )
        return existed

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT d.document_id, d.title, d.source, d.created_at, d.updated_at,
                       COUNT(c.chunk_id) AS chunk_count
                FROM documents d LEFT JOIN chunks c USING(document_id)
                GROUP BY d.document_id
                ORDER BY d.updated_at DESC, d.document_id
                """
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
        return [
            {**dict(row), "metadata": json.loads(row["metadata_json"])}
            for row in rows
        ]

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM documents WHERE document_id=?", (document_id,)
            )
            return cursor.rowcount > 0

    def count_documents(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
