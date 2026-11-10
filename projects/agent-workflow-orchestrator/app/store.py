import json
import sqlite3
from pathlib import Path
from .models import AuditEvent, WorkflowRecord


class WorkflowStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    task_id TEXT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_workflow
                    ON audit_events(workflow_id, event_id);
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def save(self, workflow: WorkflowRecord) -> None:
        payload = workflow.model_dump_json()
        with self._connect() as db:
            db.execute(
                """INSERT INTO workflows(workflow_id,payload) VALUES(?,?)
                   ON CONFLICT(workflow_id) DO UPDATE SET payload=excluded.payload""",
                (workflow.workflow_id, payload),
            )

    def get(self, workflow_id: str) -> WorkflowRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT payload FROM workflows WHERE workflow_id=?", (workflow_id,)
            ).fetchone()
        return WorkflowRecord.model_validate_json(row["payload"]) if row else None

    def add_event(self, event: AuditEvent) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO audit_events
                   (workflow_id,task_id,event_type,actor,details,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (event.workflow_id, event.task_id, event.event_type, event.actor,
                 json.dumps(event.details, ensure_ascii=False), event.created_at.isoformat()),
            )

    def events(self, workflow_id: str) -> list[AuditEvent]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_events WHERE workflow_id=? ORDER BY event_id",
                (workflow_id,),
            ).fetchall()
        return [AuditEvent(
            event_id=row["event_id"], workflow_id=row["workflow_id"],
            task_id=row["task_id"], event_type=row["event_type"], actor=row["actor"],
            details=json.loads(row["details"]), created_at=row["created_at"],
        ) for row in rows]
