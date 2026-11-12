"""Durable webhook outbox, idempotency, signing, and retry lifecycle."""

from __future__ import annotations

import hashlib
import hmac
import json
import random
import sqlite3
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

Sender = Callable[[str, str, dict[str, str]], int]


@dataclass(frozen=True)
class Subscription:
    subscription_id: str
    event_type: str
    url: str
    secret: str


@dataclass
class Delivery:
    delivery_id: str
    event_id: str
    subscription_id: str
    event_type: str
    url: str
    body: str
    status: str = "queued"
    attempts: int = 0
    signature: str | None = None
    last_status_code: int | None = None
    last_error: str | None = None
    next_attempt_at: float = 0
    created_at: float = 0
    updated_at: float = 0


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def create_signature(secret: str, body: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{body}".encode()
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: str, timestamp: int, signature: str) -> bool:
    return hmac.compare_digest(create_signature(secret, body, timestamp), signature)


class WebhookDispatcher:
    """SQLite-backed transactional outbox.

    Delivery is at-least-once: a process crash after remote acceptance but before
    the local acknowledgement can cause a duplicate. Consumers should deduplicate
    using the stable X-Webhook-Delivery header.
    """

    def __init__(self, database_path: str = "data/relayforge.sqlite3") -> None:
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        if self.database_path != ":memory:":
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS subscriptions(
                    subscription_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    secret TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events(
                    event_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deliveries(
                    delivery_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL REFERENCES events(event_id),
                    subscription_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    signature TEXT,
                    last_status_code INTEGER,
                    last_error TEXT,
                    next_attempt_at REAL NOT NULL DEFAULT 0,
                    lease_until REAL NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_delivery_due
                ON deliveries(status,next_attempt_at,lease_until);
                CREATE INDEX IF NOT EXISTS idx_delivery_event
                ON deliveries(event_id);
                CREATE TABLE IF NOT EXISTS delivery_attempts(
                    attempt_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL REFERENCES deliveries(delivery_id),
                    attempt_number INTEGER NOT NULL,
                    started_at REAL NOT NULL,
                    finished_at REAL,
                    status_code INTEGER,
                    outcome TEXT NOT NULL,
                    error TEXT
                );
                """
            )
        if self.database_path != ":memory:":
            try:
                Path(self.database_path).chmod(0o600)
            except OSError:
                pass

    def register_subscription(
        self, subscription_id: str, event_type: str, url: str, secret: str
    ) -> Subscription:
        parsed = urlparse(url)
        if not subscription_id.strip() or not event_type.strip():
            raise ValueError("subscription_id and event_type are required")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Webhook URL must be absolute HTTPS without embedded credentials")
        if len(secret) < 16:
            raise ValueError("Secret must contain at least 16 characters")
        try:
            with self._connect() as db:
                db.execute(
                    "INSERT INTO subscriptions VALUES(?,?,?,?,?)",
                    (subscription_id, event_type, url, secret, time.time()),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Subscription already exists") from exc
        return Subscription(subscription_id, event_type, url, secret)

    def list_subscriptions(self) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT subscription_id,event_type,url FROM subscriptions ORDER BY subscription_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def remove_subscription(self, subscription_id: str) -> bool:
        with self._connect() as db:
            pending = db.execute(
                "SELECT 1 FROM deliveries WHERE subscription_id=? "
                "AND status IN ('queued','retry','sending') LIMIT 1",
                (subscription_id,),
            ).fetchone()
            if pending:
                raise ValueError("Subscription has pending deliveries; dispatch or resolve them first")
            cursor = db.execute(
                "DELETE FROM subscriptions WHERE subscription_id=?", (subscription_id,)
            )
            return cursor.rowcount > 0

    def was_event_seen(self, event_id: str) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone() is not None

    def enqueue_event(
        self, event_id: str, event_type: str, payload: dict, timestamp: int
    ) -> list[str]:
        if not event_id.strip() or not event_type.strip() or timestamp <= 0:
            raise ValueError("event_id, event_type, and a positive timestamp are required")
        body = canonical_json({
            "event_id": event_id, "event_type": event_type,
            "occurred_at": timestamp, "payload": payload,
        })
        fingerprint = hashlib.sha256(body.encode("utf-8")).hexdigest()
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT fingerprint FROM events WHERE event_id=?", (event_id,)
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ValueError("event_id was already used with a different event payload")
                rows = db.execute(
                    "SELECT delivery_id FROM deliveries WHERE event_id=? ORDER BY delivery_id",
                    (event_id,),
                ).fetchall()
                return [row["delivery_id"] for row in rows]
            db.execute(
                "INSERT INTO events(event_id,fingerprint,body,created_at) VALUES(?,?,?,?)",
                (event_id, fingerprint, body, now),
            )
            subscriptions = db.execute(
                "SELECT subscription_id,event_type,url FROM subscriptions WHERE event_type=?",
                (event_type,),
            ).fetchall()
            ids = []
            for sub in subscriptions:
                delivery_id = f"{event_id}:{sub['subscription_id']}"
                db.execute(
                    """
                    INSERT INTO deliveries(
                        delivery_id,event_id,subscription_id,event_type,url,body,status,
                        next_attempt_at,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,'queued',?,?,?)
                    """,
                    (delivery_id,event_id,sub["subscription_id"],event_type,sub["url"],body,now,now,now),
                )
                ids.append(delivery_id)
        return ids

    @staticmethod
    def _delivery(row: sqlite3.Row) -> Delivery:
        return Delivery(**{key: row[key] for key in Delivery.__dataclass_fields__})

    def get_delivery(self, delivery_id: str) -> Delivery | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)).fetchone()
        return self._delivery(row) if row else None

    def list_deliveries(
        self, delivery_status: str | None = None, limit: int = 100
    ) -> list[dict]:
        with self._connect() as db:
            if delivery_status:
                rows = db.execute(
                    "SELECT * FROM deliveries WHERE status=? ORDER BY created_at,delivery_id LIMIT ?",
                    (delivery_status, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM deliveries ORDER BY created_at,delivery_id LIMIT ?",
                    (limit,),
                ).fetchall()
        return [asdict(self._delivery(row)) for row in rows]

    def count_pending(self) -> int:
        with self._connect() as db:
            return int(db.execute(
                "SELECT COUNT(*) FROM deliveries WHERE status IN ('queued','retry','sending')"
            ).fetchone()[0])

    def dispatch(
        self,
        delivery_id: str,
        sender: Sender,
        timestamp: int,
        max_attempts: int = 5,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 300.0,
        lease_seconds: float = 60.0,
    ) -> Delivery:
        if timestamp <= 0:
            raise ValueError("timestamp must be positive")
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        now = time.time()
        attempt_id = str(uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
            ).fetchone()
            if row is None:
                raise KeyError("Delivery not found")
            delivery = self._delivery(row)
            if delivery.status in {"delivered", "dead_letter"}:
                return delivery
            if delivery.status == "retry" and delivery.next_attempt_at > now:
                return delivery
            if delivery.status == "sending" and row["lease_until"] > now:
                return delivery
            sub = db.execute(
                "SELECT secret FROM subscriptions WHERE subscription_id=?",
                (delivery.subscription_id,),
            ).fetchone()
            if sub is None:
                raise ValueError("The subscription no longer exists")
            attempt_number = delivery.attempts + 1
            signature = create_signature(sub["secret"], delivery.body, timestamp)
            cursor = db.execute(
                """
                UPDATE deliveries SET status='sending',attempts=?,signature=?,
                    lease_until=?,updated_at=?
                WHERE delivery_id=? AND status IN ('queued','retry','sending')
                """,
                (attempt_number, signature, now + lease_seconds, now, delivery_id),
            )
            if cursor.rowcount != 1:
                current = db.execute(
                    "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
                ).fetchone()
                return self._delivery(current)  # another worker won the claim
            db.execute(
                """
                INSERT INTO delivery_attempts(
                    attempt_id,delivery_id,attempt_number,started_at,outcome
                ) VALUES(?,?,?,?, 'sending')
                """,
                (attempt_id, delivery_id, attempt_number, now),
            )
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": delivery.event_type,
                "X-Webhook-Delivery": delivery.delivery_id,
                "X-Webhook-Timestamp": str(timestamp),
                "X-Webhook-Signature": signature,
            }

        status_code: int | None = None
        error: str | None = None
        try:
            status_code = int(sender(delivery.url, delivery.body, headers))
            if not 200 <= status_code < 300:
                error = f"Receiver returned HTTP {status_code}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:1000]

        finished = time.time()
        if error is None:
            new_status = "delivered"
            next_attempt = 0.0
        elif attempt_number >= max_attempts:
            new_status = "dead_letter"
            next_attempt = 0.0
        else:
            new_status = "retry"
            delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt_number - 1)))
            next_attempt = finished + delay * random.uniform(0.8, 1.2)

        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """
                UPDATE deliveries SET status=?,last_status_code=?,last_error=?,
                    next_attempt_at=?,lease_until=0,updated_at=?
                WHERE delivery_id=? AND status='sending'
                """,
                (new_status,status_code,error,next_attempt,finished,delivery_id),
            )
            db.execute(
                """
                UPDATE delivery_attempts SET finished_at=?,status_code=?,outcome=?,error=?
                WHERE attempt_id=?
                """,
                (finished,status_code,new_status,error,attempt_id),
            )
        return self.get_delivery(delivery_id)

    def dispatch_due(
        self, sender: Sender, max_attempts: int = 5, limit: int = 50,
        base_delay_seconds: float = 2.0,
    ) -> list[Delivery]:
        now = time.time()
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT delivery_id FROM deliveries
                WHERE (status IN ('queued','retry') AND next_attempt_at<=?)
                   OR (status='sending' AND lease_until<=?)
                ORDER BY created_at,delivery_id LIMIT ?
                """,
                (now, now, limit),
            ).fetchall()
        results = []
        for row in rows:
            results.append(
                self.dispatch(
                    row["delivery_id"], sender, int(time.time()), max_attempts,
                    base_delay_seconds=base_delay_seconds,
                )
            )
        return results

    def count_deliveries(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0])
