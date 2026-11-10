"""FastAPI interface for the workflow orchestration engine."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.engine import WorkflowStep, execute_workflow, validate_workflow

app = FastAPI(
    title="Workflow Orchestration Engine",
    description="Validate and execute small dependency-aware workflows.",
    version="1.0.0",
)


class StepRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=40)
    depends_on: list[str] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    steps: list[StepRequest] = Field(min_length=1, max_length=100)
    max_attempts: int = Field(default=2, ge=1, le=10)


def to_steps(request: WorkflowRequest) -> list[WorkflowStep]:
    return [
        WorkflowStep(
            name=step.name,
            action=step.action,
            depends_on=tuple(step.depends_on),
            params=step.params,
        )
        for step in request.steps
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/workflows/validate")
def validate(request: WorkflowRequest) -> dict:
    try:
        order = validate_workflow(to_steps(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"valid": True, "execution_order": order}


@app.post("/workflows/execute")
def execute(request: WorkflowRequest) -> dict:
    try:
        result = execute_workflow(to_steps(request), max_attempts=request.max_attempts)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.to_dict()
