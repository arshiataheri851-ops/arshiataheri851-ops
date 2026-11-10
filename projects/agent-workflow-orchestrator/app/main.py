from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import InvalidTransitionError, WorkflowEngine, WorkflowNotFoundError
from .models import TaskAction, WorkflowCreate
from .store import WorkflowStore

store = WorkflowStore("./data/workflows.sqlite3")
engine = WorkflowEngine(store)
app = FastAPI(
    title="Agent Workflow Orchestrator",
    version="1.0.0",
    description=(
        "A deterministic, auditable workflow state machine with dependency scheduling "
        "and human approval gates. Agent execution is delegated to external workers."
    ),
)


class ApprovalRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-workflow-orchestrator"}


@app.post("/v1/workflows", status_code=201)
def create_workflow(payload: WorkflowCreate):
    try:
        return engine.create(payload)
    except (ValueError, InvalidTransitionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    try:
        return engine.get(workflow_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow or task not found") from exc


@app.post("/v1/workflows/{workflow_id}/tasks/{task_id}/approve")
def approve_task(workflow_id: str, task_id: str, payload: ApprovalRequest):
    try:
        return engine.approve(workflow_id, task_id, payload.actor)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow or task not found") from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/workflows/{workflow_id}/tasks/{task_id}/claim")
def claim_task(workflow_id: str, task_id: str, payload: ApprovalRequest):
    try:
        return engine.claim(workflow_id, task_id, payload.actor)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow or task not found") from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/workflows/{workflow_id}/tasks/{task_id}/complete")
def complete_task(workflow_id: str, task_id: str, payload: TaskAction):
    try:
        return engine.complete(workflow_id, task_id, payload.actor, payload.result)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow or task not found") from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/workflows/{workflow_id}/tasks/{task_id}/fail")
def fail_task(workflow_id: str, task_id: str, payload: TaskAction):
    try:
        return engine.fail(
            workflow_id, task_id, payload.actor, payload.error or "unspecified error"
        )
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow or task not found") from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/workflows/{workflow_id}/audit")
def workflow_audit(workflow_id: str):
    try:
        return engine.audit(workflow_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workflow not found") from exc
