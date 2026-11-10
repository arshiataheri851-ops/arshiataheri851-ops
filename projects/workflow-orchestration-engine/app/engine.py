"""DAG validation and deterministic workflow execution."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from math import prod
from typing import Any

Action = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    action: str
    depends_on: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepOutcome:
    name: str
    status: str
    attempts: int = 0
    output: Any = None
    error: str | None = None


@dataclass
class WorkflowOutcome:
    status: str
    steps: list[StepOutcome]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "steps": [asdict(step) for step in self.steps]}


def builtin_actions() -> dict[str, Action]:
    def sum_values(params: dict[str, Any], _: dict[str, Any]) -> int | float:
        values = params.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("'values' must be a non-empty list")
        return sum(values)

    def multiply_values(params: dict[str, Any], _: dict[str, Any]) -> int | float:
        values = params.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("'values' must be a non-empty list")
        return prod(values)

    def concatenate(params: dict[str, Any], _: dict[str, Any]) -> str:
        values = params.get("values")
        if not isinstance(values, list):
            raise ValueError("'values' must be a list")
        separator = params.get("separator", "")
        return str(separator).join(str(value) for value in values)

    def copy_dependency(params: dict[str, Any], dependencies: dict[str, Any]) -> Any:
        dependency = params.get("dependency")
        if dependency not in dependencies:
            raise ValueError("The requested dependency output is unavailable")
        return dependencies[dependency]

    return {
        "sum": sum_values,
        "multiply": multiply_values,
        "concat": concatenate,
        "copy_dependency": copy_dependency,
    }


def validate_workflow(
    steps: list[WorkflowStep], actions: dict[str, Action] | None = None
) -> list[str]:
    if not steps:
        raise ValueError("A workflow must contain at least one step")

    registry = actions or builtin_actions()
    names = [step.name for step in steps]
    if any(not name.strip() for name in names):
        raise ValueError("Step names cannot be empty")
    if len(names) != len(set(names)):
        raise ValueError("Step names must be unique")

    known = set(names)
    for step in steps:
        if step.action not in registry:
            raise ValueError(f"Unknown action '{step.action}' in step '{step.name}'")
        if step.name in step.depends_on:
            raise ValueError(f"Step '{step.name}' cannot depend on itself")
        missing = set(step.depends_on) - known
        if missing:
            raise ValueError(
                f"Step '{step.name}' has unknown dependencies: {sorted(missing)}"
            )

    indegree = {step.name: len(set(step.depends_on)) for step in steps}
    children: dict[str, list[str]] = {name: [] for name in names}
    for step in steps:
        for dependency in set(step.depends_on):
            children[dependency].append(step.name)

    ready = deque(name for name in names if indegree[name] == 0)
    order: list[str] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for child in children[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)

    if len(order) != len(steps):
        raise ValueError("Workflow contains a dependency cycle")
    return order


def execute_workflow(
    steps: list[WorkflowStep],
    max_attempts: int = 2,
    actions: dict[str, Action] | None = None,
) -> WorkflowOutcome:
    if max_attempts < 1 or max_attempts > 10:
        raise ValueError("max_attempts must be between 1 and 10")

    registry = actions or builtin_actions()
    order = validate_workflow(steps, registry)
    by_name = {step.name: step for step in steps}
    outcomes: dict[str, StepOutcome] = {}

    for name in order:
        step = by_name[name]
        failed_dependencies = [
            dep for dep in step.depends_on if outcomes[dep].status != "succeeded"
        ]
        if failed_dependencies:
            outcomes[name] = StepOutcome(
                name=name,
                status="skipped",
                error=f"Dependencies did not succeed: {failed_dependencies}",
            )
            continue

        dependency_outputs = {dep: outcomes[dep].output for dep in step.depends_on}
        outcome = StepOutcome(name=name, status="failed")
        for attempt in range(1, max_attempts + 1):
            outcome.attempts = attempt
            try:
                outcome.output = registry[step.action](step.params, dependency_outputs)
                outcome.status = "succeeded"
                outcome.error = None
                break
            # Actions are extension points; capture their failures per step.
            except Exception as exc:
                outcome.error = f"{type(exc).__name__}: {exc}"

        outcomes[name] = outcome

    ordered_outcomes = [outcomes[name] for name in order]
    workflow_status = (
        "failed" if any(item.status == "failed" for item in ordered_outcomes) else "succeeded"
    )
    return WorkflowOutcome(status=workflow_status, steps=ordered_outcomes)
