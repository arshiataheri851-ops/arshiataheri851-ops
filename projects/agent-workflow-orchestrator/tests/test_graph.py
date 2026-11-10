import pytest
from app.graph import WorkflowValidationError, validate_graph
from app.models import TaskSpec


def task(task_id, dependencies=None):
    return TaskSpec(task_id=task_id, role="planner", description="test",
                    depends_on=dependencies or [])


def test_valid_dag_passes():
    validate_graph([task("a"), task("b", ["a"]), task("c", ["a", "b"])])


def test_cycle_is_rejected():
    with pytest.raises(WorkflowValidationError, match="cycle"):
        validate_graph([task("a", ["b"]), task("b", ["a"])])


def test_unknown_dependency_is_rejected():
    with pytest.raises(WorkflowValidationError, match="unknown dependencies"):
        validate_graph([task("a", ["missing"])])


def test_duplicate_ids_are_rejected():
    with pytest.raises(WorkflowValidationError, match="unique"):
        validate_graph([task("a"), task("a")])
