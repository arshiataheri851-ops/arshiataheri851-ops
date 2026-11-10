"""SQLite event store for recommendation interactions."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from typing import Any


EVENT_WEIGHTS = {"view": 1.0, "click": 3.0, "purchase": 8.0}


class EventStore:
    def __init__(
        self,
        db_path: str = ":memory:",
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._clock = clock or time.time
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS interaction_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                occurred_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_user
                ON interaction_events(user_id, occurred_at);
            CREATE INDEX IF NOT EXISTS idx_events_item
                ON interaction_events(item_id, event_type);
            """
        )
        self._connection.commit()

    def record_event(self, user_id: str, item_id: str, event_type: str) -> dict[str, Any]:
        if not user_id.strip() or not item_id.strip():
            raise ValueError("user_id and item_id are required")
        if event_type not in EVENT_WEIGHTS:
            raise ValueError(f"event_type must be one of {sorted(EVENT_WEIGHTS)}")
        occurred_at = float(self._clock())
        cursor = self._connection.execute(
            """
            INSERT INTO interaction_events(user_id, item_id, event_type, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, item_id, event_type, occurred_at),
        )
        self._connection.commit()
        return {
            "event_id": cursor.lastrowid,
            "user_id": user_id,
            "item_id": item_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
        }

    def user_events(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT item_id, event_type, occurred_at
            FROM interaction_events
            WHERE user_id = ?
            ORDER BY occurred_at, id
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def seen_items(self, user_id: str) -> set[str]:
        rows = self._connection.execute(
            "SELECT DISTINCT item_id FROM interaction_events WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {row["item_id"] for row in rows}

    def item_popularity(self) -> dict[str, float]:
        rows = self._connection.execute(
            """
            SELECT item_id,
                SUM(CASE event_type
                    WHEN 'view' THEN 1.0
                    WHEN 'click' THEN 3.0
                    WHEN 'purchase' THEN 8.0
                    ELSE 0.0 END) AS score
            FROM interaction_events
            GROUP BY item_id
            """
        ).fetchall()
        return {row["item_id"]: float(row["score"]) for row in rows}

    def close(self) -> None:
        self._connection.close()
