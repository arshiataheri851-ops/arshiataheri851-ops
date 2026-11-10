import pytest
from app.engine import InvalidTransitionError, WorkflowEngine
from app.models import WorkflowCreate
from app.store import WorkflowStore


def make_engine(tmp_path):
    return WorkflowEngine(WorkflowStore(str(tmp_path / "engine.sqlite3")))


def sample_workflow():
    return WorkflowCreate(
        workflow_id="demo", title="Demo workflow",
        tasks=[
            {"task_id": "research", "role": "researcher", "description": "Gather sources"},
            {"task_id": "review", "role": "reviewer", "description": "Review findings",
             "depends_on": ["research"], "requires_approval": True},
            {"task_id": "write", "role": "writer", "description": "Write report",
             "depends_on": ["review"]},
        ],
    )


def test_dependency_and_approval_gates(tmp_path):
    engine = make_engine(tmp_path)
    workflow = engine.create(sample_workflow())
    assert workflow.tasks["research"].status == "ready"
    assert workflow.tasks["review"].status == "pending"
    engine.claim("demo", "research", "worker-1")
    workflow = engine.complete("demo", "research", "worker-1", {"sources": 3})
    assert workflow.tasks["review"].status == "awaiting_approval"
    with pytest.raises(InvalidTransitionError):
        engine.claim("demo", "review", "worker-2")
    workflow = engine.approve("demo", "review", "human-reviewer")
    assert workflow.tasks["review"].status == "ready"
    engine.claim("demo", "review", "worker-2")
    workflow = engine.complete("demo", "review", "worker-2", {"approved": True})
    assert workflow.tasks["write"].status == "ready"


def test_retry_budget_then_downstream_block(tmp_path):
    engine = make_engine(tmp_path)
    payload = WorkflowCreate(
        workflow_id="retry-demo", title="Retry",
        tasks=[
            {"task_id": "a", "role": "worker", "description": "A", "max_attempts": 2},
            {"task_id": "b", "role": "worker", "description": "B", "depends_on": ["a"]},
        ],
    )
    engine.create(payload)
    engine.claim("retry-demo", "a", "worker")
    workflow = engine.fail("retry-demo", "a", "worker", "temporary")
    assert workflow.tasks["a"].status == "ready"
    engine.claim("retry-demo", "a", "worker")
    workflow = engine.fail("retry-demo", "a", "worker", "permanent")
    assert workflow.tasks["a"].status == "failed"
    assert workflow.tasks["b"].status == "blocked"


def test_audit_trail_is_persisted(tmp_path):
    engine = make_engine(tmp_path)
    engine.create(sample_workflow(), actor="test-suite")
    engine.claim("demo", "research", "worker-a")
    events = engine.audit("demo")
    assert [event.event_type for event in events] == [
        "workflow_created", "task_ready", "task_started"
    ]
    assert events[-1].actor == "worker-a"
