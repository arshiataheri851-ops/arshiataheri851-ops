from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IngestResult:
    event_id: str
    status: str
    duplicate: bool = False


class EventPipeline:
    """Small, durable event pipeline with deduplication and replayable aggregates."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    value REAL NOT NULL,
                    payload TEXT NOT NULL,
                    ingested_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS aggregates (
                    window_start TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    value_sum REAL NOT NULL,
                    PRIMARY KEY (window_start, event_type)
                );
                """
            )

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str):
            raise ValueError("occurred_at must be an ISO-8601 string")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("occurred_at must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return parsed.astimezone(UTC)

    @staticmethod
    def _validate(payload: Any) -> tuple[str, str, datetime, float]:
        if not isinstance(payload, dict):
            raise ValueError("event must be a JSON object")
        event_id = payload.get("event_id")
        event_type = payload.get("event_type")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be a non-empty string")
        occurred_at = EventPipeline._parse_timestamp(payload.get("occurred_at"))
        value = payload.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("value must be a number")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("value must be finite")
        return event_id, event_type, occurred_at, numeric_value

    def ingest(self, payload: Any) -> IngestResult:
        received_at = datetime.now(UTC).isoformat()
        try:
            event_id, event_type, occurred_at, value = self._validate(payload)
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            with self._connect() as db:
                cursor = db.execute(
                    """INSERT OR IGNORE INTO events
                       (event_id, event_type, occurred_at, value, payload, ingested_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (event_id, event_type, occurred_at.isoformat(), value, serialized, received_at),
                )
                if cursor.rowcount == 0:
                    return IngestResult(event_id, "accepted", duplicate=True)
            return IngestResult(event_id, "accepted")
        except (ValueError, TypeError, OverflowError) as exc:
            with self._connect() as db:
                db.execute(
                    "INSERT INTO dead_letters (payload, reason, received_at) VALUES (?, ?, ?)",
                    (json.dumps(payload, default=str, sort_keys=True), str(exc), received_at),
                )
            rejected_id = (
                payload.get("event_id", "unknown")
                if isinstance(payload, dict)
                else "unknown"
            )
            return IngestResult(str(rejected_id), "rejected")

    def rebuild_aggregates(self, window_minutes: int = 1) -> int:
        if (
            isinstance(window_minutes, bool)
            or not isinstance(window_minutes, int)
            or window_minutes <= 0
        ):
            raise ValueError("window_minutes must be a positive integer")
        with self._connect() as db:
            db.execute("DELETE FROM aggregates")
            rows = db.execute("SELECT event_type, occurred_at, value FROM events").fetchall()
            buckets: dict[tuple[str, str], list[float]] = {}
            for row in rows:
                timestamp = datetime.fromisoformat(row["occurred_at"])
                window_seconds = window_minutes * 60
                bucket_epoch = int(timestamp.timestamp()) // window_seconds * window_seconds
                bucket = datetime.fromtimestamp(bucket_epoch, tz=UTC)
                key = (bucket.isoformat(), row["event_type"])
                buckets.setdefault(key, []).append(float(row["value"]))
            db.executemany(
                "INSERT INTO aggregates "
                "(window_start, event_type, event_count, value_sum) VALUES (?, ?, ?, ?)",
                [
                    (start, event_type, len(values), sum(values))
                    for (start, event_type), values in buckets.items()
                ],
            )
            return len(buckets)

    def get_aggregates(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT window_start, event_type, event_count, value_sum "
                "FROM aggregates ORDER BY window_start, event_type"
            ).fetchall()
        return [dict(row) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as db:
            events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            dead_letters = db.execute("SELECT COUNT(*) FROM dead_letters").fetchone()[0]
        return {"events": events, "dead_letters": dead_letters}
