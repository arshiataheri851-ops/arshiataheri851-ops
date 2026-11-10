from datetime import datetime, timezone
from typing import Any
from .graph import validate_graph
from .models import (
    AuditEvent, TaskRecord, TaskSpec, TaskStatus, WorkflowCreate, WorkflowRecord,
)
from .store import WorkflowStore


class WorkflowNotFoundError(LookupError):
    pass


class InvalidTransitionError(ValueError):
    pass


class WorkflowEngine:
    """Deterministic workflow state machine; agent execution is an external adapter."""

    def __init__(self, store: WorkflowStore):
        self.store = store

    def _event(self, workflow_id: str, task_id: str | None, event_type: str,
               actor: str, details: dict[str, Any] | None = None) -> None:
        self.store.add_event(AuditEvent(
            workflow_id=workflow_id, task_id=task_id, event_type=event_type,
            actor=actor, details=details or {},
        ))

    def _load(self, workflow_id: str) -> WorkflowRecord:
        workflow = self.store.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    def _refresh(self, workflow: WorkflowRecord) -> None:
        changed = True
        while changed:
            changed = False
            for task_id, task in workflow.tasks.items():
                if task.status not in {TaskStatus.PENDING, TaskStatus.BLOCKED}:
                    continue
                dependencies = [workflow.tasks[item].status for item in task.spec.depends_on]
                if any(status in {TaskStatus.FAILED, TaskStatus.BLOCKED} for status in dependencies):
                    task.status = TaskStatus.BLOCKED
                    task.updated_at = datetime.now(timezone.utc)
                    changed = True
                elif all(status == TaskStatus.SUCCEEDED for status in dependencies):
                    task.status = (
                        TaskStatus.AWAITING_APPROVAL
                        if task.spec.requires_approval and not task.approved_by
                        else TaskStatus.READY
                    )
                    task.updated_at = datetime.now(timezone.utc)
                    changed = True

    def create(self, payload: WorkflowCreate, actor: str = "api") -> WorkflowRecord:
        validate_graph(payload.tasks)
        if self.store.get(payload.workflow_id) is not None:
            raise InvalidTransitionError("workflow_id already exists")
        tasks = {spec.task_id: TaskRecord(spec=spec) for spec in payload.tasks}
        workflow = WorkflowRecord(
            workflow_id=payload.workflow_id, title=payload.title,
            metadata=payload.metadata, tasks=tasks,
        )
        self._refresh(workflow)
        self.store.save(workflow)
        self._event(payload.workflow_id, None, "workflow_created", actor,
                    {"task_count": len(tasks)})
        for task_id, task in workflow.tasks.items():
            if task.status == TaskStatus.READY:
                self._event(payload.workflow_id, task_id, "task_ready", "engine")
            elif task.status == TaskStatus.AWAITING_APPROVAL:
                self._event(payload.workflow_id, task_id, "approval_requested", "engine")
        return workflow

    def get(self, workflow_id: str) -> WorkflowRecord:
        return self._load(workflow_id)

    def approve(self, workflow_id: str, task_id: str, actor: str) -> WorkflowRecord:
        workflow = self._load(workflow_id)
        task = workflow.tasks.get(task_id)
        if task is None:
            raise WorkflowNotFoundError(task_id)
        if task.status != TaskStatus.AWAITING_APPROVAL:
            raise InvalidTransitionError("task is not waiting for approval")
        task.approved_by = actor
        task.status = TaskStatus.READY
        task.updated_at = datetime.now(timezone.utc)
        workflow.updated_at = task.updated_at
        self.store.save(workflow)
        self._event(workflow_id, task_id, "approval_granted", actor)
        self._event(workflow_id, task_id, "task_ready", "engine")
        return workflow

    def claim(self, workflow_id: str, task_id: str, actor: str) -> WorkflowRecord:
        workflow = self._load(workflow_id)
        task = workflow.tasks.get(task_id)
        if task is None:
            raise WorkflowNotFoundError(task_id)
        if task.status != TaskStatus.READY:
            raise InvalidTransitionError("only ready tasks can be claimed")
        if task.attempts >= task.spec.max_attempts:
            raise InvalidTransitionError("task has exhausted its attempt budget")
        task.status = TaskStatus.RUNNING
        task.attempts += 1
        task.updated_at = datetime.now(timezone.utc)
        workflow.updated_at = task.updated_at
        self.store.save(workflow)
        self._event(workflow_id, task_id, "task_started", actor,
                    {"attempt": task.attempts})
        return workflow

    def complete(self, workflow_id: str, task_id: str, actor: str,
                 result: dict[str, Any]) -> WorkflowRecord:
        workflow = self._load(workflow_id)
        task = workflow.tasks.get(task_id)
        if task is None:
            raise WorkflowNotFoundError(task_id)
        if task.status != TaskStatus.RUNNING:
            raise InvalidTransitionError("only running tasks can be completed")
        task.status = TaskStatus.SUCCEEDED
        task.result = result
        task.error = None
        task.updated_at = datetime.now(timezone.utc)
        workflow.updated_at = task.updated_at
        self._refresh(workflow)
        self.store.save(workflow)
        self._event(workflow_id, task_id, "task_succeeded", actor,
                    {"result_keys": sorted(result.keys())})
        for child_id, child in workflow.tasks.items():
            if child.status == TaskStatus.READY and task_id in child.spec.depends_on:
                self._event(workflow_id, child_id, "task_ready", "engine")
            elif child.status == TaskStatus.AWAITING_APPROVAL and task_id in child.spec.depends_on:
                self._event(workflow_id, child_id, "approval_requested", "engine")
        return workflow

    def fail(self, workflow_id: str, task_id: str, actor: str, error: str) -> WorkflowRecord:
        workflow = self._load(workflow_id)
        task = workflow.tasks.get(task_id)
        if task is None:
            raise WorkflowNotFoundError(task_id)
        if task.status != TaskStatus.RUNNING:
            raise InvalidTransitionError("only running tasks can fail")
        task.error = error
        task.status = (
            TaskStatus.READY if task.attempts < task.spec.max_attempts else TaskStatus.FAILED
        )
        task.updated_at = datetime.now(timezone.utc)
        workflow.updated_at = task.updated_at
        self._refresh(workflow)
        self.store.save(workflow)
        self._event(workflow_id, task_id, "task_retry_scheduled" if task.status == TaskStatus.READY
                    else "task_failed", actor, {"error": error, "attempt": task.attempts})
        return workflow

    def audit(self, workflow_id: str) -> list[AuditEvent]:
        self._load(workflow_id)
        return self.store.events(workflow_id)
