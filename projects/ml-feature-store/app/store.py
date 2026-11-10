"""SQLite-backed feature groups with type validation and freshness metadata."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Callable
from time import time
from typing import Any


SUPPORTED_TYPES = {"integer", "number", "string", "boolean", "object"}


class FeatureStore:
    def __init__(
        self,
        db_path: str = ":memory:",
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._clock = clock or time
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS feature_groups (
                name TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                ttl_seconds INTEGER
            );
            CREATE TABLE IF NOT EXISTS feature_values (
                group_name TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                value_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (group_name, entity_id, feature_name),
                FOREIGN KEY (group_name) REFERENCES feature_groups(name) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_feature_entity
                ON feature_values(group_name, entity_id);
            """
        )
        self._connection.commit()

    def create_group(
        self,
        group_name: str,
        schema: dict[str, str],
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        if not group_name.strip():
            raise ValueError("group_name cannot be empty")
        if not schema:
            raise ValueError("Feature schema cannot be empty")
        if any(not name.strip() for name in schema):
            raise ValueError("Feature names cannot be empty")
        invalid_types = set(schema.values()) - SUPPORTED_TYPES
        if invalid_types:
            raise ValueError(f"Unsupported feature types: {sorted(invalid_types)}")
        if ttl_seconds is not None and ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")

        try:
            self._connection.execute(
                "INSERT INTO feature_groups(name, schema_json, ttl_seconds) VALUES (?, ?, ?)",
                (group_name, json.dumps(schema, sort_keys=True), ttl_seconds),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Feature group '{group_name}' already exists") from exc
        return {"group_name": group_name, "schema": schema, "ttl_seconds": ttl_seconds}

    def _get_group(self, group_name: str) -> sqlite3.Row:
        row = self._connection.execute(
            "SELECT name, schema_json, ttl_seconds FROM feature_groups WHERE name = ?",
            (group_name,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Feature group '{group_name}' not found")
        return row

    @staticmethod
    def _matches_type(value: Any, expected: str) -> bool:
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and (not isinstance(value, float) or math.isfinite(value))
            )
        if expected == "string":
            return isinstance(value, str)
        if expected == "boolean":
            return isinstance(value, bool)
        return isinstance(value, dict)

    def write(self, group_name: str, entity_id: str, features: dict[str, Any]) -> dict[str, Any]:
        group = self._get_group(group_name)
        if not entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        if not features:
            raise ValueError("At least one feature value is required")

        schema = json.loads(group["schema_json"])
        unknown = set(features) - set(schema)
        if unknown:
            raise ValueError(f"Undeclared features: {sorted(unknown)}")
        for name, value in features.items():
            if not self._matches_type(value, schema[name]):
                raise ValueError(f"Feature '{name}' must have type {schema[name]}")

        now = float(self._clock())
        rows = [
            (group_name, entity_id, name, json.dumps(value, allow_nan=False), now)
            for name, value in features.items()
        ]
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO feature_values(
                    group_name, entity_id, feature_name, value_json, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(group_name, entity_id, feature_name) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at,
                    version = feature_values.version + 1
                """,
                rows,
            )
        return {"group_name": group_name, "entity_id": entity_id, "written": list(features)}

    def get(self, group_name: str, entity_id: str) -> dict[str, Any]:
        group = self._get_group(group_name)
        rows = self._connection.execute(
            """
            SELECT feature_name, value_json, updated_at, version
            FROM feature_values
            WHERE group_name = ? AND entity_id = ?
            ORDER BY feature_name
            """,
            (group_name, entity_id),
        ).fetchall()
        now = float(self._clock())
        ttl = group["ttl_seconds"]
        features: dict[str, Any] = {}
        for row in rows:
            age = max(0.0, now - float(row["updated_at"]))
            stale = ttl is not None and age > ttl
            features[row["feature_name"]] = {
                "value": json.loads(row["value_json"]),
                "version": row["version"],
                "updated_at": row["updated_at"],
                "age_seconds": age,
                "stale": stale,
            }
        return {
            "group_name": group_name,
            "entity_id": entity_id,
            "features": features,
            "is_stale": any(item["stale"] for item in features.values()),
        }

    def get_many(self, group_name: str, entity_ids: list[str]) -> list[dict[str, Any]]:
        if len(entity_ids) > 500:
            raise ValueError("A batch can contain at most 500 entity IDs")
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("Batch entity IDs must be unique")
        self._get_group(group_name)
        return [self.get(group_name, entity_id) for entity_id in entity_ids]

    def close(self) -> None:
        self._connection.close()
