import pytest

from app.engine import WorkflowStep, execute_workflow, validate_workflow


def test_dependency_order_and_outputs():
    steps = [
        WorkflowStep("double", "multiply", params={"values": [6, 2]}),
        WorkflowStep(
            "copy",
            "copy_dependency",
            depends_on=("double",),
            params={"dependency": "double"},
        ),
    ]
    result = execute_workflow(steps)
    assert result.status == "succeeded"
    assert [step.name for step in result.steps] == ["double", "copy"]
    assert result.steps[1].output == 12


def test_cycle_is_rejected():
    steps = [
        WorkflowStep("a", "sum", depends_on=("b",), params={"values": [1]}),
        WorkflowStep("b", "sum", depends_on=("a",), params={"values": [2]}),
    ]
    with pytest.raises(ValueError, match="cycle"):
        validate_workflow(steps)


def test_unknown_dependency_is_rejected():
    with pytest.raises(ValueError, match="unknown dependencies"):
        validate_workflow([WorkflowStep("a", "sum", depends_on=("missing",))])


def test_retry_then_success_and_skip_after_failure():
    calls = {"count": 0}

    def flaky(_: dict, __: dict) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary")
        return "done"

    steps = [
        WorkflowStep("unstable", "flaky"),
        WorkflowStep("after", "copy_dependency", depends_on=("unstable",), params={"dependency": "unstable"}),
    ]
    result = execute_workflow(steps, actions={**__import__("app.engine", fromlist=["builtin_actions"]).builtin_actions(), "flaky": flaky})
    assert result.status == "succeeded"
    assert result.steps[0].attempts == 2
    assert result.steps[1].output == "done"

    failed = execute_workflow(
        [WorkflowStep("broken", "sum", params={"values": []}), WorkflowStep("blocked", "sum", depends_on=("broken",), params={"values": [1]})],
        max_attempts=1,
    )
    assert failed.status == "failed"
    assert failed.steps[1].status == "skipped"
