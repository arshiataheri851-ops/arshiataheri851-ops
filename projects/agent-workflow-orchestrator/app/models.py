from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskSpec(BaseModel):
    task_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    role: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    depends_on: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    max_attempts: int = Field(default=2, ge=1, le=10)


class WorkflowCreate(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    title: str = Field(min_length=1, max_length=200)
    tasks: list[TaskSpec] = Field(min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    spec: TaskSpec
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    approved_by: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowRecord(BaseModel):
    workflow_id: str
    title: str
    metadata: dict[str, Any]
    tasks: dict[str, TaskRecord]
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    event_id: int | None = None
    workflow_id: str
    task_id: str | None = None
    event_type: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class TaskAction(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=2000)
